"""Analytics endpoints checked against hand-calculated results.

The fixture is tests/fixtures/validation_reviews.csv; every expected number is derived by hand in
tests/fixtures/EXPECTED_RESULTS.md.
"""

from pathlib import Path

import pytest

from app.core.config import Settings
from tests.test_import_api import run_import

FIXTURE = Path(__file__).parent / "fixtures" / "validation_reviews.csv"
AS_OF = "2026-03-29"


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    """Small thresholds so a 21-review file can exercise the sample-size guards."""
    return Settings(
        upload_dir=str(tmp_path / "uploads"),
        app_env="test",
        min_sample_comparison=6,
        min_aspect_mentions=3,
        min_sample_trend_window=4,
    )


@pytest.fixture()
def loaded(client) -> dict[str, int]:
    """Import the validation file (analysis runs automatically) and return name -> property id."""
    ids = {}
    for name in ("Alpha Hotel", "Beta Hotel", "Gamma Hotel"):
        ids[name] = client.post("/api/properties", json={"name": name}).json()["data"]["id"]
    response = run_import(client, FIXTURE.read_bytes())
    assert response.status_code == 200, response.text
    report = response.json()["data"]
    assert report["imported_rows"] == 21
    return ids


def get(client, path: str, **params):
    response = client.get(f"/api/analytics/{path}", params=params)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def by_aspect(items: list[dict]) -> dict[str, dict]:
    return {i["aspect"]: i for i in items}


# ------------------------------------------------------------------ analysis happened on import
def test_import_triggers_analysis(client, loaded):
    status = client.get("/api/analysis/status").json()["data"]
    assert status["total_reviews"] == 21
    assert status["analysed"] == 19
    assert status["no_text"] == 1
    assert status["non_english"] == 1
    assert status["pending"] == 0
    assert status["latest_run"]["triggered_by"] == "import"


# ------------------------------------------------------------------ overview
def test_overview_counts_ratings_and_sentiment(client, loaded):
    data = get(client, "overview")
    assert data["reviews"] == {"n": 21, "with_text_analysis": 19}
    assert data["rating"]["value"] == 7.24
    assert data["rating"]["n"] == 21
    assert data["rating"]["missing"] == 0
    bins = {b["label"]: b["n"] for b in data["rating"]["distribution"]}
    assert bins["1-2"] == 1 and bins["5-6"] == 3 and bins["6-7"] == 5
    assert bins["7-8"] == 2 and bins["8-9"] == 2 and bins["9-10"] == 8
    assert sum(bins.values()) == 21

    sentiment = data["sentiment"]
    assert (sentiment["positive"], sentiment["neutral"], sentiment["negative"]) == (9, 2, 8)
    assert sentiment["analysed_n"] == 19
    assert sentiment["positive_share"] == pytest.approx(9 / 19, abs=1e-4)
    assert sentiment["negative_share"] == pytest.approx(8 / 19, abs=1e-4)
    assert sentiment["not_analysed"] == {"no_text": 1, "non_english": 1, "pending": 0}


def test_overview_lists_each_property_with_its_own_sample(client, loaded):
    rows = {p["name"]: p for p in get(client, "overview")["properties"]}
    assert rows["Alpha Hotel"]["rating"]["value"] == 7.1 and rows["Alpha Hotel"]["reviews"] == 10
    assert rows["Beta Hotel"]["rating"]["value"] == 5.5
    assert rows["Gamma Hotel"]["rating"]["value"] == 9.6
    # Gamma has 5 rated reviews and the minimum is 6, so the number is flagged as thin.
    assert rows["Gamma Hotel"]["rating"]["low_sample"] is True
    assert rows["Alpha Hotel"]["rating"]["low_sample"] is False


