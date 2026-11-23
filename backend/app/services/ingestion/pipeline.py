"""The import pipeline: preview -> validate -> de-duplicate -> store, with a full audit trail.

Design rules:
  * Row-level problems never abort an import; each becomes a reported issue.
  * Everything that touches the database for one import happens in a single transaction. An
    unexpected failure rolls the whole import back, so there are never half-imported files.
  * Counts always reconcile: total rows = imported + updated + duplicate + rejected.
"""

import hashlib
import logging
import re
import time
import uuid
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.models import ImportBatch, ImportRowIssue, PropertyAlias, Review
from app.models.base import ImportStatus, RowOutcome, utcnow
from app.services.ingestion.mapping import FIELD_KEYS, TEXT_FIELD_KEYS, suggest_mapping
from app.services.ingestion.normalise import content_hash, normalise_for_match
from app.services.ingestion.parsing import ParsedTable, parse_file
from app.services.ingestion.rows import DATE_FORMATS, CleanRow, RowIssueData, convert_row
from app.services.properties import PropertyIndex

logger = logging.getLogger(__name__)

SYNTHETIC_SOURCE = "synthetic-demo"
DEFAULT_SOURCE = "booking.com"
PREVIEW_ROWS = 20
MAX_PROPERTY_VALUES = 200
STALE_PREVIEW_HOURS = 24
DB_RETRIES = 3


# --------------------------------------------------------------------------- requests / results
@dataclass
class CommitRequest:
    column_mapping: dict[str, str]  # internal field -> file column
    property_mapping: dict[str, int] = field(default_factory=dict)  # raw file value -> property id
    fixed_property_id: int | None = None  # every row belongs to this property
    rating_scale_max: Decimal = Decimal(10)
    date_format: str = "auto"
    source_name: str = DEFAULT_SOURCE
    is_synthetic: bool = False
    sheet: str | None = None
    remember_aliases: bool = True


@dataclass
class PropertyValue:
    value: str
    count: int
    suggested_property_id: int | None
    match_type: str | None


@dataclass
class PreviewResult:
    batch: ImportBatch
    table: ParsedTable
    suggested_mapping: dict[str, str | None]
    property_values: list[PropertyValue]
    property_values_truncated: bool
    already_imported: ImportBatch | None


# --------------------------------------------------------------------------- helpers
def _chunks(items: list, size: int = 500) -> Iterator[list]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime | date):
        return value.isoformat()
    text = str(value)
    return text if len(text) <= 300 else text[:300] + "…"


