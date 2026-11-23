"""End-to-end import tests through the real API against a migrated temporary database."""

import csv
import io
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.core.config import Settings, get_settings
from app.models import ImportBatch, ImportRowIssue, Property, PropertyAlias, Review
from app.services.ingestion import pipeline
from tests.test_ingestion_units import xlsx_bytes

GOOD_HEADERS = ["Review ID", "Hotel", "Review Date", "Score", "Positive review", "Negative review"]


def make_csv(rows: list[list], headers: list[str] | None = None) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(headers or GOOD_HEADERS)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def review_row(n: int, hotel: str = "Hotel A", **kw) -> list:
    return [
        kw.get("id", f"R{n}"),
        hotel,
        kw.get("date", "2026-03-01"),
        kw.get("score", "8"),
        kw.get("pos", f"Lovely stay number {n}"),
        kw.get("neg", ""),
    ]


@pytest.fixture()
def prop_a(client) -> int:
    return client.post("/api/properties", json={"name": "Hotel A"}).json()["data"]["id"]


@pytest.fixture()
def prop_b(client) -> int:
    return client.post("/api/properties", json={"name": "Hotel B"}).json()["data"]["id"]


def upload(client, data: bytes, name: str = "reviews.csv"):
    return client.post("/api/imports/preview", files={"file": (name, data, "text/csv")})


def run_import(client, data: bytes, name: str = "reviews.csv", **overrides):
    """Preview then commit using the suggested column mapping. Returns the commit response."""
    preview = upload(client, data, name)
    assert preview.status_code == 201, preview.text
    body = preview.json()["data"]
    commit = {
        "column_mapping": {k: v for k, v in body["suggested_mapping"].items() if v},
        "property_mapping": {
            v["value"]: v["suggested_property_id"]
            for v in body["property_values"]["values"]
            if v["suggested_property_id"]
        },
    } | overrides
    return client.post(f"/api/imports/{body['import_id']}/commit", json=commit)


def counts(report: dict) -> tuple[int, int, int, int]:
    return (
        report["imported_rows"],
        report["updated_rows"],
        report["duplicate_rows"],
        report["rejected_rows"],
    )


def assert_reconciles(report: dict) -> None:
    assert sum(counts(report)) == report["total_rows"]


# ---------------------------------------------------------------- preview
def test_preview_returns_columns_sample_mapping_and_property_suggestions(client, prop_a):
    data = make_csv([review_row(i) for i in range(30)] + [review_row(99, hotel="hotel  a ")])
    body = upload(client, data).json()["data"]
    assert body["total_rows"] == 31
    assert body["columns"] == GOOD_HEADERS
    assert len(body["sample_rows"]) == 20
    assert body["suggested_mapping"]["property"] == "Hotel"
    values = {v["value"]: v for v in body["property_values"]["values"]}
    assert values["Hotel A"]["suggested_property_id"] == prop_a
    assert values["Hotel A"]["match_type"] == "name"
    assert values["hotel  a"]["suggested_property_id"] == prop_a  # tolerant of case/spacing


def test_preview_suggests_close_spellings_as_similar(client, prop_a):
    body = upload(client, make_csv([review_row(1, hotel="Hotl A")])).json()["data"]
    value = body["property_values"]["values"][0]
    assert value["match_type"] == "similar"
    assert value["suggested_property_id"] == prop_a


def test_preview_does_not_write_reviews(client, db_session, prop_a):
    upload(client, make_csv([review_row(1)]))
    assert db_session.scalar(select(func.count()).select_from(Review)) == 0


@pytest.mark.parametrize(
    ("name", "data", "status", "code"),
    [
        ("reviews.csv", b"", 422, "EMPTY_FILE"),
        ("reviews.csv", b"Date,Score\n", 422, "NO_DATA_ROWS"),
        ("reviews.pdf", b"%PDF-1.4 fake", 415, "UNSUPPORTED_FILE_TYPE"),
        ("reviews.xlsx", b"just,text\n1,2\n", 415, "FILE_CONTENT_MISMATCH"),
        ("reviews.csv", b"PK\x03\x04zipdata", 415, "FILE_CONTENT_MISMATCH"),
    ],
)
def test_invalid_uploads_return_clear_errors_and_store_nothing(
    client, settings, name, data, status, code
):
    response = upload(client, data, name)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert not settings.resolved_upload_dir.exists() or not list(
        settings.resolved_upload_dir.iterdir()
    )


