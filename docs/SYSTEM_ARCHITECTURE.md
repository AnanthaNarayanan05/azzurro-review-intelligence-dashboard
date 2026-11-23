# System Architecture

Status: Proposed (Phase 1).

## 1. Overview

A **modular monolith**: one Next.js frontend, one FastAPI backend, one relational database.
The frontend talks to the backend only through REST APIs. The backend owns all business logic,
NLP and analytics.

```
 Authorised export (CSV / XLSX)        [future: authorised API adapter]
              │                                   │
              ▼                                   ▼
 ┌───────────────────────── FastAPI backend ─────────────────────────┐
 │  ingestion/   source adapters → column mapping → validation →     │
 │               normalisation → property resolution → dedup         │
 │                         │                                          │
 │                         ▼                                          │
 │  models/  SQLAlchemy ──► SQLite (dev) / PostgreSQL (hosted)        │
 │                         │                                          │
 │  analytics/nlp/  text cleaning → sentence split → sentiment →      │
 │                  aspect detection → aspect sentiment (stored)      │
 │                         │                                          │
 │  analytics/metrics/  KPIs, distributions, comparison, trends       │
 │                         │   (SQL aggregates, deterministic)        │
 │                         ▼                                          │
 │  insights/  rules engine → evidence pack → [optional LLM wording]  │
 │             → grounding validator → stored insights                │
 │                         │                                          │
 │  api/  REST routers, Pydantic schemas, error envelope, OpenAPI     │
 └─────────────────────────┬──────────────────────────────────────────┘
                           │ JSON over HTTPS
                           ▼
 ┌──────────────────────── Next.js frontend ─────────────────────────┐
 │  App Router pages · TanStack Query data layer · shadcn/ui ·       │
 │  Recharts · URL-synced filters                                    │
 └────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  Management decisions
```

## 2. Component responsibilities

| Component | Responsibility |
|---|---|
| `backend/app/api` | HTTP routers, request validation, pagination, response/error envelopes |
| `backend/app/core` | Settings (pydantic-settings from env), DB session, logging, error types |
| `backend/app/models` | SQLAlchemy ORM models, constraints, indexes |
| `backend/app/schemas` | Pydantic request/response models (the API contract) |
| `backend/app/services/ingestion` | File parsing (pandas), column-mapping suggestions, validation, dedup, import reports, source-adapter interface |
| `backend/app/analytics/nlp` | Text normalisation, sentence segmentation, sentiment engines (pluggable), aspect lexicon & detector |
| `backend/app/analytics/metrics` | Aggregations for overview, comparison, property, aspects, trends; sample-size guards |
| `backend/app/services/insights` | Rules that turn metrics into insight candidates, evidence selection, optional LLM narrative, grounding validation |
| `frontend/app` | Route pages: overview, properties, comparison, reviews, insights, import, settings |
| `frontend/services` | Typed API client (one function per endpoint) |
| `frontend/components` | Charts, KPI tiles, tables, filter bar, upload wizard, states (loading/empty/error) |

## 3. Key data flows

**Import:** upload → `POST /api/imports/preview` parses the file, stores it temporarily under
`data/uploads/` (git-ignored), returns columns, sample rows and suggested mapping → user confirms
mapping and property mapping → `POST /api/imports/{id}/commit` validates every row, writes valid reviews,
records rejected/duplicate rows with reasons, then runs NLP on the new reviews → import report returned.

**Analysis:** NLP results are **computed once and stored** (`sentiment_results`, `aspect_mentions`)
rather than computed per request. Dashboards are SQL aggregates over stored results, so they are fast
and reproducible. `POST /api/analysis/run` re-analyses everything (e.g. after a lexicon change) and
records an `analysis_runs` row.

**Insights:** rules over the metrics layer produce candidate insights, each with the exact set of
supporting review IDs. Optional LLM wording receives only that evidence pack; its output is validated
(cited IDs ⊆ evidence IDs, no numbers that differ from computed numbers) before storage, else the
template text is kept.

