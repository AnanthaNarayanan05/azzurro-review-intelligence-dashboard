"""Unit tests for parsing, mapping, row validation and fingerprinting (no database)."""

import io
import zipfile
from datetime import date
from decimal import Decimal

import pytest
from openpyxl import Workbook

from app.core.errors import AppError
from app.services.ingestion.mapping import suggest_mapping
from app.services.ingestion.normalise import content_hash, normalise_for_match
from app.services.ingestion.parsing import parse_file
from app.services.ingestion.rows import RowError, convert_row, parse_date, parse_rating

TODAY = date(2026, 11, 23)
MAX_ROWS = 1000


def xlsx_bytes(sheets: dict[str, list[list]]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------- fingerprinting
def fingerprint(**overrides) -> str:
    base = dict(
        source="booking.com",
        property_id=1,
        review_date=date(2026, 3, 1),
        rating=Decimal("8.00"),
        title=None,
        positive_text="Great location!",
        negative_text=None,
        body_text=None,
    )
    return content_hash(**(base | overrides))


def test_fingerprint_ignores_case_punctuation_and_spacing():
    assert fingerprint() == fingerprint(positive_text="  GREAT   location ")


@pytest.mark.parametrize(
    "change",
    [
        {"property_id": 2},
        {"review_date": date(2026, 3, 2)},
        {"rating": Decimal("7.00")},
        {"rating": None},
        {"positive_text": "Great location and staff"},
        {"source": "synthetic-demo"},
    ],
)
def test_fingerprint_changes_when_the_review_changes(change):
    assert fingerprint() != fingerprint(**change)


def test_normalise_for_match():
    assert normalise_for_match("  Olympic  Hotel, Paddington! ") == "olympic hotel paddington"
    assert normalise_for_match(None) == ""


# ---------------------------------------------------------------- CSV parsing
def test_csv_utf8_with_bom_and_semicolon_delimiter():
    data = "﻿Review Date;Score;Hotel\n2026-01-02;8,5;A\n".encode()
    table = parse_file("x.csv", data, MAX_ROWS)
    assert table.columns == ["Review Date", "Score", "Hotel"]
    assert table.delimiter == ";"
    assert table.encoding == "utf-8-sig"
    assert table.rows[0]["Score"] == "8,5"


def test_csv_non_utf8_falls_back_to_cp1252():
    data = "Date,Text\n2026-01-02,Café très bon\n".encode("cp1252")
    table = parse_file("x.csv", data, MAX_ROWS)
    assert table.encoding == "cp1252"
    assert "Café" in table.rows[0]["Text"]


def test_csv_utf16():
    data = "Date,Text\n2026-01-02,hello\n".encode("utf-16")
    assert parse_file("x.csv", data, MAX_ROWS).rows[0]["Text"] == "hello"


def test_csv_skips_blank_lines_and_tracks_row_numbers():
    table = parse_file("x.csv", b"a,b\n1,2\n\n3,4\n", MAX_ROWS)
    assert table.row_numbers == [2, 4]


def test_csv_duplicate_and_blank_headers_are_made_unique():
    table = parse_file("x.csv", b"a,a,,b\n1,2,3,4\n", MAX_ROWS)
    assert table.columns == ["a", "a (2)", "b"]


@pytest.mark.parametrize(
    ("name", "data", "code", "status"),
    [
        ("x.csv", b"", "EMPTY_FILE", 422),
        ("x.csv", b"   \n  \n", "EMPTY_FILE", 422),
        ("x.csv", b"Date,Score\n", "NO_DATA_ROWS", 422),
        ("x.pdf", b"%PDF-1.4", "UNSUPPORTED_FILE_TYPE", 415),
        ("noextension", b"a,b\n1,2\n", "UNSUPPORTED_FILE_TYPE", 415),
        ("x.xls", b"\xd0\xcf\x11\xe0abc", "UNSUPPORTED_FILE_TYPE", 415),
        ("x.csv", b"PK\x03\x04binary", "FILE_CONTENT_MISMATCH", 415),
        ("x.csv", b"\x89PNG\x00\x00\x00binary\x00", "FILE_CONTENT_MISMATCH", 415),
        ("x.xlsx", b"a,b\n1,2\n", "FILE_CONTENT_MISMATCH", 415),
    ],
)
def test_bad_files_are_rejected_with_a_clear_code(name, data, code, status):
    with pytest.raises(AppError) as err:
        parse_file(name, data, MAX_ROWS)
    assert err.value.code == code
    assert err.value.status_code == status


def test_too_many_rows():
    data = ("a\n" + "1\n" * 11).encode()
    with pytest.raises(AppError) as err:
        parse_file("x.csv", data, 10)
    assert err.value.code == "TOO_MANY_ROWS"
    assert err.value.status_code == 413


# ---------------------------------------------------------------- XLSX parsing
def test_xlsx_reads_first_usable_sheet_and_lists_all_sheets():
    data = xlsx_bytes({"Empty": [], "Reviews": [["Date", "Score"], ["2026-01-02", 9]]})
    table = parse_file("x.xlsx", data, MAX_ROWS)
    assert table.sheets == ["Empty", "Reviews"]
    assert table.sheet == "Reviews"
    assert table.rows == [{"Date": "2026-01-02", "Score": 9}]


def test_xlsx_named_sheet_and_unknown_sheet():
    data = xlsx_bytes({"A": [["x"], [1]], "B": [["y"], [2]]})
    assert parse_file("x.xlsx", data, MAX_ROWS, sheet="B").columns == ["y"]
    with pytest.raises(AppError) as err:
        parse_file("x.xlsx", data, MAX_ROWS, sheet="Nope")
    assert err.value.code == "UNKNOWN_SHEET"


def test_xlsx_that_is_a_zip_but_not_a_workbook_is_rejected():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("hello.txt", "hi")
    with pytest.raises(AppError) as err:
        parse_file("x.xlsx", buffer.getvalue(), MAX_ROWS)
    assert err.value.code == "FILE_CONTENT_MISMATCH"


def test_corrupt_xlsx_is_rejected_not_crashed():
    with pytest.raises(AppError) as err:
        parse_file("x.xlsx", b"PK\x03\x04garbage-not-a-zip", MAX_ROWS)
    assert err.value.status_code in (415, 422)


# ---------------------------------------------------------------- mapping
def test_mapping_suggests_booking_style_headers():
    mapping = suggest_mapping(
        [
            "Review ID",
            "Hotel Name",
            "Review Date",
            "Reviewer Score",
            "Positive review",
            "Negative review",
            "Guest Name",
        ]
    )
    assert mapping["external_review_id"] == "Review ID"
    assert mapping["property"] == "Hotel Name"
    assert mapping["review_date"] == "Review Date"
    assert mapping["rating"] == "Reviewer Score"
    assert mapping["positive_text"] == "Positive review"
    assert mapping["negative_text"] == "Negative review"
    assert "Guest Name" not in mapping.values()  # reviewer names are never importable


def test_mapping_uses_each_column_once_and_leaves_unknowns_empty():
    mapping = suggest_mapping(["date", "stuff"])
    assert mapping["review_date"] == "date"
    assert mapping["rating"] is None
    assert list(mapping.values()).count("date") == 1


# ---------------------------------------------------------------- dates
@pytest.mark.parametrize(
    ("text", "fmt", "expected"),
    [
        ("2026-03-14", "auto", date(2026, 3, 14)),
        ("2026/03/14", "auto", date(2026, 3, 14)),
        ("2026-03-14T10:30:00", "auto", date(2026, 3, 14)),
        ("14 March 2026", "auto", date(2026, 3, 14)),
        ("March 14, 2026", "auto", date(2026, 3, 14)),
        ("25/03/2026", "auto", date(2026, 3, 25)),  # day > 12 -> unambiguous
        ("03/25/2026", "auto", date(2026, 3, 25)),  # month position > 12 -> unambiguous
        ("04/04/2026", "auto", date(2026, 4, 4)),
        ("03/04/2026", "dmy", date(2026, 4, 3)),
        ("03/04/2026", "mdy", date(2026, 3, 4)),
    ],
)
def test_date_parsing(text, fmt, expected):
    assert parse_date(text, fmt, TODAY) == expected


def test_date_objects_from_excel_are_accepted():
    from datetime import datetime

    assert parse_date(datetime(2026, 2, 3, 9, 0), "auto", TODAY) == date(2026, 2, 3)


@pytest.mark.parametrize(
    ("value", "fmt", "code"),
    [
        ("03/04/2026", "auto", "AMBIGUOUS_DATE"),
        ("2026-02-30", "auto", "INVALID_DATE"),
        ("31/02/2026", "dmy", "INVALID_DATE"),
        ("yesterday", "auto", "INVALID_DATE"),
        ("1850-01-01", "auto", "INVALID_DATE"),
        ("2099-01-01", "auto", "FUTURE_DATE"),
        ("", "auto", "MISSING_DATE"),
        (None, "auto", "MISSING_DATE"),
        ("45000", "auto", "INVALID_DATE"),
    ],
)
def test_bad_dates_are_rejected_never_guessed(value, fmt, code):
    with pytest.raises(RowError) as err:
        parse_date(value, fmt, TODAY)
    assert err.value.code == code


# ---------------------------------------------------------------- ratings
@pytest.mark.parametrize(
    ("value", "scale", "raw", "normalised"),
    [
        ("8.5", "10", "8.50", "8.50"),
        ("8,5", "10", "8.50", "8.50"),
        (9, "10", "9.00", "9.00"),
        (4.5, "5", "4.50", "9.00"),
        ("4", "5", "4.00", "8.00"),
        ("0", "10", "0.00", "0.00"),
        ("85", "100", "85.00", "8.50"),
        ("", "10", None, None),
        (None, "10", None, None),
    ],
)
def test_rating_parsing_and_scale_normalisation(value, scale, raw, normalised):
    got_raw, got_norm = parse_rating(value, Decimal(scale))
    assert got_raw == (Decimal(raw) if raw else None)
    assert got_norm == (Decimal(normalised) if normalised else None)


@pytest.mark.parametrize(
    ("value", "scale", "code"),
    [
        ("11", "10", "RATING_OUT_OF_RANGE"),
        ("-1", "10", "INVALID_RATING"),
        ("6", "5", "RATING_OUT_OF_RANGE"),
        ("great", "10", "INVALID_RATING"),
        ("8/10", "10", "INVALID_RATING"),
        (True, "10", "INVALID_RATING"),
    ],
)
def test_bad_ratings_are_rejected(value, scale, code):
    with pytest.raises(RowError) as err:
        parse_rating(value, Decimal(scale))
    assert err.value.code == code


# ---------------------------------------------------------------- whole-row validation
MAPPING = {
    "review_date": "Date",
    "rating": "Score",
    "positive_text": "Good",
    "negative_text": "Bad",
    "property": "Hotel",
}


def convert(raw, **kwargs):
    defaults = dict(scale_max=Decimal(10), date_format="auto", today=TODAY)
    return convert_row(2, raw, MAPPING, **(defaults | kwargs))


def test_good_row_is_cleaned():
    row, issues = convert(
        {"Date": "2026-01-02", "Score": "9", "Good": "  Nice  ", "Bad": "", "Hotel": " A "}
    )
    assert issues == []
    assert row.positive_text == "Nice"
    assert row.negative_text is None
    assert row.property_raw == "A"
    assert row.rating == Decimal("9.00")


def test_row_without_rating_or_text_is_rejected():
    row, issues = convert(
        {"Date": "2026-01-02", "Score": "", "Good": " ", "Bad": None, "Hotel": "A"}
    )
    assert row is None
    assert issues[0].code == "EMPTY_REVIEW"
    assert issues[0].outcome == "rejected"


def test_missing_rating_with_text_is_imported_with_a_warning():
    row, issues = convert({"Date": "2026-01-02", "Score": "", "Good": "Nice", "Hotel": "A"})
    assert issues == []
    assert row.rating is None
    assert [w.code for w in row.warnings] == ["MISSING_RATING"]


def test_bad_row_reports_the_field_and_reason():
    row, issues = convert({"Date": "nonsense", "Score": "9", "Good": "x", "Hotel": "A"})
    assert row is None
    assert (issues[0].code, issues[0].field) == ("INVALID_DATE", "review_date")


def test_oversized_text_is_rejected():
    row, issues = convert({"Date": "2026-01-02", "Score": "9", "Good": "x" * 20_001, "Hotel": "A"})
    assert row is None
    assert issues[0].code == "TEXT_TOO_LONG"


def test_optional_fields_that_are_bad_become_warnings_not_rejections():
    mapping = MAPPING | {"language": "Lang", "stay_nights": "Nights", "source_url": "Url"}
    row, _ = convert_row(
        2,
        {
            "Date": "2026-01-02",
            "Score": "9",
            "Good": "x",
            "Hotel": "A",
            "Lang": "English!!",
            "Nights": "lots",
            "Url": "javascript:alert(1)",
        },
        mapping,
        scale_max=Decimal(10),
        date_format="auto",
        today=TODAY,
    )
    assert row is not None
    assert row.language is None and row.stay_nights is None and row.source_url is None
    assert {w.code for w in row.warnings} == {
        "INVALID_LANGUAGE",
        "INVALID_STAY_NIGHTS",
        "INVALID_URL",
    }


def test_excel_numeric_external_id_has_no_decimal_suffix():
    mapping = MAPPING | {"external_review_id": "Id"}
    row, _ = convert_row(
        2,
        {"Date": "2026-01-02", "Score": "9", "Good": "x", "Hotel": "A", "Id": 123456.0},
        mapping,
        scale_max=Decimal(10),
        date_format="auto",
        today=TODAY,
    )
    assert row.external_review_id == "123456"