def test_upload_larger_than_the_limit_is_rejected_with_413(app, client):
    tiny = Settings(max_upload_mb=1, upload_dir="x")
    app.dependency_overrides[get_settings] = lambda: tiny
    response = upload(client, b"a,b\n" + b"1,2\n" * 400_000)  # ~1.6 MB
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_file_with_too_many_rows_is_rejected_with_413(app, client, tmp_path):
    app.dependency_overrides[get_settings] = lambda: Settings(
        max_import_rows=5, upload_dir=str(tmp_path / "u")
    )
    response = upload(client, make_csv([review_row(i) for i in range(6)]))
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "TOO_MANY_ROWS"


# ---------------------------------------------------------------- successful imports
def test_valid_csv_import(client, db_session, prop_a):
    response = run_import(client, make_csv([review_row(i) for i in range(1, 6)]))
    assert response.status_code == 200
    report = response.json()["data"]
    assert counts(report) == (5, 0, 0, 0)
    assert report["status"] == "completed"
    assert report["source_name"] == "booking.com"
    assert report["is_synthetic"] is False
    assert_reconciles(report)
    reviews = db_session.scalars(select(Review)).all()
    assert len(reviews) == 5
    assert all(r.property_id == prop_a and not r.is_synthetic for r in reviews)
    assert all(r.source == "booking.com" and r.imported_at is not None for r in reviews)


def test_valid_xlsx_import_with_excel_dates_and_numbers(client, db_session, prop_a):
    data = xlsx_bytes(
        {
            "Reviews": [
                GOOD_HEADERS,
                [1001, "Hotel A", date(2026, 3, 1), 9, "Great", ""],
                [1002, "Hotel A", date(2026, 3, 2), 7.5, "OK", "Noisy"],
            ]
        }
    )
    report = run_import(client, data, "reviews.xlsx").json()["data"]
    assert counts(report) == (2, 0, 0, 0)
    assert report["source_type"] == "xlsx"
    stored = {r.external_review_id: r for r in db_session.scalars(select(Review))}
    assert set(stored) == {"1001", "1002"}
    assert str(stored["1002"].rating) == "7.50"


def test_uploaded_file_is_deleted_after_a_completed_import(client, settings, prop_a):
    run_import(client, make_csv([review_row(1)]))
    assert list(settings.resolved_upload_dir.iterdir()) == []


def test_rating_scale_is_normalised_to_ten(client, db_session, prop_a):
    data = make_csv([review_row(1, score="4"), review_row(2, score="2.5")])
    run_import(client, data, rating_scale_max=5)
    ratings = sorted(float(r.rating) for r in db_session.scalars(select(Review)))
    raws = sorted(float(r.rating_raw) for r in db_session.scalars(select(Review)))
    assert ratings == [5.0, 8.0]
    assert raws == [2.5, 4.0]


def test_rating_out_of_range_for_the_chosen_scale_is_rejected(client, prop_a):
    data = make_csv([review_row(1, score="8"), review_row(2, score="4")])
    report = run_import(client, data, rating_scale_max=5).json()["data"]
    assert counts(report) == (1, 0, 0, 1)  # 8 is invalid on a 5-point scale
    assert_reconciles(report)


def test_fixed_property_needs_no_property_column(client, db_session, prop_a):
    data = make_csv(
        [["R1", "2026-03-01", "9", "Great"]],
        headers=["Review ID", "Review Date", "Score", "Positive review"],
    )
    report = run_import(client, data, fixed_property_id=prop_a).json()["data"]
    assert counts(report) == (1, 0, 0, 0)
    assert db_session.scalar(select(Review.property_id)) == prop_a


def test_custom_source_name_is_recorded(client, db_session, prop_a):
    run_import(client, make_csv([review_row(1)]), source_name="Manual export")
    assert db_session.scalar(select(Review.source)) == "manual export"


