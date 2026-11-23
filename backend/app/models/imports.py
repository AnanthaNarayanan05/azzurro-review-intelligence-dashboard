from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    ImportSourceType,
    ImportStatus,
    RowOutcome,
    check_in,
    created_at_column,
)


class ImportBatch(Base):
    """One uploaded file (or future API pull) and its outcome counts."""

    __tablename__ = "import_batches"
    __table_args__ = (
        check_in("status", ImportStatus),
        check_in("source_type", ImportSourceType),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[str] = mapped_column(String(32))
    source_name: Mapped[str] = mapped_column(String(64), default="booking.com")
    column_mapping: Mapped[dict] = mapped_column(JSON, default=dict)
    # Everything else the user chose at commit time (property mapping, date format, sheet...).
    import_options: Mapped[dict] = mapped_column(JSON, default=dict)
    # Temporary copy of the uploaded file between preview and commit; deleted afterwards.
    stored_filename: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(String(500))
    rating_scale_max: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=Decimal("10"))
    status: Mapped[str] = mapped_column(String(16), default=ImportStatus.PREVIEWED.value)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0)
    updated_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_column()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    issues: Mapped[list["ImportRowIssue"]] = relationship(
        back_populates="import_batch", cascade="all, delete-orphan"
    )


class ImportRowIssue(Base):
    """Why a source row was rejected, flagged as a duplicate, or imported with a warning."""

    __tablename__ = "import_row_issues"
    __table_args__ = (check_in("outcome", RowOutcome),)

    id: Mapped[int] = mapped_column(primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), index=True
    )
    row_number: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(16))
    field: Mapped[str | None] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(48))
    message: Mapped[str] = mapped_column(String(500))
    duplicate_of_review_id: Mapped[int | None] = mapped_column(
        ForeignKey("reviews.id", ondelete="SET NULL")
    )

    import_batch: Mapped[ImportBatch] = relationship(back_populates="issues")
