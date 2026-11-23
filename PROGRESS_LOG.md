# Progress Log

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
