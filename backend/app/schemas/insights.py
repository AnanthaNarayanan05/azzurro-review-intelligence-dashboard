from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.common import PageMeta


class InsightAspectRead(BaseModel):
    key: str
    display_name: str


class InsightPropertyRead(BaseModel):
    id: int
    name: str


class InsightEvidenceRead(BaseModel):
    """A real review cited by an insight, with the verbatim sentence that supports it."""

    review_id: int
    excerpt: str
    rank: int
    property_id: int
    property_name: str
    review_date: date
    rating: float | None
    is_synthetic: bool


class InsightRead(BaseModel):
    id: int
    insight_type: str
    scope: str
    data_scope: str
    aspect: InsightAspectRead | None
    title: str
    explanation: str
    recommended_action: str
    supporting_review_count: int
    period_start: date
    period_end: date
    evidence_strength: str
    generation_method: str
    generated_at: datetime
    properties: list[InsightPropertyRead]
    evidence: list[InsightEvidenceRead]
    metrics: dict[str, Any]


class InsightListMeta(PageMeta):
    data_scope: str
    generated_at: datetime | None
    # True when reviews or their analysis changed after these insights were generated.
    stale: bool
    analysis_run_id: int | None
    dataset: dict[str, Any]


class InsightListResponse(BaseModel):
    data: list[InsightRead]
    meta: InsightListMeta


class GenerateRequest(BaseModel):
    data_scope: Literal["genuine", "synthetic", "all"] = "genuine"


class GenerationResult(BaseModel):
    data_scope: str
    as_of: date | None
    created: int
    replaced: int
    rejected_by_validator: int
    by_type: dict[str, int]
    checked_property_aspects: int
    below_mention_floor: int
    comparisons_skipped_too_few: int
    notes: list[str]
