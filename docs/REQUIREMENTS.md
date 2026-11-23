# Requirements

Status: Draft for approval (Phase 1). IDs are referenced by tests and the roadmap.

## 1. Users

| User | Needs |
|---|---|
| General / operations manager | Portfolio health at a glance, cross-property problems, prioritised actions |
| Property manager | Their property's strengths, complaints, trends and recent reviews |
| Analyst / administrator | Import data, map columns and properties, check data quality, re-run analysis |
| Technical assessor | Clear architecture, reproducible metrics, tests, honest limitations |

## 2. Functional requirements

### Properties
- **FR-P1** Properties are stored in the database and created/edited via API and Settings UI.
- **FR-P2** Each property can have aliases so differing source names (e.g. a full listing name in one export and a short code in another) map to one property.
- **FR-P3** The system supports at least four properties; nothing in the UI or analytics hard-codes property names or counts.

### Ingestion
- **FR-I1** Accept `.csv` and `.xlsx` uploads; reject other types with a clear message.
- **FR-I2** Show a preview (first rows), detected columns, and an auto-suggested column mapping.
- **FR-I3** The user can adjust the mapping of source columns to internal fields before import.
- **FR-I4** Map source property values to existing properties (or create new ones) before import.
- **FR-I5** Validate each record: required fields, date parsing, rating range, text presence, property mapping.
- **FR-I6** Detect duplicates within the file and against previously imported data.
- **FR-I7** Never silently discard records: every rejected/duplicate row is recorded with a reason.
- **FR-I8** Produce an import report: received, imported, rejected, duplicates, reasons (grouped and per row).
- **FR-I9** Ingestion is built around a source-adapter boundary so an authorised API source can be added later. Today the only source is a user-supplied file (see "Data collection feasibility" below); no automated collector exists.
- **FR-I11** Every import records its provenance: original filename, file hash, the source name the user declared, import time, and the mapping used. A review keeps its source label and `is_synthetic` flag.
- **FR-I12** An import can be undone, removing exactly the reviews that import created.
- **FR-I10** Clearly labelled synthetic sample data can be generated/loaded for demonstration.

### Analysis
- **FR-A1** Classify review text sentiment as positive / neutral / negative, storing label, score, model name/version and timestamp.
- **FR-A2** Rating and text sentiment are stored and reported as separate measures.
- **FR-A3** Detect mentions of 8 initial aspects (cleanliness, staff & service, location, room comfort, facilities, food & breakfast, value for money, Wi-Fi & connectivity) with per-mention sentiment and evidence text.
- **FR-A4** The aspect list is configuration-driven and extensible without code changes to analytics.
- **FR-A5** Analysis is re-runnable; each run is recorded (model, lexicon version, counts).

### Analytics & dashboard
- **FR-D1** Executive overview: total reviews, average rating, sentiment distribution, volume over time, rating distribution, per-property volume & rating, top positive/negative aspects, emerging complaints, recent insights.
- **FR-D2** Comparison: total reviews, average rating, sentiment & rating distributions, aspect performance, top praise & complaints, change over time – across all properties.
- **FR-D3** Property view: all of FR-D1 scoped to one property, plus recent reviews and recommendations.
- **FR-D4** Every metric shows its sample size (n); metrics below the configured minimum sample are visibly flagged.
- **FR-D5** Global filters (property, date range) apply consistently and are reflected in the URL.

### Review explorer
- **FR-R1** Full-text search over review text.
- **FR-R2** Filter by property, date range, rating range, sentiment, aspect (and aspect sentiment).
- **FR-R3** Sort by newest, oldest, highest rating, lowest rating.
- **FR-R4** Server-side pagination.
- **FR-R5** Original review text is preserved and displayed unchanged; analysis is shown alongside.

### Insights
- **FR-N1** Generate insights of types: recurring complaint, strength to preserve, emerging negative trend, property-specific issue, cross-property issue, improvement opportunity.
- **FR-N2** Each insight stores: title, explanation, properties, supporting review count, supporting review IDs (FK-linked), period, suggested action, evidence strength.
- **FR-N3** Insights are generated from deterministic analytics; an optional LLM may only rephrase/summarise provided evidence.
- **FR-N4** If the LLM is disabled or fails, template-based insights are still produced and the dashboard is fully functional.

_Status (Phase 6):_ FR-N1, FR-N2 and FR-N4 are implemented and tested. FR-N3's optional LLM is not built (it needs the project owner's approval of a provider and cost); every insight is template-written and passes the grounding validator.

## 3. Non-functional requirements

- **NFR-1 Correctness** – Analytics match hand-calculated results on the validation fixture.
- **NFR-2 Reproducibility** – Same input + same configuration ⇒ identical metrics.
- **NFR-3 Performance** – Dashboard API responses < 1 s for up to ~50k reviews on SQLite locally; import of 10k rows < 60 s with VADER.
- **NFR-4 Security** – Upload type/size limits, parameterised queries (ORM), secrets only in env vars, no internal errors leaked to clients, no guest names stored.
- **NFR-5 Usability** – Responsive (≥ 360 px), keyboard-accessible controls, loading/empty/error states for every data view.
- **NFR-6 Maintainability** – Typed code (TypeScript, Pydantic, type hints), modular analytics, tests in CI-ready form.
- **NFR-7 Transparency** – Synthetic data flagged; limitations documented; model accuracy reported only from actual evaluation.

## 4. Acceptance criteria (summary)

The project is accepted when: four properties can be represented; CSV and Excel imports work end-to-end
with validation, duplicate detection and reports; sentiment and aspect analysis run and are evaluated on a
labelled sample with reported metrics; all dashboard modules are wired to live API data; search, filters,
sort and pagination work; insights link to real review IDs; core tests pass; documentation matches the
implementation; no secrets or private data are in Git; deployment (if required) is verified live.

## Data collection feasibility (decision recorded in Phase 3)

**Question:** can reviews for the four properties be collected automatically from their public Booking.com pages?

**Finding:** not in a way this project is permitted to build.
- Booking.com's published terms prohibit automated access to the site and scraping without its prior written
  permission, and a page being publicly visible does not grant that permission.
- There is no public Booking.com API for retrieving guest reviews. Review access through the partner programme
  requires an approved partner account, which this project does not have, and none is assumed.
- Evading restrictions (CAPTCHAs, rate limits, disguised automation) is out of scope under the project rules.

**Decision:** no scraper is built. Reviews enter the system only through
1. **file import (CSV/XLSX)** of an export the property owner is entitled to use, e.g. from the Booking.com
   extranet or another authorised source; and
2. **clearly labelled synthetic demo data** for development and demonstration.

**What this means for requirements:** every requirement that said "collect" is satisfied by "import". Collection
timestamps are recorded as the import time (`imported_at`), and provenance as the batch (filename, file hash,
declared source). The declared source name is the uploader's statement and is not verified by the system.

**Future path:** if written permission or a partner API is obtained, a new adapter would produce the same
normalised rows that file import produces and reuse the same validation, de-duplication, reporting and undo.
That would be a separate, approved piece of work.
