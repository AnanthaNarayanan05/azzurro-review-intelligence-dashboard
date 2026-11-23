# Project Blueprint

**Project:** Azzurro Hotels – Review Intelligence Dashboard
**Status:** Phase 1 (Discovery & Planning) – blueprint awaiting approval
**Last updated:** 2026-11-23

## 1. Business problem

Azzurro Hotels operates four properties that receive guest reviews on Booking.com. Reviews are
unstructured free text (Booking.com separates what a guest *liked* from what they *disliked*) plus a
numerical score. Reading them one by one does not scale and does not answer management questions such as:

- Is guest satisfaction improving or declining, and at which property?
- What do guests repeatedly complain about, and is it one property or all of them?
- Which parts of the experience (cleanliness, staff, breakfast, Wi-Fi …) are strengths to protect?
- Where should operational effort go next, and what evidence supports that?

## 2. Objective

Build a full-stack web application that ingests authorised review exports, analyses them with
reproducible NLP, and presents evidence-linked business intelligence for the four properties.

## 3. Scope

**In scope**

- CSV / Excel ingestion with preview, column mapping, validation, duplicate detection and import reports.
- Dynamic property management (no property names hard-coded in the application).
- Review-level sentiment analysis and aspect-based sentiment analysis (8 initial aspects, extensible).
- Analytics: KPIs, distributions, property comparison, time-based trends with sample-size guards.
- Evidence-grounded insight generation (deterministic rules engine; optional LLM narrative layer).
- Dashboard: Overview, Properties, Comparison, Reviews explorer, Insights, Data Import, Settings.
- Tests, analytics validation against hand-calculated results, model evaluation on a labelled sample.
- Documentation and a verified deployment (if deployment is part of the final delivery).

**Out of scope (unless requirements change)**

- Scraping Booking.com or any direct Booking.com API integration without confirmed authorised access.
  The ingestion layer is designed with a source-adapter interface so an authorised API can be added later.
- Replying to reviews, multi-tenant SaaS features, complex role-based access control.
- Microservices, message queues, vector databases, Kubernetes.

## 4. Feature set

| Module | Purpose |
|---|---|
| Executive Overview | Portfolio KPIs, sentiment mix, volume & rating trends, top positive / negative aspects, emerging complaints, latest insights |
| Properties | One analytics view per property: KPIs, trends, aspects, complaints, praise, recent reviews, recommendations |
| Comparison | Side-by-side metrics and aspect performance across all four properties, with sample-size flags |
| Reviews | Searchable, filterable, sortable, paginated explorer showing original text plus analysis |
| Insights | Evidence-linked findings with supporting review count, example reviews, period, suggested action, evidence strength |
| Data Import | Upload → preview → map columns/properties → validate → import → report |
| Settings | Manage properties and their source-name aliases; view the aspect lexicon; re-run analysis |

## 5. Expected business value

- Faster identification of recurring operational problems, with the review evidence attached.
- Fair, like-for-like comparison of properties (same metrics, same methodology, sample sizes shown).
- Separation of what guests *score* from what they *say* (rating vs text sentiment), which surfaces
  problems that a good average score hides.
- A repeatable process: the same export produces the same numbers every time.

## 6. Guiding principles

1. **Evidence first** – every metric is computed from stored records; every insight links to review IDs.
2. **Reproducible core** – deterministic analytics work with no external AI service.
3. **Honest data** – synthetic data is flagged as synthetic in the database and in the UI; low sample sizes
   are flagged instead of over-interpreted.
4. **Maintainable modular monolith** – one FastAPI backend, one Next.js frontend, one relational database.
