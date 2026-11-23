"""Safe parsing of uploaded CSV and XLSX files into a plain table.

The file is checked by extension *and* by content: a renamed binary is rejected, and an XLSX
(which is a zip archive) is checked for decompression bombs before it is opened.
"""

import csv
import io
import zipfile
from dataclasses import dataclass, field
from typing import Any

from app.core.errors import AppError

CSV_EXTENSIONS = {".csv", ".txt"}
XLSX_EXTENSIONS = {".xlsx"}
MAX_UNCOMPRESSED_XLSX_BYTES = 200 * 1024 * 1024
_ZIP_MAGIC = b"PK\x03\x04"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0"  # legacy .xls


@dataclass
class ParsedTable:
    source_type: str  # "csv" | "xlsx"
    columns: list[str]
    rows: list[dict[str, Any]]  # one dict per non-blank data row, keyed by column name
    row_numbers: list[int]  # spreadsheet row number of each entry in `rows` (header = row 1)
    sheets: list[str] = field(default_factory=list)
    sheet: str | None = None
    encoding: str | None = None
    delimiter: str | None = None


def extension_of(filename: str) -> str:
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
    return name[name.rfind(".") :] if "." in name else ""


def detect_source_type(filename: str, data: bytes) -> str:
    """Return "csv" or "xlsx", or raise 415/422. Never trusts the extension alone."""
    ext = extension_of(filename)
    if not data:
        raise AppError(422, "EMPTY_FILE", "The uploaded file is empty.")
    if ext in XLSX_EXTENSIONS:
        if not data.startswith(_ZIP_MAGIC):
            raise AppError(
                415, "FILE_CONTENT_MISMATCH", "This file is named .xlsx but is not an Excel file."
            )
        return "xlsx"
    if ext in CSV_EXTENSIONS:
        if data.startswith(_ZIP_MAGIC) or data.startswith(_OLE_MAGIC):
            raise AppError(
                415, "FILE_CONTENT_MISMATCH", "This file is named .csv but contains binary data."
            )
        return "csv"
    raise AppError(
        415,
        "UNSUPPORTED_FILE_TYPE",
        "Only .csv and .xlsx files can be imported.",
        [{"extension": ext or "(none)"}],
    )


def _decode_csv(data: bytes) -> tuple[str, str]:
    """Decode bytes to text. Returns (text, encoding_name)."""
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), "utf-16"
    if b"\x00" in data[:8192]:
        raise AppError(
            415, "FILE_CONTENT_MISMATCH", "This file contains binary data and is not a CSV."
        )
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        # Excel on Windows commonly saves "CSV" as cp1252.
        return data.decode("cp1252", errors="replace"), "cp1252"


def _sniff_delimiter(text: str) -> str:
    sample = text[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        lines = sample.splitlines()
        first_line = lines[0] if lines else ""
        return max(",;\t|", key=first_line.count)


def _clean_headers(raw_headers: list[Any]) -> list[str | None]:
    """Trim headers; blank ones become None (ignored); duplicates get a numeric suffix."""
    seen: dict[str, int] = {}
    headers: list[str | None] = []
    for raw in raw_headers:
        name = str(raw).strip() if raw is not None else ""
        if not name:
            headers.append(None)
            continue
        seen[name] = seen.get(name, 0) + 1
        headers.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return headers


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _build_table(source_type: str, raw_rows: Any, max_rows: int, **extra: Any) -> ParsedTable:
    iterator = iter(raw_rows)
    try:
        raw_headers = list(next(iterator))
    except StopIteration:
        raise AppError(422, "EMPTY_FILE", "The file has no header row.") from None
    headers = _clean_headers(raw_headers)
    if not any(headers):
        raise AppError(422, "NO_HEADER", "The first row must contain column names.")

    rows: list[dict[str, Any]] = []
    row_numbers: list[int] = []
    for row_number, values in enumerate(iterator, start=2):
        values = list(values)
        if all(_is_blank(v) for v in values):
            continue  # fully blank lines are not records
        if len(rows) >= max_rows:
            raise AppError(
                413,
                "TOO_MANY_ROWS",
                f"The file has more than {max_rows:,} data rows. Split it into smaller files.",
            )
        rows.append(
            {h: (values[i] if i < len(values) else None) for i, h in enumerate(headers) if h}
        )
        row_numbers.append(row_number)
    if not rows:
        raise AppError(422, "NO_DATA_ROWS", "The file has a header row but no data rows.")
    return ParsedTable(
        source_type=source_type,
        columns=[h for h in headers if h],
        rows=rows,
        row_numbers=row_numbers,
        **extra,
    )


def parse_csv(data: bytes, max_rows: int) -> ParsedTable:
    text, encoding = _decode_csv(data)
    if not text.strip():
        raise AppError(422, "EMPTY_FILE", "The uploaded file is empty.")
    delimiter = _sniff_delimiter(text)
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
        return _build_table("csv", reader, max_rows, encoding=encoding, delimiter=delimiter)
    except csv.Error as exc:
        raise AppError(422, "UNREADABLE_FILE", f"The CSV could not be read: {exc}") from exc


def parse_xlsx(data: bytes, max_rows: int, sheet: str | None = None) -> ParsedTable:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if "xl/workbook.xml" not in set(archive.namelist()):
                raise AppError(415, "FILE_CONTENT_MISMATCH", "This is not a valid Excel workbook.")
            if sum(i.file_size for i in archive.infolist()) > MAX_UNCOMPRESSED_XLSX_BYTES:
                raise AppError(
                    413,
                    "FILE_TOO_LARGE",
                    "The workbook expands to an unsafe size and was rejected.",
                )
    except zipfile.BadZipFile:
        raise AppError(
            415, "FILE_CONTENT_MISMATCH", "This is not a valid Excel workbook."
        ) from None

    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises many unrelated types for damaged files
        raise AppError(422, "UNREADABLE_FILE", "The Excel workbook could not be read.") from exc
    try:
        sheets = list(workbook.sheetnames)
        if sheet is not None and sheet not in sheets:
            raise AppError(422, "UNKNOWN_SHEET", f"The workbook has no sheet named '{sheet}'.")
        last_error: AppError | None = None
        for name in [sheet] if sheet else sheets:
            try:
                return _build_table(
                    "xlsx",
                    workbook[name].iter_rows(values_only=True),
                    max_rows,
                    sheets=sheets,
                    sheet=name,
                )
            except AppError as exc:
                if exc.code == "TOO_MANY_ROWS":
                    raise
                last_error = exc  # when no sheet was named, fall through to the next one
        assert last_error is not None
        raise last_error
    finally:
        workbook.close()


def parse_file(filename: str, data: bytes, max_rows: int, sheet: str | None = None) -> ParsedTable:
    if detect_source_type(filename, data) == "xlsx":
        return parse_xlsx(data, max_rows, sheet)
    return parse_csv(data, max_rows)
