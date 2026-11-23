"""Load and clear the SYNTHETIC demo dataset through the normal import pipeline."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.models import ImportBatch, Property, Review
from app.services.demo_data import generate_csv, load_demo_properties
from app.services.ingestion import pipeline
from app.services.ingestion.mapping import suggest_mapping
from app.services.ingestion.normalise import normalise_for_match
from app.services.properties import PropertyIndex, make_code

DEMO_FILENAME = "synthetic_demo_reviews.csv"


def demo_status(db: Session) -> dict:
    batches = list(
        db.scalars(
            select(ImportBatch).where(ImportBatch.is_synthetic.is_(True)).order_by(ImportBatch.id)
        )
    )
    count = (
        db.scalar(select(func.count()).select_from(Review).where(Review.is_synthetic.is_(True)))
        or 0
    )
    return {
        "loaded": count > 0,
        "synthetic_review_count": count,
        "import_ids": [b.id for b in batches],
    }


def load_demo(db: Session, settings: Settings, today: date | None = None) -> ImportBatch:
    if demo_status(db)["loaded"]:
        raise AppError(
            409,
            "DEMO_ALREADY_LOADED",
            "Demo data is already loaded. Remove it first if you want to regenerate it.",
        )
    demo_properties = load_demo_properties()

    # Make sure the properties exist (reuse any that already match by name).
    index = PropertyIndex(db)
    codes = set(db.scalars(select(Property.code)))
    property_mapping: dict[str, int] = {}
    for demo in demo_properties:
        match = index.exact(demo.name)
        if match:
            property_mapping[demo.name] = match.property_id
            continue
        code = demo.code if demo.code not in codes else make_code(demo.name, codes)
        prop = Property(name=demo.name, code=code)
        db.add(prop)
        db.flush()
        codes.add(code)
        property_mapping[demo.name] = prop.id
    db.commit()

    data = generate_csv(today or date.today())
    preview = pipeline.create_preview(db, settings, DEMO_FILENAME, data)
    mapping = {k: v for k, v in suggest_mapping(preview.table.columns).items() if v}
    request = pipeline.CommitRequest(
        column_mapping=mapping,
        property_mapping={
            raw: pid for raw, pid in property_mapping.items() if normalise_for_match(raw)
        },
        date_format="iso",
        is_synthetic=True,
        remember_aliases=False,
    )
    return pipeline.commit_import(db, settings, preview.batch.id, request)


def clear_demo(db: Session, settings: Settings) -> int:
    """Remove every synthetic import (and its reviews). Genuine data is never touched."""
    batches = list(db.scalars(select(ImportBatch).where(ImportBatch.is_synthetic.is_(True))))
    return pipeline.purge_batches(db, settings, batches)
