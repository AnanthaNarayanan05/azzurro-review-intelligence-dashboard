"""Database integrity: constraints, foreign keys and cascades match DATABASE_SCHEMA.md."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AnalysisRun,
    ImportBatch,
    Property,
    PropertyAlias,
    Review,
    SentimentResult,
)

EXPECTED_TABLES = {
    "properties",
    "property_aliases",
    "import_batches",
    "import_row_issues",
    "reviews",
    "analysis_runs",
    "sentiment_results",
    "aspects",
    "aspect_mentions",
    "insights",
    "insight_properties",
    "insight_evidence",
}


def make_property(session: Session, code: str = "p1") -> Property:
    prop = Property(code=code, name=f"Test Property {code}")
    session.add(prop)
    session.flush()
    return prop


def make_import(session: Session) -> ImportBatch:
    batch = ImportBatch(filename="test.csv", file_sha256="0" * 64, source_type="csv")
    session.add(batch)
    session.flush()
    return batch


def make_review(session: Session, prop: Property, batch: ImportBatch, **overrides) -> Review:
    values = {
        "property_id": prop.id,
        "import_id": batch.id,
        "review_date": date(2026, 1, 15),
        "rating": Decimal("8.0"),
        "positive_text": "Friendly staff.",
        "content_hash": overrides.pop("content_hash", "a" * 64),
    }
    values.update(overrides)
    review = Review(**values)
    session.add(review)
    session.flush()
    return review


def test_migration_creates_every_documented_table(engine) -> None:
    tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
    assert tables == EXPECTED_TABLES


def test_sqlite_foreign_keys_are_enforced(db_session: Session) -> None:
    batch = make_import(db_session)
    db_session.add(
        Review(
            property_id=9999,
            import_id=batch.id,
            review_date=date(2026, 1, 1),
            rating=Decimal("7"),
            content_hash="b" * 64,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("rating", [Decimal("-0.5"), Decimal("10.5")])
def test_rating_outside_zero_to_ten_is_rejected(db_session: Session, rating: Decimal) -> None:
    prop, batch = make_property(db_session), make_import(db_session)
    with pytest.raises(IntegrityError):
        make_review(db_session, prop, batch, rating=rating)


def test_review_without_any_text_or_rating_is_rejected(db_session: Session) -> None:
    prop, batch = make_property(db_session), make_import(db_session)
    with pytest.raises(IntegrityError):
        make_review(db_session, prop, batch, rating=None, positive_text=None)


def test_review_with_rating_but_no_text_is_allowed(db_session: Session) -> None:
    prop, batch = make_property(db_session), make_import(db_session)
    review = make_review(db_session, prop, batch, positive_text=None)
    assert review.id is not None


def test_property_code_and_name_are_unique(db_session: Session) -> None:
    make_property(db_session, "dup")
    db_session.add(Property(code="dup", name="Another name"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_property_alias_is_unique_across_properties(db_session: Session) -> None:
    first, second = make_property(db_session, "a"), make_property(db_session, "b")
    db_session.add(PropertyAlias(property_id=first.id, alias_normalised="hotel a"))
    db_session.flush()
    db_session.add(PropertyAlias(property_id=second.id, alias_normalised="hotel a"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_content_hash_detects_duplicate_reviews(db_session: Session) -> None:
    prop, batch = make_property(db_session), make_import(db_session)
    make_review(db_session, prop, batch, content_hash="c" * 64)
    with pytest.raises(IntegrityError):
        make_review(db_session, prop, batch, content_hash="c" * 64)


def test_external_id_unique_per_source_but_nulls_allowed(db_session: Session) -> None:
    prop, batch = make_property(db_session), make_import(db_session)
    make_review(db_session, prop, batch, content_hash="1" * 64, external_review_id=None)
    make_review(db_session, prop, batch, content_hash="2" * 64, external_review_id=None)
    make_review(db_session, prop, batch, content_hash="3" * 64, external_review_id="BK-1")
    with pytest.raises(IntegrityError):
        make_review(db_session, prop, batch, content_hash="4" * 64, external_review_id="BK-1")


def test_sentiment_label_must_be_controlled_value(db_session: Session) -> None:
    prop, batch = make_property(db_session), make_import(db_session)
    review = make_review(db_session, prop, batch)
    run = AnalysisRun(triggered_by="manual", sentiment_engine="vader", aspect_lexicon_version="1")
    db_session.add(run)
    db_session.flush()
    db_session.add(
        SentimentResult(
            review_id=review.id,
            analysis_run_id=run.id,
            segment="overall",
            # short enough to fit the column, so the CHECK constraint (not the length) rejects it
            label="unhappy",
            score=Decimal("0.5"),
            model_name="vader",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_import_cascades_to_reviews_and_analysis(db_session: Session) -> None:
    prop, batch = make_property(db_session), make_import(db_session)
    review = make_review(db_session, prop, batch)
    run = AnalysisRun(triggered_by="import", sentiment_engine="vader", aspect_lexicon_version="1")
    db_session.add(run)
    db_session.flush()
    db_session.add(
        SentimentResult(
            review_id=review.id,
            analysis_run_id=run.id,
            segment="overall",
            label="positive",
            score=Decimal("0.6"),
            model_name="vader",
        )
    )
    db_session.flush()

    db_session.delete(batch)
    db_session.flush()
    db_session.expunge_all()

    assert db_session.scalars(select(Review)).all() == []
    assert db_session.scalars(select(SentimentResult)).all() == []
    assert db_session.get(Property, prop.id) is not None


def test_property_with_reviews_cannot_be_deleted(db_session: Session) -> None:
    prop, batch = make_property(db_session), make_import(db_session)
    make_review(db_session, prop, batch)
    db_session.expunge_all()

    with pytest.raises(IntegrityError):
        db_session.execute(Property.__table__.delete().where(Property.id == prop.id))


def test_ingestion_migration_upgrades_a_database_that_already_has_data(tmp_path):
    """The ingestion migration adds NOT NULL columns; it must not fail on existing rows."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    from tests.conftest import BACKEND_DIR

    url = f"sqlite:///{(tmp_path / 'old.db').as_posix()}"
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "4d3a2519d93a")  # the Phase 2 schema
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO import_batches (filename, file_sha256, source_type, source_name, "
                "column_mapping, rating_scale_max, status, total_rows, imported_rows, "
                "rejected_rows, duplicate_rows, is_synthetic, created_at) VALUES "
                "('old.csv', 'abc', 'csv', 'booking.com', '{}', 10, 'completed', 1, 1, 0, 0, 0, "
                "'2026-01-01')"
            )
        )
    command.upgrade(config, "head")
    with engine.connect() as conn:
        row = conn.execute(text("SELECT updated_rows, import_options FROM import_batches")).one()
    assert row[0] == 0
    assert row[1] == "{}"
    engine.dispose()
