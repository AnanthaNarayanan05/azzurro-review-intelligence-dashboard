# API Specification

Status: Phases 2–4 implemented (health, properties, imports, demo data, analysis runs, analytics). Reviews and
insights are still the agreed design. The live, authoritative contract is the generated OpenAPI documentation at `/docs`
(Swagger UI) and `/openapi.json`; this file explains intent and behaviour.

## Conventions

- Base path: `/api`. JSON everywhere except file upload (`multipart/form-data`).
- **List responses:** `{ "data": [...], "meta": { "page": 1, "page_size": 25, "total": 1234 } }`
- **Single responses:** `{ "data": {...} }`
- **Metric responses** always include sample sizes, e.g. `{ "value": 8.4, "n": 312, "missing": 5, "low_sample": false }`.
- **Errors:** `{ "error": { "code": "VALIDATION_ERROR", "message": "Human readable", "details": [...] } }`
  - 400 malformed request · 404 not found · 409 conflict (e.g. duplicate property) · 413 file too large ·
    415 unsupported file type · 422 validation error · 500 generic (no stack traces or internals exposed).
- **Common analytics filters:** `property_ids` (comma-separated), `date_from`, `date_to` (ISO dates).
- Dates ISO-8601; ratings on a 0–10 scale.

**Implemented so far:** `GET /api/health` (Phase 2); properties, imports and demo-data endpoints (Phase 3); analysis
and analytics endpoints (Phase 4). Sections
marked *Design only* are not implemented yet.

## System
| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | **Implemented.** Returns `{data: {status, version, environment, database, database_backend, sentiment_engine, llm_enabled}}`; HTTP 200 when healthy, 503 with `status: "degraded"` when the database is unreachable |

## Properties (implemented, Phase 3)
| Method | Path | Description |
|---|---|---|
| GET | `/api/properties` | List properties with `review_count` (genuine reviews only), `synthetic_review_count` and aliases |
| GET | `/api/properties/{id}` | Property detail with aliases |
| POST | `/api/properties` | Create `{ name, code?, location? }`. `code` is derived from the name if omitted. 409 if name or code exists |
| PATCH | `/api/properties/{id}` | Update `name`, `location`, `is_active` |
| POST | `/api/properties/{id}/aliases` | Add a source-name alias `{ alias }` (stored lower-cased, whitespace-collapsed). 409 if another property already uses it |
| DELETE | `/api/properties/{id}/aliases/{alias_id}` | Remove an alias (204) |

Property names are data. Nothing in the code refers to a specific hotel.

## Imports (implemented, Phase 3)

The import is a two-step flow so that nothing is written until the user has seen what will happen.

| Method | Path | Description |
|---|---|---|
| GET | `/api/imports/fields` | The importable fields (key, label, description, `required`: `always` / `one_of` / `no`) |
| POST | `/api/imports/preview` | Multipart `file`. Validates type, content and size, stores the upload privately, creates a `previewed` batch and returns `import_id`, filename, `source_type`, `total_rows`, `columns`, `sheets` / `sheet` (XLSX), `encoding`, `delimiter`, first rows, `suggested_mapping`, `property_values` and `already_imported_as` (id of an earlier import of the identical file, else null) |
| GET | `/api/imports/{id}/preview?sheet=` | Re-read a previewed XLSX with another worksheet selected |
| GET | `/api/imports/{id}/property-values?column=&sheet=` | Distinct values of a chosen column with counts and the suggested property (`alias`, `name`, `code` or `similar` match) |
| POST | `/api/imports/{id}/commit` | Body `{ column_mapping, property_mapping, fixed_property_id, rating_scale_max, date_format, source_name, is_synthetic, sheet, remember_aliases }`. Validates and writes in **one transaction**. Returns the import report. A failure rolls everything back, marks the batch `failed` and deletes the stored file |
| GET | `/api/imports` | History (paginated, newest first; abandoned previews are hidden unless filtered) |
| GET | `/api/imports/{id}` | Import report: counts, grouped issue summary |
| GET | `/api/imports/{id}/issues` | Paginated row issues; filters `outcome`, `code`; `page_size` ≤ 100 |
| DELETE | `/api/imports/{id}` | Undo: removes the batch, its reviews and issues. Returns `{ removed_reviews }` |

Report counts always reconcile: `total_rows = imported_rows + updated_rows + duplicate_rows + rejected_rows`.
`updated_rows` counts existing reviews (same source and external review ID) whose content changed and were updated in
place. `warning_count` is the number of imported rows that carry a warning.

