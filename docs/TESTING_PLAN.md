# Testing Plan

Status: In progress. Results of each run are recorded in `PROJECT_PROGRESS.md`.

**Implemented (Phase 2):**
- Backend (pytest, 26 tests): health endpoint (ok and degraded), error envelope for 404/405/422/500 with no
  internal details leaked, CORS allow/deny, OpenAPI served, settings parsing, and database integrity
  (migration creates all tables, FK enforcement, rating/content CHECKs, unique codes/aliases/hashes, partial
  unique external ID, controlled vocabularies, cascade on import delete, RESTRICT on property delete).
- Frontend (Vitest + Testing Library, 15 tests): API client error mapping (envelope, network, non-JSON,
  unreadable body), health 503 handling, status indicator states, status card retry, navigation (active page,
  disabled unbuilt pages are not links).
- Manual browser check: desktop and 375 px mobile layouts, mobile menu, backend-down error state and recovery.

**Implemented (Phase 3):**
- Backend (pytest, **151 tests in total**, run 2026-11-24): parsing (CSV encodings, delimiters, BOM, XLSX sheets, empty and header-only files, renamed binaries, oversize and row-cap), mapping suggestions, date/rating parsing (ambiguous, future, comma decimals, scale conversion), row validation, in-file and cross-import de-duplication, in-place updates, property resolution and aliases, count reconciliation, transactional rollback and file cleanup on failure, stale-preview purge, undo, synthetic separation, demo load/clear, migration upgrade on a populated database, and every import/property/demo endpoint including error codes.
- Frontend (Vitest, **28 tests in total**): wizard logic (`mappingProblems`, `propertyProblems`, `buildCommitRequest`), mapping step (blocks until valid, same-file warning), report view (reconciliation sentence, synthetic and failed labels), plus the Phase 2 suites.
- Manual browser run (2026-11-24, built-in browser): upload a CSV with a duplicate, an unreadable date and a future date, create properties from file values, import, read the report (6 rows = 3 imported + 1 duplicate + 2 rejected), undo (reviews removed, properties kept), load demo data (465 reviews across four properties, counted as synthetic), remove it, view history. No application console errors on fresh loads.
- Not yet covered: automated browser (Playwright) test of the wizard, XLSX upload through the UI, accessibility audit.

## 1. Backend unit tests (pytest)

| Area | Examples |
|---|---|
| Parsing | CSV with BOM / `;` delimiter / non-UTF-8 encoding; XLSX with multiple sheets; empty file; header-only file |
| File validation | Wrong extension; renamed binary; oversize file → 413; too many rows |
| Column mapping | Suggestions for common header variants ("Review Date", "date", "Positive review", "Liked") |
| Row validation | Invalid date, future date, rating out of range, rating on /5 scale with scale set, missing text and rating, unknown property |
| Dedup | Same external ID twice in a file; same content hash vs existing DB row; re-upload of same file |
| Property resolution | Alias match, case/whitespace differences, unmapped value → rejection with reason |
| Pre-processing | Placeholder detection ("Nothing", "N/A"), sentence splitting |
| Sentiment | Known positive/negative/neutral sentences; segment scoring; no-text handling |
| Aspects | Each aspect's keywords trigger; word-boundary checks (e.g. "bedroom" vs "bed" rules); multi-word phrases; one count per review per aspect |
| Metrics | Averages ignore null ratings; percentages use documented denominators; sample-size flags |
| Trends | Insufficient data path; significant vs non-significant change |
| Insights | Rules fire on crafted data; every insight's evidence IDs exist; grounding validator rejects invented IDs/numbers |

## 2. Analytics validation (hand-calculated fixture)

A small fixture (`backend/tests/fixtures/validation_reviews.csv`, ~20 reviews over 4 test properties and
several months) with expected values worked out by hand in `backend/tests/fixtures/EXPECTED_RESULTS.md`:
review counts, average rating (with a null rating present), rating distribution, sentiment percentages,
aspect mention counts and splits, per-property comparison, monthly volumes. Tests assert API output equals
these values exactly.

## 3. API / integration tests

FastAPI `TestClient` against a temporary SQLite DB: every endpoint's happy path, 404s, 422 validation,
pagination bounds, filter combinations, error envelope shape, and that no stack traces are returned.

## 4. Database integrity

Foreign-key enforcement, cascade on import deletion, unique constraints (property name/code, alias,
content hash), check constraints (rating range, labels), `total = imported + rejected + duplicates`.

## 5. Model evaluation

On the human-labelled sample from the real dataset (see `AI_ANALYTICS.md` §7): accuracy, precision,
recall, F1 (per class + macro), confusion matrix; aspect detection precision/recall. Script:
`backend/scripts/evaluate_models.py`, output saved to `docs/` (aggregate metrics only, no private text).

## 6. Frontend tests

- **Component tests (Vitest + Testing Library):** KPI tile renders n / low-sample flag; filter bar updates URL;
  tables paginate; upload wizard step validation; empty and error states.
- **Manual checks:** responsive layouts at 375 / 768 / 1280 px; keyboard navigation; chart readability.

## 7. End-to-end (Playwright)

Upload synthetic CSV → preview → map columns/properties → import → report shows correct counts →
overview shows matching totals → filter reviews by property & aspect → open an insight and its evidence.

## 8. Test data policy

Only synthetic or hand-written fixtures are committed. Real review data stays in git-ignored folders.
