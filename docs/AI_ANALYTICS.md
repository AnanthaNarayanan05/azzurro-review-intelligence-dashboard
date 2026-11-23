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

## 7. Evaluation methodology (planned - Phase 7)

- **Labelled sample:** stratified random sample of ~150–200 real reviews across properties and ratings,
  labelled for overall sentiment and aspect mentions by a human (ideally the project owner), using a
  short labelling guide. A model's own labels are never used as ground truth.
- **Sentiment metrics:** accuracy, per-class precision/recall/F1, macro-F1, confusion matrix.
- **Aspect metrics:** per-aspect precision and recall of mention detection; accuracy of aspect sentiment
  on correctly detected mentions.
- Results, sample size and date of evaluation are written into this document. Until then, no accuracy is claimed.
- Synthetic data is used **only** for software testing, never to report model accuracy.

## 8. Insight generation (planned - Phase 6)

### Deterministic rules engine
Rules run over the metrics layer and produce insight candidates, for example:
| Type | Rule (initial, thresholds configurable) |
|---|---|
| Recurring complaint | Aspect negative mentions ≥ 10 and negative share ≥ 40 % in period |
| Strength to preserve | Aspect mentions ≥ 10 and positive share ≥ 80 % |
| Emerging negative trend | Significant rise in aspect negative share (§6) |
| Property-specific issue | Property's aspect negative share significantly above the other properties' pooled share |
| Cross-property issue | Recurring complaint present at ≥ 2 properties |
| Opportunity | Aspect with high mention rate and mixed sentiment, or rating/sentiment mismatch cluster |

Each candidate carries: properties, aspect, period, supporting review IDs, counts and the exact metrics.

### Evidence strength
- **strong:** ≥ 20 supporting reviews, spread over ≥ 2 months, low-sample flag false.
- **moderate:** ≥ 8 supporting reviews.
- **limited:** below that – shown only in the Insights list with a "limited evidence" label, never as a headline.
(Initial thresholds, to be calibrated against real volumes and documented.)

### Template wording (always available)
Title, explanation and suggested action are rendered from templates using the computed numbers, e.g.
"Breakfast complaints at {property}: {neg} of {mentions} breakfast mentions were negative ({pct}%) between {start} and {end}."
Suggested actions come from a per-aspect action catalogue (e.g. breakfast → review buffet replenishment
schedule and quality checks), clearly presented as suggestions.

### Optional LLM narrative layer
- Off by default (`LLM_PROVIDER=none`). Any paid provider is enabled only after a cost estimate is approved.
- Input: the candidate's metrics JSON + up to N evidence excerpts with their review IDs. Nothing else.
- Output: structured JSON (title, explanation, action, cited_review_ids).
- **Grounding validator:** rejects output if cited IDs are not in the evidence set, if it contains numbers
  not present in the metrics, or if it fails schema validation. On rejection, failure, timeout, rate-limit
  or missing key → template text is kept and the reason is logged (without review text).

## 9. Known limitations

- Keyword aspect extraction misses implicit mentions and can mis-assign ambiguous words ("view", "connection").
- VADER is English-only and can misread sarcasm and mixed sentences; its thresholds and the
  neutral-sentence box rule (section 5) are unevaluated.
- Small review counts per property/month limit trend detection; the system reports this instead of guessing.
- Running many comparisons (4 properties x 8 aspects x several windows) will produce some "significant"
  results by chance; the dashboard presents them as indications with their sample sizes, not as proof.
- Booking.com review exports may not include every field described here; the mapping layer adapts but
  analytics are limited by what the data contains.
