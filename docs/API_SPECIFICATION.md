# API Specification

Status: Proposed (Phase 1). The live, authoritative contract will be the generated OpenAPI docs at
`/docs` (Swagger UI) and `/openapi.json` once the backend exists.

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

## System
| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness + DB connectivity + configured sentiment engine + whether LLM is enabled |

## Properties
| Method | Path | Description |
|---|---|---|
| GET | `/api/properties` | List properties with review counts |
| GET | `/api/properties/{id}` | Property detail with aliases |
| POST | `/api/properties` | Create `{ name, code, location? }` |
| PATCH | `/api/properties/{id}` | Update name/location/active |
| POST | `/api/properties/{id}/aliases` | Add a source-name alias |
| DELETE | `/api/properties/{id}/aliases/{alias_id}` | Remove an alias |

## Imports
| Method | Path | Description |
|---|---|---|
| POST | `/api/imports/preview` | Upload file (`file`). Validates type/size/structure. Returns `import_id`, detected columns, first 20 rows, suggested column mapping, distinct property values with suggested property matches |
| POST | `/api/imports/{id}/commit` | Body `{ column_mapping, property_mapping, rating_scale_max, date_format? }`. Validates, imports, analyses. Returns import report |
| GET | `/api/imports` | Import history |
| GET | `/api/imports/{id}` | Import report summary (counts + grouped rejection reasons) |
| GET | `/api/imports/{id}/issues` | Paginated row-level issues (`outcome`, `code` filters) |
| DELETE | `/api/imports/{id}` | Remove an import and its reviews (undo) |

Internal fields available for mapping: `external_review_id, property, review_date, rating, title,
positive_text, negative_text, body_text, language, traveller_type, reviewer_country, room_type, stay_nights`.
Required: `property` (or a single fixed property chosen in the UI), `review_date`, and at least one of
rating / text fields.

## Reviews
| Method | Path | Description |
|---|---|---|
| GET | `/api/reviews` | Query params: `q`, `property_ids`, `date_from`, `date_to`, `rating_min`, `rating_max`, `sentiment`, `aspect`, `aspect_sentiment`, `language`, `sort` (`newest`/`oldest`/`rating_desc`/`rating_asc`), `page`, `page_size` (≤ 100) |
| GET | `/api/reviews/{id}` | Original text + sentiment per segment + aspect mentions with evidence |

## Analytics
| Method | Path | Description |
|---|---|---|
| GET | `/api/analytics/overview` | KPIs, sentiment distribution, rating distribution, per-property volume & rating, top positive/negative aspects |
| GET | `/api/analytics/comparison` | Per-property metric matrix incl. aspect performance, with low-sample flags and best/worst only where justified |
| GET | `/api/analytics/properties/{id}` | Overview scoped to a property + top praise/complaints |
| GET | `/api/analytics/sentiment` | Sentiment distribution, optionally `group_by=property|month` |
| GET | `/api/analytics/aspects` | Per-aspect mention counts and sentiment split; `aspect` for example evidence |
| GET | `/api/analytics/trends` | `metric` (`volume`/`avg_rating`/`sentiment`/`aspect_negative_share`), `granularity` (`month`/`quarter`), `aspect?`; returns series + detected changes (or `insufficient_data`) |

## Analysis
| Method | Path | Description |
|---|---|---|
| POST | `/api/analysis/run` | Re-run NLP over all (or filtered) reviews; returns `analysis_run_id` |
| GET | `/api/analysis/runs` | History of analysis runs |

## Insights
| Method | Path | Description |
|---|---|---|
| GET | `/api/insights` | Filters: `property_ids`, `insight_type`, `evidence_strength`; paginated |
| GET | `/api/insights/{id}` | Insight + linked properties + evidence reviews + metrics used |
| POST | `/api/insights/generate` | Regenerate insights from current analytics. Body `{ use_llm: bool }` (ignored if LLM disabled) |

## Limits
- Upload: `.csv`, `.xlsx` only (extension **and** content sniffing), max `MAX_UPLOAD_MB` (default 20 MB), max `MAX_IMPORT_ROWS`.
- `page_size` capped at 100; text search query capped at 200 characters.