def test_overview_reports_top_aspects_only_from_well_supported_aspects(client, loaded):
    aspects = get(client, "overview")["aspects"]
    assert aspects["most_criticised"][0]["aspect"] == "staff_service"
    assert aspects["most_praised"][0]["aspect"] == "staff_service"
    listed = {a["aspect"] for a in aspects["most_praised"] + aspects["most_criticised"]}
    assert "wifi_connectivity" not in listed  # a single mention is below the minimum of 3
    assert "location" not in listed  # 2 mentions, below the minimum


def test_overview_respects_filters(client, loaded):
    alpha = get(client, "overview", property_ids=loaded["Alpha Hotel"])
    assert alpha["reviews"]["n"] == 10
    window = get(client, "overview", date_from="2026-03-01", date_to="2026-03-15")
    # Alpha A1-A4, Beta B3-B5 (B4 is 03-08, B5 is 03-15, B3 is 03-03), Gamma G1,G2.
    assert window["reviews"]["n"] == 4 + 3 + 2


def test_empty_selection_returns_nulls_not_zeroes(client, loaded):
    data = get(client, "overview", date_from="2030-01-01")
    assert data["reviews"]["n"] == 0
    assert data["rating"]["value"] is None
    assert data["sentiment"]["positive_share"] is None


# ------------------------------------------------------------------ aspects
def test_aspect_counts_match_hand_calculation(client, loaded):
    data = get(client, "aspects")
    items = by_aspect(data["items"])
    expected = {
        "staff_service": (10, 4, 0, 6),
        "cleanliness": (4, 2, 1, 1),
        "location": (2, 2, 0, 0),
        "room_comfort": (2, 0, 0, 2),
        "facilities": (2, 0, 0, 2),
        "value_for_money": (2, 2, 0, 0),
        "wifi_connectivity": (1, 0, 0, 1),
    }
    for key, (mentions, positive, neutral, negative) in expected.items():
        item = items[key]
        assert (item["mentions"], item["positive"], item["neutral"], item["negative"]) == (
            mentions,
            positive,
            neutral,
            negative,
        ), key
    assert "food_breakfast" not in items  # no review mentions it
    assert items["staff_service"]["mention_rate"] == pytest.approx(10 / 19, abs=1e-4)
    assert items["staff_service"]["low_sample"] is False
    assert items["location"]["low_sample"] is True


def test_aspect_label_for_mixed_review_is_neutral(client, loaded):
    # A5 praises the room's cleanliness and criticises the bathroom's dirt: the two cancel out.
    items = by_aspect(get(client, "aspects", property_ids=loaded["Alpha Hotel"])["items"])
    assert items["cleanliness"]["neutral"] == 1


def test_examples_are_verbatim_sentences_with_review_ids(client, loaded):
    response = client.get(
        "/api/analytics/aspects/staff_service/examples", params={"sentiment": "negative"}
    )
    assert response.status_code == 200
    examples = response.json()["data"]
    assert examples
    assert {e["evidence_text"] for e in examples} == {"Staff were rude and unhelpful."}
    assert all(e["review_id"] and e["is_synthetic"] is False for e in examples)


def test_examples_for_unknown_aspect_is_404(client, loaded):
    response = client.get("/api/analytics/aspects/not_an_aspect/examples")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ASPECT_NOT_FOUND"


# ------------------------------------------------------------------ comparison
def test_comparison_names_no_winner_when_intervals_overlap(client, loaded):
    data = get(client, "comparison")
    rows = {p["name"]: p for p in data["properties"]}
    assert rows["Alpha Hotel"]["rating"]["ci_low"] == pytest.approx(5.54, abs=0.01)
    assert rows["Alpha Hotel"]["rating"]["ci_high"] == pytest.approx(8.66, abs=0.01)
    assert rows["Beta Hotel"]["rating"]["ci_low"] == pytest.approx(5.06, abs=0.01)
    assert rows["Beta Hotel"]["rating"]["ci_high"] == pytest.approx(5.94, abs=0.01)
    ranking = data["rating_ranking"]
    assert ranking["status"] == "difference_not_significant"
    assert ranking["best"] is None and ranking["worst"] is None
    assert loaded["Gamma Hotel"] not in ranking["ordered"]  # too few reviews to rank


