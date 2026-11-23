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