def _safe_filename(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    name = re.sub(r"[\x00-\x1f]", "", name)
    return (name or "upload")[:255]


def _upload_path(settings: Settings, stored_filename: str) -> Path:
    return settings.resolved_upload_dir / stored_filename


def _remove_stored_file(settings: Settings, batch: ImportBatch) -> None:
    if batch.stored_filename:
        try:
            _upload_path(settings, batch.stored_filename).unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove stored upload for import %s", batch.id)
        batch.stored_filename = None


def get_batch(db: Session, batch_id: int) -> ImportBatch:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise AppError(404, "IMPORT_NOT_FOUND", f"Import {batch_id} does not exist.")
    return batch


def load_stored_table(
    db: Session, settings: Settings, batch: ImportBatch, sheet: str | None = None
) -> ParsedTable:
    if batch.status != ImportStatus.PREVIEWED or not batch.stored_filename:
        raise AppError(409, "IMPORT_NOT_PENDING", "This import is no longer waiting for commit.")
    path = _upload_path(settings, batch.stored_filename)
    try:
        data = path.read_bytes()
    except OSError:
        raise AppError(
            410, "UPLOAD_EXPIRED", "The uploaded file is no longer available. Upload it again."
        ) from None
    return parse_file(batch.filename, data, settings.max_import_rows, sheet)


# --------------------------------------------------------------------------- preview
def purge_stale_previews(db: Session, settings: Settings) -> int:
    """Remove previews that were never committed (and their stored files)."""
    cutoff = utcnow() - timedelta(hours=STALE_PREVIEW_HOURS)
    stale = list(
        db.scalars(
            select(ImportBatch).where(
                ImportBatch.status == ImportStatus.PREVIEWED, ImportBatch.created_at < cutoff
            )
        )
    )
    for batch in stale:
        _remove_stored_file(settings, batch)
        db.delete(batch)
    if stale:
        db.commit()
    return len(stale)


def property_values_for_column(
    db: Session, table: ParsedTable, column: str
) -> tuple[list[PropertyValue], bool]:
    if column not in table.columns:
        raise AppError(422, "UNKNOWN_COLUMN", f"The file has no column named '{column}'.")
    counts: Counter[str] = Counter()
    for row in table.rows:
        value = row.get(column)
        text = str(value).strip() if value is not None else ""
        if text:
            counts[text] += 1
    index = PropertyIndex(db)
    values: list[PropertyValue] = []
    for value, count in counts.most_common():
        match = index.suggest(value)
        values.append(
            PropertyValue(
                value,
                count,
                match.property_id if match else None,
                match.match_type if match else None,
            )
        )
    return values[:MAX_PROPERTY_VALUES], len(values) > MAX_PROPERTY_VALUES


def create_preview(db: Session, settings: Settings, filename: str, data: bytes) -> PreviewResult:
    purge_stale_previews(db, settings)
    filename = _safe_filename(filename)
    table = parse_file(filename, data, settings.max_import_rows)  # raises on bad files

    digest = hashlib.sha256(data).hexdigest()
    previous = db.scalars(
        select(ImportBatch)
        .where(ImportBatch.file_sha256 == digest, ImportBatch.status == ImportStatus.COMPLETED)
        .order_by(ImportBatch.id.desc())
    ).first()

    upload_dir = settings.resolved_upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{'.xlsx' if table.source_type == 'xlsx' else '.csv'}"
    _upload_path(settings, stored_name).write_bytes(data)

    batch = ImportBatch(
        filename=filename,
        file_sha256=digest,
        source_type=table.source_type,
        status=ImportStatus.PREVIEWED.value,
        total_rows=len(table.rows),
        stored_filename=stored_name,
    )
    db.add(batch)
    try:
        db.commit()
    except Exception:
        db.rollback()
        _upload_path(settings, stored_name).unlink(missing_ok=True)
        raise

    return _assemble_preview(db, batch, table, previous)


def _assemble_preview(
    db: Session, batch: ImportBatch, table: ParsedTable, previous: ImportBatch | None
) -> PreviewResult:
    suggested = suggest_mapping(table.columns)
    values: list[PropertyValue] = []
    truncated = False
    if suggested.get("property"):
        values, truncated = property_values_for_column(db, table, suggested["property"])
    return PreviewResult(batch, table, suggested, values, truncated, previous)


def preview_for_batch(
    db: Session, settings: Settings, batch: ImportBatch, sheet: str | None = None
) -> PreviewResult:
    """Re-read a stored upload (optionally another worksheet) without uploading it again."""
    table = load_stored_table(db, settings, batch, sheet)
    return _assemble_preview(db, batch, table, None)


def sample_rows(table: ParsedTable) -> list[dict[str, str]]:
    return [
        {col: _stringify(row.get(col)) for col in table.columns}
        for row in table.rows[:PREVIEW_ROWS]
    ]


# --------------------------------------------------------------------------- commit
def _validate_request(
    db: Session, table: ParsedTable, req: CommitRequest, index: PropertyIndex
) -> None:
    problems: list[dict[str, str]] = []

    def fail(field_name: str, message: str) -> None:
        problems.append({"field": field_name, "message": message})

    for key, column in req.column_mapping.items():
        if key not in FIELD_KEYS:
            fail(key, f"'{key}' is not an importable field.")
        elif column not in table.columns:
            fail(key, f"The file has no column named '{column}'.")
    if "review_date" not in req.column_mapping:
        fail("review_date", "Map a column to the review date.")
    if not any(k in req.column_mapping for k in ("rating", *TEXT_FIELD_KEYS)):
        fail("rating", "Map at least a rating or a review text column.")
    if req.fixed_property_id is None and "property" not in req.column_mapping:
        fail("property", "Map a property column, or choose one property for the whole file.")
    if req.fixed_property_id is not None and req.fixed_property_id not in index.ids:
        fail("fixed_property_id", f"Property {req.fixed_property_id} does not exist.")
    for raw, property_id in req.property_mapping.items():
        if property_id not in index.ids:
            fail("property_mapping", f"Property {property_id} (for '{raw}') does not exist.")
    if req.date_format not in DATE_FORMATS:
        fail("date_format", f"Date format must be one of {', '.join(DATE_FORMATS)}.")
    if not (Decimal(0) < req.rating_scale_max <= Decimal(100)):
        fail("rating_scale_max", "The rating scale maximum must be between 0 and 100.")
    if problems:
        raise AppError(422, "INVALID_MAPPING", "The import settings are not valid.", problems)


@dataclass
class _Outcome:
    imported: int = 0
    updated: int = 0
    duplicates: int = 0
    rejected: int = 0
    issues: int = 0


def _existing_reviews(
    db: Session, source: str, hashes: list[str], external_ids: list[str]
) -> tuple[dict[str, int], dict[str, Review]]:
    by_hash: dict[str, int] = {}
    for chunk in _chunks(hashes):
        by_hash.update(
            dict(
                db.execute(
                    select(Review.content_hash, Review.id).where(Review.content_hash.in_(chunk))
                ).all()
            )
        )
    by_external: dict[str, Review] = {}
    for chunk in _chunks(external_ids):
        for review in db.scalars(
            select(Review).where(Review.source == source, Review.external_review_id.in_(chunk))
        ):
            by_external[review.external_review_id] = review
    return by_hash, by_external


def _write_phase(
    db: Session,
    batch_id: int,
    clean_rows: list[CleanRow],
    row_issues: list[RowIssueData],
    req: CommitRequest,
    total_rows: int,
    source: str,
) -> None:
    """All database writes for one import. The caller owns commit/rollback."""
    batch = db.get(ImportBatch, batch_id)
    assert batch is not None
    index = PropertyIndex(db)
    mapping_norm = {normalise_for_match(k): v for k, v in req.property_mapping.items()}

    # 1. Resolve each row's property and compute its fingerprint.
    resolved: list[tuple[CleanRow, int, str]] = []
    rejected_issues: list[RowIssueData] = list(row_issues)
    for row in clean_rows:
        if req.fixed_property_id is not None:
            property_id = req.fixed_property_id
        elif not row.property_raw:
            rejected_issues.append(
                RowIssueData(
                    row.row_number,
                    RowOutcome.REJECTED,
                    "MISSING_PROPERTY",
                    "The property value is missing.",
                    "property",
                )
            )
            continue
        else:
            key = normalise_for_match(row.property_raw)
            property_id = mapping_norm.get(key)
            if property_id is None:
                match = index.exact(row.property_raw)
                property_id = match.property_id if match else None
            if property_id is None:
                rejected_issues.append(
                    RowIssueData(
                        row.row_number,
                        RowOutcome.REJECTED,
                        "UNKNOWN_PROPERTY",
                        f"No property is mapped for '{row.property_raw}'.",
                        "property",
                    )
                )
                continue
        fingerprint = content_hash(
            source=source,
            property_id=property_id,
            review_date=row.review_date,
            rating=row.rating,
            title=row.title,
            positive_text=row.positive_text,
            negative_text=row.negative_text,
            body_text=row.body_text,
        )
        resolved.append((row, property_id, fingerprint))

    # 2. Look up what already exists, in bulk.
    existing_by_hash, existing_by_external = _existing_reviews(
        db,
        source,
        [h for _, _, h in resolved],
        [r.external_review_id for r, _, _ in resolved if r.external_review_id],
    )

    # 3. Decide each row's fate, in file order.
    outcome = _Outcome(rejected=len({i.row_number for i in rejected_issues}))
    issues: list[tuple[RowIssueData, int | Review | None]] = [(i, None) for i in rejected_issues]
    new_reviews: list[Review] = []
    seen_hash: dict[str, Review] = {}
    seen_external: dict[str, Review] = {}

    def add_issue(
        row_number: int,
        kind: str,
        code: str,
        message: str,
        of: int | Review | None = None,
        field_name: str | None = None,
    ) -> None:
        issues.append((RowIssueData(row_number, kind, code, message, field_name), of))

    for row, property_id, fingerprint in resolved:
        external = row.external_review_id
        if external and external in seen_external:
            outcome.duplicates += 1
            add_issue(
                row.row_number,
                RowOutcome.DUPLICATE,
                "DUPLICATE_IN_FILE",
                f"Review ID '{external}' already appeared earlier in this file; "
                "the first occurrence was kept.",
                seen_external[external],
            )
            continue
        if fingerprint in seen_hash:
            outcome.duplicates += 1
            add_issue(
                row.row_number,
                RowOutcome.DUPLICATE,
                "DUPLICATE_IN_FILE",
                "Identical to an earlier row in this file.",
                seen_hash[fingerprint],
            )
            continue

        existing = existing_by_external.get(external) if external else None
        if existing is not None:
            if existing.content_hash == fingerprint:
                outcome.duplicates += 1
                add_issue(
                    row.row_number,
                    RowOutcome.DUPLICATE,
                    "DUPLICATE_EXTERNAL_ID",
                    f"Review ID '{external}' is already imported and unchanged.",
                    existing.id,
                )
                continue
            if fingerprint in existing_by_hash:
                outcome.duplicates += 1
                add_issue(
                    row.row_number,
                    RowOutcome.DUPLICATE,
                    "DUPLICATE_CONTENT",
                    "The updated content is identical to another stored review.",
                    existing_by_hash[fingerprint],
                )
                continue
            changed = _apply_update(existing, row, property_id, fingerprint)
            existing_by_hash.pop(existing.content_hash, None)
            existing_by_hash[fingerprint] = existing.id
            seen_hash[fingerprint] = existing
            seen_external[external] = existing
            outcome.updated += 1
            add_issue(
                row.row_number,
                RowOutcome.WARNING,
                "REVIEW_UPDATED",
                f"Existing review {existing.id} was updated (changed: {', '.join(changed)}).",
                existing.id,
            )
            for warning in row.warnings:
                issues.append((warning, None))
            continue

        if fingerprint in existing_by_hash:
            outcome.duplicates += 1
            add_issue(
                row.row_number,
                RowOutcome.DUPLICATE,
                "DUPLICATE_CONTENT",
                "A review with the same property, date, rating and text is already stored.",
                existing_by_hash[fingerprint],
            )
            continue

        review = Review(
            external_review_id=external,
            property_id=property_id,
            import_id=batch_id,
            source=source,
            review_date=row.review_date,
            rating=row.rating,
            rating_raw=row.rating_raw,
            title=row.title,
            positive_text=row.positive_text,
            negative_text=row.negative_text,
            body_text=row.body_text,
            language=row.language,
            traveller_type=row.traveller_type,
            reviewer_country=row.reviewer_country,
            room_type=row.room_type,
            stay_nights=row.stay_nights,
            source_url=row.source_url,
            content_hash=fingerprint,
            is_synthetic=req.is_synthetic,
        )
        new_reviews.append(review)
        seen_hash[fingerprint] = review
        if external:
            seen_external[external] = review
        outcome.imported += 1
        for warning in row.warnings:
            issues.append((warning, None))

    if outcome.imported + outcome.updated + outcome.duplicates + outcome.rejected != total_rows:
        raise RuntimeError("Import counts do not reconcile; rolling back.")

    # 4. Persist reviews first so in-file duplicates can point at real IDs.
    db.add_all(new_reviews)
    db.flush()
    db.add_all(
        ImportRowIssue(
            import_id=batch_id,
            row_number=data.row_number,
            outcome=data.outcome,
            field=data.field,
            code=data.code,
            message=data.message[:500],
            duplicate_of_review_id=of.id if isinstance(of, Review) else of,
        )
        for data, of in issues
    )

    # 5. Remember new spellings of property names for next time.
    if req.remember_aliases and req.property_mapping:
        _remember_aliases(db, req.property_mapping, index)

    batch.status = ImportStatus.COMPLETED.value
    batch.total_rows = total_rows
    batch.imported_rows = outcome.imported
    batch.updated_rows = outcome.updated
    batch.duplicate_rows = outcome.duplicates
    batch.rejected_rows = outcome.rejected
    batch.completed_at = utcnow()
    batch.error_message = None


def _apply_update(review: Review, row: CleanRow, property_id: int, fingerprint: str) -> list[str]:
    candidates: dict[str, Any] = {
        "property": property_id,
        "date": row.review_date,
        "rating": row.rating,
        "title": row.title,
        "positive text": row.positive_text,
        "negative text": row.negative_text,
        "review text": row.body_text,
    }
    current: dict[str, Any] = {
        "property": review.property_id,
        "date": review.review_date,
        "rating": review.rating,
        "title": review.title,
        "positive text": review.positive_text,
        "negative text": review.negative_text,
        "review text": review.body_text,
    }
    changed = [name for name, new in candidates.items() if new != current[name]]
    review.property_id = property_id
    review.review_date = row.review_date
    review.rating = row.rating
    review.rating_raw = row.rating_raw
    review.title = row.title
    review.positive_text = row.positive_text
    review.negative_text = row.negative_text
    review.body_text = row.body_text
    review.language = row.language or review.language
    review.traveller_type = row.traveller_type or review.traveller_type
    review.reviewer_country = row.reviewer_country or review.reviewer_country
    review.room_type = row.room_type or review.room_type
    review.stay_nights = row.stay_nights if row.stay_nights is not None else review.stay_nights
    review.source_url = row.source_url or review.source_url
    review.content_hash = fingerprint
    review.updated_at = utcnow()
    return changed or ["details"]


def _remember_aliases(db: Session, mapping: dict[str, int], index: PropertyIndex) -> None:
    known = {normalise_for_match(raw) for raw in mapping if index.exact(raw) is not None}
    added: set[str] = set()
    for raw, property_id in mapping.items():
        key = normalise_for_match(raw)
        if not key or key in known or key in added:
            continue
        db.add(PropertyAlias(property_id=property_id, alias_normalised=key[:200]))
        added.add(key)


def _is_locked(exc: OperationalError) -> bool:
    text = str(exc.orig).lower() if exc.orig else ""
    return "locked" in text or "busy" in text


def commit_import(
    db: Session, settings: Settings, batch_id: int, req: CommitRequest
) -> ImportBatch:
    batch = get_batch(db, batch_id)
    if batch.status != ImportStatus.PREVIEWED:
        raise AppError(409, "IMPORT_NOT_PENDING", "This import has already been processed.")

    table = load_stored_table(db, settings, batch, req.sheet)
    index = PropertyIndex(db)
    _validate_request(db, table, req, index)

    source = (
        SYNTHETIC_SOURCE
        if req.is_synthetic
        else (req.source_name.strip().lower() or DEFAULT_SOURCE)
    )
    source = source[:64]
    today = date.today()

    # Phase A (no database writes): validate every row.
    clean_rows: list[CleanRow] = []
    row_issues: list[RowIssueData] = []
    for row_number, raw in zip(table.row_numbers, table.rows, strict=True):
        clean, rejection = convert_row(
            row_number,
            raw,
            req.column_mapping,
            scale_max=req.rating_scale_max,
            date_format=req.date_format,
            today=today,
        )
        if clean is None:
            row_issues.extend(rejection)
        else:
            clean_rows.append(clean)

    batch.column_mapping = dict(req.column_mapping)
    batch.rating_scale_max = req.rating_scale_max
    batch.source_name = source
    batch.is_synthetic = req.is_synthetic
    batch.import_options = {
        "property_mapping": req.property_mapping,
        "fixed_property_id": req.fixed_property_id,
        "date_format": req.date_format,
        "sheet": table.sheet,
        "remember_aliases": req.remember_aliases,
    }
    batch.status = ImportStatus.PROCESSING.value
    db.commit()

    # Phase B: one transaction, retried if SQLite is briefly locked.
    last_error: Exception | None = None
    for attempt in range(DB_RETRIES):
        try:
            _write_phase(db, batch_id, clean_rows, row_issues, req, len(table.rows), source)
            db.commit()
            last_error = None
            break
        except OperationalError as exc:
            db.rollback()
            last_error = exc
            if _is_locked(exc) and attempt < DB_RETRIES - 1:
                time.sleep(0.25 * 2**attempt)
                continue
            break
        except Exception as exc:  # noqa: BLE001 - everything must roll back, then be reported
            db.rollback()
            last_error = exc
            break

    if last_error is not None:
        logger.exception("Import %s failed and was rolled back", batch_id, exc_info=last_error)
        failed = db.get(ImportBatch, batch_id)
        if failed is not None:
            failed.status = ImportStatus.FAILED.value
            failed.error_message = "The import failed and was rolled back. No reviews were saved."
            _remove_stored_file(settings, failed)
            db.commit()
        raise AppError(
            500, "IMPORT_FAILED", "The import failed and was rolled back. No reviews were saved."
        )

    batch = get_batch(db, batch_id)
    _remove_stored_file(settings, batch)  # review data is private; do not keep the raw upload
    db.commit()
    return batch


# --------------------------------------------------------------------------- history / undo
def issue_summary(db: Session, batch_id: int) -> list[tuple[str, str, int]]:
    rows = db.execute(
        select(ImportRowIssue.outcome, ImportRowIssue.code, func.count())
        .where(ImportRowIssue.import_id == batch_id)
        .group_by(ImportRowIssue.outcome, ImportRowIssue.code)
        .order_by(func.count().desc())
    ).all()
    return [(o, c, n) for o, c, n in rows]


def delete_import(db: Session, settings: Settings, batch_id: int) -> int:
    """Undo an import: remove the batch, its issues and every review it created."""
    batch = get_batch(db, batch_id)
    if batch.status == ImportStatus.PROCESSING:
        raise AppError(409, "IMPORT_IN_PROGRESS", "This import is still running.")
    removed = (
        db.scalar(select(func.count()).select_from(Review).where(Review.import_id == batch_id)) or 0
    )
    _remove_stored_file(settings, batch)
    db.execute(delete(Review).where(Review.import_id == batch_id))
    db.delete(batch)
    db.commit()
    return removed


def purge_batches(db: Session, settings: Settings, batches: Iterable[ImportBatch]) -> int:
    total = 0
    for batch in list(batches):
        total += delete_import(db, settings, batch.id)
    return total
