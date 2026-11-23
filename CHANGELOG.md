# Changelog

All notable changes, newest first. Dates are when the work was completed.

## Phase 8 - Deployment and handover (2026-11-24)

**Not deployed, by the owner's final decision:** a live demo was requested and then dropped; the deploy files below are optional and unused.

### Added (live-demo preparation)
- `render.yaml` (Render Blueprint for the API: free plan, Python 3.11.9, migrations then uvicorn, demo upload caps) and
  `docs/GO_LIVE.md` (Neon, Render, Vercel step by step, and how to reset or switch off the demo).

### Added
- **PostgreSQL support verified:** `psycopg[binary]` added to `requirements.txt`; `postgres://` / `postgresql://` URLs are
  completed to the psycopg driver; connections are health-checked before use (`pool_pre_ping`) because hosted databases
  drop idle connections.
- `TEST_DATABASE_URL` runs the whole test suite on an empty disposable PostgreSQL database; all 334 tests pass on both
  PostgreSQL and SQLite. `scripts.benchmark --database-url` measures PostgreSQL (0.45 s slowest endpoint at ~50,000 reviews).
- `docs/HANDOVER.md` (plain-language guide, demo script, what is and is not proven, likely questions), the hosting
  runbook with the candidate free plans' limits in `docs/DEPLOYMENT.md`, and screenshots of every page on synthetic data
  (`frontend/scripts/screenshots.mjs`, `docs/screenshots/`).

### Changed
- Two tests no longer assume SQLite (the health backend name; a label short enough to reach the CHECK constraint).

### Known issues recorded (see `docs/RISK_REGISTER.md` R37-R38)
- No login on a hosted copy; free API plans sleep and run one instance; a remote managed PostgreSQL has not been tried.

## Phase 7 - Testing and optimisation (2026-11-24)

### Added
- **Browser end-to-end tests** (`frontend/e2e`, Playwright driving the installed Chrome, `npm run e2e`): 9 tests cover the
  whole story on a throwaway API and database: empty start, wizard import of the synthetic sample with reconciled
  counts, matching Overview total with the synthetic label, filters, insight generation and its evidence link, layout at
  375 and 768 px on all seven pages, and an axe-core accessibility audit of all pages.
- **Performance benchmark** (`backend/scripts/benchmark.py`) and its documented results (NFR-3 met at ~50,000 reviews).
- **Model evaluation tooling** (`backend/app/analytics/evaluation.py`, `backend/scripts/evaluate_models.py`) with 14
  tests, and `docs/LABELLING_GUIDE.md`. **No accuracy has been measured**: it needs a human-labelled sample of real reviews.
- `backend/scripts/e2e_server.py`: starts the API on a fresh temporary database for the browser tests.

### Fixed (found by the new audits)
- The "destructive" badge text (recurring-complaint insights, failed imports) had colour contrast below WCAG AA; darkened.
- The aspect table's "Complaints" button had an accessible name that did not include its visible text; renamed.
- Property cards placed non-definition elements directly inside a definition list; restructured.

### Known issues recorded (see `docs/RISK_REGISTER.md` R33-R36)
- Accuracy unmeasured; real-data import not done (no data supplied); one browser and automated accessibility rules only;
  performance figures are for SQLite and repeated synthetic text; dev-only `npm audit` advisories (4 moderate) not force-fixed.

## Phase 6 - Insights (2026-11-24)

### Added
- **Insights engine** (`backend/app/services/insights`): deterministic rules over the stored analytics produce six
  insight types: recurring complaint, strength to preserve, emerging negative trend, property-specific issue,
  cross-property issue and opportunity (split opinion). Thresholds sit in one file and are stored with every insight.
- **Evidence:** every insight stores its full supporting-review count and up to 10 verbatim example sentences,
  linked to real reviews by foreign key. Its stored filter reproduces exactly those reviews in the Reviews explorer,
  and the explorer total equals the stored count.
- **Evidence strength** (strong / moderate / limited) from the number of supporting reviews, the months they span
  and the sample-size flag.
- **Template wording and an action catalogue** (`insight_actions.json`, one entry per aspect plus a default).
- **Grounding validator**, applied to every text including templates: rejects missing fields, cited reviews outside
  the evidence set and numbers not derivable from the stored metrics. Rejected drafts are not stored and are counted.
- **API:** `GET /api/insights`, `GET /api/insights/{id}`, `POST /api/insights/generate`.
- **Insights page** with type and evidence filters, working Generate / Regenerate button, an out-of-date warning,
  expandable example sentences that link to the full review, a "See all N reviews" link, paging and empty states.
  A **Top insights** teaser on the Overview. The Insights navigation entry is enabled.
- `insights.data_scope` column (migration `b7c1e5a90d42`): genuine, synthetic and mixed insights are generated,
  stored and replaced independently, and synthetic-data insights are labelled on every card.
- `FilterBar` can hide the date range (`showDates`), because each insight carries its own period.

### Changed
- `_aspect_rows` in the metrics module is now public (`aspect_rows`) so the insight rules reuse the same counting
  as the dashboard.
- The navigation test no longer relies on a real page being unbuilt; it adds a planned entry to prove the disabled
  rendering still works.

### Not done / not claimed
- **No LLM adapter.** It would need a paid provider and key, so it waits for the project owner's approval. All
  insights are `generation_method: template`, and the app works fully without one.
- Thresholds are starting points and are not validated; no multiple-testing correction.
- On the demo data no trend insight fires (windows need at least 30 mentions each).
- Accuracy of sentiment and aspects is still not evaluated (Phase 7).

### Tests
- Backend 316 passed (48 new), frontend 94 passed (15 new); `ruff`, `tsc`, `eslint` and `next build` clean.

## Phase 5 - Dashboard (2026-11-24)

### Added
- Pages on live data: **Overview**, **Properties** (list) and **property detail**, **Comparison**, **Reviews**
  explorer. Their navigation entries are now enabled.
- Global filters kept in the URL: property chips, date range, data scope (genuine / synthetic / all). A banner is
  shown whenever the data is not genuine-only. An inverted date range is explained and nothing is requested.
- Charts (hand-written SVG/CSS, each with a table view and hover detail): rating distribution, sentiment split,
  aspect split bars, rating intervals per property, trend line with hollow points for unfinished or thin periods.
- Trends panel with measure, aspect and week/month selectors and a plain-language change summary.
- Aspect drill-down to the real sentences behind each count.
- Reviews explorer: text search, sentiment, rating range, aspect and aspect stance, sort, paging, and a drawer
  showing segment scores and each aspect mention's evidence sentence.
- Backend: `GET /api/reviews` and `GET /api/reviews/{id}`; `min_sample` on the overview and trends responses.

### Changed
- Deactivated properties are now excluded from every analytics figure and the review list.
- Charts are hand-written instead of using Recharts (fewer dependencies; recorded in `SYSTEM_ARCHITECTURE.md`).

### Not done / not claimed
- Insights (Phase 6). No automated browser tests, accessibility audit or 375 px check of the new pages yet (Phase 7).
- Sentiment and aspect accuracy are still not evaluated.

### Tests
- Backend 268 passed (29 new), frontend 79 passed (47 new); `ruff`, `tsc`, `eslint` and `next build` clean.

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
