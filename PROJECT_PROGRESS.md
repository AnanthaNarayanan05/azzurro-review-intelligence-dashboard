# Project Progress

## 2026-11-23 – Phase 1: Discovery & planning

**Completed**
- Inspected local project folder: completely empty, no Git repository, no existing code to preserve.
- Inspected remote `AnanthaNarayanan05/azzurro-review-intelligence-dashboard`: private, empty (no commits);
  authenticated GitHub account has admin permission.
- Initialised Git on branch `main`, set `origin` to the provided repository URL.
- Verified local toolchain: Git 2.55, GitHub CLI 2.100 (authenticated), Node 24.19 / npm 11.17, Python 3.11.9 / pip 24.0.
- Wrote Phase 1 blueprint: `docs/PROJECT_BLUEPRINT.md`, `REQUIREMENTS.md`, `SYSTEM_ARCHITECTURE.md`,
  `DATABASE_SCHEMA.md`, `API_SPECIFICATION.md`, `AI_ANALYTICS.md`, `DEVELOPMENT_ROADMAP.md`,
  `TESTING_PLAN.md`, `RISK_REGISTER.md`, `DEPLOYMENT.md`.
- Added `.gitignore` (secrets, dependencies, builds, local DBs, raw/processed/uploaded review data),
  `.env.example`, `README.md`, `data/README.md`, this log.

**Tests performed:** none (no code yet).

**Commits:** see `git log` – `chore: initialise repository hygiene`, `docs: add phase 1 technical blueprint`.

**Blockers / open questions**
- Real review dataset not yet supplied (format and columns unknown).
- Property names for the four hotels not yet known.
- Decision needed on optional LLM provider (paid) vs template-only insights.
- Whether hosted deployment is required, and whether it must be access-protected.
- Assessment deadline.

**Next steps:** on blueprint approval, start Phase 2 (backend and frontend foundation, health check).

## 2026-11-23 – Phase 2: Project foundation

**Completed**
- Backend (`backend/`): FastAPI app with environment-driven settings (`pydantic-settings`), SQLAlchemy 2.1
  session, consistent error envelope (internal errors logged, never returned), CORS for the frontend origin,
  `GET /api/health` with a live database probe (503 + `degraded` when the DB is unreachable).
- Database: ORM models for all 12 tables in `docs/DATABASE_SCHEMA.md` with PK/FK/UNIQUE/CHECK constraints and
  indexes; SQLite foreign keys enforced per connection; Alembic initial migration (`alembic check` clean).
  Renamed `analysis_runs.trigger` → `triggered_by` (SQL keyword); schema doc updated.
- Frontend (`frontend/`): Next.js 16.4 (App Router, Cache Components), Tailwind 4, shadcn/ui (Radix, Nova
  preset) with a restrained azure accent, TanStack Query, typed API client, responsive app shell (sidebar +
  mobile sheet), live service-status indicator and system-status card, 404 page, `/` → `/overview` redirect.
  Pages not built yet appear as disabled nav items labelled with their roadmap phase.
- Docs: `DEPLOYMENT.md` (verified local setup + troubleshooting), README quick start, architecture decisions
  9–10 and implementation status, API/roadmap/testing status. Frontend `.env.example` added.

**Tests performed**
- Backend `pytest`: **26 passed**. `ruff check`: clean.
- Frontend `vitest`: **15 passed**. `tsc --noEmit`, `eslint`, `next build`: clean.
- Manual (in-browser): overview at desktop and 375 px widths, mobile menu, backend stopped → "Analytics API
  unreachable" error state → backend restarted → "Try again" recovers; `/docs` Swagger UI loads; unknown route → 404 page.

**Issues found and fixed**
- Windows Application Control blocks SQLAlchemy's compiled extensions and pip's `.exe` launchers →
  SQLAlchemy reinstalled as pure Python (`DISABLE_SQLALCHEMY_CEXT=1`), tools run via `python -m` (documented).
- Hydration mismatch in the status card (Cache Components hydrate page segments after the header filled the
  query cache) → `useHydrated()` guard for data-driven components.
