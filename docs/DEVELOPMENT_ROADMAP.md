# Development Roadmap

Each phase ends with: tests run → failures fixed → docs + `PROGRESS_LOG.md` updated → commit → push.

**Status (2026-11-23):** Phase 1 complete (approved) · Phase 2 complete · Phase 3 next.

| Phase | Goal | Key tasks | Depends on | Completion criteria | Planned commits |
|---|---|---|---|---|---|
| **1. Discovery & planning** | Approved blueprint | Inspect env, connect GitHub, requirements, architecture, schema, API, NLP method, risks, roadmap | – | Blueprint approved by project owner | `chore: initialise repository`, `docs: add phase 1 technical blueprint` |
| **2. Foundation** | Running skeleton | FastAPI app (settings, DB session, error envelope, `/api/health`), SQLAlchemy models + Alembic migration, Next.js app (Tailwind, shadcn/ui, layout, sidebar nav), typed API client, CORS, health indicator in UI | 1 | `pytest` passes; frontend shows live backend health; `alembic upgrade head` creates schema | `chore: scaffold backend`, `chore: scaffold frontend`, `feat: implement database models` |
| **3. Data ingestion** | Working import pipeline | CSV/XLSX parsing, type/size validation, preview, mapping suggestions, property resolution & aliases, row validation, dedup, import reports, undo import, synthetic data generator (flagged), import UI wizard | 2 | Edge-case tests pass (empty file, bad dates, out-of-range ratings, unknown property, duplicates, wrong type); report counts reconcile | `feat: implement review ingestion`, `feat: add review validation`, `feat: add import wizard`, `chore: add synthetic sample data` |
| **4. Analytics engine** | Stored NLP + metrics | Pre-processing, VADER engine, aspect lexicon & detector, analysis runs, metrics (overview, comparison, property, aspects, trends) with sample guards | 3 | Hand-calculated fixture matches API output exactly; NLP unit tests pass | `feat: implement sentiment analysis`, `feat: implement aspect extraction`, `feat: add analytics engine` |
| **5. Dashboard** | All pages on live data | Global filters (URL-synced), Overview, Properties list + detail, Comparison, Reviews explorer, Settings; loading/empty/error states; responsive | 4 | Every control works against the API; no static numbers; component tests pass | `feat: build executive dashboard`, `feat: add property comparison`, `feat: implement review explorer` |
| **6. Insights** | Evidence-grounded insights | Rules engine, evidence selection, templates, action catalogue, Insights UI with evidence drill-down, optional LLM adapter + grounding validator (only if approved) | 4, 5 | Every insight links to existing review IDs; tests prove validator rejects ungrounded output; works with LLM disabled | `feat: add evidence-based insights` |
| **7. Testing & optimisation** | Verified product | Real-data import (when supplied), labelled-sample evaluation, Playwright E2E, responsive & accessibility checks, performance check, bug fixes | 3–6 + real data | Evaluation metrics documented; E2E upload→dashboard passes; known issues documented | `test: add analytics validation tests`, `test: add e2e workflow`, `fix: …` |
| **8. Deployment & handover** | Live, documented demo | Choose hosts (after checking current free-tier limits), PostgreSQL, env config, deploy, verify live, screenshots, README, walkthrough | 7 | Live app tested end-to-end; docs match reality | `docs: complete deployment instructions` |

## Critical path & blockers

- The **real dataset** is needed for Phase 7 evaluation, final aspect lexicon tuning and real-data
  demonstration. Phases 2–6 proceed on clearly labelled synthetic data plus a small hand-written test fixture.
- An **LLM provider decision** is needed only for the optional narrative layer in Phase 6.
- A **deployment decision** (required or not; public or protected) is needed before Phase 8.
