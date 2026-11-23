"""Insights: rules checked on hand-countable data, evidence integrity, grounding validator."""

import json
from datetime import date

import pytest

from app.models.base import EvidenceStrength, SentimentLabel
from app.services.insights import evidence, grounding, wording
from tests.insight_helpers import JAN_FEB, World, basic_world, months


def generate(client, scope="genuine"):
    response = client.post("/api/insights/generate", json={"data_scope": scope})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def listing(client, **params):
    response = client.get("/api/insights", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def by_type(body):
    out: dict[str, list[dict]] = {}
    for insight in body["data"]:
        out.setdefault(insight["insight_type"], []).append(insight)
    return out


# ------------------------------------------------------------------------- the rules
def test_rules_fire_on_crafted_data(client, db_session):
    basic_world(db_session)
    summary = generate(client)
    assert summary["by_type"] == {
        "recurring_complaint": 2,
        "cross_property_issue": 1,
        "strength": 1,
        "opportunity": 1,
    }
    assert summary["created"] == 5 and summary["replaced"] == 0
    assert summary["rejected_by_validator"] == 0
    assert summary["as_of"] == "2026-02-20"

    found = by_type(listing(client))
    complaints = {i["properties"][0]["name"]: i for i in found["recurring_complaint"]}
    assert set(complaints) == {"Alpha", "Beta"}
    alpha = complaints["Alpha"]
    assert alpha["supporting_review_count"] == 10
    assert alpha["metrics"]["mentions"] == 14 and alpha["metrics"]["negative"] == 10
    assert alpha["metrics"]["negative_share"] == pytest.approx(10 / 14, abs=1e-4)
    assert alpha["aspect"]["key"] == "cleanliness"
    assert (
        "10 of 14 reviews that mention cleanliness at Alpha were negative (71%)"
        in (alpha["explanation"])
    )
    assert alpha["generation_method"] == "template"

    [cross] = found["cross_property_issue"]
    assert {p["name"] for p in cross["properties"]} == {"Alpha", "Beta"}
    assert cross["scope"] == "multi_property"
    assert cross["metrics"]["negative"] == 20 and cross["metrics"]["mentions"] == 26
    assert cross["supporting_review_count"] == 20
    assert cross["evidence_strength"] == "strong"  # 20 reviews over two months

    [strength] = found["strength"]
    assert strength["properties"][0]["name"] == "Gamma"
    assert strength["metrics"]["positive"] == 17 and strength["metrics"]["mentions"] == 20
    assert strength["evidence_strength"] == "moderate"

    [opportunity] = found["opportunity"]
    assert opportunity["aspect"]["key"] == "wifi_connectivity"
    assert opportunity["metrics"]["positive"] == 8 and opportunity["metrics"]["negative"] == 4


def test_thin_aspects_produce_nothing(client, db_session):
    basic_world(db_session)
    generate(client)
    keys = {i["aspect"]["key"] for i in listing(client)["data"]}
    assert "location" not in keys  # 5 mentions, all negative, but below the 10-mention floor


def test_generation_reports_what_it_could_not_assess(client, db_session):
    basic_world(db_session)
    summary = generate(client)
    # Alpha/Beta cleanliness, Gamma staff / Wi-Fi / location.
    assert summary["checked_property_aspects"] == 5
    assert summary["below_mention_floor"] == 1
    # None of the five has 30 observations per side, so no comparison could be made.
    assert summary["comparisons_skipped_too_few"] == 8  # 4 aspects x (difference + trend)


def test_property_issue_needs_a_real_gap_and_enough_data(client, db_session):
    w = World(db_session)
    w.add("Alpha", "food_breakfast", "negative", 24, JAN_FEB)
    w.add("Alpha", "food_breakfast", "positive", 16, JAN_FEB)
    w.add("Beta", "food_breakfast", "negative", 6, JAN_FEB)
    w.add("Beta", "food_breakfast", "positive", 34, JAN_FEB)
    generate(client)
    issues = by_type(listing(client)).get("property_issue", [])
    [issue] = issues
    assert issue["properties"][0]["name"] == "Alpha"
    assert issue["metrics"]["negative"] == 24 and issue["metrics"]["mentions"] == 40
    assert issue["metrics"]["rest"] == {"mentions": 40, "negative": 6, "negative_share": 0.15}
    assert issue["metrics"]["difference"] == pytest.approx(0.45, abs=1e-4)
    assert issue["metrics"]["ci_low"] > 0
    assert "60%" in issue["explanation"] and "15%" in issue["explanation"]


def test_property_issue_not_raised_when_gap_is_within_chance(client, db_session):
    w = World(db_session)
    # 50 % vs 45 %: a real difference of 5 points but nowhere near significant with n = 40.
    w.add("Alpha", "food_breakfast", "negative", 20, JAN_FEB)
    w.add("Alpha", "food_breakfast", "positive", 20, JAN_FEB)
    w.add("Beta", "food_breakfast", "negative", 18, JAN_FEB)
    w.add("Beta", "food_breakfast", "positive", 22, JAN_FEB)
    generate(client)
    assert "property_issue" not in by_type(listing(client))


def _trend_world(db_session, recent_negative: int) -> World:
    """Three months before and three months after, 36 mentions in each window."""
    w = World(db_session, names=("Alpha",))
    previous = months(2026, [7, 8, 9])  # 6 dates
    recent = months(2026, [10, 11, 12])
    w.add("Alpha", "cleanliness", "negative", 4, previous)
    w.add("Alpha", "cleanliness", "positive", 32, previous)
    w.add("Alpha", "cleanliness", "negative", recent_negative, recent)
    w.add("Alpha", "cleanliness", "positive", 36 - recent_negative, recent)
    # A later review closes December, so October-December counts as a complete window.
    w.add("Alpha", "location", "positive", 1, [date(2027, 1, 2)])
    return w


def test_emerging_negative_trend_detected(client, db_session):
    _trend_world(db_session, recent_negative=20)
    summary = generate(client)
    assert summary["by_type"].get("emerging_negative_trend") == 1
    [trend] = by_type(listing(client))["emerging_negative_trend"]
    m = trend["metrics"]
    assert m["previous_share"] == pytest.approx(4 / 36, abs=1e-4)
    assert m["recent_share"] == pytest.approx(20 / 36, abs=1e-4)
    assert m["recent_window"]["n"] == 36 and m["previous_window"]["n"] == 36
    assert trend["period_start"] == "2026-10-01" and trend["period_end"] == "2026-12-31"
    assert trend["supporting_review_count"] == 20  # negative reviews in the latest window only
    assert "rose from 11% (36 mentions" in trend["explanation"]


def test_flat_trend_is_not_reported(client, db_session):
    _trend_world(db_session, recent_negative=4)
    generate(client)
    assert "emerging_negative_trend" not in by_type(listing(client))


# ------------------------------------------------------------------------- evidence integrity
def test_every_insight_links_to_real_reviews_with_verbatim_evidence(client, db_session):
    basic_world(db_session)
    generate(client)
    for insight in listing(client)["data"]:
        assert 1 <= len(insight["evidence"]) <= evidence.EXAMPLE_LIMIT
        assert len({e["review_id"] for e in insight["evidence"]}) == len(insight["evidence"])
        for item in insight["evidence"]:
            review = client.get(f"/api/reviews/{item['review_id']}").json()["data"]
            sentences = {m["evidence_text"] for m in review["mentions"]}
            assert item["excerpt"] in sentences, "excerpt must be a sentence stored for that review"
            assert item["property_name"] == review["property_name"]


def test_stored_evidence_matches_the_stance_of_the_insight(client, db_session):
    basic_world(db_session)
    generate(client)
    found = by_type(listing(client))
    for item in found["recurring_complaint"][0]["evidence"]:
        assert "negative" in item["excerpt"]
    for item in found["strength"][0]["evidence"]:
        assert "positive" in item["excerpt"]
    kinds = {("positive" in e["excerpt"]) for e in found["opportunity"][0]["evidence"]}
    assert kinds == {True, False}  # a split opinion shows both sides


def test_supporting_count_equals_the_review_explorer_total(client, db_session):
    basic_world(db_session)
    generate(client)
    for insight in listing(client)["data"]:
        f = insight["metrics"]["filters"]
        params = {
            "property_ids": ",".join(map(str, f["property_ids"])),
            "aspect": f["aspect"],
            "date_from": f["date_from"],
            "date_to": f["date_to"],
            "data_scope": f["data_scope"],
        }
        if f["aspect_sentiment"]:
            params["aspect_sentiment"] = f["aspect_sentiment"]
        total = client.get("/api/reviews", params=params).json()["meta"]["total"]
        assert total == insight["supporting_review_count"], insight["title"]


def test_text_numbers_come_from_the_metrics(client, db_session):
    basic_world(db_session)
    generate(client)
    for insight in listing(client)["data"]:
        result = grounding.check_grounding(
            {
                "title": insight["title"],
                "explanation": insight["explanation"],
                "recommended_action": insight["recommended_action"],
            },
            insight["metrics"],
            cited_review_ids=[],
            evidence_review_ids=[],
            known_names=[
                *(p["name"] for p in insight["properties"]),
                insight["aspect"]["display_name"],
                wording.inline_name(insight["aspect"]["display_name"]),
            ],
        )
        assert result.ok, result.problems


def test_metrics_record_provenance_and_thresholds(client, db_session):
    basic_world(db_session)
    generate(client)
    m = listing(client)["data"][0]["metrics"]
    assert m["thresholds"]["min_mentions"] == 10
    assert m["generation"]["reviews_in_scope"] == 63
    assert m["generation"]["analysis_run_id"] is not None
    assert m["evidence"]["supporting_reviews"] >= 1


# ------------------------------------------------------------------------- scope and lifecycle
def test_synthetic_data_never_leaks_into_genuine_insights(client, db_session):
    w = World(db_session)
    w.add("Alpha", "cleanliness", "negative", 12, JAN_FEB, synthetic=True)
    w.add("Alpha", "cleanliness", "positive", 3, JAN_FEB, synthetic=True)
    genuine = generate(client, "genuine")
    assert genuine["created"] == 0 and genuine["as_of"] is None
    assert any("no reviews" in note for note in genuine["notes"])

    synthetic = generate(client, "synthetic")
    assert synthetic["created"] == 1
    assert listing(client)["meta"]["total"] == 0  # default scope is genuine
    body = listing(client, data_scope="synthetic")
    assert body["meta"]["total"] == 1
    assert body["data"][0]["data_scope"] == "synthetic"
    assert body["meta"]["dataset"]["synthetic_reviews"] == 15
    assert all(e["is_synthetic"] for e in body["data"][0]["evidence"])


def test_regenerating_replaces_only_its_own_scope(client, db_session):
    w = World(db_session)
    w.add("Alpha", "cleanliness", "negative", 12, JAN_FEB)
    w.add("Beta", "cleanliness", "negative", 12, JAN_FEB, synthetic=True)
    generate(client, "genuine")
    generate(client, "synthetic")
    first = {i["id"] for i in listing(client)["data"]}
    again = generate(client, "genuine")
    assert again["replaced"] == 1 and again["created"] == 1
    assert {i["id"] for i in listing(client)["data"]}.isdisjoint(first)
    assert listing(client, data_scope="synthetic")["meta"]["total"] == 1


def test_results_are_deterministic(client, db_session):
    basic_world(db_session)
    generate(client)
    first = [
        (i["title"], i["explanation"], i["supporting_review_count"])
        for i in listing(client)["data"]
    ]
    generate(client)
    second = [
        (i["title"], i["explanation"], i["supporting_review_count"])
        for i in listing(client)["data"]
    ]
    assert first == second


def test_insights_become_stale_when_reviews_change(client, db_session):
    w = basic_world(db_session)
    generate(client)
    assert listing(client)["meta"]["stale"] is False
    w.add("Alpha", "cleanliness", "negative", 1, JAN_FEB)
    assert listing(client)["meta"]["stale"] is True
    generate(client)
    assert listing(client)["meta"]["stale"] is False


def test_deactivated_property_gets_no_insights(client, db_session):
    w = basic_world(db_session)
    assert (
        client.patch(f"/api/properties/{w.pid('Beta')}", json={"is_active": False}).status_code
        == 200
    )
    summary = generate(client)
    assert summary["by_type"] == {"recurring_complaint": 1, "strength": 1, "opportunity": 1}
    names = {p["name"] for i in listing(client)["data"] for p in i["properties"]}
    assert "Beta" not in names


def test_empty_database_is_not_an_error(client, db_session):
    summary = generate(client)
    assert summary["created"] == 0 and summary["as_of"] is None
    body = listing(client)
    assert body["data"] == [] and body["meta"]["total"] == 0 and body["meta"]["stale"] is False


def test_failed_generation_keeps_previous_insights(client, db_session, monkeypatch):
    basic_world(db_session)
    generate(client)
    before = [i["id"] for i in listing(client)["data"]]

    def boom(*args, **kwargs):
        raise RuntimeError("template failure")

    monkeypatch.setattr(wording, "render", boom)
    assert client.post("/api/insights/generate", json={}).status_code == 500
    assert [i["id"] for i in listing(client)["data"]] == before


def test_ungrounded_text_is_rejected_and_not_stored(client, db_session, monkeypatch):
    basic_world(db_session)
    original = wording.render

    def invented(*args, **kwargs):
        text = original(*args, **kwargs)
        text["explanation"] += " Complaints rose 87% last week."
        return text

    monkeypatch.setattr(wording, "render", invented)
    summary = generate(client)
    assert summary["created"] == 0 and summary["rejected_by_validator"] == 5
    assert listing(client)["meta"]["total"] == 0


# ------------------------------------------------------------------------- list and detail API
def test_list_filters_ordering_and_paging(client, db_session):
    w = basic_world(db_session)
    generate(client)
    assert listing(client, insight_type="strength")["meta"]["total"] == 1
    assert listing(client, evidence_strength="strong")["meta"]["total"] == 1
    assert listing(client, aspect="wifi_connectivity")["meta"]["total"] == 1
    assert listing(client, property_ids=str(w.pid("Gamma")))["meta"]["total"] == 2
    assert listing(client, property_ids=f"{w.pid('Alpha')},{w.pid('Beta')}")["meta"]["total"] == 3
    order = [i["insight_type"] for i in listing(client)["data"]]
    assert order[0] == "cross_property_issue"  # strong evidence first, then the type order
    page = listing(client, page_size=2, page=3)
    assert len(page["data"]) == 1 and page["meta"]["total"] == 5


@pytest.mark.parametrize(
    "params",
    [
        {"property_ids": "a,b"},
        {"insight_type": "nonsense"},
        {"data_scope": "everything"},
        {"page": 0},
    ],
)
def test_list_rejects_invalid_filters(client, db_session, params):
    assert client.get("/api/insights", params=params).status_code == 422


def test_get_one_insight_and_missing_one(client, db_session):
    basic_world(db_session)
    generate(client)
    first = listing(client)["data"][0]
    detail = client.get(f"/api/insights/{first['id']}")
    assert detail.status_code == 200 and detail.json()["data"] == first
    missing = client.get("/api/insights/99999")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "INSIGHT_NOT_FOUND"


def test_generate_rejects_unknown_scope(client, db_session):
    response = client.post("/api/insights/generate", json={"data_scope": "everything"})
    assert response.status_code == 422


# ------------------------------------------------------------------------- grounding validator
METRICS = {
    "mentions": 14,
    "negative": 10,
    "negative_share": 0.7143,
    "difference": -0.25,
    "period": {"from": "2026-03-01"},
    "confidence_percent": 95,
}
FIELDS = {
    "title": "T",
    "explanation": "10 of 14 were negative (71%).",
    "recommended_action": "Act.",
}


def check(fields=None, metrics=None, cited=(), evidence_ids=(1, 2), names=()):
    return grounding.check_grounding(
        fields or FIELDS,
        metrics or METRICS,
        cited_review_ids=cited,
        evidence_review_ids=evidence_ids,
        known_names=names,
    )


def test_validator_accepts_numbers_from_metrics():
    assert check().ok
    percent_points = dict(FIELDS, explanation="25 percentage points, 71.4% of 14, on 1 March 2026.")
    assert check(percent_points).ok  # 0.25 -> 25, 0.7143 -> 71.4, date parts 2026 / 3 / 1


def test_validator_rejects_an_invented_number():
    bad = dict(FIELDS, explanation="10 of 14 were negative (87%).")
    result = check(bad)
    assert not result.ok and "87" in result.problems[0]


def test_validator_rejects_citing_a_review_outside_the_evidence():
    result = check(cited=[1, 99])
    assert not result.ok and "99" in result.problems[0]
    assert check(cited=[1, 2]).ok


def test_validator_requires_every_field():
    result = check(dict(FIELDS, recommended_action=" "))
    assert not result.ok and "recommended_action" in result.problems[0]


def test_validator_ignores_digits_inside_names():
    fields = dict(FIELDS, title="Hotel 54 wing 7")
    assert not check(fields).ok
    assert check(fields, names=["Hotel 54 wing 7"]).ok


def test_validator_does_not_treat_booleans_as_numbers():
    assert 1.0 not in grounding.allowed_numbers({"flag": True})


# ------------------------------------------------------------------------- evidence helpers
@pytest.mark.parametrize(
    ("supporting", "span", "low", "expected"),
    [
        (20, 2, False, EvidenceStrength.STRONG),
        (19, 2, False, EvidenceStrength.MODERATE),
        (20, 1, False, EvidenceStrength.MODERATE),  # one month only
        (30, 3, True, EvidenceStrength.MODERATE),  # low-sample flag blocks "strong"
        (8, 1, False, EvidenceStrength.MODERATE),
        (7, 5, False, EvidenceStrength.LIMITED),
        (0, 0, False, EvidenceStrength.LIMITED),
    ],
)
def test_evidence_grade(supporting, span, low, expected):
    assert evidence.grade(supporting, span, low) is expected


def test_months_spanned_counts_calendar_months():
    days = [date(2026, 1, 31), date(2026, 2, 1), date(2026, 2, 28), date(2027, 1, 5)]
    assert evidence.months_spanned(days) == 3


def test_examples_prefer_distinct_wording_and_one_per_review(db_session):
    w = World(db_session, names=("Alpha",))
    # Twelve reviews with identical wording, then three with different wording.
    ids = w.add("Alpha", "cleanliness", "negative", 15, JAN_FEB)
    from sqlalchemy import update

    from app.models import AspectMention

    db_session.execute(
        update(AspectMention)
        .where(AspectMention.review_id.in_(ids[:12]))
        .values(evidence_text="Dirty room.")
    )
    db_session.commit()
    picked = evidence.select_examples(db_session, ids, "cleanliness", SentimentLabel.NEGATIVE)
    texts = [p["excerpt"] for p in picked]
    assert len(picked) == 10 and len({p["review_id"] for p in picked}) == 10
    assert texts.count("Dirty room.") == 7  # the 4 distinct sentences first, then repeats
    assert [p["rank"] for p in picked] == list(range(1, 11))


def test_examples_empty_when_no_reviews(db_session):
    assert evidence.select_examples(db_session, [], "cleanliness", None) == []


# ------------------------------------------------------------------------- wording
def test_action_catalogue_covers_every_aspect_without_numbers():
    from app.analytics.nlp.aspects import load_lexicon

    catalogue = json.loads(wording.ACTIONS_PATH.read_text(encoding="utf-8"))
    for aspect in load_lexicon().aspects:
        assert aspect.key in catalogue["aspects"], f"no suggested actions for {aspect.key}"
    texts = [catalogue["default"], *catalogue["aspects"].values()]
    for entry in texts:
        for kind in ("complaint", "strength", "opportunity"):
            assert entry[kind] and not any(c.isdigit() for c in entry[kind])


def test_unknown_aspect_falls_back_to_the_default_action():
    assert (
        wording.suggested_action("something_new", "complaint")
        == (wording.load_actions()["default"]["complaint"])
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Cleanliness", "cleanliness"), ("Wi-Fi & connectivity", "Wi-Fi & connectivity"), ("", "")],
)
def test_inline_name(name, expected):
    assert wording.inline_name(name) == expected
