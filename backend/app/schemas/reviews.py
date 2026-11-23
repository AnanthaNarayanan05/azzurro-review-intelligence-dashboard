from datetime import date, datetime

from pydantic import BaseModel


class AspectLabel(BaseModel):
    """A review's overall stance on one aspect (sign of positive minus negative mentions)."""

    aspect: str
    display_name: str
    label: str


class SentimentSummary(BaseModel):
    label: str
    score: float


class ReviewListItem(BaseModel):
    id: int
    property_id: int
    property_name: str
    review_date: date
    rating: float | None
    title: str | None
    positive_text: str | None
    negative_text: str | None
    body_text: str | None
    language: str | None
    source: str
    is_synthetic: bool
    analysis_status: str | None
    sentiment: SentimentSummary | None
    aspects: list[AspectLabel]


class SegmentSentiment(BaseModel):
    segment: str
    label: str
    score: float
    model_name: str


class MentionRead(BaseModel):
    aspect: str
    display_name: str
    label: str
    score: float
    source_field: str
    matched_term: str
    evidence_text: str


class ReviewDetail(ReviewListItem):
    language_detected: bool
    traveller_type: str | None
    reviewer_country: str | None
    room_type: str | None
    stay_nights: int | None
    source_url: str | None
    imported_at: datetime
    segments: list[SegmentSentiment]
    mentions: list[MentionRead]