- `redirect()` in `app/page.tsx` blocked Next's instant-navigation validation → moved to `next.config.ts` redirects.
- Disabled nav items were focusable and popped tooltips when the mobile menu opened → made non-focusable text
  with a screen-reader explanation.
- Dependency conflicts: `@vitejs/plugin-react` (Babel 8 vs 7) dropped as unnecessary; `@types/node` raised to
  v24 to match the runtime. `npm audit`: 4 moderate findings in the shadcn CLI's dev-only tooling
  (`ts-morph` → `minimatch`); not shipped to the browser, CLI moved to devDependencies; the suggested
  `--force` fix would downgrade shadcn to 1.0, so not applied.

**Commits:** `2d33ef5 feat: add backend foundation with database models and health check`, then the
frontend/docs commit for this phase (see `git log`).

**Blockers / open questions** (unchanged): real dataset, the four property names, LLM provider decision,
deployment/access requirements, assessment deadline.

**Next steps:** Phase 3 – data ingestion (properties API, CSV/XLSX upload, preview, column and property mapping,
validation, duplicate detection, import reports, synthetic sample data, import UI).

## 2026-11-24 – Phase 3: Data ingestion

**Current state:** Phases 1–3 complete. Branch `main`. Latest commit before this phase: `6cea551`; the Phase 3
commit is the one that contains this entry (see `git log`). Next: Phase 4.

**Decision recorded:** no scraping of Booking.com. Its terms prohibit automated access without written permission
and there is no public reviews API. Reviews enter through CSV/XLSX import or clearly labelled synthetic data.
Details in `docs/REQUIREMENTS.md` ("Data collection feasibility").

**Completed**
- Backend ingestion (`backend/app/services/ingestion/`): safe parsing, mapping suggestions, row validation,
  de-duplication (in-file, by external ID, by content hash), in-place updates, transactional commit with rollback
  and file cleanup, undo, stale-preview purge.
- Properties API with aliases and fuzzy suggestions; demo-data service and API (deterministic synthetic generator,
  26 weeks, four profiles in `data/sample/demo_properties.json`).
- Frontend: Data Import wizard (upload → match columns → properties and formats → report), import history with
  details and undo, Settings (properties, aliases, demo data). Navigation entries enabled.
- Sample files `data/sample/synthetic_reviews_sample.csv/.xlsx` (465 synthetic rows).

**Files (main)**
- Backend: `app/api/routes/{properties,imports,demo}.py`, `app/services/{properties,demo,demo_data}.py`,
  `app/services/ingestion/*`, `app/schemas/{properties,imports}.py`, `scripts/generate_sample_files.py`,
  migration `20261123_ed37217dbf40_ingestion_fields.py`, tests `test_import_api.py`, `test_ingestion_units.py`.
- Frontend: `app/{import,settings}/page.tsx`, `components/import/*`, `components/settings/*`, `lib/import-wizard.ts`,
  `services/{imports,properties}.ts`, shadcn `ui` additions.

**Database changes:** migration adds `reviews.source_url`, `reviews.updated_at`, `import_batches.updated_rows`,
`import_options`, `stored_filename`, `error_message` (with server defaults). `alembic check` clean; upgrade on a
populated database is tested.

**API changes:** properties, imports and demo endpoints (see `docs/API_SPECIFICATION.md`).

**Tests run (2026-11-24):** backend `pytest` 151 passed; `ruff check` and `ruff format --check` clean; frontend
`vitest` 28 passed; `tsc --noEmit`, `eslint`, `next build` clean. Manual browser run of the whole flow (upload with
a duplicate, a bad date and a future date; create properties; import; report reconciles 6 = 3+0+1+2; undo; demo
load and removal; history). A stale hydration warning seen mid-session came from a dev server started before the
navigation change; it did not recur after a restart.

**Issues found and fixed:** migration lacked server defaults for NOT NULL columns; rollback test was ineffective
(rewritten with a patched clock after preview); stale alias list from the properties route (`populate_existing`);
SQLite row-id reuse in a test; long shell heredocs failing in this environment (files written with the editor tools).