## 4. Technology choices

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js (App Router) + TypeScript | Requested; strong routing/layout model; deploys easily to Vercel |
| Styling/UI | Tailwind CSS + shadcn/ui + Lucide | Accessible Radix primitives, code is owned in-repo (no opaque template) |
| Charts | Recharts | Declarative React charts, adequate for bar/line/stacked/distribution charts |
| Data fetching | TanStack Query | Caching, loading/error states and refetch for free; avoids hand-rolled state |
| Backend | Python 3.11 + FastAPI + Pydantic v2 | Python is where the NLP ecosystem is; FastAPI gives typed validation and OpenAPI docs |
| ORM/migrations | SQLAlchemy 2.0 + Alembic | Parameterised queries (SQL-injection safe), same code on SQLite and PostgreSQL |
| Data handling | pandas + openpyxl | Robust CSV/XLSX parsing, type coercion, encoding handling |
| Sentiment | VADER baseline, transformer candidate | See `AI_ANALYTICS.md`; final choice by measured evaluation |
| Language detection | `langdetect` or `lingua` (evaluate) | Booking.com reviews are multilingual; analysis must know the language |
| DB | SQLite (local) → PostgreSQL (hosted) | Zero-setup locally; durable managed storage when deployed |
| Tests | pytest, httpx TestClient; Vitest + Testing Library; Playwright | Unit, API, component and end-to-end coverage |

Versions are pinned in `backend/requirements*.txt` and `frontend/package-lock.json` (Python 3.11.9, Node 24.x,
Next.js 16.4, React 19.3, FastAPI 0.165, SQLAlchemy 2.1, Pydantic 2.14).

## 5. Design decisions

1. **Store NLP output, don't recompute per request** – fast dashboards, auditable results, records which model produced which label.
2. **Analyse Booking.com's liked/disliked fields separately** – they are a strong structural signal; mixing them loses information. Placeholder answers ("Nothing", "N/A", "-") are recognised and excluded from sentiment.
3. **Rating ≠ sentiment** – kept as separate measures; mismatches (e.g. 9/10 with a negative complaint) are surfaced, not hidden.
4. **Insights are rules first, LLM optional** – guarantees grounding and a working product without paid APIs.
5. **Sample-size guards everywhere** – a metric with n below threshold is shown with a warning and excluded from "best/worst" claims and trend claims.
6. **No authentication initially** – not stated as an assessment requirement; to be confirmed. If a hosted demo needs protection, a minimal shared-secret / platform-level protection is preferred over a full user system.
7. **Synchronous processing with FastAPI BackgroundTasks for large imports** – no message queue needed at this scale.
8. **Guest names are not stored** even if present in an export (data minimisation).
9. **Next.js Cache Components are enabled** (the Next.js 16 default). Pages render a static shell, and data
   is fetched in the browser through TanStack Query, so the backend stays the only owner of data. Two rules follow:
   - Components that read the URL (`usePathname`, `useSearchParams`) sit inside `<Suspense>` with a
     URL-independent fallback.
   - Components that render query data wait for `useHydrated()` before showing cached results. Page segments
     can hydrate after another component has already filled the shared query cache, and rendering that data
     during hydration would not match the server HTML.
10. **Navigation is config-driven** (`frontend/lib/navigation.ts`). Pages not built yet are shown as disabled
    items labelled with their roadmap phase, never as links to placeholder pages.

## Implementation status

| Component | Status |
|---|---|
| Backend: settings, DB session, error envelope, CORS, `/api/health` | Implemented (Phase 2) |
| Database: all 12 tables, constraints, indexes, initial Alembic migration | Implemented (Phase 2) |
| Frontend: app shell, responsive navigation, typed API client, live service status | Implemented (Phase 2) |
| Ingestion, NLP, analytics, insights, dashboard pages | Not started (Phases 3–6) |
