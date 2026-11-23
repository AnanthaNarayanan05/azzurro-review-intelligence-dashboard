# AI & Analytics Methodology

Status: **Sections 1-6 and 9 are implemented (Phase 4)**; sections 7-8 are still the plan (evaluation
is Phase 7, insights are Phase 6). **No accuracy figure is claimed anywhere: the sentiment and aspect
methods have not been evaluated against human labels yet.** Everything below says what the code does,
not how well it does it.

## 1. Principles

1. Deterministic, reproducible core: the same data + configuration gives the same numbers.
2. Explainable first: start with transparent methods; add complexity only if evaluation shows it is needed.
3. Rating and text sentiment are separate measurements.
4. Generated text may explain numbers but never create them.
5. A number never travels without its sample size. Thin samples are flagged, not hidden or guessed.

## 2. Pre-processing (`app/analytics/nlp/preprocess.py`)

- The original text in `reviews` is never modified; analysis reads it and writes results to other tables.
- **Placeholders.** Answers that mean "there is nothing to say" ("Nothing", "N/A", "None", "No comment",
  "Nothing to complain about", ...) are not scored. A value is compared after lower-casing and removing
  punctuation, against the `placeholders.any` list in `aspect_lexicon.json`. A "Nothing" in the
  *disliked* box is therefore not a negative review. **"Everything" is deliberately not a placeholder**:
  in either box it is a real, strong statement (this corrects the earlier plan, which listed it).
- **Sentence splitting** is rule-based: line breaks and `.`/`!`/`?`; overlong sentences are cut at
  500 characters.
- **Language.** The review's own language is used and normalised to its primary subtag (`en-GB` -> `en`).
  If it is missing, `langdetect` runs (fixed seed, so results repeat) on texts of at least 30 characters and
  is trusted only at confidence >= 0.90; the result is stored with `language_detected = true`. Unknown
  language is analysed as English.

## 3. Sentiment analysis (`sentiment.py`, `review_analysis.py`)

**Implemented: VADER**, behind a `SentimentEngine` interface (`name`, `score(text) -> compound`).
VADER is a fixed word-list method: fast, deterministic and easy to explain, but English-only and weak on
sarcasm, mixed sentences and domain wording. Example from the test suite: "The wifi was slow and kept
dropping." scores exactly 0.0 (neutral).

