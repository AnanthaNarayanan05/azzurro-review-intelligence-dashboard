# Changelog

All notable changes, newest first. Dates are when the work was completed.

## Phase 4 - Analytics engine (2026-11-24)

### Added
- Text analysis: placeholder handling ("Nothing", "N/A"), rule-based sentence splitting, language normalisation
  and detection, VADER sentiment behind a `SentimentEngine` interface, and a JSON aspect lexicon (8 aspects) with
  exclusion phrases. Each aspect mention stores the verbatim sentence as evidence.
- Analysis runs: results are stored per run with the engine and lexicon version; runs happen automatically after
  every import or demo load and can be re-run (`pending` or `all`). A failed run changes nothing and is recorded.
- Analytics API: `overview`, `comparison`, `properties/{id}`, `aspects`, `aspects/{key}/examples`, `trends`.
  Sample sizes everywhere, `low_sample` flags, best/worst only when 95% intervals separate, trend changes only for
  complete periods with enough data, `data_scope` (genuine by default) so demo data never mixes in silently.
- Analysis API: `GET /api/analysis/status`, `POST /api/analysis/run`, `GET /api/analysis/runs`.
- Settings page: **Text analysis** card (status, counts, working re-run buttons).
- Migration `analysis_fields`: `reviews.analysis_status`, `reviews.analysed_run_id`.
- Hand-calculated validation fixture `backend/tests/fixtures/` (CSV + `EXPECTED_RESULTS.md`).
- Dependencies: `vaderSentiment`, `langdetect`.

### Changed
- A re-import that changes a review's content resets it so it is analysed again.
- `docs/AI_ANALYTICS.md` rewritten to describe what is implemented: JSON lexicon (not YAML), "Everything" is
  not a placeholder, the neutral-sentence box rule, Wald (not Wilson) intervals, week definition.

### Not done / not claimed
- Accuracy of the sentiment and aspect methods has **not** been evaluated (needs a human-labelled sample, Phase 7).
- No dashboard pages yet (Phase 5).

### Tests
- Backend 239 passed (88 new), frontend 32 passed (4 new); `ruff`, `tsc`, `eslint` clean.

## Phase 3 - Data ingestion (2026-11-24)

### Added
- Review import pipeline: safe CSV/XLSX parsing, column-mapping suggestions, row validation, de-duplication,
  in-place updates, import reports, undo, transactional writes.
- Properties API with aliases; fuzzy property suggestions the user confirms.
- Synthetic demo data generator (deterministic, labelled, loaded and removed through the normal pipeline).
- Frontend: **Data Import** (4-step wizard and import history) and **Settings** (properties, aliases, demo data) pages.
- Sample files `data/sample/synthetic_reviews_sample.csv` and `.xlsx`.
- Database migration `ingestion_fields`: `reviews.source_url`, `reviews.updated_at`, and
  `import_batches.updated_rows / import_options / stored_filename / error_message`.
- `CHANGELOG.md`; `PROJECT_PROGRESS.md` (the former `PROGRESS_LOG.md`, renamed).

### Decided
- No automated collection from Booking.com (terms prohibit it, no public reviews API). File import is the route.
  See `docs/REQUIREMENTS.md`.

### Tests
- Backend 151 passed, frontend 28 passed, `ruff`, `tsc`, `eslint` and `next build` clean.

## Phase 2 - Project foundation (2026-11-23)
- FastAPI backend with settings, error envelope, CORS and `/api/health`; 12-table schema and initial migration.
- Next.js frontend with app shell, navigation, typed API client and live service status.

## Phase 1 - Discovery and planning (2026-11-23)
- Blueprint, requirements, architecture, schema, API design, AI approach, roadmap, test plan, risk register.
