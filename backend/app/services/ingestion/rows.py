"""Row-level validation: turn one raw spreadsheet row into a clean review, or explain why not."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.core.errors import AppError
from app.models.base import RowOutcome
from app.services.ingestion.normalise import clean_text

DATE_FORMATS = ("auto", "iso", "dmy", "mdy")
EARLIEST_PLAUSIBLE_DATE = date(1996, 1, 1)  # online hotel reviews do not exist before this
MAX_TEXT_LENGTH = 20_000

_NUMERIC_DATE = re.compile(r"^(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{1,4})$")
_TEXT_DATE_FORMATS = (
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%A, %d %B %Y",
    "%d %B, %Y",
)
_PLAIN_NUMBER = re.compile(r"^\d+(\.\d+)?$")
_LANGUAGE = re.compile(r"^[A-Za-z]{2,3}([-_][A-Za-z0-9]{2,4})?$")


class RowError(Exception):
    """A single field problem that makes the whole row unusable."""

    def __init__(self, field: str, code: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.code = code
        self.message = message


@dataclass
class RowIssueData:
    row_number: int
    outcome: str
    code: str
    message: str
    field: str | None = None


@dataclass
class CleanRow:
    row_number: int
    external_review_id: str | None
    property_raw: str | None
    review_date: date
    rating_raw: Decimal | None
    rating: Decimal | None  # normalised to 0-10
    title: str | None
    positive_text: str | None
    negative_text: str | None
    body_text: str | None
    language: str | None
    traveller_type: str | None
    reviewer_country: str | None
    room_type: str | None
    stay_nights: int | None
    source_url: str | None
    warnings: list[RowIssueData] = field(default_factory=list)


def parse_date(value: Any, date_format: str, today: date) -> date:
    """Parse a cell into a date. Ambiguous day/month order is rejected, never guessed."""
    if date_format not in DATE_FORMATS:
        raise AppError(422, "INVALID_DATE_FORMAT", f"Unknown date format '{date_format}'.")
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        text = clean_text(value)
        if text is None:
            raise RowError("review_date", "MISSING_DATE", "The review date is missing.")
        parsed = _parse_date_text(text, date_format)

    if parsed > today:
        raise RowError("review_date", "FUTURE_DATE", f"The review date {parsed} is in the future.")
    if parsed < EARLIEST_PLAUSIBLE_DATE:
        raise RowError("review_date", "INVALID_DATE", f"The review date {parsed} is not plausible.")
    return parsed


def _parse_date_text(text: str, date_format: str) -> date:
    bad = RowError("review_date", "INVALID_DATE", f"'{text}' is not a recognised date.")

    # ISO first: 2026-03-14, 2026/03/14, with an optional time part.
    iso = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[T ].*)?$", text)
    if iso:
        try:
            return date(int(iso[1]), int(iso[2]), int(iso[3]))
        except ValueError:
            raise bad from None

    for fmt in _TEXT_DATE_FORMATS:  # "14 March 2026", "March 14, 2026"
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    numeric = _NUMERIC_DATE.match(text)
    if numeric and len(numeric[3]) == 4:
        first, second, year = int(numeric[1]), int(numeric[2]), int(numeric[3])
        if date_format == "iso":
            raise bad
        order = date_format
        if date_format == "auto":
            if first > 12:
                order = "dmy"
            elif second > 12:
                order = "mdy"
            elif first == second:
                order = "dmy"  # same either way
            else:
                raise RowError(
                    "review_date",
                    "AMBIGUOUS_DATE",
                    f"'{text}' could be day/month or month/day. "
                    "Choose the date format for this file.",
                )
        day, month = (first, second) if order == "dmy" else (second, first)
        try:
            return date(year, month, day)
        except ValueError:
            raise bad from None
    raise bad


def parse_rating(value: Any, scale_max: Decimal) -> tuple[Decimal | None, Decimal | None]:
    """Return (raw, normalised-to-0..10). Blank is (None, None). Out of range raises."""
    if value is None or isinstance(value, bool):
        return (None, None) if value is None else _bad_rating(value)
    if isinstance(value, int | float | Decimal):
        number_text = str(value)
    else:
        number_text = str(value).strip()
        if not number_text:
            return None, None
        if "," in number_text and "." not in number_text:
            number_text = number_text.replace(",", ".")  # "8,5" decimal comma
    if not _PLAIN_NUMBER.match(number_text):
        return _bad_rating(value)
    try:
        raw = Decimal(number_text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return _bad_rating(value)
    if raw < 0 or raw > scale_max:
        raise RowError(
            "rating",
            "RATING_OUT_OF_RANGE",
            f"Rating {raw} is outside the allowed range 0 to {scale_max:g}.",
        )
    normalised = (raw * Decimal(10) / scale_max).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return raw, normalised


def _bad_rating(value: Any) -> tuple[None, None]:
    raise RowError("rating", "INVALID_RATING", f"'{value}' is not a valid rating.")


def _external_id(value: Any) -> str | None:
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # Excel stores 123456 as 123456.0
    text = clean_text(value)
    return text[:128] if text else None


def convert_row(
    row_number: int,
    raw: dict[str, Any],
    mapping: dict[str, str],
    *,
    scale_max: Decimal,
    date_format: str,
    today: date,
) -> tuple[CleanRow | None, list[RowIssueData]]:
    """Validate one row: (clean row, []) or (None, [rejection]). Warnings ride on the row."""

    def cell(field_key: str) -> Any:
        column = mapping.get(field_key)
        return raw.get(column) if column else None

    try:
        review_date = parse_date(cell("review_date"), date_format, today)
        rating_raw, rating = parse_rating(cell("rating"), scale_max)
    except RowError as err:
        return None, [
            RowIssueData(row_number, RowOutcome.REJECTED, err.code, err.message, err.field)
        ]

    texts: dict[str, str | None] = {}
    for key in ("title", "positive_text", "negative_text", "body_text"):
        text = clean_text(cell(key))
        if text is not None and len(text) > MAX_TEXT_LENGTH:
            return None, [
                RowIssueData(
                    row_number,
                    RowOutcome.REJECTED,
                    "TEXT_TOO_LONG",
                    f"{key} is longer than {MAX_TEXT_LENGTH:,} characters.",
                    key,
                )
            ]
        texts[key] = text

    if rating is None and not any(
        texts[k] for k in ("positive_text", "negative_text", "body_text")
    ):
        return None, [
            RowIssueData(
                row_number,
                RowOutcome.REJECTED,
                "EMPTY_REVIEW",
                "The row has neither a rating nor any review text.",
            )
        ]

    warnings: list[RowIssueData] = []
    if rating is None:
        warnings.append(
            RowIssueData(
                row_number,
                RowOutcome.WARNING,
                "MISSING_RATING",
                "No rating; imported with text only.",
                "rating",
            )
        )

    language = clean_text(cell("language"))
    if language and not _LANGUAGE.match(language):
        warnings.append(
            RowIssueData(
                row_number,
                RowOutcome.WARNING,
                "INVALID_LANGUAGE",
                f"'{language}' is not a language code (e.g. 'en'); ignored.",
                "language",
            )
        )
        language = None
    language = language.lower().replace("_", "-") if language else None

    stay_nights: int | None = None
    nights_raw = clean_text(cell("stay_nights"))
    if nights_raw:
        try:
            stay_nights = int(float(nights_raw))
            if not 0 <= stay_nights <= 1000:
                raise ValueError
        except ValueError:
            stay_nights = None
            warnings.append(
                RowIssueData(
                    row_number,
                    RowOutcome.WARNING,
                    "INVALID_STAY_NIGHTS",
                    f"'{nights_raw}' is not a valid number of nights; ignored.",
                    "stay_nights",
                )
            )

    source_url = clean_text(cell("source_url"))
    if source_url and not re.match(r"^https?://", source_url, re.IGNORECASE):
        warnings.append(
            RowIssueData(
                row_number,
                RowOutcome.WARNING,
                "INVALID_URL",
                "The source URL is not an http(s) link; ignored.",
                "source_url",
            )
        )
        source_url = None

    def short(key: str) -> str | None:
        text = clean_text(cell(key))
        return text[:100] if text else None

    return (
        CleanRow(
            row_number=row_number,
            external_review_id=_external_id(cell("external_review_id")),
            property_raw=clean_text(cell("property")),
            review_date=review_date,
            rating_raw=rating_raw,
            rating=rating,
            title=texts["title"],
            positive_text=texts["positive_text"],
            negative_text=texts["negative_text"],
            body_text=texts["body_text"],
            language=language[:8] if language else None,
            traveller_type=short("traveller_type"),
            reviewer_country=short("reviewer_country"),
            room_type=short("room_type"),
            stay_nights=stay_nights,
            source_url=source_url,
            warnings=warnings,
        ),
        [],
    )
