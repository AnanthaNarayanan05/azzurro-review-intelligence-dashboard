"""Review explorer endpoints, checked against the hand-calculated validation fixture."""

import pytest

from tests.test_analytics_api import get, loaded, settings


def listing(client, **params):
    response = client.get("/api/reviews", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def texts(body):
    return {r["positive_text"] or r["negative_text"] for r in body["data"]}


def test_default_listing_is_genuine_newest_first_and_paginated(client, loaded):
    body = listing(client, page_size=5)
    assert body["meta"] == {"page": 1, "page_size": 5, "total": 21}
    dates = [r["review_date"] for r in body["data"]]
    assert dates == sorted(dates, reverse=True)
    assert body["data"][0]["review_date"] == "2026-03-31"
    page_5 = listing(client, page_size=5, page=5)
    assert len(page_5["data"]) == 1  # 21 reviews = 4 full pages + 1


def test_listing_carries_sentiment_and_review_level_aspect_labels(client, loaded):
    body = listing(
        client, property_ids=loaded["Alpha Hotel"], date_from="2026-03-17", date_to="2026-03-17"
    )
    [review] = body["data"]  # A5: clean room praised, bathroom dirty
    assert review["property_name"] == "Alpha Hotel"
    assert review["sentiment"]["label"] == "neutral"
    labels = {a["aspect"]: a["label"] for a in review["aspects"]}
    assert labels == {"cleanliness": "neutral", "facilities": "negative"}


def test_unanalysed_states_are_visible(client, loaded):
    body = listing(client, property_ids=loaded["Gamma Hotel"], sort="oldest")
    by_status = {r["analysis_status"] for r in body["data"]}
    assert by_status == {"analysed", "no_text", "non_english"}
    french = next(r for r in body["data"] if r["analysis_status"] == "non_english")
    assert french["sentiment"] is None and french["language"] == "fr"


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"q": "wifi"}, 1),
        ({"q": "WIFI"}, 1),
        ({"q": "100%"}, 0),  # % is a literal, not a wildcard
        ({"q": "_"}, 0),
        ({"sentiment": "negative"}, 8),
        ({"sentiment": "positive"}, 9),
        ({"rating_min": 9}, 8),
        ({"rating_max": 5}, 4),  # B1, B3, B5 (5) and A10 (1)
        ({"language": "fr"}, 1),
        ({"aspect": "staff_service"}, 10),
        ({"aspect": "staff_service", "aspect_sentiment": "negative"}, 6),
        ({"aspect": "staff_service", "aspect_sentiment": "positive"}, 4),
        ({"aspect": "cleanliness", "aspect_sentiment": "neutral"}, 1),
        ({"date_from": "2026-03-01", "date_to": "2026-03-15"}, 9),
    ],
)
def test_filters(client, loaded, params, expected):
    assert listing(client, **params)["meta"]["total"] == expected


def test_sort_by_rating(client, loaded):
    top = listing(client, sort="rating_desc", page_size=3)["data"]
    assert all(r["rating"] == 10 for r in top)
    bottom = listing(client, sort="rating_asc", page_size=1)["data"][0]
    assert bottom["rating"] == 1


def test_aspect_counts_match_the_analytics_endpoint(client, loaded):
    # The explorer and the analytics page must agree about how many reviews are negative on staff.
    negative = get(client, "aspects")["items"]
    staff = next(i for i in negative if i["aspect"] == "staff_service")["negative"]
    assert (
        listing(client, aspect="staff_service", aspect_sentiment="negative")["meta"]["total"]
        == staff
    )


@pytest.mark.parametrize(
    "params",
    [
        {"rating_min": 8, "rating_max": 2},
        {"aspect_sentiment": "negative"},
        {"sentiment": "angry"},
        {"page_size": 101},
        {"page": 0},
        {"q": "x" * 201},
    ],
)
def test_invalid_filters_are_rejected(client, loaded, params):
    assert client.get("/api/reviews", params=params).status_code == 422


def test_unknown_aspect_is_404(client, loaded):
    assert client.get("/api/reviews", params={"aspect": "nope"}).status_code == 404


def test_review_detail_has_segments_and_verbatim_evidence(client, loaded):
    a5 = listing(
        client, date_from="2026-03-17", date_to="2026-03-17", property_ids=loaded["Alpha Hotel"]
    )
    detail = client.get(f"/api/reviews/{a5['data'][0]['id']}").json()["data"]
    assert {s["segment"] for s in detail["segments"]} == {"positive", "negative", "overall"}
    mention_text = {m["evidence_text"] for m in detail["mentions"]}
    assert mention_text == {"The room was clean.", "The bathroom was dirty."}
    assert all(m["source_field"] in {"positive", "negative"} for m in detail["mentions"])
    assert detail["sentiment"]["label"] == "neutral"


def test_missing_review_is_404(client, loaded):
    response = client.get("/api/reviews/99999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REVIEW_NOT_FOUND"


def test_deactivated_property_is_left_out_of_every_figure(client, loaded):
    gamma = loaded["Gamma Hotel"]
    assert client.patch(f"/api/properties/{gamma}", json={"is_active": False}).status_code == 200
    overview = get(client, "overview")
    assert overview["reviews"]["n"] == 16
    assert overview["dataset"]["genuine_reviews"] == 16
    assert {p["name"] for p in overview["properties"]} == {"Alpha Hotel", "Beta Hotel"}
    assert {p["name"] for p in get(client, "comparison")["properties"]} == {
        "Alpha Hotel",
        "Beta Hotel",
    }
    assert listing(client)["meta"]["total"] == 16
