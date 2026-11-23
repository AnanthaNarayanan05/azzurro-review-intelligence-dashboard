# Azzurro Hotels – Review Intelligence Dashboard

An evidence-based review analytics platform that turns guest reviews for four hotel properties into
measurable business intelligence: satisfaction KPIs, property comparison, aspect-level strengths and
complaints, trends, and operational recommendations linked to the reviews that support them.

> **Project status: all eight phases done as a local-only handover (decided by the project owner, 2026-11-24).** The app is
> not hosted; a hosting runbook is ready if that changes. Working now: CSV/XLSX import with preview, mapping,
> validation, duplicate handling and undo; property management; labelled synthetic demo data; the analytics
> engine (sentiment, aspect mentions, comparison and trend statistics); and the dashboard pages that show it on
> live data: Overview, Properties (list and detail), Comparison and a Reviews explorer, driven by URL-synced
> filters; and evidence-based **Insights** written from fixed rules and templates, each linked to the real
> reviews behind it (no AI text service is used or needed). The sentiment and aspect methods are explainable
> baselines and have **not been evaluated** against human labels: the evaluation tooling is built and tested, but it
> needs a labelled sample of real reviews, so no accuracy figure is claimed. A browser end-to-end test, responsive and
> accessibility checks and a performance benchmark now exist. This README is updated as features are implemented and
> verified.

## Features

Working:
- CSV / Excel import of authorised review exports with preview, column mapping, validation,
  duplicate detection, import reports and undo
- Dynamic property management (no hard-coded hotel names)
- Review sentiment (VADER) and aspect mentions (cleanliness, staff, location, room comfort, facilities,
  food & breakfast, value, Wi-Fi) with the exact sentence as evidence – reproducible, explainable baseline
- Analytics API: overview, property comparison, per-property detail, aspect breakdown with examples, weekly /
  monthly trends. Every number carries its sample size; small samples return "insufficient data" instead of a guess
- Settings page: property manager, text-analysis status with a working re-run, demo data

- Dashboard on live data: executive overview (KPIs with sample sizes, rating distribution, sentiment split,
  praised and criticised aspects with the real sentences behind them, trends), property list and detail,
  comparison that names a best or worst property only when the difference is unlikely to be chance, and a
  review explorer (search, filters, sort, paging, and a view showing the evidence behind each analysis)
- Global filters (properties, dates, genuine / synthetic data) kept in the URL, so any view can be bookmarked or
  shared; synthetic data is always labelled

- Insights: recurring complaints, strengths, property-specific and cross-property issues, emerging trends and
  split-opinion opportunities. Each shows its counts, period, evidence strength, a suggested action, verbatim example
  sentences, and a link that opens exactly the reviews it counted. A grounding validator rejects any text whose numbers or
  review references the data does not support. Insights from synthetic demo data are labelled

Planned:
- Optional LLM wording (only after the project owner approves a provider and its cost; it must pass the same validator)

## Architecture (summary)

Next.js + TypeScript frontend → REST API → FastAPI backend (ingestion, NLP, analytics, insights) →
SQLite locally / PostgreSQL when hosted. See [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md).

## Technology stack

In use now: Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 · shadcn/ui (Radix) · TanStack Query ·
Python 3.11 · FastAPI · Pydantic 2 · SQLAlchemy 2.1 · Alembic · SQLite · openpyxl (XLSX import) ·
VADER (sentiment) · langdetect (language) · pytest · Vitest · Testing Library.

Charts are hand-written SVG/CSS (no chart library; each has a table view). Planned for later phases: Playwright (E2E), PostgreSQL (hosted).

## Documentation

