# Handover and walkthrough

For the person who will run, present or defend this project. Plain language first; the other documents hold the detail.
Status at the end of Phase 8 (2026-11-24): everything below works on a local machine. The owner decided **not to host** it
(2026-11-24), so nothing is hosted; optional deploy files and steps exist (`docs/GO_LIVE.md`) but were never used. The accuracy of the sentiment and aspect methods has **not** been measured
(see "What is and is not proven").

## 1. What it is, in one minute

Hotels publish guest reviews. This app takes an export of those reviews for the four Azzurro properties (a CSV or Excel
file), checks every row, stores the valid ones, and works out measurable things from them: average ratings, how many
guests were positive or negative, which topics (cleanliness, staff, location, ...) are praised or complained about,
how the properties compare, and how things change over time. It then writes plain-English **insights** such as
"Cleanliness draws more complaints at Property X than elsewhere", and every insight links to the exact guest sentences
it is based on.

Three rules run through everything and are the best things to say when asked "why should I trust it?":

1. **Nothing is invented.** Every number is calculated from stored reviews, and every insight cites real review sentences.
   Insights come from fixed rules and templates, not a text generator; a validator rejects any insight whose numbers or
   citations don't trace back to stored data.
2. **Small samples are flagged, not hidden.** Each figure shows how many reviews it is based on ("n"), and
   conclusions such as "better than" appear only when the statistics support them.
3. **Demo data is always labelled.** The sample reviews are generated, marked synthetic in the database, kept out of the
   default (genuine) view, and labelled on every page that shows them.

## 2. How it fits together

```
 CSV / Excel file
       |  upload, preview, match columns, choose properties
       v
  Import pipeline  -- validates each row, de-duplicates, reports every rejected row, can be undone
       v
  Database (SQLite locally, PostgreSQL when hosted)
       v
  Analysis  -- splits text into sentences, scores sentiment (VADER), finds topics (keyword lexicon)
       v
  Analytics  -- averages, shares, confidence intervals, comparisons, trends
       v
  Insights   -- rules + templates + evidence + grounding check
       v
  API (FastAPI)  <---->  Web app (Next.js): Overview, Properties, Comparison, Reviews, Insights, Import, Settings
```

| Folder | What is in it |
|---|---|
| `backend/app/services/ingestion` | file parsing, column mapping, validation, de-duplication, import pipeline |
| `backend/app/analytics` | NLP (`nlp/`: sentences, VADER, topic lexicon), statistics (`stats.py`), metrics, evaluation maths |
| `backend/app/services/insights` | insight rules, evidence, wording templates, grounding validator |
| `backend/app/api/routes` | the HTTP endpoints (documented in `docs/API_SPECIFICATION.md`) |
| `backend/migrations` | database schema history (Alembic) |
| `frontend/app`, `frontend/components` | pages and UI pieces |
| `frontend/e2e` | browser tests |
| `data/sample` | the committed **synthetic** sample files |
| `docs/` | blueprint, requirements, architecture, schema, API, AI method, testing, risks, deployment, this guide |

## 3. Run it (about five minutes)

Commands are in `docs/DEPLOYMENT.md` ("Local setup"). In short: create the backend virtual environment and run
`alembic upgrade head` and `uvicorn`; run `npm install` and `npm run dev` in `frontend/`; open http://localhost:3000.
No keys or accounts are needed.

## 4. A ten-minute demonstration

Screenshots of these pages (synthetic data) are in `docs/screenshots/`.

1. **Settings -> Load demo data.** Explain these are generated reviews, counted as synthetic; analysis runs automatically.
2. **Overview** (`overview.png`). Point at the "Synthetic demo data" banner, the review count and "Based on N reviews"
   under each figure, and the sentiment bar (sentiment of the *text*, not the star rating).
3. **Aspects table** on the Overview: click "Complaints" on a topic; real sentences appear. Mention the "Low sample" tag.
4. **Comparison** (`comparison.png`): note that a "best" property is named only when the confidence intervals separate.
5. **Reviews** (`reviews.png`): filter by property, search a word, open a review and show its evidence (the sentences
   and topics the system found in it).
6. **Insights** (`insights.png`): open "See all N reviews" and show N equals the Reviews page total; expand example sentences.
7. **Data Import** (`import.png`): upload `data/sample/synthetic_reviews_sample.csv`, show the preview, mapping, the report
   ("465 rows = imported + updated + duplicates + rejected") and **undo**.