# ---------------------------------------------------------------- validation outcomes
def test_invalid_rows_are_reported_individually_and_never_silently_dropped(client, prop_a):
    rows = [
        review_row(1),
        review_row(2, date="not a date"),
        review_row(3, date=""),
        review_row(4, score="eleven"),
        review_row(5, score="11"),
        review_row(6, date="2099-01-01"),
        review_row(7, hotel="Unknown Inn"),
        review_row(8, pos="", neg="", score=""),
        review_row(9, hotel=""),
    ]
    report = run_import(client, make_csv(rows)).json()["data"]
    assert counts(report) == (1, 0, 0, 8)
    assert_reconciles(report)
    codes = {s["code"] for s in report["issue_summary"] if s["outcome"] == "rejected"}
    assert codes == {
        "INVALID_DATE",
        "MISSING_DATE",
        "INVALID_RATING",
        "RATING_OUT_OF_RANGE",
        "FUTURE_DATE",
        "UNKNOWN_PROPERTY",
        "EMPTY_REVIEW",
        "MISSING_PROPERTY",
    }
    issues = client.get(f"/api/imports/{report['id']}/issues?outcome=rejected").json()
    assert issues["meta"]["total"] == 8
    assert {i["row_number"] for i in issues["data"]} == set(range(3, 11))  # header is row 1
    assert all(i["message"] for i in issues["data"])


def test_missing_rating_is_imported_with_a_warning(client, db_session, prop_a):
    report = run_import(client, make_csv([review_row(1, score="")])).json()["data"]
    assert counts(report) == (1, 0, 0, 0)
    assert report["warning_count"] == 1
    assert db_session.scalar(select(Review.rating)) is None


def test_ambiguous_dates_are_rejected_unless_a_format_is_chosen(client, prop_a):
    data = make_csv([review_row(1, date="03/04/2026")])
    assert counts(run_import(client, data).json()["data"]) == (0, 0, 0, 1)
    again = run_import(client, data, date_format="dmy").json()["data"]
    assert counts(again) == (1, 0, 0, 0)


def test_unmapped_property_value_can_be_mapped_explicitly(client, db_session, prop_a):
    data = make_csv([review_row(1, hotel="HOTEL-A-CODE")])
    report = run_import(client, data, property_mapping={"HOTEL-A-CODE": prop_a}).json()["data"]
    assert counts(report) == (1, 0, 0, 0)
    # The new spelling is remembered, so the next file needs no manual mapping.
    assert db_session.scalar(select(PropertyAlias.alias_normalised)) == "hotel a code"
    second = run_import(client, make_csv([review_row(2, hotel="hotel-a-code")])).json()["data"]
    assert counts(second) == (1, 0, 0, 0)


