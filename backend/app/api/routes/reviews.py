"""Review explorer: search, filter and read individual reviews with their stored analysis."""

from collections import defaultdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.analytics.metrics import Filters, aspect_review_labels
from app.api.routes.analytics import get_filters
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Aspect, AspectMention, Property, Review, SentimentResult
from app.models.base import SentimentLabel, TextSegment
from app.schemas.common import DataResponse, ListResponse, PageMeta
from app.schemas.reviews import (
    AspectLabel,
    MentionRead,
    ReviewDetail,
    ReviewListItem,
    SegmentSentiment,
    SentimentSummary,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])

Sort = Literal["newest", "oldest", "rating_desc", "rating_asc"]


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _aspect_labels(db: Session, review_ids: list[int]) -> dict[int, list[AspectLabel]]:
    """Per review and aspect: sign of (positive - negative mentions), as the analytics use."""
    if not review_ids:
        return {}
    rows = db.execute(
        select(
            AspectMention.review_id, Aspect.key, Aspect.display_name, AspectMention.sentiment_label
        )
        .join(Aspect, Aspect.id == AspectMention.aspect_id)
        .where(AspectMention.review_id.in_(review_ids), Aspect.is_active.is_(True))
    ).all()
    balance: dict[tuple[int, str], int] = defaultdict(int)
    names: dict[str, str] = {}
    for review_id, key, display_name, label in rows:
        names[key] = display_name
        balance[(review_id, key)] += {"positive": 1, "negative": -1}.get(label, 0)
    out: dict[int, list[AspectLabel]] = defaultdict(list)
    for (review_id, key), value in sorted(balance.items(), key=lambda kv: kv[0][1]):
        label = "positive" if value > 0 else "negative" if value < 0 else "neutral"
        out[review_id].append(AspectLabel(aspect=key, display_name=names[key], label=label))
    return out


def _overall(db: Session, review_ids: list[int]) -> dict[int, SentimentSummary]:
    if not review_ids:
        return {}
    rows = db.execute(
        select(SentimentResult.review_id, SentimentResult.label, SentimentResult.score).where(
            SentimentResult.review_id.in_(review_ids),
            SentimentResult.segment == TextSegment.OVERALL.value,
        )
    )
    return {rid: SentimentSummary(label=label, score=float(score)) for rid, label, score in rows}


def _item_fields(review: Review, property_name: str) -> dict:
    return {
        "id": review.id,
        "property_id": review.property_id,
        "property_name": property_name,
        "review_date": review.review_date,
        "rating": None if review.rating is None else float(review.rating),
        "title": review.title,
        "positive_text": review.positive_text,
        "negative_text": review.negative_text,
        "body_text": review.body_text,
        "language": review.language,
        "source": review.source,
        "is_synthetic": review.is_synthetic,
        "analysis_status": review.analysis_status,
    }