8. Narrow the window (`overview-375px.png`) to show the layout adapts.

## 5. What is and is not proven

| Claim | Status |
|---|---|
| Imports reject bad rows and the counts reconcile | Tested (unit, API and browser tests) |
| Dashboard figures equal hand-calculated values | Tested against a hand-worked fixture |
| Every insight's evidence exists and its count matches the Reviews page | Tested |
| The app works end to end in a browser (upload -> dashboard -> insight -> evidence) | 9 Playwright tests |
| No sideways scrolling at 375 / 768 px; no automated accessibility violations | Tested (axe-core, Chrome only) |
| Fast enough: dashboard endpoints under 1 s at ~50,000 reviews | Measured on SQLite and PostgreSQL (synthetic data, local) |
| Works on PostgreSQL | All 334 tests pass on PostgreSQL |
| **Sentiment and topic detection are accurate** | **NOT measured.** The tool exists; it needs a person to label ~150-200 real reviews (`docs/LABELLING_GUIDE.md`) |
| The insights are useful for the real hotels | **NOT assessed**: no real data has been used |
| Hosted deployment works | **Not done, by the owner's decision.** The API start command was checked locally with production settings; the rest is untested |
| An AI text generator writes anything | **No.** No LLM is used or built |

## 6. Questions you may be asked, and honest answers

- **Why VADER and a keyword lexicon instead of a bigger AI model?** They are fast, free, need no keys, and every result
  can be explained by pointing at a word. The cost is that they miss sarcasm and implied topics ("we couldn't sleep"
  about noise). That is why evaluation against human labels is built in, and why the method can be swapped (the engine
  is behind an interface) if the numbers are poor.
- **How accurate is it?** I don't know yet, and I won't quote a number I haven't measured. Here is how I would measure
  it: sample real reviews, label them by hand without seeing the system's output, compare, and report accuracy,
  per-class precision and recall, and a confusion matrix.
- **What stops it making things up?** Insights are rule-and-template based. A grounding validator rejects any text with a
  number that isn't derivable from stored metrics or a citation that isn't in the evidence set; tests include a
  deliberately ungrounded candidate that must be rejected.
- **Why does a small property show "Low sample"?** With few reviews an average is mostly noise; the app says so rather
  than ranking it.
- **How do you know the maths is right?** A 21-review fixture was worked out by hand (`backend/tests/fixtures/EXPECTED_RESULTS.md`)
  and the API must reproduce it exactly; insight rules are tested on tiny datasets worked out on paper.
- **What happens with duplicate or broken rows?** Duplicates are skipped, rows that can't be read are rejected with a reason,
  nothing is silently dropped, and a whole import can be undone.
- **Is guest data private?** Guest names are not importable, unmapped columns are not stored, uploaded files are deleted
  after import, and real review data folders are git-ignored. The app has **no login**, so do not host real data without
  adding access control.
- **Why SQLite and PostgreSQL?** SQLite needs no setup for local use; PostgreSQL is for hosting. The same migrations and the
  same tests run on both.
- **What would you do next?** Get the real dataset, label a sample and report accuracy, tune the lexicon, then deploy
  with access control.

## 7. Keeping it going

- **Add or rename a property:** Settings -> property manager (names are data, never in code). Aliases map file values to a property.
- **Change a topic's keywords or add a topic:** `backend/app/analytics/nlp/aspect_lexicon.json` (bump its version), then use Settings -> **Re-analyse all
  reviews** so stored results use the new words. Re-run the tests.
- **Change insight thresholds:** `backend/app/services/insights/rules.py` (one place; thresholds are stored with each insight).
  They are unvalidated starting points.
- **Change the database:** edit models, `alembic revision --autogenerate`, review the file, `alembic upgrade head`,
  and run the tests (they build the database from the real migrations).
- **Before changing anything:** run the backend tests (`pytest`), the frontend tests (`npm test`) and the browser tests (`npm run e2e`).

## 8. What the project owner still needs to provide or decide

1. The real review export (format, columns), if genuine data should be shown. Until then every demonstration uses synthetic data.
2. A person to label ~150-200 reviews so accuracy can be measured (`docs/LABELLING_GUIDE.md`).
3. Only if hosting is wanted later: follow `docs/GO_LIVE.md`. Decided for now: local only.
4. Whether an AI-written narrative layer is wanted. It would need a provider choice and cost approval, and it must pass the
   same grounding validator.
5. The assessment deadline, so remaining work can be prioritised.
