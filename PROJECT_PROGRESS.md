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


## 2026-11-24 – Phase 6: Insights

**Branch:** `main`. **Commit:** see `git log` (`feat: add evidence-based insights - Phase 6`).

**Completed**
- Rules engine (`backend/app/services/insights/rules.py`) over the stored analytics: recurring complaint (>= 10
  negative and >= 40 % negative), strength (>= 80 % positive), opportunity (negative and positive each >= 30 %, below
  the complaint line), property-specific issue (difference of proportions against the pooled other properties; interval
  excludes zero, >= 5 points, >= 30 per side), emerging negative trend (monthly change from the Phase 4 trend code; >= 60
  mentions) and cross-property issue. "Now" is the latest review in scope.
- Evidence selection and grading (`evidence.py`): full supporting count, up to 10 verbatim sentences (one per review,
  distinct wording preferred), strong / moderate / limited.
- Template wording plus per-aspect action catalogue (`wording.py`, `insight_actions.json`).
- Grounding validator (`grounding.py`) applied to every text, templates included; rejected drafts are counted, not stored.
- `generate.py`: builds first, then replaces the old insights of the scope in one transaction (a failure keeps the old ones).
- API: `GET /api/insights`, `GET /api/insights/{id}`, `POST /api/insights/generate`.
- Frontend: Insights page (type and evidence filters, Generate / Regenerate, out-of-date warning, expandable examples,
  "See all N reviews", paging, empty states), Overview "Top insights" teaser, navigation entry enabled, `FilterBar showDates`.

**Files:** backend `app/services/insights/{__init__,generate,rules,evidence,wording,grounding}.py`,
`app/services/insights/insight_actions.json`, `app/api/routes/insights.py`, `app/schemas/insights.py`,
`app/models/{base,insight}.py`, `app/analytics/metrics.py`, `app/api/router.py`,
`migrations/versions/20261124_b7c1e5a90d42_insight_data_scope.py`, `tests/{insight_helpers,test_insights}.py`; frontend
`app/insights/page.tsx`, `components/insights/*`, `components/filters/filter-bar.tsx`, `components/dashboard/overview-view.tsx`,
`hooks/use-insights.ts`, `services/insights.ts`, `lib/{insights,format,navigation}.ts`, `types/analytics.ts`, tests and
`test/insight-fixtures.ts`.

**Database changes:** `insights.data_scope` (VARCHAR(16), NOT NULL, default `genuine`, CHECK, index); migration
`b7c1e5a90d42` applied to the dev database and round-tripped.

**API changes:** the three insights endpoints above. `POST /api/insights/generate` takes `{data_scope}`; there is no
`use_llm` option.

**Tests run (2026-11-24):** backend `pytest` **316 passed** (48 new); `ruff check` and `ruff format --check` clean;
frontend `vitest` **94 passed** (15 new); `tsc --noEmit`, `eslint` and `next build` clean. Manual browser run on the demo
data (details in `docs/TESTING_PLAN.md`): 15 synthetic-labelled insights, examples, evidence link total matched (20),
filter, regenerate, genuine-scope empty state, Overview teaser.

**Issues found and fixed:** the first demo run produced 22 of 31 insights as "opportunity" noise, so the opportunity
floor went from 20 % to 30 % (recorded as an unvalidated judgement call, risk R30); "wi-fi" was lower-cased in titles
(`inline_name` keeps capitals when a name has them); the navigation test asserted that some page is unbuilt and broke
when the last one was built (it now supplies its own planned entry).

**Known limitations / bugs**
- **The LLM adapter is not built.** It needs the project owner's choice of provider and cost approval; insights are
  template-written.
- No trend insight fires on the demo data (windows need >= 30 mentions each); the generation result reports the skipped
  comparisons. A recurring complaint and a property-specific issue can both appear for the same property and aspect.
