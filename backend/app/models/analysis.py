from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    AnalysisTrigger,
    Base,
    RunStatus,
    SentimentLabel,
    SourceField,
    TextSegment,
    check_in,
    created_at_column,
)


class AnalysisRun(Base):
    """One execution of the NLP pipeline; records which model and lexicon produced the results."""

    __tablename__ = "analysis_runs"
    __table_args__ = (
        check_in("triggered_by", AnalysisTrigger),
        check_in("status", RunStatus),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    triggered_by: Mapped[str] = mapped_column(String(16))
    sentiment_engine: Mapped[str] = mapped_column(String(64))
    aspect_lexicon_version: Mapped[str] = mapped_column(String(32))
    reviews_processed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default=RunStatus.RUNNING.value)
    started_at: Mapped[datetime] = created_at_column()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SentimentResult(Base):
    __tablename__ = "sentiment_results"
    __table_args__ = (
        check_in("segment", TextSegment),
        check_in("label", SentimentLabel),
        UniqueConstraint("review_id", "segment", "model_name"),
        Index("ix_sentiment_results_segment_label", "segment", "label"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"))
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    segment: Mapped[str] = mapped_column(String(16))
    label: Mapped[str] = mapped_column(String(8))
    score: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    model_name: Mapped[str] = mapped_column(String(64))
    analysed_at: Mapped[datetime] = created_at_column()

    review: Mapped["Review"] = relationship(back_populates="sentiment_results")  # noqa: F821


class Aspect(Base):
    """An analysable hospitality aspect. Keywords live in a versioned lexicon file."""

    __tablename__ = "aspects"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(48), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AspectMention(Base):
    __tablename__ = "aspect_mentions"
    __table_args__ = (
        check_in("source_field", SourceField),
        check_in("sentiment_label", SentimentLabel),
        Index("ix_aspect_mentions_aspect_label", "aspect_id", "sentiment_label"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    aspect_id: Mapped[int] = mapped_column(ForeignKey("aspects.id", ondelete="RESTRICT"))
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    source_field: Mapped[str] = mapped_column(String(16))
    sentiment_label: Mapped[str] = mapped_column(String(8))
    score: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    evidence_text: Mapped[str] = mapped_column(Text)
    matched_term: Mapped[str] = mapped_column(String(100))

    review: Mapped["Review"] = relationship(back_populates="aspect_mentions")  # noqa: F821
    aspect: Mapped[Aspect] = relationship()