Importable fields: `external_review_id, property, review_date, rating, title, positive_text, negative_text,
body_text, language, traveller_type, reviewer_country, room_type, stay_nights, source_url`. Guest names are never
importable. Required: `review_date`, a property (a `property` column **or** `fixed_property_id`), and at least one of
rating / text fields.

Dates: ISO, textual (`14 March 2026`), or day/month/year vs month/day/year as chosen with `date_format`
(`auto`, `iso`, `dmy`, `mdy`). In `auto` mode an ambiguous date such as `03/04/2026` is rejected rather than
guessed. Dates in the future or before 1996 are rejected. Ratings are converted to 0–10 using `rating_scale_max`
(comma decimals accepted); the original value is stored in `rating_raw`.

Row issue codes: rejected – `MISSING_DATE, INVALID_DATE, AMBIGUOUS_DATE, FUTURE_DATE, INVALID_RATING,
RATING_OUT_OF_RANGE, EMPTY_REVIEW, TEXT_TOO_LONG, MISSING_PROPERTY, UNKNOWN_PROPERTY`; duplicate –
`DUPLICATE_EXTERNAL_ID, DUPLICATE_CONTENT, DUPLICATE_IN_FILE`; warning – `REVIEW_UPDATED, MISSING_RATING,
INVALID_LANGUAGE, INVALID_STAY_NIGHTS, INVALID_URL`.

Import error codes (HTTP status): `EMPTY_FILE`, `NO_HEADER`, `NO_DATA_ROWS`, `UNREADABLE_FILE`, `UNKNOWN_SHEET`,
`UNKNOWN_COLUMN` and `INVALID_MAPPING` (422); `UNSUPPORTED_FILE_TYPE` and `FILE_CONTENT_MISMATCH` (415);
`FILE_TOO_LARGE` and `TOO_MANY_ROWS` (413); `IMPORT_NOT_FOUND` (404); `IMPORT_NOT_PENDING` and `IMPORT_IN_PROGRESS`
(409); `UPLOAD_EXPIRED` (410, the stored preview was purged after 24 hours); `IMPORT_FAILED` (500, rolled back).
Property error codes: `PROPERTY_NOT_FOUND`, `ALIAS_NOT_FOUND` (404); `PROPERTY_EXISTS`, `ALIAS_EXISTS` (409).

## Demo data (implemented, Phase 3)
| Method | Path | Description |
|---|---|---|
| GET | `/api/demo` | `{ loaded, synthetic_review_count, import_ids, notice }` |
| POST | `/api/demo/load` | Generates the deterministic synthetic dataset and loads it through the normal import pipeline (201). 409 `DEMO_ALREADY_LOADED` if present |
| DELETE | `/api/demo` | Removes every synthetic review and its import batch. Genuine reviews and properties are untouched |

Synthetic reviews always have `source = synthetic-demo` and `is_synthetic = true`; they can never be labelled as
coming from Booking.com.

## Reviews (implemented, Phase 5)

List responses are `{ "data": [...], "meta": { "page", "page_size", "total" } }`. The endpoint shares the analytics
filters (`property_ids`, `date_from`, `date_to`, `data_scope`, default `genuine`), so a count in the explorer matches
the same count on the dashboard.

| Method | Path | Description |
|---|---|---|
| GET | `/api/reviews` | Extra params: `q` (max 200 characters; case-insensitive search of the liked, disliked, body and title text; `%` and `_` are matched literally), `rating_min`, `rating_max` (0-10; 422 `INVALID_FILTER` if min > max), `sentiment` (label of the overall review text), `aspect` (404 `ASPECT_NOT_FOUND` if unknown), `aspect_sentiment` (positive / neutral / negative; needs `aspect`, else 422 `INVALID_FILTER`; uses the same per-review stance as the aspect breakdown), `language`, `sort` = `newest` (default) / `oldest` / `rating_desc` / `rating_asc` (ties broken by id), `page`, `page_size` (1-100, default 25). Each item carries the review text, `analysis_status`, the overall `sentiment` and the review-level aspect stances |
| GET | `/api/reviews/{id}` | The same item plus the sentiment of each text segment and every aspect mention with its verbatim `evidence_text`. 404 `REVIEW_NOT_FOUND` |

**Deactivated properties** (`is_active = false`) are excluded from every analytics figure and from this list.
Two fields were added so the dashboard never hard-codes a threshold: `overview.min_sample`
(`MIN_SAMPLE_COMPARISON`) and `trends.min_sample` (`MIN_SAMPLE_TREND_WINDOW`).

## Analysis (implemented, Phase 4)

