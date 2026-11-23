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
 │  hand-written SVG/CSS charts · URL-synced filters                 │
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
| Charts | Hand-written SVG and CSS (no chart library) | Phase 5 decision: only five simple chart types are needed (distribution bars, split bars, line, interval, table), so a dependency was avoided. Each chart has a table view, hover details and written labels; colours are CSS variables (`--viz-*`) with light and dark values |
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
| Ingestion: parsing, mapping, validation, de-duplication, import reports, undo, property aliases, synthetic demo data (API plus Data Import and Settings pages) | Implemented (Phase 3) |
| Analysis: preprocessing, VADER sentiment, aspect lexicon, stored analysis runs (`app/analytics/nlp`, `app/services/analysis.py`), metrics and statistics (`app/analytics/metrics.py`, `stats.py`), analysis and analytics APIs, Settings "Text analysis" card | Implemented (Phase 4) |
| Dashboard pages: Overview, Properties, Comparison, Reviews explorer (hand-written charts, URL-synced filters) | Implemented (Phase 5) |
| Insights: rules engine, evidence selection, template wording, action catalogue, grounding validator (`app/services/insights`), insights API, Insights page and Overview teaser. No LLM adapter | Implemented (Phase 6) |

Analysis flow: import commit (or demo load) → `analyse_after_import` → `run_analysis` writes sentiment rows, aspect
mentions and review statuses in one transaction → analytics endpoints read the stored rows. Metrics are computed from
stored results on request (fast enough at the current scale: about 0.2 s for 465 reviews); if volumes grow they can be
cached or pre-aggregated without changing the API.

## Ingestion design (implemented in Phase 3)

```
upload -> preview -> (user chooses mapping, properties, formats) -> commit -> report -> [undo]
          |                                                          |
          stored privately in data/uploads                           one transaction; file deleted afterwards
```

Module layout (`backend/app/services/ingestion/`):

| Module | Responsibility |
|---|---|
| `parsing.py` | Safe parsing. Extension **and** content check, CSV encodings (utf-8, utf-8-sig, utf-16, cp1252) and delimiter sniffing, XLSX zip-bomb guard, row cap |
| `mapping.py` | The importable fields and header-name suggestions. Reviewer names are not importable |
| `rows.py` | Per-row conversion and validation: dates, ratings, text, optional fields; produces a clean row or issues |
| `normalise.py` | Text cleaning and the content fingerprint |
| `pipeline.py` | Preview, commit (validate, de-duplicate, write), undo, stale-preview purge |

Rules worth knowing when explaining the design:
1. **Preview before write.** Nothing is saved until the user confirms; an abandoned preview is purged after 24 hours.
2. **All or nothing.** The write phase is one database transaction. On a SQLite "locked" error it retries (3 attempts); on any other failure everything is rolled back, the batch is marked `failed` and the stored file is deleted.
3. **De-duplication order.** In-file external ID or content hash first, then an existing review with the same source + external ID (unchanged = duplicate; changed = updated in place), then an existing review with the same content hash.
4. **Counts reconcile.** `total = imported + updated + duplicates + rejected`, checked by tests and shown in the UI.
5. **Synthetic separation.** `is_synthetic` forces the source `synthetic-demo`; genuine and synthetic counts are reported separately everywhere.
6. **Property resolution.** Alias, name, code, then a fuzzy match (similarity 0.86 or higher) which is only a *suggestion* the user confirms. Confirmed spellings are remembered as aliases.

### Source-adapter boundary

The pipeline consumes a table of rows plus a mapping. Anything that can produce such a table is a "source". Today
that is `parse_file` (CSV/XLSX). A future authorised API source would implement the same hand-off and reuse every
step after parsing. No code is written for a Booking.com collector (see `REQUIREMENTS.md`, "Data collection
feasibility"); the boundary is a design rule, not an unused abstraction layer.
