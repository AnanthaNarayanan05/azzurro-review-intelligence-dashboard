# Hand-calculated expectations for `validation_reviews.csv`

21 invented reviews for three invented hotels (Alpha, Beta, Gamma). They exist only to check the
analytics arithmetic; they are not real guest data. Every expected value below was worked out by
hand, then asserted in `tests/test_analytics_api.py`.

Test settings use small thresholds so a small file can exercise the guards:
`min_sample_comparison = 6`, `min_aspect_mentions = 3`, `min_sample_trend_window = 4`.

## Sentence sentiment (VADER compound, thresholds +/-0.05)

| Sentence | Score | Label |
|---|---|---|
| Great location close to the train station. | 0.625 | positive |
| The room was clean. | 0.402 | positive |
| Staff were friendly. | 0.494 | positive |
| Great value for money. | 0.758 | positive |
| The bathroom was dirty. | -0.440 | negative |
| Staff were rude and unhelpful. | -0.459 | negative |
| Noisy at night. | -0.178 | negative |
| The wifi was slow and kept dropping. | 0.000 | neutral (becomes a *negative mention* because it is in the "disliked" box) |

"Nothing" / "N/A" are placeholders and are not scored.

## Review outcomes

| Hotel | Rated | Mean rating | Overall sentiment |
|---|---|---|---|
| Alpha | 10 (9,9,8,8,7,7,6,6,10,1) | 71/10 = 7.10 | 5 positive (A1,A2,A3,A4,A9), 2 neutral (A5 = (0.402-0.440)/2 = -0.019; A7 = 0.000), 3 negative (A6,A8,A10) |
| Beta | 6 (5,6,5,6,5,6) | 33/6 = 5.50 | 1 positive (B6), 5 negative |
| Gamma | 5 (10,10,9,9,10) | 48/5 = 9.60 | 3 positive (G1,G2,G3); G4 is French (not scored); G5 has no text |

All hotels: 21 rated, mean 152/21 = 7.24; 19 analysed; 9 positive (0.4737), 2 neutral (0.1053),
8 negative (0.4211); 1 `no_text`, 1 `non_english`.

Rating distribution (integer bins, last bin holds 9 and 10): 1-2: 1, 5-6: 3, 6-7: 5, 7-8: 2,
8-9: 2, 9-10: 8.

## Aspects (a review counts once per aspect; label = sign of positive minus negative mentions)

| Aspect | Reviews | Positive | Neutral | Negative |
|---|---|---|---|---|
| staff_service | 10 | 4 | 0 | 6 |
| cleanliness | 4 | 2 | 1 (A5: clean room + dirty bathroom cancel out) | 1 |
| location | 2 | 2 | 0 | 0 |
| room_comfort | 2 | 0 | 0 | 2 |
| facilities | 2 | 0 | 0 | 2 |
| value_for_money | 2 | 2 | 0 | 0 |
| wifi_connectivity | 1 | 0 | 0 | 1 |

staff_service mention rate = 10/19 = 0.5263.

## Comparison of ratings (95% interval = mean +/- 1.96 x sd/sqrt(n))

* All Alpha reviews: sd^2 = 56.9/9 = 6.322, interval 5.54 to 8.66. Beta: sd^2 = 0.3, interval
  5.06 to 5.94. They overlap, so **no best/worst is named** (`difference_not_significant`). Gamma has
  5 < 6 rated reviews, so it is excluded as `low_sample`.
* Same comparison with `date_to=2026-03-30` (drops Alpha's rating of 1): Alpha mean 7.78,
  interval 6.87 to 8.69; Beta's upper limit 5.94 is below it, so Alpha is best and Beta worst.

## Trends (Alpha, weekly, window 2 weeks, as_of 2026-03-29, a Sunday)

* Recent window 2026-03-16 to 2026-03-29: A5,A6,A7,A8 -> ratings 7,7,6,6, mean 6.5, variance 1/3.
* Previous window 2026-03-02 to 2026-03-15: A1..A4 -> ratings 9,9,8,8, mean 8.5, variance 1/3.
* Difference -2.0, margin 1.96 x sqrt(1/12 + 1/12) = 0.8002, interval -2.8002 to -1.1998:
  excludes zero and exceeds the 0.3-point practical threshold -> `decrease`.
* Negative-sentiment share: recent 2/4 = 0.5, previous 0/4 = 0. Margin 1.96 x sqrt(0.25/4) = 0.49,
  interval 0.01 to 0.99 -> `increase`.
* A10 (2026-03-31) is after `as_of` and must not appear anywhere in a trend.
* With `as_of = 2026-03-26` (a Thursday) the week of 03-23 is incomplete, so the recent window moves
  back to 03-09..03-22 (4 reviews) and the previous window holds only 2 reviews: `insufficient_data`.