| Document | Contents |
|---|---|
| [Project blueprint](docs/PROJECT_BLUEPRINT.md) | Problem, objective, scope, value |
| [Requirements](docs/REQUIREMENTS.md) | Functional / non-functional requirements, acceptance criteria |
| [System architecture](docs/SYSTEM_ARCHITECTURE.md) | Components, data flow, technology choices |
| [Database schema](docs/DATABASE_SCHEMA.md) | Tables, relationships, constraints, indexes |
| [API specification](docs/API_SPECIFICATION.md) | Endpoints, parameters, response and error formats |
| [AI & analytics](docs/AI_ANALYTICS.md) | Sentiment, aspects, trends, insights, evaluation, limitations |
| [Roadmap](docs/DEVELOPMENT_ROADMAP.md) | Phases, milestones, completion criteria |
| [Testing plan](docs/TESTING_PLAN.md) | Unit, API, analytics validation, E2E |
| [Risk register](docs/RISK_REGISTER.md) | Risks and mitigations |
| [Deployment](docs/DEPLOYMENT.md) | Setup, PostgreSQL testing, hosting runbook (not deployed: local-only handover) |
| [Handover](docs/HANDOVER.md) | Plain-language walkthrough, demo script, what is and is not proven, likely questions |
| [Labelling guide](docs/LABELLING_GUIDE.md) | How to label a sample so accuracy can be measured |
| [Project progress](PROJECT_PROGRESS.md) | Current phase, files, tests, decisions, exact next steps |
| [Changelog](CHANGELOG.md) | What changed in each phase |

## Data policy

- Review data is only ingested from authorised exports (CSV/XLSX). Booking.com is not scraped: its terms prohibit automated access and it has no public reviews API (see [Requirements](docs/REQUIREMENTS.md#data-collection-feasibility-decision-recorded-in-phase-3)).
- Real review files, uploads and local databases are git-ignored and never committed.
- Any sample data in this repository is **synthetic**, is labelled as such, and is not real guest feedback.

## Quick start (local)

```powershell
# Terminal 1 – backend (from the repository root)
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Terminal 2 – frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000, go to **Settings → Load demo data** to try the dashboard with clearly labelled
synthetic reviews, or **Data Import** to upload your own CSV/XLSX export. API docs: http://localhost:8000/docs. No `.env` file or API keys are needed
for local development. Full instructions, configuration and troubleshooting (including a Windows
Application Control workaround) are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Testing

```powershell
# from backend/  – 334 tests (also runnable on PostgreSQL, see docs/DEPLOYMENT.md): API, errors, config, database integrity, ingestion, NLP, analysis runs, analytics, review explorer, insights, evaluation metrics
.venv\Scripts\python.exe -m pytest
# from frontend/ – 94 tests: API client, status UI, navigation, import wizard, analysis card, filters, charts, dashboard pages, insights
npm test
# from frontend/ – 9 browser tests (Playwright + installed Chrome): import to dashboard to insight, 375/768 px layout, accessibility.
# Starts its own API on a throwaway database (ports 8100/3100); stop the dev servers first. First run builds the app (~1 min).
npm run e2e
```

Other Phase 7 tools (run from `backend/`):

```powershell
# time import, analysis, endpoints and insights on N synthetic reviews (temporary database)
.venv\Scripts\python.exe -m scripts.benchmark --reviews 50000
# measure sentiment/aspect accuracy against a person's labels – see docs/LABELLING_GUIDE.md
.venv\Scripts\python.exe -m scripts.evaluate_models export --size 150
```

## Repository layout

```
backend/    FastAPI app (app/api, app/core, app/models, app/schemas, app/services, app/analytics), Alembic migrations, tests
frontend/   Next.js App Router app (app/, components/, hooks/, lib/, services/, types/), tests
docs/       Blueprint, requirements, architecture, schema, API, AI/NLP, roadmap, testing, risks, deployment
data/       sample/ (synthetic, tracked) · raw/, processed/, uploads/ (private, git-ignored)
backend/scripts/  generate_sample_files.py (rebuilds data/sample/synthetic_reviews_sample.csv/.xlsx)
```

## Deployment

**Not deployed, by decision:** the project owner chose a local-only handover (2026-11-24). The app runs locally and has been
tested against PostgreSQL; the hosting runbook, limits of the candidate free plans and the decisions that would be needed
are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) if hosting is wanted later.
Screenshots (synthetic data) are in `docs/screenshots/`.

## Known limitations

See [docs/AI_ANALYTICS.md §9](docs/AI_ANALYTICS.md) and [docs/RISK_REGISTER.md](docs/RISK_REGISTER.md).
