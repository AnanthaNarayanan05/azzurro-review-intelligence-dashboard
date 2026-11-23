# Azzurro Hotels – Review Intelligence Dashboard

An evidence-based review analytics platform that turns guest reviews for four hotel properties into
measurable business intelligence: satisfaction KPIs, property comparison, aspect-level strengths and
complaints, trends, and operational recommendations linked to the reviews that support them.

> **Project status: Phase 2 complete – application foundation.** The backend (FastAPI, database schema,
> migrations, health check) and frontend shell (navigation, live service status) run and are tested.
> Review import, analytics and dashboards are **not built yet** (Phases 3–6). This README is updated as
> features are implemented and verified.

## Planned features

- CSV / Excel import of authorised review exports with preview, column mapping, validation,
  duplicate detection and import reports
- Dynamic property management (no hard-coded hotel names)
- Review sentiment and aspect-based sentiment (cleanliness, staff, location, room comfort, facilities,
  food & breakfast, value, Wi-Fi) – reproducible, explainable baseline
- Executive overview, per-property analytics, four-property comparison, review explorer
- Insights with supporting review counts, example reviews, period, suggested action and evidence strength
- Works fully without any paid AI service; optional LLM wording is grounded and validated

## Architecture (summary)

Next.js + TypeScript frontend → REST API → FastAPI backend (ingestion, NLP, analytics, insights) →
SQLite locally / PostgreSQL when hosted. See [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md).

## Technology stack

In use now: Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 · shadcn/ui (Radix) · TanStack Query ·
Python 3.11 · FastAPI · Pydantic 2 · SQLAlchemy 2.1 · Alembic · SQLite · pytest · Vitest · Testing Library.

Planned for later phases: pandas/openpyxl (import), VADER (sentiment), Recharts (charts), Playwright (E2E),
PostgreSQL (hosted).

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
| [Deployment](docs/DEPLOYMENT.md) | Setup and hosting (planned) |
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
# from backend/  – 151 tests: API, errors, config, database integrity, ingestion
.venv\Scripts\python.exe -m pytest
# from frontend/ – 28 tests: API client, status UI, navigation, import wizard
npm test
```

## Repository layout

```
backend/    FastAPI app (app/api, app/core, app/models, app/schemas), Alembic migrations, tests
frontend/   Next.js App Router app (app/, components/, hooks/, lib/, services/, types/), tests
docs/       Blueprint, requirements, architecture, schema, API, AI/NLP, roadmap, testing, risks, deployment
data/       sample/ (synthetic, tracked) · raw/, processed/, uploads/ (private, git-ignored)
backend/scripts/  generate_sample_files.py (rebuilds data/sample/synthetic_reviews_sample.csv/.xlsx)
```

## Deployment

Not deployed yet (Phase 8). See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Known limitations

See [docs/AI_ANALYTICS.md §9](docs/AI_ANALYTICS.md) and [docs/RISK_REGISTER.md](docs/RISK_REGISTER.md).