- Thresholds are unvalidated starting points; many rules are checked at once and no multiple-testing correction is applied.
- The demo data repeats identical sentences, so example lists show repeats.
- The dev database holds synthetic-scope insights generated during testing (derived data; regenerate to refresh).
- The dev server logs harmless Next.js HMR websocket errors in the browser console.
- Still no automated browser tests, accessibility audit or 375 px check (Phase 7).

**Decisions**
- Insights are generated on request per data scope and replace the previous set, so they are reproducible and never
  silently mixed across genuine and synthetic data.
- The same grounding validator guards templates, so a future LLM adapter has a ready test to pass.
- Insights are not date-filtered on the page: each carries its own period.

**Open questions for the project owner (unchanged):** the real dataset and its format, hosting and login requirements,
LLM provider and cost (only if wording by an LLM is wanted), assessment deadline, a human-labelled sample for evaluation.

**Next steps (Phase 7 – testing and optimisation)**
1. If the real dataset arrives, import it, regenerate insights on genuine scope and review each insight by hand.
2. Evaluate sentiment and aspect detection against a human-labelled sample; report accuracy only from that.
3. Playwright end-to-end test: import to dashboard to insight to evidence.
4. Responsive (375 px) and keyboard / screen-reader checks of every page; performance check on a larger dataset.
5. Revisit insight thresholds with real data and feedback; decide on multiple-testing handling.
6. Fix defects found; update docs, progress, commit and push.

## 2026-11-24 – Phase 7: Testing and optimisation

**Completed**
- **Playwright end-to-end suite** (`frontend/playwright.config.ts`, `frontend/e2e/workflow.spec.ts`, `frontend/e2e/checks.ts`):
  9 tests, all passing in about a minute. It starts its own API (`backend/scripts/e2e_server.py`: fresh temporary SQLite
  database plus migrations, port 8100) and a production build of the frontend (port 3100), and drives the installed Google
  Chrome (no browser download). Covers: empty start, wizard import of `data/sample/synthetic_reviews_sample.csv` (465 rows,
  counts reconcile, 0 rejected), Overview total equals imported and is labelled synthetic (genuine scope stays empty),
  property filter and no-match search, insight generation and evidence link (N claimed = N shown), no sideways scrolling at
  375 and 768 px on all seven pages, axe-core WCAG 2.1 A/AA audit of all pages, and "out of date" flag after removing the import.
- **Accessibility fixes** from the first axe run: badge text contrast (`components/ui/badge.tsx`), the "Complaints" button's
  accessible name (`aspects-section.tsx`), and definition-list structure on property cards (`properties-view.tsx`).
- **Performance benchmark** (`backend/scripts/benchmark.py`): 10,000 reviews: import 1.5 s, analysis 9.2 s, slowest endpoint
  0.16 s. 49,815 reviews: import 10.6 s, analysis 43.9 s, slowest endpoint 0.77 s (overview), insights generated in 9.5 s.
  NFR-3 (under 1 s to ~50k reviews; 10k import under 60 s) is met on SQLite. Caveats: in-process timings, repeated synthetic
  text, one laptop, no PostgreSQL.
- **Evaluation tooling** (`backend/app/analytics/evaluation.py`, `backend/scripts/evaluate_models.py`, `docs/LABELLING_GUIDE.md`,
  `backend/tests/test_evaluation.py`, 14 tests): export a stratified sample of genuine reviews, a person labels it, then
  evaluate reports accuracy, per-class precision / recall / F1, macro-F1, confusion matrix, per-aspect detection and stance accuracy.
  **It has not been run on real labels, so no accuracy figure exists or is claimed.**
- Docs: TESTING_PLAN (Phase 7 results), AI_ANALYTICS section 7 (status and method), ROADMAP, RISK_REGISTER (R33-R36),
  REQUIREMENTS (NFR-3 measured), README, CHANGELOG.

**Database changes:** none. **API changes:** none.

**Tests run (2026-11-24):** backend `pytest` **330 passed** (14 new), `ruff check` and `ruff format --check` clean;
frontend `vitest` **94 passed**, `tsc --noEmit` and `eslint` clean, `next build` succeeds (run by the e2e web server);
`npm run e2e` **9 passed**.

