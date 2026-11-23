"""Read-only analytics endpoints. Every number comes from stored reviews and stored analysis
results."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import metrics
from app.analytics.metrics import DataScope, Filters, Granularity, TrendMetric
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Aspect, Property
from app.models.base import SentimentLabel

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _parse_ids(raw: str | None) -> tuple[int, ...] | None:
    if not raw:
        return None
    try:
        ids = tuple(int(part) for part in raw.split(",") if part.strip())
    except ValueError as exc:
        raise AppError(
            422, "INVALID_FILTER", "property_ids must be a comma-separated list of integers."
        ) from exc
    return ids or None


def get_filters(
    property_ids: Annotated[str | None, Query(description="Comma-separated property ids")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    data_scope: DataScope = "genuine",
) -> Filters:
    if date_from and date_to and date_from > date_to:
        raise AppError(422, "INVALID_FILTER", "date_from must not be after date_to.")
    return Filters(_parse_ids(property_ids), date_from, date_to, data_scope)


@router.get("/overview")
def get_overview(
    f: Filters = Depends(get_filters),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return {"data": metrics.overview(db, f, settings)}


@router.get("/comparison")
def get_comparison(
    f: Filters = Depends(get_filters),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return {"data": metrics.comparison(db, f, settings)}


@router.get("/properties/{property_id}")
def get_property(
    property_id: int,
    f: Filters = Depends(get_filters),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    if db.get(Property, property_id) is None:
        raise AppError(404, "PROPERTY_NOT_FOUND", f"Property {property_id} does not exist.")
    return {"data": metrics.property_detail(db, property_id, f, settings)}


@router.get("/aspects")
def get_aspects(
    f: Filters = Depends(get_filters),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return {"data": metrics.aspect_summary(db, f, settings)}


@router.get("/aspects/{aspect_key}/examples")
def get_aspect_examples(
    aspect_key: str,
    sentiment: SentimentLabel = SentimentLabel.NEGATIVE,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    f: Filters = Depends(get_filters),
    db: Session = Depends(get_db),
) -> dict:
    exists = db.scalar(
        select(Aspect.id).where(Aspect.key == aspect_key, Aspect.is_active.is_(True))
    )
    if exists is None:
        raise AppError(404, "ASPECT_NOT_FOUND", f"Aspect '{aspect_key}' does not exist.")
    return {"data": metrics.aspect_examples(db, f, aspect_key, sentiment, limit)}


@router.get("/trends")
def get_trends(
    metric: TrendMetric = "avg_rating",
    granularity: Granularity = "month",
    aspect: str | None = None,
    window: Annotated[int | None, Query(ge=1, le=26)] = None,
    as_of: date | None = None,
    f: Filters = Depends(get_filters),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    if metric == "aspect_negative_share" and not aspect:
        raise AppError(422, "INVALID_FILTER", "metric 'aspect_negative_share' requires an aspect.")
    if aspect and db.scalar(select(Aspect.id).where(Aspect.key == aspect)) is None:
        raise AppError(404, "ASPECT_NOT_FOUND", f"Aspect '{aspect}' does not exist.")
    return {
        "data": metrics.trends(
            db,
            f,
            settings,
            metric_name=metric,
            granularity=granularity,
            aspect_key=aspect,
            window=window,
            as_of=as_of or date.today(),
        )
    }