@router.get("", response_model=ListResponse[ReviewListItem])
def list_reviews(
    f: Filters = Depends(get_filters),
    q: Annotated[str | None, Query(max_length=200)] = None,
    rating_min: Annotated[float | None, Query(ge=0, le=10)] = None,
    rating_max: Annotated[float | None, Query(ge=0, le=10)] = None,
    sentiment: SentimentLabel | None = None,
    aspect: str | None = None,
    aspect_sentiment: SentimentLabel | None = None,
    language: Annotated[str | None, Query(max_length=8)] = None,
    sort: Sort = "newest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    db: Session = Depends(get_db),
) -> ListResponse[ReviewListItem]:
    if rating_min is not None and rating_max is not None and rating_min > rating_max:
        raise AppError(422, "INVALID_FILTER", "rating_min must not exceed rating_max.")
    if aspect_sentiment and not aspect:
        raise AppError(422, "INVALID_FILTER", "aspect_sentiment requires an aspect.")
    if aspect and db.scalar(select(Aspect.id).where(Aspect.key == aspect)) is None:
        raise AppError(404, "ASPECT_NOT_FOUND", f"Aspect '{aspect}' does not exist.")

    conditions = list(f.clauses())
    if q and q.strip():
        pattern = f"%{_escape_like(q.strip().lower())}%"
        conditions.append(
            or_(
                *(
                    func.lower(column).like(pattern, escape="\\")
                    for column in (
                        Review.positive_text,
                        Review.negative_text,
                        Review.body_text,
                        Review.title,
                    )
                )
            )
        )
    if rating_min is not None:
        conditions.append(Review.rating >= rating_min)
    if rating_max is not None:
        conditions.append(Review.rating <= rating_max)
    if language:
        conditions.append(Review.language == language.strip().lower())
    if sentiment:
        conditions.append(
            exists().where(
                SentimentResult.review_id == Review.id,
                SentimentResult.segment == TextSegment.OVERALL.value,
                SentimentResult.label == sentiment.value,
            )
        )
    if aspect:
        sub = aspect_review_labels(Filters(data_scope="all"), aspect).subquery()
        match = [sub.c.review_id == Review.id]
        if aspect_sentiment is SentimentLabel.POSITIVE:
            match.append(sub.c.balance > 0)
        elif aspect_sentiment is SentimentLabel.NEGATIVE:
            match.append(sub.c.balance < 0)
        elif aspect_sentiment is SentimentLabel.NEUTRAL:
            match.append(sub.c.balance == 0)
        conditions.append(exists().where(*match))

    order = {
        "newest": [Review.review_date.desc(), Review.id.desc()],
        "oldest": [Review.review_date.asc(), Review.id.asc()],
        "rating_desc": [Review.rating.desc().nulls_last(), Review.id.desc()],
        "rating_asc": [Review.rating.asc().nulls_last(), Review.id.desc()],
    }[sort]

    total = db.scalar(select(func.count()).select_from(Review).where(*conditions)) or 0
    rows = db.execute(
        select(Review, Property.name)
        .join(Property, Property.id == Review.property_id)
        .where(*conditions)
        .order_by(*order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    ids = [review.id for review, _ in rows]
    sentiments, aspects = _overall(db, ids), _aspect_labels(db, ids)
    return ListResponse(
        data=[
            ReviewListItem(
                **_item_fields(review, name),
                sentiment=sentiments.get(review.id),
                aspects=aspects.get(review.id, []),
            )
            for review, name in rows
        ],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{review_id}", response_model=DataResponse[ReviewDetail])
def get_review(review_id: int, db: Session = Depends(get_db)) -> DataResponse[ReviewDetail]:
    row = db.execute(
        select(Review, Property.name)
        .join(Property, Property.id == Review.property_id)
        .where(Review.id == review_id)
    ).first()
    if row is None:
        raise AppError(404, "REVIEW_NOT_FOUND", f"Review {review_id} does not exist.")
    review, name = row
    segments = [
        SegmentSentiment(
            segment=s.segment, label=s.label, score=float(s.score), model_name=s.model_name
        )
        for s in db.scalars(
            select(SentimentResult)
            .where(SentimentResult.review_id == review_id)
            .order_by(SentimentResult.id)
        )
    ]
    mentions = [
        MentionRead(
            aspect=aspect.key,
            display_name=aspect.display_name,
            label=m.sentiment_label,
            score=float(m.score),
            source_field=m.source_field,
            matched_term=m.matched_term,
            evidence_text=m.evidence_text,
        )
        for m, aspect in db.execute(
            select(AspectMention, Aspect)
            .join(Aspect, Aspect.id == AspectMention.aspect_id)
            .where(AspectMention.review_id == review_id, Aspect.is_active.is_(True))
            .order_by(AspectMention.id)
        )
    ]
    overall = next((s for s in segments if s.segment == TextSegment.OVERALL.value), None)
    return DataResponse(
        data=ReviewDetail(
            **_item_fields(review, name),
            sentiment=SentimentSummary(label=overall.label, score=overall.score)
            if overall
            else None,
            aspects=_aspect_labels(db, [review_id]).get(review_id, []),
            language_detected=review.language_detected,
            traveller_type=review.traveller_type,
            reviewer_country=review.reviewer_country,
            room_type=review.room_type,
            stay_nights=review.stay_nights,
            source_url=review.source_url,
            imported_at=review.imported_at,
            segments=segments,
            mentions=mentions,
        )
    )