**Issues found and fixed:** the three accessibility defects above. The E2E test of the confirm dialog first failed only
because the dialog is an `alertdialog` (test selector, not an app bug). Removing an import leaves insights flagged
out of date, as designed (no bug).

**Known limitations / bugs**
- **No real dataset has been supplied**, so real-data import and the labelled-sample accuracy evaluation were not done.
  Accuracy of VADER and the aspect lexicon remains unknown (R33).
- The LLM adapter is still not built (needs provider and cost approval).
- Browser tests run in Chrome only; accessibility was checked with automated rules, not a screen reader or a full
  keyboard-only walk-through (R35).
- Overview and comparison endpoints take about 0.75 s at 50,000 reviews on SQLite (rating aggregation is done in Python):
  within the target but with little headroom (R34).
- `npm audit`: 4 moderate advisories, all in the `shadcn` CLI's dev dependency chain (0 in production dependencies); not force-fixed (R36).

**Decisions**
- E2E uses separate ports, a throwaway database and a production build so it can never touch development data or race the dev server.
- Evaluation never samples synthetic reviews and reports n/a (not 0) where there is nothing to divide by.
- The performance benchmark runs in-process against SQLite; PostgreSQL measurement is left to Phase 8.

**Open questions for the project owner (unchanged):** the real dataset and its format, hosting and login requirements,
LLM provider and cost (only if wording by an LLM is wanted), assessment deadline, and a human-labelled sample for evaluation.

**Next steps**
1. If real reviews arrive: import them, generate insights on genuine scope and review each by hand; run
   `scripts.evaluate_models export`, have a person label it (`docs/LABELLING_GUIDE.md`), run `evaluate`, and write the
   figures into `docs/AI_ANALYTICS.md` section 7; revise the neutral-sentence rule and lexicon if results are poor.
2. Phase 8 (deployment and handover): decide hosting (check current free-tier limits and cost with the owner first),
   PostgreSQL and re-run the test suite and benchmark against it, environment configuration, deploy, verify live, handover docs.
3. Before any public release: a manual keyboard and screen-reader pass.

## 2026-11-24 – Phase 8: Deployment and handover (prepared; live deployment waiting for the owner)

**Completed**
- **PostgreSQL verification.** Started a throwaway local PostgreSQL (`pgserver` package in a separate virtual environment) and
  ran the whole backend suite against it through the new `TEST_DATABASE_URL` setting in `tests/conftest.py` (database wiped
  per test, real migrations). All four migrations apply. First run: 328 of 330 passed; the two failures were test assumptions
  (health test asserted `sqlite`; a test used a label too long for its column so PostgreSQL raised a different error type).
  Fixed the tests. **Result: all 334 tests pass on PostgreSQL and on SQLite.**
- **Production configuration:** `postgres://` / `postgresql://` URLs are completed to `postgresql+psycopg://`
  (`normalise_database_url`, 4 tests); `psycopg[binary]==3.3.9` in `requirements.txt`; `pool_pre_ping=True` on the engine.
- **PostgreSQL benchmark** (`scripts.benchmark --database-url`): 10,000 reviews: import 2.5 s, analysis 11.3 s, slowest endpoint
  0.08 s. 49,815 reviews: import 13.2 s, analysis 60.2 s, slowest endpoint 0.45 s (text search), overview 0.42 s, insights 4.1 s.
  Local server, so no network latency.
- **Hosting research** (2026-11-24, vendor pages and third-party summaries; figures to be verified before choosing):
  Vercel Hobby is personal / non-commercial only; Render free web service sleeps after 15 minutes idle, 750 instance hours a
  month, reportedly 512 MB; Neon free has 1 GB storage and 100 compute-hours per project. Recorded in `docs/DEPLOYMENT.md`.
