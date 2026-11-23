from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class IssueSummaryItem(BaseModel):
    outcome: str
    code: str
    count: int


class ImportReport(BaseModel):
    id: int
    filename: str
    source_type: str
    source_name: str
    status: str
    is_synthetic: bool
    rating_scale_max: float
    total_rows: int
    imported_rows: int
    updated_rows: int
    duplicate_rows: int
    rejected_rows: int
    warning_count: int
    created_at: datetime
    completed_at: datetime | None
    error_message: str | None
    column_mapping: dict[str, str]
    issue_summary: list[IssueSummaryItem]


class IssueRead(BaseModel):
    id: int
    row_number: int
    outcome: str
    field: str | None
    code: str
    message: str
    duplicate_of_review_id: int | None


class FieldSpecRead(BaseModel):
    key: str
    label: str
    description: str
    required: str  # "always" | "one_of" | "no"


class PropertyValueRead(BaseModel):
    value: str
    count: int
    suggested_property_id: int | None
    match_type: str | None


class PropertyValuesRead(BaseModel):
    values: list[PropertyValueRead]
    truncated: bool


class PreviewRead(BaseModel):
    import_id: int
    filename: str
    source_type: str
    total_rows: int
    columns: list[str]
    sheets: list[str]
    sheet: str | None
    encoding: str | None
    delimiter: str | None
    sample_rows: list[dict[str, str]]
    suggested_mapping: dict[str, str | None]
    property_values: PropertyValuesRead
    already_imported_as: int | None = Field(
        description="ID of an earlier completed import of a byte-identical file, if any."
    )


class CommitBody(BaseModel):
    column_mapping: dict[str, str] = Field(description="internal field -> file column")
    property_mapping: dict[str, int] = Field(
        default_factory=dict, description="raw property value in the file -> property id"
    )
    fixed_property_id: int | None = Field(
        default=None, description="Assign every row to this property (no property column needed)."
    )
    rating_scale_max: Decimal = Field(default=Decimal(10), gt=0, le=100)
    date_format: Literal["auto", "iso", "dmy", "mdy"] = "auto"
    source_name: str = Field(default="booking.com", min_length=1, max_length=64)
    is_synthetic: bool = False
    sheet: str | None = None
    remember_aliases: bool = True

    @field_validator("column_mapping")
    @classmethod
    def _no_blank_columns(cls, value: dict[str, str]) -> dict[str, str]:
        return {k: v for k, v in value.items() if v}


class RemovedRead(BaseModel):
    removed_reviews: int
