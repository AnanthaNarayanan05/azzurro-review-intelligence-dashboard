# AI & Analytics Methodology

Status: Proposed (Phase 1). **No model has been evaluated yet** – choices below are the plan, and the
final selection will be made from measured results on the real dataset.

## 1. Principles

1. Deterministic, reproducible core: the same data + configuration gives the same numbers.
2. Explainable first: start with transparent methods; add complexity only if evaluation shows it is needed.
3. Rating and text sentiment are separate measurements.
4. Generated text may explain numbers but never create them.

## 2. Pre-processing

- Keep the original text untouched in `reviews`; analysis works on a normalised copy.
- **Booking.com placeholder handling:** values such as "Nothing", "None", "N/A", "-", "Nothing to dislike",
  "Everything" are common in the liked/disliked fields. A configurable placeholder list marks these as
  *no substantive text* so they are not scored (a "Nothing" in the *disliked* box is not a negative review).
- Sentence segmentation (rule-based splitter tuned for review text: line breaks, `.!?`, bullet characters).
- Language: use the export's language column if present, otherwise detect. Non-English handling is
  decided after seeing the language mix (see §4).

## 3. Sentiment analysis

### Candidates
| Option | Pros | Cons |
|---|---|---|
| **VADER** (baseline) | Fast, no GPU, deterministic, explainable lexicon, handles negation/intensifiers | English only; weaker on sarcasm and domain phrases ("room was small but fine") |
| **Pretrained transformer** (e.g. a RoBERTa sentiment model; a multilingual XLM-R model if needed) | Better context handling; multilingual options exist | Large dependency (PyTorch), slower on CPU, harder to explain, heavier to host |
| **Hybrid** | Use VADER, fall back to transformer for low-confidence / non-English text | More moving parts |

### Plan
1. Implement VADER as the baseline engine behind a `SentimentEngine` interface.
2. Score **per segment**: `positive` field, `negative` field, `body` (if single-field source).
3. `overall` review sentiment = mean compound score over all substantive sentences across segments;
   thresholds `≥ 0.05` positive, `≤ −0.05` negative, otherwise neutral (VADER's standard thresholds,
   to be re-checked on the labelled sample).
4. Evaluate on a manually labelled sample (§7). Introduce a transformer only if it improves macro-F1
   materially and the hosting cost is acceptable. Because results are stored, a heavier model can run
   locally/offline at import time while the hosted backend only serves stored results.

## 4. Multilingual reviews

Booking.com reviews are often multilingual. Options, chosen once the language distribution is known:
- If ≥ ~90 % English: analyse English; show non-English reviews in the explorer with "not text-analysed" and report the excluded count.
- Otherwise: a multilingual transformer for sentiment, plus translated keyword lists for the main languages in the aspect lexicon.
- Machine translation via a paid API is **not** planned without approval.

## 5. Aspect-based sentiment

### Baseline (explainable, rule-based)
- `aspect_lexicon.yaml` defines each aspect with keywords/phrases and exclusions, e.g.
  - cleanliness: clean, dirty, dust, stain, hygiene, smell, mould, spotless …
  - staff_service: staff, reception, receptionist, friendly, rude, helpful, check-in …
  - location: location, central, walking distance, beach, metro, noisy street …
  - room_comfort: bed, pillow, mattress, noise, air conditioning, spacious, small room …
  - facilities: pool, gym, parking, lift/elevator, spa, bathroom, shower …
  - food_breakfast: breakfast, buffet, coffee, restaurant, food, dinner …
  - value_for_money: price, value, expensive, overpriced, worth, cheap …
  - wifi_connectivity: wifi, wi-fi, internet, connection, signal …
- Matching on lemmatised, lower-cased tokens with word boundaries; multi-word phrases supported.
- **Aspect sentiment = sentiment of the matched sentence**, with the Booking.com field as a prior: a
  mention in the *disliked* field that scores neutral is labelled negative only if the sentence is
  substantive (configurable rule, validated in evaluation).
- Each mention stores `matched_term` and `evidence_text` so every number is traceable to a sentence.

### Metrics per aspect
Mention count (reviews mentioning the aspect), positive / neutral / negative mention counts, sentiment
share (denominator = mentions of that aspect), mention rate (denominator = reviews with substantive
text), and example evidence.

### When to go beyond keywords
If evaluation shows poor recall (e.g. many implicit mentions missed) an embedding- or zero-shot-based
classifier can be evaluated, but only if it measurably improves results.

## 6. Trend detection

- Default granularity: month (quarter if volumes are low).
- Compare the most recent window (default 3 months) with the previous window of equal length.
- **Minimum sample:** each window must have ≥ `MIN_SAMPLE_TREND_WINDOW` (default 30) reviews, otherwise
  the API returns `insufficient_data` and the UI says so.
- Proportions (negative share, aspect negative share): two-proportion test with Wilson intervals; a
  change is reported only when it is statistically meaningful **and** above a practical threshold
  (e.g. ≥ 5 percentage points).
- Average rating: difference of means with a confidence interval (Welch); report direction only when the
  interval excludes zero.
- **Emerging complaint:** an aspect whose negative-mention share rises significantly between windows and
  has ≥ a minimum number of recent negative mentions.

## 7. Evaluation methodology

- **Labelled sample:** stratified random sample of ~150–200 real reviews across properties and ratings,
  labelled for overall sentiment and aspect mentions by a human (ideally the project owner), using a
  short labelling guide. A model's own labels are never used as ground truth.
- **Sentiment metrics:** accuracy, per-class precision/recall/F1, macro-F1, confusion matrix.
- **Aspect metrics:** per-aspect precision and recall of mention detection; accuracy of aspect sentiment
  on correctly detected mentions.
- Results, sample size and date of evaluation are written into this document. Until then, no accuracy is claimed.
- Synthetic data is used **only** for software testing, never to report model accuracy.

## 8. Insight generation

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

## 9. Known limitations (initial)

- Keyword aspect extraction misses implicit mentions and can mis-assign ambiguous words ("bar", "view").
- VADER is English-only and can misread sarcasm and mixed sentences.
- Small review counts per property/month limit trend detection; the system reports this instead of guessing.
- Booking.com review exports may not include every field described here; the mapping layer adapts but
  analytics are limited by what the data contains.
