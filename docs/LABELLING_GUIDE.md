# Labelling guide (for the accuracy check)

Purpose: to measure how often the system's sentiment and aspect labels agree with a person's judgement. The
numbers are only as good as these labels, so please label **from the text alone, without looking at what the
system said** (the sheet does not contain it).

You need roughly **150–200 genuine reviews**. Fewer than 100 are reported with a warning that the figures are too
few to rely on. Synthetic demo reviews are never used for this.

## Steps

1. Import the real reviews (Data Import). Then, from `backend/`:

   ```powershell
   .venv\Scripts\python.exe -m scripts.evaluate_models export --size 150
   ```

   This writes `data/processed/labelling_sample.csv` (git-ignored, because it contains review text). The sample is
   spread across properties and rating bands and uses a fixed seed, so it can be drawn again.
2. Open it in Excel. Fill in the two empty columns, **`human_sentiment`** and **`human_aspects`**, for every row you
   label. Rows left blank are skipped and reported. Do not edit the other columns.
3. Save as CSV (UTF-8) and run:

   ```powershell
   .venv\Scripts\python.exe -m scripts.evaluate_models evaluate --labelled data\processed\labelling_sample.csv
   ```

   It prints the metrics, saves `data/processed/evaluation_report.md`, and refuses a sheet with a typo (it names
   the row) rather than guessing.
4. Copy the aggregate figures (never review text) into `docs/AI_ANALYTICS.md` §7 with the sample size and date.

## `human_sentiment`: the overall tone of what the guest wrote

One word, lower case: `positive`, `neutral` or `negative`.

- Judge the guest's **written text** as a whole (the positive box, the negative box and any single comment together),
  not the numeric rating. A 7/10 review that is mostly complaints is `negative`.
- Mixed review, one clear overall lean: choose that lean. Mixed review with no lean: `neutral`.
- Placeholders such as "Nothing" or "N/A" in a box carry no opinion; ignore that box.

## `human_aspects`: which topics the guest mentions, and how they feel about each

Format: `aspect:stance` pairs separated by `;`, for example `cleanliness:negative; staff_service:positive`.
Leave it empty if no topic is mentioned. List each aspect **once**, with one stance (`positive`, `neutral` or
`negative`); if the guest is mixed on a topic, choose the dominant feeling.

Aspect names (exactly as written):

| Name | Mention it when the guest talks about |
|---|---|
| `cleanliness` | cleanliness, dirt, smell, bedding, bathroom condition, pests |
| `staff_service` | staff, reception, courtesy, helpfulness, check-in and check-out service |
| `location` | where the hotel is: transport, shops, walking distance, noise from the street |
| `room_comfort` | the room itself: size, bed, noise, temperature, view, layout |
| `facilities` | gym, pool, lift, parking, lobby and other amenities |
| `food_breakfast` | breakfast, restaurant, food and drink |
| `value_for_money` | price against what was received |
| `wifi_connectivity` | Wi-Fi and internet |

Mark an aspect even when the guest says it **indirectly** (for example "we couldn't sleep, the walls are thin" is
`room_comfort:negative`). Those implied mentions are exactly what a keyword method can miss, and the report
measures that.

## How to read the result

- **Accuracy and macro-F1** summarise sentiment agreement; the per-class table and confusion matrix show *where*
  the system goes wrong (for example neutral reviews called negative).
- **Aspect detection** reports, per aspect, how many reviews both found, how many only the system found (false
  alarms) and how many only you found (misses).
- **n/a** means there were no cases to divide by, not zero.
- One person's labels are one opinion. If time allows, have a second person label the same 30 rows and compare;
  low agreement between people sets a ceiling on what the system can be expected to reach.