def test_comparison_names_best_and_worst_when_clearly_separated(client, loaded):
    data = get(client, "comparison", date_to="2026-03-30")  # excludes Alpha's rating of 1
    alpha = next(p for p in data["properties"] if p["name"] == "Alpha Hotel")
    assert alpha["rating"]["value"] == pytest.approx(7.78, abs=0.01)
    ranking = data["rating_ranking"]
    assert ranking["status"] == "ranked"
    assert ranking["best"] == loaded["Alpha Hotel"]
    assert ranking["worst"] == loaded["Beta Hotel"]


def test_comparison_with_one_eligible_property_is_insufficient(client, loaded):
    ids = f"{loaded['Alpha Hotel']},{loaded['Gamma Hotel']}"
    ranking = get(client, "comparison", property_ids=ids)["rating_ranking"]
    assert ranking["status"] == "insufficient_data"
    assert ranking["best"] is None


# ------------------------------------------------------------------ property detail
def test_property_detail_has_praise_and_complaints_with_evidence(client, loaded):
    detail = get(client, f"properties/{loaded['Alpha Hotel']}")
    assert detail["reviews"]["n"] == 10
    assert [a["aspect"] for a in detail["top_complaints"]] == ["staff_service"]
    complaint = detail["top_complaints"][0]
    assert complaint["negative"] == 3
    assert complaint["examples"][0]["evidence_text"] == "Staff were rude and unhelpful."
    assert [a["aspect"] for a in detail["top_praise"]] == ["staff_service"]