**Known limitations / bugs**
- `reviews.extra` is not populated; unmapped columns are discarded on purpose.
- The "source" label on an import is the uploader's statement and is not verified.
- No automated browser (Playwright) test of the wizard yet; XLSX upload through the UI is covered only by backend tests.
- There is no endpoint to delete a property (aliases can be removed, properties can be deactivated).
- Language detection is not done yet (Phase 4).

**Decisions**
- Rating scale is chosen per import and converted to 0–10; the raw value is stored.
- Ambiguous dates are rejected unless the user picks a day/month order.
- Fuzzy property matches are suggestions only; the user confirms.
- A changed re-import of the same external review ID updates in place and is reported as an update.

**Open questions for the project owner (unchanged):** the real dataset (format, timing, which export), whether
hosting and login are required, LLM provider vs template-only insights, assessment deadline, and whether a
human-labelled sample can be supplied for evaluation.

**Next steps (Phase 4 – analytics engine)**
1. Inspect the current models for sentiment, aspect and analysis-run tables against the Phase 4 needs.
2. Pre-processing: placeholder detection ("Nothing", "N/A"), language detection, sentence splitting.
3. VADER sentiment per positive/negative/body segment with stored model name/version.
4. Rule-based aspect lexicon (config-driven) with evidence text and per-mention sentiment.
5. Analysis runs (recorded, re-runnable) and metrics endpoints with sample-size guards; hand-calculated fixture test.
6. Update docs, tests, changelog and this file; commit and push.

## 2026-11-24 – Phase 4: Analytics engine

**Current state:** Phases 1–4 complete. Branch `main`. Latest commit before this phase: `d2de3f4` (Phase 3); the
Phase 4 commit is the one that contains this entry (see `git log`). Next: Phase 5 (dashboard).

**Completed**
- NLP (`backend/app/analytics/nlp/`): placeholder handling, rule-based sentence splitting, language normalisation and
  detection (`langdetect`, fixed seed), VADER behind a `SentimentEngine` interface, JSON aspect lexicon v1.0.0
  (8 aspects, exclusion phrases, `*` suffix wildcard), per-review analysis returning segment/overall sentiment and
  aspect mentions with verbatim evidence.
- Analysis runs (`app/services/analysis.py`): results stored per run with engine and lexicon version; single
  transaction; failure rolls back and records a `failed` run (500 `ANALYSIS_FAILED`); automatic after import and
  demo load (failures there never fail the import); engine/lexicon change forces a full re-run.
- Metrics (`app/analytics/metrics.py`, `stats.py`) and API: overview, comparison, property detail, aspects,
  aspect examples, trends. Sample sizes on every number; `low_sample`; best/worst only if 95% intervals separate;
  trends use complete periods only (`as_of`), Monday-based weeks, equal-length windows, practical-size thresholds.
  `data_scope` defaults to `genuine` so synthetic data never mixes in silently.
- Frontend: Settings → **Text analysis** card (counts, method, honesty notes, working "Analyse waiting reviews" and
  "Re-analyse all reviews"); import/undo/demo flows refresh analysis and analytics queries.
- Docs updated: AI_ANALYTICS (rewritten to the implemented method), API_SPECIFICATION, DATABASE_SCHEMA,
  SYSTEM_ARCHITECTURE, TESTING_PLAN, DEVELOPMENT_ROADMAP, RISK_REGISTER (R22–R25), README (was stale at Phase 2), CHANGELOG.

**Files (main)**
- Backend: `app/analytics/{stats,metrics}.py`, `app/analytics/nlp/{preprocess,sentiment,aspects,review_analysis}.py`,
  `app/analytics/nlp/aspect_lexicon.json`, `app/services/analysis.py`, `app/schemas/analysis.py`,
  `app/api/routes/{analysis,analytics}.py`, migration `20261124_9968fa3529ac_analysis_fields.py`, tests
  `test_nlp_units.py`, `test_analysis_api.py`, `test_analytics_api.py`, fixtures `tests/fixtures/`.
