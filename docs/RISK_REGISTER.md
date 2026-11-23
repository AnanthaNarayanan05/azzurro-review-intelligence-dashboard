# Risk Register

Likelihood / Impact: L = low, M = medium, H = high.

| # | Risk | Category | L | I | Mitigation |
|---|---|---|---|---|---|
| R1 | Real dataset not yet provided; its format is unknown | Data availability | H | H | Flexible column mapping; build on flagged synthetic data; schema designed to adapt; re-tune once data arrives |
| R2 | No authorised Booking.com API access; the site's terms prohibit automated collection | API dependency / legal | H | M | **Decision (Phase 3):** no scraper. File import is the only collection route; provenance recorded per import; the pipeline accepts any future authorised source. See `REQUIREMENTS.md` |
| R3 | Export lacks fields (no review ID, no language, single text field) | Data | M | M | Content-hash dedup; language detection; `body_text` path; analytics degrade gracefully and report what is missing |
| R4 | Multilingual reviews reduce English-only NLP coverage | AI/NLP | M | H | Measure language mix first; multilingual model if needed; report excluded counts transparently |
| R5 | Sentiment/aspect accuracy lower than expected | AI/NLP | M | H | Labelled-sample evaluation; tune lexicon/thresholds; consider transformer only if it measurably helps |
| R6 | LLM fabricates statistics or evidence (hallucination) | AI | M | H | LLM optional and off by default; evidence-only input; grounding validator; template fallback |
| R7 | Paid API costs | Cost | L | M | No paid service without cost estimate and approval; free deterministic path is complete on its own |
| R8 | Small samples lead to misleading comparisons/trends | Analytics | H | H | Show n everywhere; minimum-sample thresholds; significance tests; "insufficient data" states |
| R9 | Rating vs text sentiment confusion in interpretation | Analytics | M | M | Keep separate measures; label clearly in UI; document |
| R10 | Transformer dependencies too heavy for free hosting | Performance/deploy | M | M | Store NLP results; run heavy models offline/at import; VADER on hosted instance |
| R11 | Large uploads exhaust memory | Performance | L | M | Size/row limits; chunked processing; streaming read where possible |
| R12 | Private review data or secrets committed to Git | Security | M | H | `.gitignore` for data/DB/env; review staged changes before each commit; only synthetic data tracked |
| R13 | Malicious upload (formula injection, zip bombs in XLSX, wrong type) | Security | L | M | Extension + content checks, size limits, openpyxl read-only mode, never evaluate formulas, escape on export |
| R14 | Hosted demo exposes data publicly | Security/privacy | M | H | Deploy with synthetic data only unless approved; optional access protection; confirm with project owner |
| R15 | Free-tier hosting limits change (sleep, DB expiry) | Deployment | M | M | Check current limits at Phase 8; document; keep local run fully supported |
| R16 | Scope creep vs assessment deadline | Delivery | M | H | Phase gates; core analytics before optional LLM; ask for deadline |
| R17 | SQLite → PostgreSQL behaviour differences | Technical | L | M | SQLAlchemy portable types; run test suite against PostgreSQL before deployment |
| R18 | Uploaded export contains guest names or other personal data | Privacy | M | H | Guest names are not importable; unmapped columns are not stored; uploads are deleted after commit; imports can be undone |
| R19 | Day/month ambiguity silently misdates reviews | Data quality | M | M | Ambiguous dates are rejected unless the user chooses an order; the choice is stored on the batch |
| R20 | The declared source name on an import is wrong or misleading | Provenance | M | M | Shown as the uploader's statement, not verified; synthetic data is forced to `synthetic-demo` and counted separately |
| R21 | SQLite write contention ("database is locked") during import | Technical | L | M | Single transaction, 3 retries, full rollback on failure (tested); PostgreSQL planned for hosting |
| R22 | Neutral-sentence rule (a neutral sentence takes the polarity of its Booking.com box) and VADER thresholds mislabel mentions | AI/NLP | M | M | Rule is documented and applies to mentions only; evaluate on the labelled sample in Phase 7 and revise or remove it; evidence sentences are always shown |
| R23 | Keyword aspects miss implicit mentions, so aspect counts understate real issues | AI/NLP | H | M | Documented limit; mention counts are reported with `low_sample` flags; measure recall in Phase 7; embedding/zero-shot only if evaluation justifies it |
| R24 | Many property x aspect x window comparisons yield chance "significant" results | Analytics | M | M | Practical-size thresholds as well as intervals; minimum samples; wording presents indications with n, not proof |
| R25 | Analysis fails or is skipped, leaving reviews unscored and dashboards incomplete | Technical | L | M | Reviews are counted as "waiting" on every figure; failed runs are recorded and roll back cleanly; re-run from Settings; import never fails because of analysis |
