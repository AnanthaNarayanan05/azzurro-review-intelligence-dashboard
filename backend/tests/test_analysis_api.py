"""Analysis runs: what gets scored, when, and what happens when something goes wrong."""

import pytest
from sqlalchemy import func, select

from app.analytics.nlp.review_analysis import analyse_review as real_analyse_review
from app.models import AnalysisRun, AspectMention, Review, SentimentResult
from app.services import analysis
from tests.test_import_api import make_csv, review_row, run_import


@pytest.fixture()
def hotel(client) -> int:
    return client.post("/api/properties", json={"name": "Hotel A"}).json()["data"]["id"]


def status(client) -> dict:
    return client.get("/api/analysis/status").json()["data"]


def count(db_session, model) -> int:
    db_session.expire_all()
    return db_session.scalar(select(func.count()).select_from(model))


def import_rows(client, rows):
    response = run_import(client, make_csv(rows))
    assert response.status_code == 200, response.text
    return response.json()["data"]


# ------------------------------------------------------------------ status model
def test_status_before_any_data(client):
    data = status(client)
    assert data["total_reviews"] == 0 and data["pending"] == 0 and data["latest_run"] is None
    assert data["engine"].startswith("vader-")
    assert any("not been evaluated" in note for note in data["notes"])


def test_import_scores_reviews_and_stores_run_provenance(client, db_session, hotel):
    import_rows(
        client, [review_row(1, pos="Lovely clean room"), review_row(2, pos="", neg="Nothing")]
    )
    data = status(client)
    assert (data["analysed"], data["no_text"], data["pending"]) == (1, 1, 0)
    run = data["latest_run"]
    assert run["triggered_by"] == "import" and run["status"] == "completed"
    assert run["sentiment_engine"].startswith("vader-") and run["aspect_lexicon_version"]
    assert count(db_session, SentimentResult) >= 1  # overall + segment rows


def test_reviews_without_a_language_get_a_detected_one_stored(client, db_session, hotel):
    import_rows(
        client, [review_row(1, pos="La chambre était très propre et le personnel très aimable.")]
    )
    review = db_session.scalar(select(Review))
    assert review.analysis_status == "non_english"
    assert review.language == "fr" and review.language_detected is True
    assert count(db_session, SentimentResult) == 0  # not scored: VADER is English-only


# ------------------------------------------------------------------ manual runs
def test_rerun_all_gives_identical_results_without_duplicating_rows(client, db_session, hotel):
    import_rows(
        client,
        [review_row(i, pos=f"Staff were friendly. The room was clean {i}.") for i in range(3)],
    )
    before = (count(db_session, SentimentResult), count(db_session, AspectMention))
    scores = sorted(float(s) for s in db_session.scalars(select(SentimentResult.score)))

    response = client.post("/api/analysis/run", json={"scope": "all"})
    assert response.status_code == 200
    assert response.json()["data"]["processed"] == 3

    assert (count(db_session, SentimentResult), count(db_session, AspectMention)) == before
    assert sorted(float(s) for s in db_session.scalars(select(SentimentResult.score))) == scores


def test_pending_run_with_nothing_pending_processes_nothing(client, hotel):
    import_rows(client, [review_row(1)])
    data = client.post("/api/analysis/run").json()["data"]
    assert data["processed"] == 0
    assert data["run"]["status"] == "completed"


def test_import_with_nothing_new_does_not_create_an_empty_run(client, db_session, hotel):
    import_rows(client, [review_row(1)])
    runs = count(db_session, AnalysisRun)
    report = import_rows(client, [review_row(1)])  # exact duplicate
    assert report["duplicate_rows"] == 1
    assert count(db_session, AnalysisRun) == runs


def test_run_history_is_listed_newest_first(client, hotel):
    import_rows(client, [review_row(1)])
    client.post("/api/analysis/run", json={"scope": "all"})
    body = client.get("/api/analysis/runs").json()
    assert body["meta"]["total"] == 2
    assert [r["triggered_by"] for r in body["data"]] == ["manual", "import"]


def test_invalid_scope_is_rejected(client):
    assert client.post("/api/analysis/run", json={"scope": "everything"}).status_code == 422


# ------------------------------------------------------------------ changed content
def test_changed_review_is_rescored_after_reimport(client, db_session, hotel):
    import_rows(client, [review_row(1, pos="Staff were friendly and helpful")])
    first = db_session.scalar(
        select(SentimentResult.label).where(SentimentResult.segment == "overall")
    )
    assert first == "positive"

    report = import_rows(client, [review_row(1, pos="Staff were rude and unhelpful")])
    assert report["updated_rows"] == 1
    db_session.expire_all()
    review = db_session.scalar(select(Review))
    assert review.analysis_status == "analysed"  # re-analysed automatically after the import
    label = db_session.scalar(
        select(SentimentResult.label).where(SentimentResult.segment == "overall")
    )
    assert label == "negative"
    assert (
        count(db_session, SentimentResult) == 2
    )  # old rows replaced, not accumulated: positive + overall


# ------------------------------------------------------------------ engine / lexicon changes
def test_changing_engine_version_forces_a_full_rerun(db_session, client, hotel):
    class OtherEngine:
        name = "other-engine-1"

        def score(self, text: str) -> float:
            return 0.9

    import_rows(client, [review_row(1), review_row(2)])
    summary = analysis.run_analysis(db_session, scope="pending", engine=OtherEngine())
    assert (
        summary.processed == 2
    )  # nothing was pending, but the engine changed so everything re-ran
    labels = set(db_session.scalars(select(SentimentResult.label)))
    assert labels == {"positive"}
    assert set(db_session.scalars(select(SentimentResult.model_name))) == {"other-engine-1"}


# ------------------------------------------------------------------ failure handling
def test_failed_run_rolls_back_and_is_recorded(client, db_session, hotel, monkeypatch):
    import_rows(client, [review_row(i, pos=f"Staff were friendly {i}") for i in range(4)])
    before = sorted(float(s) for s in db_session.scalars(select(SentimentResult.score)))

    calls = {"n": 0}

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("boom")
        return real_analyse_review(**kwargs)

    monkeypatch.setattr(analysis, "analyse_review", flaky)
    response = client.post("/api/analysis/run", json={"scope": "all"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "ANALYSIS_FAILED"
    assert "boom" not in response.text  # internal detail is not leaked

    db_session.expire_all()
    assert sorted(float(s) for s in db_session.scalars(select(SentimentResult.score))) == before
    runs = list(db_session.scalars(select(AnalysisRun).order_by(AnalysisRun.id)))
    assert [r.status for r in runs] == ["completed", "failed"]
    assert status(client)["analysed"] == 4  # statuses untouched


def test_failure_after_import_does_not_fail_the_import(client, db_session, hotel, monkeypatch):
    def broken(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(analysis, "analyse_review", broken)
    report = import_rows(client, [review_row(1), review_row(2)])
    assert report["imported_rows"] == 2  # reviews are saved
    data = status(client)
    assert data["pending"] == 2 and data["analysed"] == 0  # and can be analysed later

    monkeypatch.undo()
    assert client.post("/api/analysis/run").json()["data"]["processed"] == 2
    assert status(client)["pending"] == 0


# ------------------------------------------------------------------ schema
def test_database_rejects_an_unknown_analysis_status(client, db_session, hotel):
    from sqlalchemy.exc import IntegrityError

    import_rows(client, [review_row(1)])
    review = db_session.scalar(select(Review))
    review.analysis_status = "maybe"
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