- Frontend: `components/settings/analysis-card(.test).tsx`, `services/analysis.ts`, `types/api.ts`.

**Database changes:** migration `analysis_fields` adds `reviews.analysis_status` (CHECK, indexed) and
`reviews.analysed_run_id` (FK, SET NULL). `alembic check` clean; upgrade → downgrade → upgrade verified on the dev DB.

**API changes:** `GET /api/analysis/status`, `POST /api/analysis/run`, `GET /api/analysis/runs`;
`GET /api/analytics/{overview,comparison,properties/{id},aspects,aspects/{key}/examples,trends}`.
New dependencies in `backend/requirements.txt`: `vaderSentiment==3.3.2`, `langdetect==1.0.9`.

**Tests run (2026-11-24):** backend `pytest` **239 passed** (88 new; exit code 0); `ruff check` and
`ruff format --check` clean; frontend `vitest` **32 passed** (4 new); `tsc --noEmit` and `eslint` clean. Manual
browser run: demo load analysed 465 reviews (450 analysed, 15 non-English), manual re-run worked, live API calls
~0.2 s. `next build` was not re-run for this phase (no route or config changes beyond one added component).

**Issues found and fixed:** `f-string` backslash error in the lexicon regex builder; Alembic autogenerate misses
CHECK constraints (added by hand); test data with identical text was collapsed as duplicates by the importer (tests
now use distinct text); the API's naive UTC timestamps displayed in the wrong zone (card now parses them as UTC);
a nested `data.data` key in analytics responses (renamed `dataset`).

**Known limitations / bugs**
- **Sentiment and aspect accuracy are not evaluated.** VADER thresholds and the "neutral sentence takes the box's
  polarity" rule are judgement calls until Phase 7 (risks R22, R23).
- Keyword aspects miss implicit mentions; "view"/"connection" are ambiguous.
- Proportion intervals use the normal (Wald) approximation, not Wilson.
- Metrics are computed per request from stored rows (fine at hundreds–low thousands of reviews; not load-tested at
  100k).
- The dev database currently holds the 465 synthetic demo reviews (removable from Settings → Demo data).
- Windows paths: the project folder name contains an en dash; quote paths in shells.

**Decisions**
- Stored analysis (not per-request scoring); one transaction per run.
- A review counts once per aspect; label = sign of positive minus negative mentions.
- Non-English reviews are counted, not scored. "Everything" is not a placeholder.
- Weeks are Monday–Sunday on calendar dates, no time-zone conversion; only complete periods are compared.
- Best/worst property named only when 95% rating intervals do not overlap.

**Open questions for the project owner (unchanged):** the real dataset (format, timing, which export), whether
hosting and login are required, LLM provider vs template-only insights, assessment deadline, and whether a
human-labelled sample can be supplied for evaluation (needed for Phase 7).

**Next steps (Phase 5 – dashboard)**
1. Inspect `frontend/` navigation (`lib/navigation.ts`), the Overview page and the API client; add typed analytics
   services and TanStack Query hooks for the Phase 4 endpoints.
2. Global filter bar synced to the URL (property multi-select from `/api/properties`, date range, data scope with a
   clear "synthetic demo data" banner whenever scope ≠ genuine).
3. Overview page: KPI tiles (n, missing, low-sample), rating distribution, sentiment split with the not-analysed
   counts, per-property table, top praised/criticised aspects with example sentences.
4. Properties list and detail pages; Comparison page honouring `rating_ranking.status` (no winner unless `ranked`);
   trends charts (Recharts) with `insufficient_data` and incomplete-period states.
5. Review explorer needs a `GET /api/reviews` endpoint (not built yet; see API_SPECIFICATION "Reviews").
6. Component tests, browser verification of every control, docs + progress + commit + push.

## 2026-11-24 – Phase 5: Dashboard

**Branch:** `main`. **Commit:** see `git log` (`feat: build dashboard pages on live analytics - Phase 5`).

