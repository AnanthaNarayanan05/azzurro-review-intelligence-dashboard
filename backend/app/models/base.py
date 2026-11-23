"""Declarative base, shared column helpers and controlled vocabularies."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint names: required for reliable Alembic migrations (especially on SQLite).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    return datetime.now(UTC)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


def check_in(column: str, values: type[StrEnum], name: str | None = None) -> CheckConstraint:
    """CHECK constraint restricting a string column to the values of an enum."""
    allowed = ", ".join(f"'{member.value}'" for member in values)
    return CheckConstraint(f"{column} IN ({allowed})", name=name or f"{column}_allowed")


class SentimentLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class TextSegment(StrEnum):
    OVERALL = "overall"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    BODY = "body"


class SourceField(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    BODY = "body"
    TITLE = "title"


class ImportStatus(StrEnum):
    PREVIEWED = "previewed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImportSourceType(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"
    API = "api"


class RowOutcome(StrEnum):
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    WARNING = "warning"


class AnalysisTrigger(StrEnum):
    IMPORT = "import"
    MANUAL = "manual"


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class InsightType(StrEnum):
    RECURRING_COMPLAINT = "recurring_complaint"
    STRENGTH = "strength"
    EMERGING_NEGATIVE_TREND = "emerging_negative_trend"
    PROPERTY_ISSUE = "property_issue"
    CROSS_PROPERTY_ISSUE = "cross_property_issue"
    OPPORTUNITY = "opportunity"


class InsightScope(StrEnum):
    PORTFOLIO = "portfolio"
    PROPERTY = "property"
    MULTI_PROPERTY = "multi_property"


class EvidenceStrength(StrEnum):
    STRONG = "strong"
    MODERATE = "moderate"
    LIMITED = "limited"


class GenerationMethod(StrEnum):
    TEMPLATE = "template"
    LLM = "llm"