def test_invalid_mapping_is_rejected_with_details(client, prop_a):
    preview = upload(client, make_csv([review_row(1)])).json()["data"]
    response = client.post(
        f"/api/imports/{preview['import_id']}/commit",
        json={"column_mapping": {"rating": "Score", "bogus": "Nope"}},
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_MAPPING"
    fields = {d["field"] for d in error["details"]}
    assert {"bogus", "review_date", "property"} <= fields


def test_commit_validates_property_ids_and_scale(client, prop_a):
    preview = upload(client, make_csv([review_row(1)])).json()["data"]
    mapping = {k: v for k, v in preview["suggested_mapping"].items() if v}
    response = client.post(
        f"/api/imports/{preview['import_id']}/commit",
        json={"column_mapping": mapping, "property_mapping": {"Hotel A": 9999}},
    )
    assert response.status_code == 422
    too_big = client.post(
        f"/api/imports/{preview['import_id']}/commit",
        json={"column_mapping": mapping, "rating_scale_max": 1000},
    )
    assert too_big.status_code == 422


def test_text_that_looks_like_sql_is_stored_as_plain_text(client, db_session, prop_a):
    evil = "Robert'); DROP TABLE reviews;--"
    run_import(client, make_csv([review_row(1, pos=evil), review_row(2, hotel=evil)]))
    assert (
        db_session.scalar(select(Review.positive_text).where(Review.external_review_id == "R1"))
        == evil
    )
    assert db_session.scalar(select(func.count()).select_from(Review)) == 1


# ---------------------------------------------------------------- duplicates and updates
def test_reimporting_the_same_file_creates_no_duplicates(client, db_session, prop_a):
    data = make_csv([review_row(i) for i in range(1, 6)])
    first = run_import(client, data).json()["data"]
    preview = upload(client, data).json()["data"]
    assert preview["already_imported_as"] == first["id"]
    second = run_import(client, data).json()["data"]
    assert counts(second) == (0, 0, 5, 0)
    assert_reconciles(second)
    assert db_session.scalar(select(func.count()).select_from(Review)) == 5
    issues = client.get(f"/api/imports/{second['id']}/issues?outcome=duplicate").json()
    assert {i["code"] for i in issues["data"]} == {"DUPLICATE_EXTERNAL_ID"}
    assert all(i["duplicate_of_review_id"] for i in issues["data"])


def test_duplicates_within_one_file_are_reported_and_first_is_kept(client, db_session, prop_a):
    rows = [
        review_row(1),
        review_row(1),
        review_row(2, id="", pos="same text"),
        review_row(3, id="", pos="same text"),
    ]
    report = run_import(client, make_csv(rows)).json()["data"]
    assert counts(report) == (2, 0, 2, 0)
    assert_reconciles(report)
    assert db_session.scalar(select(func.count()).select_from(Review)) == 2
    issues = client.get(f"/api/imports/{report['id']}/issues?outcome=duplicate").json()["data"]
    assert {i["code"] for i in issues} == {"DUPLICATE_IN_FILE"}
    assert all(i["duplicate_of_review_id"] is not None for i in issues)


def test_reviews_without_ids_are_deduplicated_by_content(client, db_session, prop_a):
    no_id = [review_row(1, id=""), review_row(2, id="")]
    run_import(client, make_csv(no_id))
    second = run_import(client, make_csv(no_id + [review_row(3, id="")])).json()["data"]
    assert counts(second) == (1, 0, 2, 0)
    assert {s["code"] for s in second["issue_summary"] if s["outcome"] == "duplicate"} == {
        "DUPLICATE_CONTENT"
    }
    assert db_session.scalar(select(func.count()).select_from(Review)) == 3


def test_same_text_on_a_different_date_is_not_a_duplicate(client, db_session, prop_a):
    rows = [
        review_row(1, id="", pos="Nice", date="2026-03-01"),
        review_row(2, id="", pos="Nice", date="2026-03-02"),
    ]
    assert counts(run_import(client, make_csv(rows)).json()["data"]) == (2, 0, 0, 0)


def test_same_text_for_a_different_property_is_not_a_duplicate(client, db_session, prop_a, prop_b):
    rows = [
        review_row(1, id="", pos="Nice", hotel="Hotel A"),
        review_row(2, id="", pos="Nice", hotel="Hotel B"),
    ]
    assert counts(run_import(client, make_csv(rows)).json()["data"]) == (2, 0, 0, 0)


def test_changed_review_with_same_external_id_is_updated_not_duplicated(client, db_session, prop_a):
    run_import(client, make_csv([review_row(1, score="6", pos="Okay")]))
    report = run_import(client, make_csv([review_row(1, score="9", pos="Actually great")])).json()[
        "data"
    ]
    assert counts(report) == (0, 1, 0, 0)
    assert_reconciles(report)
    reviews = db_session.scalars(select(Review)).all()
    assert len(reviews) == 1
    assert str(reviews[0].rating) == "9.00"
    assert reviews[0].positive_text == "Actually great"
    assert reviews[0].updated_at is not None
    issue = client.get(f"/api/imports/{report['id']}/issues?outcome=warning").json()["data"][0]
    assert issue["code"] == "REVIEW_UPDATED"
    assert "rating" in issue["message"]


# ---------------------------------------------------------------- transactions
def commit_with_failure(client, monkeypatch, data: bytes) -> object:
    """Preview normally, then make the very last step of the database write blow up."""
    preview = upload(client, data).json()["data"]
    mapping = {k: v for k, v in preview["suggested_mapping"].items() if v}

    def explode():
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(pipeline, "utcnow", explode)  # used when the batch is marked completed
    return client.post(
        f"/api/imports/{preview['import_id']}/commit", json={"column_mapping": mapping}
    )


def test_unexpected_failure_rolls_back_everything(
    client, db_session, settings, prop_a, monkeypatch
):
    rows = [review_row(1), review_row(2), review_row(3, score="bad"), review_row(1)]
    response = commit_with_failure(client, monkeypatch, make_csv(rows))
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "IMPORT_FAILED"
    assert "disk on fire" not in response.text  # internals never leak
    db_session.expire_all()
    # Reviews and issue rows had already been flushed; none of it may survive.
    assert db_session.scalar(select(func.count()).select_from(Review)) == 0
    assert db_session.scalar(select(func.count()).select_from(ImportRowIssue)) == 0
    batch = db_session.scalars(select(ImportBatch)).one()
    assert batch.status == "failed"
    assert batch.error_message
    assert batch.imported_rows == 0
    assert list(settings.resolved_upload_dir.iterdir()) == []


def test_a_failed_import_does_not_block_the_next_one(client, prop_a, monkeypatch):
    with monkeypatch.context() as m:
        assert commit_with_failure(client, m, make_csv([review_row(1)])).status_code == 500
    assert counts(run_import(client, make_csv([review_row(1)])).json()["data"]) == (1, 0, 0, 0)


def test_temporary_database_lock_is_retried(client, db_session, prop_a, monkeypatch):
    real = pipeline._write_phase
    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OperationalError("INSERT", {}, Exception("database is locked"))
        return real(*args, **kwargs)

    monkeypatch.setattr(pipeline, "_write_phase", flaky)
    monkeypatch.setattr(pipeline.time, "sleep", lambda _s: None)
    report = run_import(client, make_csv([review_row(1)])).json()["data"]
    assert calls["n"] == 2
    assert counts(report) == (1, 0, 0, 0)


def test_a_non_temporary_database_error_is_not_retried(client, prop_a, monkeypatch):
    calls = {"n": 0}

    def broken(*_a, **_k):
        calls["n"] += 1
        raise OperationalError("INSERT", {}, Exception("no such table: reviews"))

    monkeypatch.setattr(pipeline, "_write_phase", broken)
    assert run_import(client, make_csv([review_row(1)])).status_code == 500
    assert calls["n"] == 1


def test_a_batch_cannot_be_committed_twice(client, prop_a):
    preview = upload(client, make_csv([review_row(1)])).json()["data"]
    mapping = {k: v for k, v in preview["suggested_mapping"].items() if v}
    url = f"/api/imports/{preview['import_id']}/commit"
    assert client.post(url, json={"column_mapping": mapping}).status_code == 200
    again = client.post(url, json={"column_mapping": mapping})
    assert again.status_code == 409


def test_commit_for_unknown_import_is_404(client):
    assert client.post("/api/imports/999/commit", json={"column_mapping": {}}).status_code == 404


# ---------------------------------------------------------------- larger files
def test_a_few_thousand_rows_import_correctly(client, db_session, prop_a):
    rows = [
        review_row(i, date=(date(2026, 1, 1) + timedelta(days=i % 200)).isoformat())
        for i in range(3000)
    ]
    rows += [review_row(5000, score="oops")]
    report = run_import(client, make_csv(rows)).json()["data"]
    assert counts(report) == (3000, 0, 0, 1)
    assert_reconciles(report)
    assert db_session.scalar(select(func.count()).select_from(Review)) == 3000


# ---------------------------------------------------------------- history and undo
def test_history_lists_completed_imports_and_hides_unfinished_previews(client, prop_a):
    upload(client, make_csv([review_row(1)]))  # previewed, never committed
    run_import(client, make_csv([review_row(2)]))
    history = client.get("/api/imports").json()
    assert history["meta"]["total"] == 1
    assert history["data"][0]["status"] == "completed"
    assert client.get("/api/imports?status=previewed").json()["meta"]["total"] == 1


def test_undoing_an_import_removes_only_its_reviews(client, db_session, prop_a):
    first = run_import(client, make_csv([review_row(1), review_row(2)])).json()["data"]
    second = run_import(client, make_csv([review_row(3)])).json()["data"]
    response = client.delete(f"/api/imports/{first['id']}")
    assert response.json()["data"]["removed_reviews"] == 2
    assert client.get(f"/api/imports/{first['id']}").status_code == 404
    assert [r.external_review_id for r in db_session.scalars(select(Review))] == ["R3"]
    assert client.get(f"/api/imports/{second['id']}").status_code == 200
    # ...and the same file can be imported again afterwards.
    assert counts(run_import(client, make_csv([review_row(1), review_row(2)])).json()["data"]) == (
        2,
        0,
        0,
        0,
    )


def test_deleting_a_pending_preview_removes_its_stored_file(client, settings, prop_a):
    preview = upload(client, make_csv([review_row(1)])).json()["data"]
    assert len(list(settings.resolved_upload_dir.iterdir())) == 1
    assert client.delete(f"/api/imports/{preview['import_id']}").status_code == 200
    assert list(settings.resolved_upload_dir.iterdir()) == []


def test_stale_previews_are_purged(client, db_session, settings, prop_a):
    preview = upload(client, make_csv([review_row(1)])).json()["data"]
    batch = db_session.get(ImportBatch, preview["import_id"])
    from datetime import UTC, datetime

    batch.created_at = datetime.now(UTC) - timedelta(hours=48)
    db_session.commit()
    upload(client, make_csv([review_row(2)]))  # any new preview triggers the purge
    # Compare by file hash: SQLite re-uses freed row ids, so the id alone proves nothing.
    old_hash = batch.file_sha256
    remaining = db_session.scalars(select(ImportBatch.file_sha256)).all()
    assert len(remaining) == 1
    assert old_hash not in remaining
    assert len(list(settings.resolved_upload_dir.iterdir())) == 1


def test_issue_listing_pagination_and_filters(client, prop_a):
    rows = [review_row(i, score="bad") for i in range(1, 8)] + [review_row(99, score="")]
    report = run_import(client, make_csv(rows)).json()["data"]
    page = client.get(f"/api/imports/{report['id']}/issues?page_size=3&page=2").json()
    assert page["meta"] == {"page": 2, "page_size": 3, "total": 8}
    assert len(page["data"]) == 3
    only = client.get(f"/api/imports/{report['id']}/issues?code=MISSING_RATING").json()
    assert only["meta"]["total"] == 1
    assert client.get(f"/api/imports/{report['id']}/issues?page_size=500").status_code == 422


def test_import_fields_endpoint_lists_the_mappable_fields(client):
    fields = {f["key"]: f for f in client.get("/api/imports/fields").json()["data"]}
    assert fields["review_date"]["required"] == "always"
    assert fields["rating"]["required"] == "one_of"
    assert "reviewer_name" not in fields


# ---------------------------------------------------------------- properties API
def test_property_crud_aliases_and_conflicts(client):
    created = client.post("/api/properties", json={"name": "Sea View", "location": "  Harbour  "})
    assert created.status_code == 201
    prop = created.json()["data"]
    assert prop["code"] == "sea-view"
    assert prop["location"] == "Harbour"
    assert prop["review_count"] == 0

    assert client.post("/api/properties", json={"name": "sea view"}).status_code == 409
    assert client.post("/api/properties", json={"name": "  "}).status_code == 422

    alias = client.post(f"/api/properties/{prop['id']}/aliases", json={"alias": "The Sea View!"})
    assert alias.status_code == 201
    alias_id = alias.json()["data"]["aliases"][0]["id"]
    assert (
        client.post(
            f"/api/properties/{prop['id']}/aliases", json={"alias": "the sea view"}
        ).status_code
        == 409
    )
    assert client.post("/api/properties", json={"name": "The Sea View"}).status_code == 409

    patched = client.patch(f"/api/properties/{prop['id']}", json={"is_active": False})
    assert patched.json()["data"]["is_active"] is False
    assert client.delete(f"/api/properties/{prop['id']}/aliases/{alias_id}").status_code == 204
    assert client.delete(f"/api/properties/{prop['id']}/aliases/{alias_id}").status_code == 404
    assert client.get("/api/properties/9999").status_code == 404


def test_property_review_counts_separate_genuine_from_synthetic(client, prop_a):
    run_import(client, make_csv([review_row(1), review_row(2)]))
    run_import(client, make_csv([review_row(3)]), is_synthetic=True)
    prop = client.get(f"/api/properties/{prop_a}").json()["data"]
    assert (prop["review_count"], prop["synthetic_review_count"]) == (2, 1)


def test_property_with_reviews_cannot_be_deleted_via_aliases_or_cascade(client, db_session, prop_a):
    run_import(client, make_csv([review_row(1)]))
    assert db_session.scalar(select(func.count()).select_from(Property)) == 1


# ---------------------------------------------------------------- synthetic data
def test_synthetic_flag_forces_a_synthetic_source_and_separates_counts(client, db_session, prop_a):
    report = run_import(
        client, make_csv([review_row(1)]), is_synthetic=True, source_name="booking.com"
    ).json()["data"]
    assert report["is_synthetic"] is True
    assert report["source_name"] == "synthetic-demo"  # can never be labelled as Booking.com
    review = db_session.scalars(select(Review)).one()
    assert review.is_synthetic is True
    assert review.source == "synthetic-demo"


def test_genuine_and_synthetic_reviews_with_identical_content_do_not_collide(
    client, db_session, prop_a
):
    row = [review_row(1)]
    run_import(client, make_csv(row))
    again = run_import(client, make_csv(row), is_synthetic=True).json()["data"]
    assert counts(again) == (1, 0, 0, 0)


def test_demo_data_loads_labelled_and_separate_then_clears(client, db_session):
    status = client.get("/api/demo").json()["data"]
    assert status["loaded"] is False
    loaded = client.post("/api/demo/load")
    assert loaded.status_code == 201
    report = loaded.json()["data"]
    assert report["is_synthetic"] is True
    assert report["rejected_rows"] == 0
    assert_reconciles(report)

    props = client.get("/api/properties").json()["data"]
    assert len(props) == 4
    assert all(p["review_count"] == 0 and p["synthetic_review_count"] > 100 for p in props)
    reviews = db_session.scalars(select(Review)).all()
    assert reviews and all(r.is_synthetic and r.source == "synthetic-demo" for r in reviews)
    assert all(r.external_review_id.startswith("SYN-") for r in reviews)

    assert client.post("/api/demo/load").status_code == 409  # not loaded twice
    assert client.get("/api/demo").json()["data"]["loaded"] is True

    removed = client.delete("/api/demo").json()["data"]["removed_reviews"]
    assert removed == len(reviews)
    assert client.get("/api/demo").json()["data"]["loaded"] is False
    assert len(client.get("/api/properties").json()["data"]) == 4  # properties are kept


def test_clearing_demo_data_never_touches_genuine_reviews(client, db_session, prop_a):
    run_import(client, make_csv([review_row(1)]))
    client.post("/api/demo/load")
    client.delete("/api/demo")
    remaining = db_session.scalars(select(Review)).all()
    assert [r.external_review_id for r in remaining] == ["R1"]
    assert remaining[0].is_synthetic is False


def test_demo_data_supports_week_over_week_comparison(client, db_session):
    client.post("/api/demo/load")
    today = date.today()
    for prop in db_session.scalars(select(Property)):
        for start, end in ((0, 7), (7, 14)):
            n = db_session.scalar(
                select(func.count())
                .select_from(Review)
                .where(
                    Review.property_id == prop.id,
                    Review.review_date > today - timedelta(days=end),
                    Review.review_date <= today - timedelta(days=start),
                )
            )
            assert n >= 7, f"{prop.name}: only {n} reviews in days {start}-{end}"


def test_demo_generation_is_deterministic():
    from app.services.demo_data import generate_csv

    anchor = date(2026, 11, 23)
    assert generate_csv(anchor) == generate_csv(anchor)
    assert generate_csv(anchor, seed=1) != generate_csv(anchor, seed=2)
    assert b"SYNTHETIC" in generate_csv(anchor)


def test_committed_sample_files_are_labelled_synthetic():
    root = Path(__file__).resolve().parents[2] / "data" / "sample"
    with (root / "synthetic_reviews_sample.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows and all(r["Data origin"] == "SYNTHETIC" for r in rows)
    assert all(r["Review ID"].startswith("SYN-") for r in rows)


def test_a_different_excel_sheet_can_be_previewed_without_uploading_again(client, prop_a):
    data = xlsx_bytes(
        {
            "Summary": [["Note"], ["not reviews"]],
            "Reviews": [GOOD_HEADERS, ["X1", "Hotel A", "2026-03-01", 9, "Great", ""]],
        }
    )
    first = upload(client, data, "book.xlsx").json()["data"]
    assert first["sheets"] == ["Summary", "Reviews"]
    assert first["columns"] == ["Note"]
    other = client.get(f"/api/imports/{first['import_id']}/preview?sheet=Reviews").json()["data"]
    assert other["columns"] == GOOD_HEADERS
    assert other["suggested_mapping"]["property"] == "Hotel"
    report = client.post(
        f"/api/imports/{first['import_id']}/commit",
        json={
            "sheet": "Reviews",
            "column_mapping": {k: v for k, v in other["suggested_mapping"].items() if v},
        },
    ).json()["data"]
    assert counts(report) == (1, 0, 0, 0)
    assert client.get("/api/imports/999/preview").status_code == 404
