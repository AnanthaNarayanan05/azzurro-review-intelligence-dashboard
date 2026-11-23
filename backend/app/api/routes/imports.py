from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import ImportBatch, ImportRowIssue
from app.models.base import ImportStatus, RowOutcome
from app.schemas.common import DataResponse, ListResponse, PageMeta
from app.schemas.imports import (
    CommitBody,
    FieldSpecRead,
    ImportReport,
    IssueRead,
    IssueSummaryItem,
    PreviewRead,
    PropertyValueRead,
    PropertyValuesRead,
    RemovedRead,
)
from app.services.ingestion import pipeline
from app.services.ingestion.mapping import IMPORT_FIELDS, TEXT_FIELD_KEYS

router = APIRouter(prefix="/imports", tags=["imports"])

_CHUNK = 1024 * 1024


def _read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Read the upload in chunks and stop as soon as it exceeds the size limit."""
    chunks: list[bytes] = []
    total = 0
    while chunk := upload.file.read(_CHUNK):
        total += len(chunk)
        if total > max_bytes:
            raise AppError(
                413,
                "FILE_TOO_LARGE",
                f"The file is larger than the {max_bytes // (1024 * 1024)} MB limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def build_report(db: Session, batch: ImportBatch) -> ImportReport:
    summary = pipeline.issue_summary(db, batch.id)
    return ImportReport(
        id=batch.id,
        filename=batch.filename,
        source_type=batch.source_type,
        source_name=batch.source_name,
        status=batch.status,
        is_synthetic=batch.is_synthetic,
        rating_scale_max=float(batch.rating_scale_max),
        total_rows=batch.total_rows,
        imported_rows=batch.imported_rows,
        updated_rows=batch.updated_rows,
        duplicate_rows=batch.duplicate_rows,
        rejected_rows=batch.rejected_rows,
        warning_count=sum(n for outcome, _, n in summary if outcome == RowOutcome.WARNING),
        created_at=batch.created_at,
        completed_at=batch.completed_at,
        error_message=batch.error_message,
        column_mapping=batch.column_mapping or {},
        issue_summary=[IssueSummaryItem(outcome=o, code=c, count=n) for o, c, n in summary],
    )


@router.get("/fields", response_model=DataResponse[list[FieldSpecRead]])
def list_fields() -> DataResponse[list[FieldSpecRead]]:
    def requirement(key: str) -> str:
        if key in ("review_date",):
            return "always"
        if key in ("rating", *TEXT_FIELD_KEYS) and key != "title":
            return "one_of"
        return "no"

    return DataResponse(
        data=[
            FieldSpecRead(
                key=f.key, label=f.label, description=f.description, required=requirement(f.key)
            )
            for f in IMPORT_FIELDS
        ]
    )


def _preview_read(result: pipeline.PreviewResult) -> PreviewRead:
    table = result.table
    return PreviewRead(
        import_id=result.batch.id,
        filename=result.batch.filename,
        source_type=table.source_type,
        total_rows=len(table.rows),
        columns=table.columns,
        sheets=table.sheets,
        sheet=table.sheet,
        encoding=table.encoding,
        delimiter=table.delimiter,
        sample_rows=pipeline.sample_rows(table),
        suggested_mapping=result.suggested_mapping,
        property_values=PropertyValuesRead(
            values=[PropertyValueRead(**vars(v)) for v in result.property_values],
            truncated=result.property_values_truncated,
        ),
        already_imported_as=result.already_imported.id if result.already_imported else None,
    )


@router.post("/preview", response_model=DataResponse[PreviewRead], status_code=201)
def preview_import(
    file: Annotated[UploadFile, File(description="A .csv or .xlsx review export")],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DataResponse[PreviewRead]:
    data = _read_limited(file, settings.max_upload_mb * 1024 * 1024)
    result = pipeline.create_preview(db, settings, file.filename or "upload", data)
    return DataResponse(data=_preview_read(result))


@router.get("/{import_id}/preview", response_model=DataResponse[PreviewRead])
def reread_preview(
    import_id: int,
    sheet: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DataResponse[PreviewRead]:
    """Preview of an already-uploaded file, e.g. after choosing a different Excel sheet."""
    batch = pipeline.get_batch(db, import_id)
    return DataResponse(data=_preview_read(pipeline.preview_for_batch(db, settings, batch, sheet)))


@router.get("/{import_id}/property-values", response_model=DataResponse[PropertyValuesRead])
def property_values(
    import_id: int,
    column: str = Query(min_length=1, max_length=255),
    sheet: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DataResponse[PropertyValuesRead]:
    """Distinct values of one column with suggested property matches (for re-mapping in the UI)."""
    batch = pipeline.get_batch(db, import_id)
    table = pipeline.load_stored_table(db, settings, batch, sheet)
    values, truncated = pipeline.property_values_for_column(db, table, column)
    return DataResponse(
        data=PropertyValuesRead(
            values=[PropertyValueRead(**vars(v)) for v in values], truncated=truncated
        )
    )


@router.post("/{import_id}/commit", response_model=DataResponse[ImportReport])
def commit_import(
    import_id: int,
    body: CommitBody,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DataResponse[ImportReport]:
    request = pipeline.CommitRequest(
        column_mapping=body.column_mapping,
        property_mapping=body.property_mapping,
        fixed_property_id=body.fixed_property_id,
        rating_scale_max=Decimal(body.rating_scale_max),
        date_format=body.date_format,
        source_name=body.source_name,
        is_synthetic=body.is_synthetic,
        sheet=body.sheet,
        remember_aliases=body.remember_aliases,
    )
    batch = pipeline.commit_import(db, settings, import_id, request)
    return DataResponse(data=build_report(db, batch))


@router.get("", response_model=ListResponse[ImportReport])
def list_imports(
    status: ImportStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ListResponse[ImportReport]:
    """Import history. Previews that were never committed are hidden unless asked for."""
    query = select(ImportBatch)
    if status:
        query = query.where(ImportBatch.status == status.value)
    else:
        query = query.where(ImportBatch.status != ImportStatus.PREVIEWED.value)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    batches = db.scalars(
        query.order_by(ImportBatch.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return ListResponse(
        data=[build_report(db, b) for b in batches],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{import_id}", response_model=DataResponse[ImportReport])
def get_import(import_id: int, db: Session = Depends(get_db)) -> DataResponse[ImportReport]:
    return DataResponse(data=build_report(db, pipeline.get_batch(db, import_id)))


@router.get("/{import_id}/issues", response_model=ListResponse[IssueRead])
def list_issues(
    import_id: int,
    outcome: RowOutcome | None = None,
    code: str | None = Query(default=None, max_length=48),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ListResponse[IssueRead]:
    pipeline.get_batch(db, import_id)
    query = select(ImportRowIssue).where(ImportRowIssue.import_id == import_id)
    if outcome:
        query = query.where(ImportRowIssue.outcome == outcome.value)
    if code:
        query = query.where(ImportRowIssue.code == code)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    issues = db.scalars(
        query.order_by(ImportRowIssue.row_number, ImportRowIssue.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ListResponse(
        data=[
            IssueRead(
                id=i.id,
                row_number=i.row_number,
                outcome=i.outcome,
                field=i.field,
                code=i.code,
                message=i.message,
                duplicate_of_review_id=i.duplicate_of_review_id,
            )
            for i in issues
        ],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.delete("/{import_id}", response_model=DataResponse[RemovedRead])
def delete_import(
    import_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DataResponse[RemovedRead]:
    """Undo an import: removes the batch and every review it created."""
    removed = pipeline.delete_import(db, settings, import_id)
    return DataResponse(data=RemovedRead(removed_reviews=removed))