- **Docs:** `docs/HANDOVER.md` (new), `docs/DEPLOYMENT.md` (PostgreSQL testing, runbook, configuration table, constraints,
  smoke-test checklist, decisions needed), screenshots in `docs/screenshots/` with `frontend/scripts/screenshots.mjs`,
  README, ROADMAP, TESTING_PLAN, RISK_REGISTER (R17 mitigated; R37, R38 new), CHANGELOG.

**Database changes:** none. **API changes:** none.

**Tests run (2026-11-24):** backend 334 passed on SQLite and 334 on PostgreSQL; `ruff check` and `ruff format --check` clean;
frontend and browser tests unchanged from Phase 7 (a frontend file was not touched in Phase 8 apart from a screenshot script).

**Nothing was deployed, signed up for or paid for.** Deploying needs accounts (and possibly a card on file) and decisions on
access control, which are the owner's to make.

**Known limitations / bugs**
- No live deployment, so there is no live smoke test; do not claim one until `docs/DEPLOYMENT.md`'s checklist has been run.
- A hosted copy has no login (R37); free plans sleep and require a single API instance (R38).
- Remote managed PostgreSQL (network latency) and memory use under load on a small host are untested.
- Carried over: accuracy unmeasured (R33), no real data, no LLM adapter, Chrome-only browser tests, screenshots show the Next.js
  development badge in the corner because they were taken from the development server.

**Decisions**
- Stop at the owner's decision point rather than create accounts or choose paid or card-requiring services on their behalf.
- PostgreSQL test mode is opt-in through an environment variable and wipes the target database, so it is documented loudly.

**Open questions for the project owner:** which hosts (or local-only), whether a free account or card is acceptable, public or
private access and whether a login or read-only mode is needed, whether genuine data may ever be hosted; plus the earlier
ones: the real dataset, a human-labelled sample, LLM provider and cost, assessment deadline.

**Next steps**
1. Owner decides on hosting; then create the database, deploy the API (release step `alembic upgrade head`) and the web app,
   run the smoke test in `docs/DEPLOYMENT.md`, and record URLs, date and results here.
2. If real data arrives: import, label a sample, run `scripts.evaluate_models`, write the figures into `docs/AI_ANALYTICS.md` section 7.
3. Before any public use: access control, and a manual keyboard and screen-reader pass.

## 2026-11-24 – Phase 8 closed: local-only handover (owner's decision)

**Decision:** the project owner chose a **local-only handover**. No hosting accounts were created and nothing was deployed or
paid for. The hosting runbook in `docs/DEPLOYMENT.md` stays ready (it has not been executed); R37 and R38 apply only if hosted.

**Verified from a fresh clone of origin/main (`c3ec1fc`):** a new virtual environment installed `requirements-dev.txt`;
`alembic upgrade head` built the database; the API started and `GET /api/health` returned `ok`; `POST /api/demo/load` imported
465 synthetic reviews and the overview reported them as synthetic; `npm ci` and `npm run build` succeeded (all routes built);
backend `pytest` passed (334 tests) and frontend `vitest` passed (94 tests). On this Windows machine SQLAlchemy had to be installed
as pure Python (`DISABLE_SQLALCHEMY_CEXT=1`, `--no-binary sqlalchemy`) as documented under Troubleshooting in `docs/DEPLOYMENT.md`.
The browser tests (`npm run e2e`) were not re-run from the clone; they last passed (9 of 9) at Phase 7, and no application
code has changed since.

**State of the project:** Phases 1 to 8 complete (Phase 8 as local-only; Phase 7 without real-data steps).

**Still open (all need the owner):** the real dataset; a human-labelled sample of ~150-200 reviews so accuracy can be measured
(`docs/LABELLING_GUIDE.md`; until then no accuracy is claimed); LLM provider and cost if AI-written wording is ever wanted
(adapter not built); hosting, access control and a manual keyboard / screen-reader pass if the app is ever made public.

**Next steps (only when the owner supplies something):** real data -> import, review insights by hand, label and evaluate,
write results into `docs/AI_ANALYTICS.md` section 7; hosting -> follow `docs/DEPLOYMENT.md`.
