"""Insights: findings computed by rules from stored analytics, each linked to real reviews."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.analytics.metrics import DataScope, Filters, data_summary
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Aspect, Insight, InsightProperty, Property, Review
from app.models.base import EvidenceStrength, InsightType
from app.schemas.common import DataResponse
from app.schemas.insights import (
    GenerateRequest,
    GenerationResult,
    InsightAspectRead,
    InsightEvidenceRead,
    InsightListMeta,
    InsightListResponse,
    InsightPropertyRead,
    InsightRead,
)
from app.services.insights import generate as generation

router = APIRouter(prefix="/insights", tags=["insights"])

_STRENGTH_ORDER = case(
    (Insight.evidence_strength == EvidenceStrength.STRONG.value, 0),
    (Insight.evidence_strength == EvidenceStrength.MODERATE.value, 1),
    else_=2,
)
# Most actionable first: a rising complaint, then issues, then strengths and opportunities.
_TYPE_ORDER = case(
    (Insight.insight_type == InsightType.EMERGING_NEGATIVE_TREND.value, 0),
    (Insight.insight_type == InsightType.CROSS_PROPERTY_ISSUE.value, 1),
    (Insight.insight_type == InsightType.PROPERTY_ISSUE.value, 2),
    (Insight.insight_type == InsightType.RECURRING_COMPLAINT.value, 3),
    (Insight.insight_type == InsightType.OPPORTUNITY.value, 4),
    else_=5,
)


def _to_read(db: Session, insights: list[Insight]) -> list[InsightRead]:
    aspects = {a.id: a for a in db.scalars(select(Aspect))}
    property_names = {p.id: p.name for p in db.scalars(select(Property))}
    review_ids = {e.review_id for i in insights for e in i.evidence}
    reviews = {r.id: r for r in db.scalars(select(Review).where(Review.id.in_(review_ids)))}
    out = []
    for i in insights:
        aspect = aspects.get(i.aspect_id) if i.aspect_id else None
        out.append(
            InsightRead(
                id=i.id,
                insight_type=i.insight_type,
                scope=i.scope,
                data_scope=i.data_scope,
                aspect=InsightAspectRead(key=aspect.key, display_name=aspect.display_name)
                if aspect
                else None,
                title=i.title,
                explanation=i.explanation,
                recommended_action=i.recommended_action,
                supporting_review_count=i.supporting_review_count,
                period_start=i.period_start,
                period_end=i.period_end,
                evidence_strength=i.evidence_strength,
                generation_method=i.generation_method,
                generated_at=i.generated_at,
                properties=[
                    InsightPropertyRead(
                        id=p.property_id, name=property_names.get(p.property_id, "")
                    )
                    for p in sorted(i.properties, key=lambda p: p.property_id)
                ],
                evidence=[
                    InsightEvidenceRead(
                        review_id=e.review_id,
                        excerpt=e.excerpt,
                        rank=e.rank,
                        property_id=reviews[e.review_id].property_id,
                        property_name=property_names.get(reviews[e.review_id].property_id, ""),
                        review_date=reviews[e.review_id].review_date,
                        rating=float(reviews[e.review_id].rating)
                        if reviews[e.review_id].rating is not None
                        else None,
                        is_synthetic=reviews[e.review_id].is_synthetic,
                    )
                    for e in i.evidence
                    if e.review_id in reviews
                ],
                metrics=i.metrics,
            )
        )
    return out


@router.get("", response_model=InsightListResponse)
def list_insights(
    property_ids: Annotated[str | None, Query(description="Comma-separated property ids")] = None,
    insight_type: InsightType | None = None,
    evidence_strength: EvidenceStrength | None = None,
    aspect: str | None = Query(default=None, max_length=48),
    data_scope: DataScope = "genuine",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> InsightListResponse:
    conditions = [Insight.data_scope == data_scope]
    if property_ids:
        try:
            ids = [int(part) for part in property_ids.split(",") if part.strip()]
        except ValueError as exc:
            raise AppError(
                422, "INVALID_FILTER", "property_ids must be a comma-separated list of integers."
            ) from exc
        conditions.append(
            Insight.id.in_(
                select(InsightProperty.insight_id).where(InsightProperty.property_id.in_(ids))
            )
        )
    if insight_type:
        conditions.append(Insight.insight_type == insight_type.value)
    if evidence_strength:
        conditions.append(Insight.evidence_strength == evidence_strength.value)
    if aspect:
        conditions.append(
            Insight.aspect_id == select(Aspect.id).where(Aspect.key == aspect).scalar_subquery()
        )

    total = db.scalar(select(func.count()).select_from(Insight).where(*conditions)) or 0
    rows = (
        db.scalars(
            select(Insight)
            .where(*conditions)
            .options(selectinload(Insight.properties), selectinload(Insight.evidence))
            .order_by(
                _STRENGTH_ORDER, _TYPE_ORDER, Insight.supporting_review_count.desc(), Insight.id
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .all()
    )

    # Freshness is judged over the whole scope, not the filtered page.
    scope_rows = db.execute(
        select(func.max(Insight.generated_at), func.min(Insight.id)).where(
            Insight.data_scope == data_scope
        )
    ).one()
    generated_at, first_id = scope_rows
    stale, run_id = False, None
    if first_id is not None:
        first = db.get(Insight, first_id)
        stored = (first.metrics or {}).get("generation", {}) if first else {}
        current = generation.scope_fingerprint(db, data_scope)
        run_id = stored.get("analysis_run_id")
        stale = (
            stored.get("analysis_run_id") != current["analysis_run_id"]
            or stored.get("reviews_in_scope") != current["reviews_in_scope"]
        )

    return InsightListResponse(
        data=_to_read(db, list(rows)),
        meta=InsightListMeta(
            page=page,
            page_size=page_size,
            total=total,
            data_scope=data_scope,
            generated_at=generated_at,
            stale=stale,
            analysis_run_id=run_id,
            dataset=data_summary(db, Filters(data_scope=data_scope)),
        ),
    )


@router.post("/generate", response_model=DataResponse[GenerationResult])
def generate_insights(
    body: GenerateRequest | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DataResponse[GenerationResult]:
    """Recompute the insights of one data scope from the stored analytics. Rule-based; no external
    service is called. The previous insights of that scope are replaced."""
    summary = generation.generate(db, settings, (body or GenerateRequest()).data_scope)
    return DataResponse(data=GenerationResult(**summary.__dict__))


@router.get("/{insight_id}", response_model=DataResponse[InsightRead])
def get_insight(insight_id: int, db: Session = Depends(get_db)) -> DataResponse[InsightRead]:
    insight = db.scalar(
        select(Insight)
        .where(Insight.id == insight_id)
        .options(selectinload(Insight.properties), selectinload(Insight.evidence))
    )
    if insight is None:
        raise AppError(404, "INSIGHT_NOT_FOUND", f"Insight {insight_id} does not exist.")
    return DataResponse(data=_to_read(db, [insight])[0])