def test_unknown_property_is_404(client, loaded):
    response = client.get("/api/analytics/properties/9999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROPERTY_NOT_FOUND"


# ------------------------------------------------------------------ trends
def trend(client, loaded, **params):
    params = {"property_ids": loaded["Alpha Hotel"], "granularity": "week", "window": 2} | params
    params.setdefault("as_of", AS_OF)
    return get(client, "trends", **params)


def test_weekly_series_is_monday_based_and_fills_empty_weeks(client, loaded):
    data = trend(client, loaded, metric="volume")
    series = {s["period_start"]: s for s in data["series"]}
    assert all(s["period_start"] and s["period_end"] for s in series.values())
    assert series["2026-03-02"]["period_end"] == "2026-03-08"  # Monday to Sunday
    assert series["2026-03-02"]["n"] == 2  # A1 (03-02) and A2 (03-05)
    assert series["2026-02-09"]["n"] == 1  # A9 on Tuesday 02-10
    assert series["2026-02-16"]["n"] == 0 and series["2026-02-23"]["n"] == 0  # gap weeks kept
    assert "2026-03-30" not in series  # A10 (03-31) is after as_of


def test_rating_trend_detects_a_real_drop(client, loaded):
    change = trend(client, loaded, metric="avg_rating")["change"]
    assert change["recent_window"] == {"from": "2026-03-16", "to": "2026-03-29", "n": 4}
    assert change["previous_window"] == {"from": "2026-03-02", "to": "2026-03-15", "n": 4}
    assert change["recent_value"] == 6.5 and change["previous_value"] == 8.5
    assert change["difference"] == -2.0
    assert change["ci_low"] == pytest.approx(-2.8002, abs=1e-3)
    assert change["ci_high"] == pytest.approx(-1.1998, abs=1e-3)
    assert change["status"] == "decrease"


def test_negative_sentiment_share_trend(client, loaded):
    change = trend(client, loaded, metric="sentiment_negative_share")["change"]
    assert change["recent_value"] == 0.5 and change["previous_value"] == 0.0
    assert change["ci_low"] == pytest.approx(0.01, abs=1e-3)
    assert change["status"] == "increase"


def test_aspect_trend_requires_an_aspect(client, loaded):
    response = client.get("/api/analytics/trends", params={"metric": "aspect_negative_share"})
    assert response.status_code == 422
    change = trend(client, loaded, metric="aspect_negative_share", aspect="staff_service")["change"]
    # recent: A6 and A8 negative (2 of 2 staff reviews); previous: A1, A3 positive (0 of 2).
    assert change["status"] == "insufficient_data"  # only 2 observations per window, minimum is 4


def test_incomplete_week_is_never_compared(client, loaded):
    # as_of is a Thursday, so the week starting 03-23 is unfinished and is left out of the windows.
    data = trend(client, loaded, metric="avg_rating", as_of="2026-03-26")
    assert data["change"]["recent_window"] == {"from": "2026-03-09", "to": "2026-03-22", "n": 4}
    assert data["change"]["status"] == "insufficient_data"
    last = data["series"][-1]
    assert last["period_start"] == "2026-03-23" and last["complete"] is False


def test_small_windows_are_reported_not_guessed(client, loaded):
    gamma = get(
        client,
        "trends",
        property_ids=loaded["Gamma Hotel"],
        metric="avg_rating",
        granularity="week",
        window=1,
        as_of=AS_OF,
    )
    assert gamma["change"]["status"] == "insufficient_data"


def test_volume_trend_is_descriptive_only(client, loaded):
    change = trend(client, loaded, metric="volume")["change"]
    assert change["status"] == "descriptive"
    assert change["recent_value"] == 4 and change["previous_value"] == 4
    assert change["difference"] == 0


def test_monthly_granularity(client, loaded):
    data = get(
        client,
        "trends",
        property_ids=loaded["Alpha Hotel"],
        metric="volume",
        granularity="month",
        as_of="2026-03-31",
    )
    series = {s["period_start"]: s for s in data["series"]}
    assert series["2026-02-01"]["n"] == 1
    assert series["2026-03-01"]["n"] == 9
    assert series["2026-03-01"]["period_end"] == "2026-03-31"
    assert data["week_definition"] == "calendar month"


# ------------------------------------------------------------------ input validation
@pytest.mark.parametrize(
    "params",
    [
        {"property_ids": "abc"},
        {"date_from": "2026-04-01", "date_to": "2026-03-01"},
        {"data_scope": "x"},
    ],
)
def test_bad_filters_are_rejected(client, loaded, params):
    response = client.get("/api/analytics/overview", params=params)
    assert response.status_code == 422


# ------------------------------------------------------------------ synthetic data is kept apart
def test_synthetic_data_is_excluded_by_default(client, loaded):
    assert client.post("/api/demo/load").status_code == 201
    genuine = get(client, "overview")
    assert genuine["reviews"]["n"] == 21
    assert genuine["dataset"]["synthetic_reviews"] > 0
    assert genuine["dataset"]["genuine_reviews"] == 21
    assert genuine["dataset"]["mixed"] is False

    synthetic = get(client, "overview", data_scope="synthetic")
    assert synthetic["reviews"]["n"] == genuine["dataset"]["synthetic_reviews"]

    combined = get(client, "overview", data_scope="all")
    assert combined["reviews"]["n"] == 21 + synthetic["reviews"]["n"]
    assert combined["dataset"]["mixed"] is True


# ------------------------------------------------------------------ missing ratings
def test_reviews_without_a_rating_are_counted_as_missing_not_as_zero(client):
    from tests.test_import_api import make_csv, review_row

    client.post("/api/properties", json={"name": "Hotel A"})
    rows = [
        review_row(1, score="8", pos="Lovely clean room"),
        review_row(2, score="", pos="Friendly staff at reception"),
    ]
    assert run_import(client, make_csv(rows)).status_code == 200
    rating = get(client, "overview")["rating"]
    assert rating["value"] == 8.0  # not 4.0: the missing rating is excluded, not treated as zero
    assert rating["n"] == 1 and rating["missing"] == 1
