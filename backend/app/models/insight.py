from datetime import date, datetime

from sqlalchemy import JSON, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    EvidenceStrength,
    GenerationMethod,
    InsightScope,
    InsightType,
    check_in,
    created_at_column,
)


class Insight(Base):
    """A finding derived from computed metrics. `metrics` holds the exact numbers the text cites."""

    __tablename__ = "insights"
    __table_args__ = (
        check_in("insight_type", InsightType),
        check_in("scope", InsightScope),
        check_in("evidence_strength", EvidenceStrength),
        check_in("generation_method", GenerationMethod),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="SET NULL"), index=True
    )
    insight_type: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(16))
    aspect_id: Mapped[int | None] = mapped_column(ForeignKey("aspects.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200))
    explanation: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    supporting_review_count: Mapped[int] = mapped_column(Integer)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    evidence_strength: Mapped[str] = mapped_column(String(8))
    metrics: Mapped[dict] = mapped_column(JSON)
    generation_method: Mapped[str] = mapped_column(
        String(16), default=GenerationMethod.TEMPLATE.value
    )
    llm_model: Mapped[str | None] = mapped_column(String(64))
    generated_at: Mapped[datetime] = created_at_column()

    properties: Mapped[list["InsightProperty"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    evidence: Mapped[list["InsightEvidence"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="InsightEvidence.rank"
    )


class InsightProperty(Base):
    __tablename__ = "insight_properties"

    insight_id: Mapped[int] = mapped_column(
        ForeignKey("insights.id", ondelete="CASCADE"), primary_key=True
    )
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), primary_key=True
    )


class InsightEvidence(Base):
    """A real review cited as evidence. The FK makes citing a non-existent review impossible."""

    __tablename__ = "insight_evidence"

    insight_id: Mapped[int] = mapped_column(
        ForeignKey("insights.id", ondelete="CASCADE"), primary_key=True
    )
    review_id: Mapped[int] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    excerpt: Mapped[str] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(Integer, default=0)
