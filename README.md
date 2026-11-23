# Azzurro Hotels – Review Intelligence Dashboard

An evidence-based review analytics platform that turns guest reviews for four hotel properties into
measurable business intelligence: satisfaction KPIs, property comparison, aspect-level strengths and
complaints, trends, and operational recommendations linked to the reviews that support them.

> **Project status: Phase 1 – technical blueprint (awaiting approval).** No application code exists yet.
> This README will be updated as features are actually implemented and verified.

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

Next.js · TypeScript · Tailwind CSS · shadcn/ui · Recharts · TanStack Query · Python 3.11 · FastAPI ·
Pydantic · SQLAlchemy · Alembic · pandas · VADER (baseline) · pytest · Vitest · Playwright

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
| [Progress log](PROGRESS_LOG.md) | Chronological development record |

## Data policy

- Review data is only ingested from authorised exports. Booking.com is not scraped.
- Real review files, uploads and local databases are git-ignored and never committed.
- Any sample data in this repository is **synthetic**, is labelled as such, and is not real guest feedback.

## Setup, running, testing, deployment

To be documented once implemented (Phase 2 onwards). Planned steps are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Known limitations

See [docs/AI_ANALYTICS.md §9](docs/AI_ANALYTICS.md) and [docs/RISK_REGISTER.md](docs/RISK_REGISTER.md).
