# Changelog

All notable changes, newest first. Dates are when the work was completed.

## Phase 3 - Data ingestion (2026-11-24)

### Added
- Review import pipeline: safe CSV/XLSX parsing, column-mapping suggestions, row validation, de-duplication,
  in-place updates, import reports, undo, transactional writes.
- Properties API with aliases; fuzzy property suggestions the user confirms.
- Synthetic demo data generator (deterministic, labelled, loaded and removed through the normal pipeline).
- Frontend: **Data Import** (4-step wizard and import history) and **Settings** (properties, aliases, demo data) pages.
- Sample files `data/sample/synthetic_reviews_sample.csv` and `.xlsx`.
- Database migration `ingestion_fields`: `reviews.source_url`, `reviews.updated_at`, and
  `import_batches.updated_rows / import_options / stored_filename / error_message`.
- `CHANGELOG.md`; `PROJECT_PROGRESS.md` (the former `PROGRESS_LOG.md`, renamed).

### Decided
- No automated collection from Booking.com (terms prohibit it, no public reviews API). File import is the route.
  See `docs/REQUIREMENTS.md`.

### Tests
- Backend 151 passed, frontend 28 passed, `ruff`, `tsc`, `eslint` and `next build` clean.

## Phase 2 - Project foundation (2026-11-23)
- FastAPI backend with settings, error envelope, CORS and `/api/health`; 12-table schema and initial migration.
- Next.js frontend with app shell, navigation, typed API client and live service status.

## Phase 1 - Discovery and planning (2026-11-23)
- Blueprint, requirements, architecture, schema, API design, AI approach, roadmap, test plan, risk register.