**Completed**
- Pages on live data, no static numbers: Overview, Properties (list and detail), Comparison, Reviews explorer.
  Navigation entries enabled (Insights stays disabled until Phase 6).
- Global filters in the URL (`properties`, `from`, `to`, `scope`; defaults omitted); a banner whenever the data is
  not genuine-only; an inverted date range is explained and no request is sent.
- Hand-written SVG/CSS charts (rating distribution, sentiment split, aspect split bars, rating intervals, trend line),
  each with a table view and written labels (meaning is never carried by colour alone). Colours are `--viz-*` CSS
  variables with light and dark values. Hollow points mark unfinished or low-sample periods; lines break at empty
  periods.
- Comparison names a best/worst property only when the API reports `ranked`; low-sample aspect cells are greyed.
- Aspect drill-down shows the real sentences; the Reviews explorer has search, sentiment, rating range, aspect and
  aspect-stance filters, sorting, paging and a drawer with segment scores and verbatim evidence.
- Loading, empty and error (with retry) states on every data view.

**Files:** backend `app/api/routes/reviews.py`, `app/schemas/reviews.py`, `tests/test_reviews_api.py`, changes in
`app/analytics/metrics.py`, `app/api/router.py`, `pyproject.toml`; frontend `app/{overview,comparison,properties,reviews}`,
`components/{charts,dashboard,filters,reviews,states}`, `hooks/use-{filters,analytics}.ts`, `lib/{filters,format,reviews-query}.ts`,
`services/analytics.ts`, `types/analytics.ts`, `test/fixtures.ts`, `app/globals.css`, `lib/navigation.ts`.

**Database changes:** none (no migration).

**API changes:** new `GET /api/reviews` and `GET /api/reviews/{id}`; `min_sample` added to the overview and trends
responses; deactivated properties are now excluded from all analytics (previously included).

**Tests run (2026-11-24):** backend `pytest` **268 passed** (29 new); `ruff check` and `ruff format --check` clean;
frontend `vitest` **79 passed** (47 new); `tsc --noEmit`, `eslint` and `next build` clean. Manual browser run on the
465-review demo data: Overview, aspect drill-down, trends, Comparison, URL filters, explorer search/filter, review
drawer, property detail.

**Issues found and fixed:** a state-in-effect lint error in the explorer search box; stale CSS variables in the dev
server (restart needed after `globals.css` edits); line-chart table omitted "low sample" for unfinished periods;
a hardcoded sample threshold in the UI replaced with the API's `min_sample`; Radix Select needs jsdom stubs in tests.

**Known limitations / bugs**
- No automated browser tests, no keyboard/screen-reader audit, no visual regression, and the new pages were not
  checked at 375 px width (Phase 7).
- The demo data repeats identical sentences, so aspect example lists show duplicates; this is a property of the
  synthetic data and was deliberately not de-duplicated.
- Sentiment/aspect accuracy is still not evaluated (Phase 7). Settings has no new controls this phase (existing
  property manager, analysis card and demo data remain).

**Decisions**
- Charts are hand-written (no Recharts): fewer dependencies for five simple chart types; docs updated.
- Property identity is shown by label, not colour; thresholds come from the API.
- Explorer counts use the same filter code as analytics so the numbers agree.

**Open questions for the project owner (unchanged):** the real dataset, hosting/login requirements, LLM provider vs
templates, assessment deadline, human-labelled sample for evaluation.

**Next steps (Phase 6 – insights)**
1. Design the insight model: finding, supporting review count, example review IDs, period, suggested action,
   evidence strength (from sample size and interval overlap), stored with provenance.
2. Rules engine over the Phase 4 analytics (aspect complaints above a threshold, significant trend changes,
   property gaps); an insight is produced only when its evidence passes the thresholds.
3. API `GET /api/insights` plus the Insights page linking each insight to its reviews in the explorer.
4. LLM wording stays off by default; if added later, it must be grounded and validated, and cost needs approval.
5. Tests, docs, progress, commit and push.