Sentiment and aspect results are computed by a *run* and stored; analytics read the stored results. A run is
triggered automatically after every import commit and demo load (only if reviews are waiting), or manually.

| Method | Path | Description |
|---|---|---|
| GET | `/api/analysis/status` | `{ engine, lexicon_version, total_reviews, analysed, no_text, non_english, pending, latest_run, notes }`. `notes` states the method's limits (VADER, English only, not evaluated) |
| POST | `/api/analysis/run` | Optional body `{ scope: "pending" \| "all" }` (default `pending`). Returns `{ run, processed, analysed, no_text, non_english, aspect_mentions }`. A different engine or lexicon version than the last run forces `all`. Runs in one transaction: on failure nothing changes, a `failed` run is recorded and the response is 500 `ANALYSIS_FAILED` |
| GET | `/api/analysis/runs` | Paginated run history, newest first (`triggered_by`, engine, lexicon version, status, counts) |

A failure *after an import* never fails the import: the reviews stay saved and are shown as "waiting".

## Analytics (implemented, Phase 4)

All endpoints are read-only and return `{ "data": ... }`. Shared filters: `property_ids` (comma-separated),
`date_from`, `date_to`, and `data_scope` = `genuine` (default) \| `synthetic` \| `all`. Invalid filters return
422 `INVALID_FILTER`. Every response carries a `dataset` block
(`scope`, `genuine_reviews`, `synthetic_reviews`, `mixed`, first/last review date) so the UI can label what it shows.
A measure is `{ value, n, missing, low_sample }`; with no data `value` is `null`, never 0.

| Method | Path | Description |
|---|---|---|
| GET | `/api/analytics/overview` | `reviews` (n, with_text_analysis); `rating` (measure + 10-bin `distribution`, last bin holds 9 and 10); `sentiment` (counts, shares over analysed reviews, `not_analysed: {no_text, non_english, pending}`); per-`properties` rating; `aspects.most_praised` / `most_criticised` (only aspects with at least `MIN_ASPECT_MENTIONS` reviews) |
| GET | `/api/analytics/comparison` | One row per property: rating with `ci_low`/`ci_high`, sentiment block, aspect rows. `rating_ranking`: `status` = `ranked` \| `difference_not_significant` \| `insufficient_data`; `best`/`worst` only when `ranked` |
| GET | `/api/analytics/properties/{id}` | Overview scoped to one property plus `top_praise` / `top_complaints`, each with verbatim `examples`. 404 `PROPERTY_NOT_FOUND` |
| GET | `/api/analytics/aspects` | Per aspect: `mentions` (reviews), positive/neutral/negative counts and shares, `mention_rate`, `low_sample`; plus `definition` text |
| GET | `/api/analytics/aspects/{key}/examples` | `sentiment` (default `negative`), `limit` (1-20): real sentences with `review_id`, `property_id`, `review_date`, `is_synthetic`, `evidence_text`, `matched_term`, `source_field`. 404 `ASPECT_NOT_FOUND` |
| GET | `/api/analytics/trends` | `metric` = `volume` \| `avg_rating` \| `sentiment_positive_share` \| `sentiment_negative_share` \| `aspect_negative_share` (needs `aspect`, else 422); `granularity` = `week` \| `month`; `window` (periods, default 4 weeks / 3 months); `as_of` (default today). Returns `series` (every period, empty ones with `n: 0`, `value: null`, plus `complete` and `low_sample`) and `change` |

`change.status` is `increase` \| `decrease` \| `no_significant_change` \| `insufficient_data` (a window has fewer
than `MIN_SAMPLE_TREND_WINDOW` observations) \| `descriptive` (volume only). It includes both windows with their
dates and `n`, both values, the difference and its 95% interval, and the practical threshold used. Method:
`docs/AI_ANALYTICS.md` section 6.

There is no separate `/sentiment` endpoint: sentiment distribution is part of `overview` and `comparison`.

## Insights (design only)
| Method | Path | Description |
|---|---|---|
| GET | `/api/insights` | Filters: `property_ids`, `insight_type`, `evidence_strength`; paginated |
| GET | `/api/insights/{id}` | Insight + linked properties + evidence reviews + metrics used |
| POST | `/api/insights/generate` | Regenerate insights from current analytics. Body `{ use_llm: bool }` (ignored if LLM disabled) |

## Limits
- Upload: `.csv`, `.xlsx` only (extension **and** content sniffing), max `MAX_UPLOAD_MB` (default 20 MB), max `MAX_IMPORT_ROWS`.
- `page_size` capped at 100; text search query capped at 200 characters.
