"""The evaluation arithmetic is checked against numbers worked out by hand, and the labelling sheet
workflow against a tiny database. No accuracy figure is asserted for the real methods: that needs a
human-labelled sample of real reviews (docs/AI_ANALYTICS.md section 7)."""

import csv
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.analytics.evaluation import (
    aspect_detection_report,
    f1_score,
    parse_human_aspects,
    ratio,
    sentiment_report,
    stance_accuracy,
    system_stances,
)
from app.analytics.nlp.aspects import load_lexicon
from app.analytics.nlp.sentiment import VaderEngine
from app.models import ImportBatch, Property, Review
from scripts.evaluate_models import SHEET_COLUMNS, draw_sample, evaluate_sheet, export_sample

P, U, N = "positive", "neutral", "negative"

# 15 (human, system) pairs. Worked out by hand:
#   correct 6 + 1 + 3 = 10 of 15            -> accuracy 2/3
#   positive: support 8, predicted 8, tp 6  -> precision 0.75, recall 0.75, F1 0.75
#   neutral:  support 2, predicted 4, tp 1  -> precision 0.25, recall 0.5,  F1 1/3
#   negative: support 5, predicted 3, tp 3  -> precision 1.0,  recall 0.6,  F1 0.75
#   macro-F1 = (0.75 + 1/3 + 0.75) / 3 = 0.6111...
PAIRS = [(P, P)] * 6 + [(P, U)] * 2 + [(U, U)] + [(U, P)] + [(N, N)] * 3 + [(N, U)] + [(N, P)]


def test_sentiment_report_matches_hand_calculation():
    report = sentiment_report(PAIRS)
    assert report.n == 15
    assert report.accuracy == pytest.approx(2 / 3)
    by = {c.label: c for c in report.classes}
    assert (by[P].support, by[P].predicted, by[P].true_positive) == (8, 8, 6)
    assert by[P].precision == pytest.approx(0.75) and by[P].recall == pytest.approx(0.75)
    assert (by[U].support, by[U].predicted) == (2, 4)
    assert by[U].precision == pytest.approx(0.25) and by[U].recall == pytest.approx(0.5)
    assert by[U].f1 == pytest.approx(1 / 3)
    assert (by[N].support, by[N].predicted) == (5, 3)
    assert by[N].precision == pytest.approx(1.0) and by[N].recall == pytest.approx(0.6)
    assert by[N].f1 == pytest.approx(0.75)
    assert report.macro_f1 == pytest.approx((0.75 + 1 / 3 + 0.75) / 3)


def test_confusion_matrix_rows_are_human_columns_are_system():
    matrix = sentiment_report(PAIRS).matrix
    assert matrix[P] == {P: 6, U: 2, N: 0}
    assert matrix[U] == {P: 1, U: 1, N: 0}
    assert matrix[N] == {P: 1, U: 1, N: 3}
    assert sum(sum(row.values()) for row in matrix.values()) == 15


def test_a_class_nobody_labelled_is_left_out_of_the_macro_average():
    report = sentiment_report([(P, P), (P, P), (N, P)])
    by = {c.label: c for c in report.classes}
    assert by[U].support == 0 and by[U].recall is None
    # positive: precision 2/3, recall 1 -> F1 0.8; negative: tp 0 -> F1 0. Neutral is excluded.
    assert report.macro_f1 == pytest.approx((0.8 + 0.0) / 2)


def test_nothing_to_divide_is_none_not_zero():
    assert ratio(0, 0) is None
    assert f1_score(None, 0.5) is None
    assert f1_score(None, 0.0) == 0.0  # humans found cases, the system predicted none
    assert f1_score(0.0, 0.0) == 0.0
    empty = sentiment_report([])
    assert empty.accuracy is None and empty.macro_f1 is None


def test_aspect_detection_counts_per_review():
    human = [{"cleanliness", "staff"}, {"cleanliness"}, {"staff"}, set()]
    system = [{"cleanliness"}, {"cleanliness", "staff"}, {"staff", "wifi"}, {"wifi"}]
    rows = {
        r.aspect: r
        for r in aspect_detection_report(human, system, ["cleanliness", "staff", "wifi"])
    }
    c, s, w = rows["cleanliness"], rows["staff"], rows["wifi"]
    assert (c.true_positive, c.false_positive, c.false_negative) == (2, 0, 0)
    assert c.precision == 1.0 and c.recall == 1.0
    assert (s.true_positive, s.false_positive, s.false_negative) == (1, 1, 1)
    assert s.precision == 0.5 and s.recall == 0.5 and s.f1 == 0.5
    assert (w.true_positive, w.false_positive, w.false_negative) == (0, 2, 0)
    assert w.precision == 0.0 and w.recall is None and w.f1 is None


def test_aspect_lists_must_line_up():
    with pytest.raises(ValueError):
        aspect_detection_report([set()], [set(), set()], ["a"])


def test_stance_accuracy_only_compares_aspects_both_sides_found():
    human = [{"cleanliness": N, "staff": P}, {"cleanliness": N}]
    system = [{"cleanliness": N}, {"cleanliness": P, "staff": P}]
    assert stance_accuracy(human, system) == (1, 2, 0.5)
    assert stance_accuracy([{}], [{"a": P}]) == (0, 0, None)


def test_system_stance_follows_the_dashboards_net_balance_rule():
    stances = system_stances([("a", P), ("a", P), ("a", N), ("b", N), ("c", P), ("c", N), ("d", U)])
    assert stances == {"a": P, "b": N, "c": U, "d": U}


