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

**Implemented (Phase 4):**
- Backend (pytest, **239 tests in total**, run 2026-11-24, exit code 0): `test_nlp_units.py` (46: placeholders incl. "Everything", sentence splitting, VADER labels and thresholds, wildcard / whole-word / exclusion matching, one sentence with several aspects, language normalisation and detection, non-English / no-text / detected-language statuses, the neutral-sentence box rule in each box, interval arithmetic against hand calculations); `test_analysis_api.py` (13: automatic analysis on import, stored provenance, idempotent re-run, pending vs all, no empty run after a duplicate-only import, run history, changed review re-scored, engine change forces a full re-run, **failed run rolls back and is recorded**, failure after import does not fail the import, CHECK constraint on `analysis_status`); `test_analytics_api.py` (28: every analytics endpoint asserted against the hand-calculated fixture in `backend/tests/fixtures/`, including overlapping vs separated intervals, low-sample flags, Monday-based weekly buckets with empty weeks kept, incomplete periods excluded via `as_of`, `insufficient_data` paths, monthly buckets, filter validation, synthetic data excluded by default).
- Frontend (Vitest, **32 tests in total**): `AnalysisCard` (counts and honesty notes shown, button disabled when nothing is waiting, run sends the chosen scope and refreshes, error with retry).
- Manual browser run (2026-11-24, built-in browser): Settings → Load demo data analysed 465 reviews automatically (450 analysed, 15 non-English); **Re-analyse all reviews** ran and the card showed the new run in local time. Live API checks on the demo data returned in about 0.2 s per call.
- **Not covered, not claimed:** accuracy of VADER and of the aspect lexicon (needs the human-labelled sample, Phase 7); recall of keyword matching; behaviour on the real dataset; PostgreSQL.

**Implemented (Phase 5):**
- Backend (pytest, **268 tests in total**, run 2026-11-24, all passing): `test_reviews_api.py` (29 new) covers the review list and detail endpoints (filters, search, sorting, paging, validation errors, evidence in the detail) and exclusion of deactivated properties from analytics.
- Frontend (Vitest, **79 tests in total**, 47 new): URL filter parsing and serialisation (round trip, malformed values, defaults omitted, API parameter names, inverted dates); explorer parameters; chart components (KPI tile with n / missing / low-sample, dataset banner for each scope, sentiment bar, rating distribution, interval chart, line chart gaps / hollow points / table); filter bar (writes to the URL, reset, inverted dates explained); Overview (live values, URL filters sent to the API, empty state, error with working retry, no request while dates are invalid); Comparison (winner named only when ranked, no winner when not significant, insufficient data, low-sample aspect cells); Reviews explorer (filters sent to the API, sentiment filter through the URL and back to page 1, paging, no-match state, inverted rating range).
- Gates: `ruff check` and `ruff format --check`, `tsc --noEmit`, `eslint` clean; `next build` succeeds with all new routes.
- Manual browser run (built-in browser, 465-review demo data, 2026-11-24): Overview, aspect drill-down to real sentences, trend chart, Comparison, property filter chips writing to the URL, Reviews search and sentiment filters, the review drawer with evidence, and a property detail page.
- **Not covered, not claimed:** automated browser (Playwright) tests; keyboard-only and screen-reader audit; visual regression; the new pages at 375 px width (responsive classes are used but were not checked in this phase).

**Implemented (Phase 6):**
- Backend (pytest, **316 tests in total**, run 2026-11-24, exit code 0): `test_insights.py` (48 new). Insight rules are checked on small datasets built directly in the database and worked out on paper (`insight_helpers.py`): recurring complaint, strength and opportunity thresholds; aspects below the mention floor produce nothing; a property-specific issue appears only when the interval separates and the false-positive guard holds; a rising trend appears and a flat one does not. Integrity checks: every cited review exists, `supporting_review_count` equals the Reviews explorer total for the stored filter, evidence is in scope, genuine / synthetic / mixed scopes stay separate, regeneration replaces and is deterministic, a deactivated property is ignored, an empty database yields nothing, a failed generation keeps the old insights, and the `stale` flag turns on after the data changes. Grounding: the validator rejects a cited review outside the evidence set, a number not derivable from the metrics and missing fields, and a deliberately ungrounded candidate is rejected and counted rather than stored. List filters, paging, 422 on bad input and 404 `INSIGHT_NOT_FOUND`. A mutation check (weakening a rule) made the tests fail, so they can fail.
- Migration `b7c1e5a90d42`: upgrade, downgrade and upgrade again, and `alembic check` clean.
- Frontend (Vitest, **94 tests in total**, 15 new): insight list rendering (type, strength, suggested action, link to exactly the supporting reviews), example sentences expand and collapse with a link to each full review, synthetic data labelled, stale warning shown only when stale and Regenerate sends the right scope, first-time and "nothing met the rules" empty states, no-reviews state without a Generate button, filters sent to the API and cleared through the URL, error state; URL parameter parsing and evidence links; `FilterBar` hides the date range when asked; navigation disabled-entry rendering.
- Gates: `ruff check` and `ruff format --check`, `tsc --noEmit`, `eslint` clean; `next build` succeeds with the `/insights` route.
- Manual browser run (built-in browser, 465-review demo data, synthetic scope): the page listed 15 insights with the synthetic label; expanding examples showed the verbatim sentences; "See all 20 reviews" opened the explorer with exactly 20 reviews; the type filter narrowed 15 to 6 strengths; Regenerate made a POST, showed a toast and refreshed the list; genuine scope showed the "no genuine reviews" explanation; the Overview teaser showed the top three with a link.
- **Not covered, not claimed:** that the insights are useful or correct for real hotels (needs the real dataset and human review); trend insights on real data (none fire on the demo data); an LLM adapter (not built); automated browser (Playwright) tests; keyboard and screen-reader audit; the page at 375 px width.

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

A small fixture (`backend/tests/fixtures/validation_reviews.csv`, 21 invented reviews over 3 test properties
and several weeks; the plan said ~20 over 4 properties) with expected values worked out by hand in
`backend/tests/fixtures/EXPECTED_RESULTS.md`: review counts, average rating, rating distribution, sentiment
shares, aspect mention counts and splits, per-property intervals and ranking, weekly series and trend changes. Tests
assert API output equals these values. (A missing rating is not in the fixture; it has its own test,
`test_reviews_without_a_rating_are_counted_as_missing_not_as_zero`.)

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
