from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_column


class Review(Base):
    """A guest review exactly as received. Original text columns are never modified."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating IS NULL OR (rating >= 0 AND rating <= 10)", name="rating_range"),
        CheckConstraint(
            "positive_text IS NOT NULL OR negative_text IS NOT NULL "
            "OR body_text IS NOT NULL OR rating IS NOT NULL",
            name="has_content",
        ),
        # Duplicate detection by the source's own ID, only where one exists.
        Index(
            "uq_reviews_source_external_id",
            "source",
            "external_review_id",
            unique=True,
            sqlite_where=text("external_review_id IS NOT NULL"),
            postgresql_where=text("external_review_id IS NOT NULL"),
        ),
        Index("ix_reviews_property_date", "property_id", "review_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_review_id: Mapped[str | None] = mapped_column(String(128))
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"))
    import_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(64), default="booking.com")
    review_date: Mapped[date] = mapped_column(Date, index=True)
    # Normalised to a 0-10 scale; rating_raw keeps the value as supplied.
    rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), index=True)
    rating_raw: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    title: Mapped[str | None] = mapped_column(Text)
    positive_text: Mapped[str | None] = mapped_column(Text)
    negative_text: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(8))
    language_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    traveller_type: Mapped[str | None] = mapped_column(String(100))
    reviewer_country: Mapped[str | None] = mapped_column(String(100))
    room_type: Mapped[str | None] = mapped_column(String(100))
    stay_nights: Mapped[int | None] = mapped_column(Integer)
    # Unmapped source columns kept for audit (personal names are excluded at import).
    extra: Mapped[dict | None] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    imported_at: Mapped[datetime] = created_at_column()

    property: Mapped["Property"] = relationship()  # noqa: F821
    sentiment_results: Mapped[list["SentimentResult"]] = relationship(  # noqa: F821
        back_populates="review", cascade="all, delete-orphan", passive_deletes=True
    )
    aspect_mentions: Mapped[list["AspectMention"]] = relationship(  # noqa: F821
        back_populates="review", cascade="all, delete-orphan", passive_deletes=True
    )
