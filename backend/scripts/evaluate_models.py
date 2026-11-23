"""Measure the sentiment and aspect methods against a sample a person has labelled.

Two steps, run from backend/:

1. Draw a sample of GENUINE reviews for a person to label (never synthetic: demo text must not
   be used to report accuracy). The sheet holds the review text but no system output, so
   labelling is not biased:

       .venv/Scripts/python.exe -m scripts.evaluate_models export --size 150

   Fill in `human_sentiment` and `human_aspects` as described in docs/LABELLING_GUIDE.md.

2. Compare the labelled sheet with what the system produces:

       .venv/Scripts/python.exe -m scripts.evaluate_models evaluate --labelled <sheet.csv>

Both files stay in data/processed/ (git-ignored) because they contain review text. The printed
report and the markdown it saves hold aggregate numbers only and may be copied into
docs/AI_ANALYTICS.md section 7.
"""

import argparse
import csv
import random
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.evaluation import (
    MIN_RELIABLE_SAMPLE,
    SENTIMENTS,
    aspect_detection_report,
    parse_human_aspects,
    sentiment_report,
    stance_accuracy,
    system_stances,
)
from app.analytics.nlp.aspects import Lexicon, load_lexicon
from app.analytics.nlp.review_analysis import analyse_review
from app.analytics.nlp.sentiment import SentimentEngine, VaderEngine
from app.core.config import REPO_ROOT
from app.models import Property, Review
from app.models.base import AnalysisStatus

OUT_DIR = REPO_ROOT / "data" / "processed"
SHEET_COLUMNS = [
    "review_id",
    "property",
    "rating",
    "language",
    "positive_text",
    "negative_text",
    "body_text",
    "human_sentiment",
    "human_aspects",
]


def _rating_band(rating) -> str:
    if rating is None:
        return "no rating"
    value = float(rating)
    return "low" if value < 5 else "middle" if value < 8 else "high"


def draw_sample(db: Session, size: int, seed: int) -> list[Review]:
    """Stratified by property and rating band; fixed seed so the same sample can be drawn again.

    Strata are visited round-robin so small ones are not drowned out, and every stratum is shuffled
    with the seed. Only genuine reviews with some text are eligible."""
    reviews = db.scalars(
        select(Review).where(Review.is_synthetic.is_(False)).order_by(Review.id)
    ).all()
    strata: dict[tuple[int, str], list[Review]] = defaultdict(list)
    for review in reviews:
        if review.positive_text or review.negative_text or review.body_text:
            strata[(review.property_id, _rating_band(review.rating))].append(review)
    rng = random.Random(seed)
    queues = []
    for key in sorted(strata):
        group = strata[key]
        rng.shuffle(group)
        queues.append(group)
    picked: list[Review] = []
    while queues and len(picked) < size:
        for queue in list(queues):
            picked.append(queue.pop())
            if not queue:
                queues.remove(queue)
            if len(picked) >= size:
                break
    return picked