def test_parse_human_aspects_accepts_good_input_and_names_every_problem():
    valid = ["cleanliness", "staff_service"]
    assert parse_human_aspects(" Cleanliness : Negative ; staff_service:positive ", valid) == {
        "cleanliness": N,
        "staff_service": P,
    }
    assert parse_human_aspects("", valid) == {}
    with pytest.raises(ValueError, match="unknown aspect 'clean'"):
        parse_human_aspects("clean:negative", valid)
    with pytest.raises(ValueError, match="needs a stance"):
        parse_human_aspects("cleanliness:bad", valid)
    with pytest.raises(ValueError, match="listed twice"):
        parse_human_aspects("cleanliness:negative;cleanliness:positive", valid)


# ---------------------------------------------------------------- the labelling workflow
def _property(db: Session, name: str) -> Property:
    prop = Property(code=name[:3].upper(), name=name)
    db.add(prop)
    db.flush()
    return prop


def _reviews(
    db: Session, prop: Property, batch: ImportBatch, n: int, *, synthetic: bool, rating, start: int
):
    for i in range(n):
        db.add(
            Review(
                property_id=prop.id,
                import_id=batch.id,
                review_date=date(2026, 2, 1),
                rating=rating,
                positive_text=f"Lovely stay number {start + i}.",
                content_hash=f"{start + i:064d}",
                is_synthetic=synthetic,
            )
        )
    db.flush()


@pytest.fixture()
def populated(db_session: Session) -> Session:
    batch = ImportBatch(filename="t.csv", file_sha256="0" * 64, source_type="csv")
    db_session.add(batch)
    db_session.flush()
    a, b = _property(db_session, "Alpha"), _property(db_session, "Beta")
    _reviews(db_session, a, batch, 6, synthetic=False, rating=Decimal("9.0"), start=1)
    _reviews(db_session, a, batch, 2, synthetic=False, rating=Decimal("3.0"), start=100)
    _reviews(db_session, b, batch, 4, synthetic=False, rating=Decimal("6.5"), start=200)
    _reviews(db_session, b, batch, 5, synthetic=True, rating=Decimal("9.0"), start=300)
    db_session.commit()
    return db_session


def test_sample_never_includes_synthetic_reviews(populated: Session):
    sample = draw_sample(populated, 100, seed=1)
    assert len(sample) == 12  # only the genuine reviews exist
    assert not any(r.is_synthetic for r in sample)


def test_sample_is_repeatable_and_covers_every_stratum_first(populated: Session):
    first = [r.id for r in draw_sample(populated, 3, seed=7)]
    assert first == [r.id for r in draw_sample(populated, 3, seed=7)]
    # Three strata exist (Alpha high, Alpha low, Beta middle): asking for 3 takes one from each.
    kinds = {(r.property_id, float(r.rating)) for r in draw_sample(populated, 3, seed=7)}
    assert len(kinds) == 3


def test_export_writes_blank_label_columns_and_no_system_output(populated: Session, tmp_path):
    out = tmp_path / "sheet.csv"
    assert export_sample(populated, 5, seed=1, out_path=out) == 5
    with out.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0].keys()) == SHEET_COLUMNS
    assert all(r["human_sentiment"] == "" and r["human_aspects"] == "" for r in rows)
    assert not any("sentiment_score" in key or "system" in key for key in rows[0])


def _sheet(tmp_path, rows):
    path = tmp_path / "labelled.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in SHEET_COLUMNS})
    return path


def test_evaluate_sheet_scores_a_handmade_sheet(tmp_path):
    sheet = _sheet(
        tmp_path,
        [
            {
                "review_id": 1,
                "language": "en",
                "positive_text": "The room was spotless and the staff were wonderful.",
                "human_sentiment": "positive",
                "human_aspects": "cleanliness:positive; staff_service:positive",
            },
            {
                "review_id": 2,
                "language": "en",
                "negative_text": "The room was dirty and the bathroom was filthy.",
                "human_sentiment": "negative",
                "human_aspects": "cleanliness:negative",
            },
            {
                "review_id": 3,
                "language": "en",
                "positive_text": "Lovely stay.",
                "human_sentiment": "positive",
            },
            {
                "review_id": 4,
                "language": "en",
                "positive_text": "Not labelled yet.",
                "human_sentiment": "",
            },
            {
                "review_id": 5,
                "language": "fr",
                "positive_text": "Très bien.",
                "human_sentiment": "positive",
            },
        ],
    )
    text, summary = evaluate_sheet(sheet, load_lexicon(), VaderEngine())
    assert summary["n"] == 3
    assert summary["unlabelled"] == 1
    assert summary["not_analysed"] == 1  # the French review is reported, not scored
    assert summary["accuracy"] == 1.0
    assert "Too few labelled reviews" in text  # 3 is far below the reliable minimum
    assert "Lovely stay" not in text and "spotless" not in text  # aggregate numbers only


def test_evaluate_sheet_rejects_bad_labels_with_the_row_number(tmp_path):
    bad_sentiment = _sheet(
        tmp_path, [{"positive_text": "ok", "language": "en", "human_sentiment": "great"}]
    )
    with pytest.raises(ValueError, match="row 2"):
        evaluate_sheet(bad_sentiment, load_lexicon(), VaderEngine())
    bad_aspect = _sheet(
        tmp_path,
        [
            {
                "positive_text": "ok",
                "language": "en",
                "human_sentiment": "positive",
                "human_aspects": "pool:positive",
            }
        ],
    )
    with pytest.raises(ValueError, match="unknown aspect 'pool'"):
        evaluate_sheet(bad_aspect, load_lexicon(), VaderEngine())
    with pytest.raises(ValueError, match="no labelled"):
        evaluate_sheet(
            _sheet(tmp_path, [{"positive_text": "ok", "language": "en"}]),
            load_lexicon(),
            VaderEngine(),
        )