- Each substantive sentence gets a compound score in [-1, 1]. Labels: `>= 0.05` positive, `<= -0.05`
  negative, otherwise neutral (VADER's customary thresholds, **not yet checked on labelled data**).
- Stored per review as up to four rows: `positive`, `negative`, `body` (whichever boxes have text) and
  `overall`. Segment score = mean of its sentences; **overall = mean over all substantive sentences** (so a
  long complaint outweighs a short compliment).
- A mixed review can land in the neutral band: "The room was clean." (+0.402) with "The bathroom was
  dirty." (-0.440) averages -0.019, which is neutral.
- **Review status** (`reviews.analysis_status`): `NULL` = waiting, `analysed`, `no_text` (nothing but
  placeholders or empty), `non_english` (counted, not scored). Dashboards report these counts; shares use
  analysed reviews as the denominator.
- Results are stored, not computed per request. Every run records the engine name/version and lexicon
  version (`analysis_runs`). Changing either forces the next run to re-score everything, so results from two
  methods are never mixed. Editing a review's text through a re-import resets it to "waiting".
- A transformer model remains a possible later upgrade (the interface exists); it would be adopted only
  if evaluation (section 7) shows a material gain and the hosting cost is acceptable.

## 4. Multilingual reviews

Reviews whose language is not English are **counted but not scored** (`non_english`), and every
dashboard figure states how many were left out. The size of that group in the real dataset will decide
whether a multilingual model is needed. Machine translation through a paid API is not planned without
approval.

## 5. Aspect-based sentiment (`aspects.py`, `aspect_lexicon.json`)

**Implemented: a keyword lexicon.** `aspect_lexicon.json` (version `1.0.0`, stored on every analysis run)
holds 8 aspects: cleanliness, staff_service, location, room_comfort, facilities, food_breakfast,
value_for_money, wifi_connectivity. (JSON, not YAML as first planned: it needs no extra dependency.)

- A term matches whole words, case-insensitively; a trailing `*` matches any ending (`clean*` ->
  cleaned, cleaning). Multi-word phrases are supported.
- **Exclusion phrases** are blanked out before matching, e.g. "room service" and "service charge" must not
  count as staff service. "Restaurants nearby" must not count as food.
- A bare "room" is **not** a term for room_comfort (it appears in nearly every review); room-specific
  words such as bed, pillow, noise and "room size" are.
- One sentence can mention several aspects ("Great location and friendly staff"). Each mention stores
  `matched_term`, `source_field`, the sentence score/label and the **verbatim sentence** as `evidence_text`.
- **Mention label.** The sentence's VADER label, with one documented extra rule: a sentence VADER calls
  *neutral* takes the polarity of the Booking.com box it was written in (disliked box -> negative, liked
  box -> positive). Reason: guests rarely write a neutral-sounding sentence in the "disliked" box unless it
  was a problem ("The wifi was slow and kept dropping."). This rule is a judgement, **not yet evaluated**,
  and applies to mentions only, not to the review's overall sentiment.
- **Counting.** A review counts once per aspect. Its label for that aspect is the sign of
  (positive mentions - negative mentions): above zero positive, below zero negative, zero neutral.

### Metrics per aspect (`/api/analytics/aspects`)
Reviews mentioning the aspect, positive / neutral / negative counts, positive and negative share
(denominator = reviews mentioning that aspect), mention rate (denominator = reviews with analysed text) and
a `low_sample` flag when fewer than `MIN_ASPECT_MENTIONS` (default 10) reviews mention it. Example
sentences come from `/api/analytics/aspects/{key}/examples`.

### Limitations
- Keyword matching misses implicit mentions ("we couldn't sleep" says nothing about the word "noise") and
  can mis-assign ambiguous words ("view", "connection", "bar"). Recall has not been measured.
- Sentence-level labelling can mislabel a sentence with several aspects ("great staff but dirty room"
  gives both aspects the same, mixed, score).

### When to go beyond keywords
If evaluation shows poor recall (e.g. many implicit mentions missed) an embedding- or zero-shot-based
classifier can be evaluated, but only if it measurably improves results.

## 6. Comparison and trend detection (`metrics.py`, `stats.py`)

All statistics use the normal approximation (z = 1.96 for 95 %). It is reasonable from about 30
observations per group, which is also the default minimum sample.

- **Data scope.** Every endpoint takes `data_scope=genuine|synthetic|all`; the default is `genuine`, so
  demo data never mixes into real figures unless asked. Responses carry both totals and a `mixed` flag.
- **Property comparison.** Each property reports its mean rating with a 95 % interval and a `low_sample`
  flag (fewer than `MIN_SAMPLE_COMPARISON`, default 30, rated reviews). "Best" and "worst" are named only
  if at least two properties have enough reviews **and** the intervals of the highest and lowest do not
  overlap; otherwise the status is `difference_not_significant` or `insufficient_data`.
- **Trends.** Granularity `week` (Monday to Sunday, labelled by the Monday) or `month`. Review dates are
  calendar dates as supplied; no time-zone conversion is applied. Metrics: `volume`, `avg_rating`,
  `sentiment_positive_share`, `sentiment_negative_share`, `aspect_negative_share` (needs an aspect). Empty
  periods are kept (`n = 0`, `value = null`) so gaps are visible. `as_of` (default today) fixes the "now":
  later reviews are ignored and **only complete periods are compared**, because a half-finished week would
  always look like a drop.
- **Change detection.** The most recent window (default 4 weeks / 3 months) is compared with the
  previous window of equal length. Each window needs at least `MIN_SAMPLE_TREND_WINDOW` (default 30)
  observations, otherwise the status is `insufficient_data`.
  - Average rating: difference of means with a Welch-style interval.
  - Proportions (positive/negative share, aspect negative share): difference of two proportions with a
    Wald interval (the Wilson interval first planned is better for very small or extreme proportions;
    Wald is acceptable at the sample sizes enforced here).
  - A change is reported as `increase`/`decrease` only if the interval excludes zero **and** the change
    reaches a practical threshold (0.3 rating points, or 5 percentage points); otherwise
    `no_significant_change`.
  - Volume is descriptive only (no significance claim).
- **Emerging complaint** detection (an aspect whose negative share rises significantly) is built on this
  in Phase 6.

### Verification
The arithmetic is checked against hand-calculated results: `backend/tests/fixtures/validation_reviews.csv`
(21 invented reviews) with every expected value derived in `backend/tests/fixtures/EXPECTED_RESULTS.md`
and asserted in `backend/tests/test_analytics_api.py`. This verifies the *calculations*; it says nothing
about how accurate VADER or the lexicon are (section 7).

## 7. Evaluation methodology (tooling built in Phase 7; **no results yet**)

> **Status:** the measuring tools exist and are unit-tested (`app/analytics/evaluation.py`,
> `backend/scripts/evaluate_models.py`, `docs/LABELLING_GUIDE.md`), but they have **not been run on a human-labelled
> sample**, because no real reviews or labels have been supplied. **No accuracy, precision, recall or F1 figure is
> claimed for the sentiment engine or the aspect lexicon.** Results will be added below, with sample size and date,
> only after a person has labelled about 150-200 genuine reviews.

### How to run it
1. `python -m scripts.evaluate_models export --size 150` writes a sheet of genuine reviews (stratified by property and
   rating band, fixed seed, synthetic reviews excluded) with no system output on it, so labelling is not biased.
2. A person fills `human_sentiment` and `human_aspects` using `docs/LABELLING_GUIDE.md`.
3. `python -m scripts.evaluate_models evaluate --labelled <sheet>` computes the metrics below on the same code path the
   dashboard uses (same pre-processing, VADER thresholds, neutral-sentence rule and aspect lexicon), and saves an
   aggregate-only report that is safe to copy here.

### Method

- **Labelled sample:** stratified random sample of ~150–200 real reviews across properties and ratings,
  labelled for overall sentiment and aspect mentions by a human (ideally the project owner), using a
  short labelling guide. A model's own labels are never used as ground truth.
- **Sentiment metrics:** accuracy, per-class precision/recall/F1, macro-F1, confusion matrix.
- **Aspect metrics:** per-aspect precision and recall of mention detection; accuracy of aspect sentiment
  on correctly detected mentions.
- Details of the arithmetic: a class with no human examples is left out of the macro average (not counted as 0); a metric
  with nothing to divide by is shown as n/a, not 0; if humans found cases and the system predicted none, F1 is 0; samples of
  fewer than 100 labelled reviews are flagged as too few to rely on; non-English or empty reviews are reported separately
  because the dashboard does not analyse them either.
- Results, sample size and date of evaluation are written into this document. Until then, no accuracy is claimed.

### Results

_None yet. Add the aggregate tables from `evaluation_report.md` here once a labelled sample exists._
- Synthetic data is used **only** for software testing, never to report model accuracy.

## 8. Insight generation (Phase 6 - implemented)

Insights are **computed by rules from the stored analytics, never written freely**. Generation is a manual,
repeatable action ("Generate insights"); it works with no AI service. Existing insights for the same data
scope are replaced by a new generation (they are derived data, not source data).

### Definitions
- **"Now"** is the date of the latest review in the chosen data scope (not today's date), so an old dataset
  still gets a meaningful "recent" window. Period-based rules use only complete weeks / months as in section 6.
- **Data scope** (`genuine` default, `synthetic`, `all`) is stored on every insight and shown on every card.
  Insights made from synthetic demo data are labelled as such and are never presented as real findings.
- **Descriptive rules** (counts and shares) need at least `MIN_ASPECT_MENTIONS` (default 10) reviews mentioning
  the aspect at that property. **Inferential rules** (property vs the rest, trend change) need at least
  `MIN_SAMPLE_COMPARISON` / `MIN_SAMPLE_TREND_WINDOW` (default 30) observations per side, because the intervals are
  normal approximations.
- Thresholds live in one place (`app/services/insights/rules.py`), are returned with every insight in
  `metrics.thresholds`, and are not tuned to any dataset. They are starting points, not validated values.

### Rules
| Type | Rule | Supporting reviews |
|---|---|---|
| Recurring complaint (per property and aspect) | at least 10 mentions, at least 10 negative, negative share >= 40 % | the negative reviews |
| Strength to preserve | at least 10 mentions, positive share >= 80 % | the positive reviews |
| Emerging negative trend | the aspect's negative share rose between the previous and the latest window (section 6: interval excludes zero **and** >= 5 percentage points; each window >= 30 mentions) | negative reviews in the latest window |
| Property-specific issue | the property's negative share for an aspect is above the pooled share of all other properties: interval of the difference excludes zero, difference >= 5 percentage points, >= 30 mentions on each side | the property's negative reviews |
| Cross-property issue | the same aspect is a recurring complaint at two or more properties | the negative reviews at those properties |
| Opportunity | at least 10 mentions, negative share between 30 % and 40 % (below the complaint line) and positive share >= 30 %: opinion is split | all reviews mentioning the aspect there |

Not built: the "rating/sentiment mismatch cluster" opportunity idea from the first design (needs evaluation first).
Because many rules are checked at once (properties x aspects), some will fire by chance; insights are presented as
indications with their counts, not as proof (section 9). The generation result lists how many property/aspect
combinations were checked and how many were skipped for too little data.

### Evidence
Each insight stores `supporting_review_count` (the full count) and up to 10 example reviews with the verbatim
sentence (`insight_evidence`, enforced by foreign key). Examples are the strongest sentences, one per review,
preferring distinct wording. `metrics.filters` holds the exact filter (properties, aspect, stance, dates, data
scope) so the full supporting set is one click away in the Reviews explorer, and its total equals the stored count.

### Evidence strength
- **strong:** at least 20 supporting reviews, spread over at least 2 calendar months, and not low-sample.
- **moderate:** at least 8 supporting reviews.
- **limited:** fewer. With the default rule floors this is rare; it exists so lowering a floor cannot silently
  produce headline claims. Limited insights are shown with a "limited evidence" label and never as a headline.

### Template wording (always available)
Title, explanation and suggested action come from templates filled with the computed numbers. Suggested actions
come from a per-aspect catalogue (`insight_actions.json`, keyed by aspect key, with a generic fallback), and are
labelled as suggestions, not facts.

### Grounding validator
A provider-independent check, applied to **every** insight text (templates too), rejects a candidate if: it cites a
review ID outside its evidence set; its text contains a number that is not derivable from `metrics`; or required
fields are missing. A rejected candidate is not stored and is counted in the generation result.

### Results on the demo data (2026-11-24)
Run on the labelled synthetic demo data (465 reviews, scope `synthetic`) with the defaults above:
15 insights, none rejected by the validator: 1 property-specific issue, 2 recurring complaints, 6 strengths and
6 opportunities. No trend insight fired, because each of the two windows needs at least 30 mentions and the demo
data is too thin per property and month; the generation result reports the skipped comparisons instead of hiding
them. These are findings about generated data and say nothing about the hotels. The opportunity floor was first
20 %, which produced 22 of 31 insights as near-universal "mixed opinion" noise; it was raised to 30 % before this
result. That change was made by looking at the demo data, so the thresholds remain starting points, not validated
values. The property-specific issue and the recurring complaint for the same property and aspect overlap by
design: one says "repeated", the other "worse than the other properties".

### Optional LLM wording - not built
No LLM adapter exists. It would need a paid provider and an API key, so it is deferred until the project owner
approves a provider and cost. The validator above is what such an adapter would have to pass; until then
`generation_method` is always `template`.

## 9. Known limitations

- Keyword aspect extraction misses implicit mentions and can mis-assign ambiguous words ("view", "connection").
- VADER is English-only and can misread sarcasm and mixed sentences; its thresholds and the
  neutral-sentence box rule (section 5) are unevaluated.
- Small review counts per property/month limit trend detection; the system reports this instead of guessing.
- Running many comparisons (4 properties x 8 aspects x several windows) will produce some "significant"
  results by chance; the dashboard presents them as indications with their sample sizes, not as proof.
- Booking.com review exports may not include every field described here; the mapping layer adapts but
  analytics are limited by what the data contains.