def export_sample(db: Session, size: int, seed: int, out_path: Path) -> int:
    names = {p.id: p.name for p in db.scalars(select(Property))}
    sample = draw_sample(db, size, seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for r in sample:
            writer.writerow(
                {
                    "review_id": r.id,
                    "property": names.get(r.property_id, ""),
                    "rating": "" if r.rating is None else r.rating,
                    "language": r.language or "",
                    "positive_text": r.positive_text or "",
                    "negative_text": r.negative_text or "",
                    "body_text": r.body_text or "",
                    "human_sentiment": "",
                    "human_aspects": "",
                }
            )
    return len(sample)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def evaluate_sheet(sheet: Path, lexicon: Lexicon, engine: SentimentEngine) -> tuple[str, dict]:
    """Returns (markdown report, summary numbers). Raises ValueError for an unusable sheet."""
    aspects = [a.key for a in lexicon.aspects]
    with sheet.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    missing = [c for c in SHEET_COLUMNS if rows and c not in rows[0]]
    if missing:
        raise ValueError(f"the sheet is missing columns: {', '.join(missing)}")

    pairs: list[tuple[str, str]] = []
    human_aspect_sets: list[set[str]] = []
    system_aspect_sets: list[set[str]] = []
    human_stances: list[dict[str, str]] = []
    system_stance_maps: list[dict[str, str]] = []
    unlabelled = not_analysed = 0

    for number, row in enumerate(rows, start=2):  # row 1 is the header
        label = (row["human_sentiment"] or "").strip().lower()
        if not label:
            unlabelled += 1
            continue
        if label not in SENTIMENTS:
            raise ValueError(f"row {number}: human_sentiment must be positive, neutral or negative")
        try:
            human = parse_human_aspects(row["human_aspects"] or "", aspects)
        except ValueError as exc:
            raise ValueError(f"row {number}: {exc}") from exc
        result = analyse_review(
            positive_text=row["positive_text"] or None,
            negative_text=row["negative_text"] or None,
            body_text=row["body_text"] or None,
            language=row["language"] or None,
            lexicon=lexicon,
            engine=engine,
        )
        if result.status is not AnalysisStatus.ANALYSED or result.overall is None:
            not_analysed += 1  # the dashboard does not analyse these either; reported, not scored
            continue
        pairs.append((label, result.overall.label.value))
        stances = system_stances((m.aspect_key, m.label.value) for m in result.mentions)
        human_aspect_sets.append(set(human))
        system_aspect_sets.append(set(stances))
        human_stances.append(human)
        system_stance_maps.append(stances)

    if not pairs:
        raise ValueError("no labelled, analysable reviews were found in the sheet")

    sentiment = sentiment_report(pairs)
    detection = aspect_detection_report(human_aspect_sets, system_aspect_sets, aspects)
    correct, compared, stance_acc = stance_accuracy(human_stances, system_stance_maps)

    lines = [
        "# Model evaluation (aggregate numbers only)",
        "",
        f"- Date: {date.today().isoformat()}",
        f"- Labelled reviews scored: {sentiment.n}",
        f"- Rows skipped, not labelled: {unlabelled}",
        f"- Labelled but not analysable by the system (no text or not English): {not_analysed}",
        f"- Sentiment engine: {type(engine).__name__}; aspect lexicon {lexicon.version}",
    ]
    if sentiment.n < MIN_RELIABLE_SAMPLE:
        lines += [
            "",
            "> **Too few labelled reviews to rely on these figures** "
            f"(fewer than {MIN_RELIABLE_SAMPLE}). "
            "Treat them as a first look, not as accuracy.",
        ]
    lines += [
        "",
        "## Overall sentiment of the review text",
        "",
        f"Accuracy {_fmt(sentiment.accuracy)}, macro-F1 {_fmt(sentiment.macro_f1)} "
        f"(n = {sentiment.n}).",
        "",
        "| Class | Human count | System count | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|",
    ]
    for c in sentiment.classes:
        lines.append(
            f"| {c.label} | {c.support} | {c.predicted} | {_fmt(c.precision)} | "
            f"{_fmt(c.recall)} | {_fmt(c.f1)} |"
        )
    lines += [
        "",
        "Confusion matrix (rows: human, columns: system):",
        "",
        "| human \\ system | " + " | ".join(SENTIMENTS) + " |",
        "|---|---|---|---|",
    ]
    for h in SENTIMENTS:
        lines.append(
            f"| {h} | " + " | ".join(str(sentiment.matrix[h][s]) for s in SENTIMENTS) + " |"
        )
    lines += [
        "",
        "## Aspect detection (per review)",
        "",
        "| Aspect | Found by both | System only | Human only | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in detection:
        lines.append(
            f"| {d.aspect} | {d.true_positive} | {d.false_positive} | {d.false_negative} | "
            f"{_fmt(d.precision)} | {_fmt(d.recall)} | {_fmt(d.f1)} |"
        )
    lines += [
        "",
        f"Aspect stance (positive / neutral / negative) agrees on {correct} of {compared} "
        "aspects both "
        f"sides found (accuracy {_fmt(stance_acc)}).",
        "",
        "n/a means there were no cases to divide by (for example no human-marked mentions of an "
        "aspect).",
    ]
    summary = {
        "n": sentiment.n,
        "accuracy": sentiment.accuracy,
        "macro_f1": sentiment.macro_f1,
        "stance_accuracy": stance_acc,
        "unlabelled": unlabelled,
        "not_analysed": not_analysed,
    }
    return "\n".join(lines) + "\n", summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="write a sheet of genuine reviews for a person to label")
    export.add_argument("--size", type=int, default=150)
    export.add_argument("--seed", type=int, default=20260101)
    export.add_argument("--out", type=Path, default=OUT_DIR / "labelling_sample.csv")
    evaluate = sub.add_parser("evaluate", help="score the system against a labelled sheet")
    evaluate.add_argument("--labelled", type=Path, required=True)
    evaluate.add_argument("--report", type=Path, default=OUT_DIR / "evaluation_report.md")
    args = parser.parse_args()

    if args.command == "export":
        from app.core.database import SessionLocal

        with SessionLocal() as db:
            count = export_sample(db, args.size, args.seed, args.out)
        if count == 0:
            print(
                "No genuine reviews with text were found, so nothing was written. "
                "Import real reviews first."
            )
            return 1
        print(f"Wrote {count} reviews to {args.out}. Label them, then run the evaluate step.")
        return 0

    try:
        text, summary = evaluate_sheet(args.labelled, load_lexicon(), VaderEngine())
    except ValueError as exc:
        print(f"Cannot evaluate: {exc}")
        return 2
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(text, encoding="utf-8")
    print(text)
    print(f"Saved to {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
