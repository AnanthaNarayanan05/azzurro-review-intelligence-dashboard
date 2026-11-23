"""Template wording: title, explanation and suggested action built only from computed numbers."""

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.base import InsightType

ACTIONS_PATH = Path(__file__).with_name("insight_actions.json")


@lru_cache
def load_actions(path: Path = ACTIONS_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def suggested_action(aspect_key: str, kind: str) -> str:
    catalogue = load_actions()
    entry = catalogue["aspects"].get(aspect_key) or catalogue["default"]
    return entry.get(kind) or catalogue["default"][kind]


def pct(share: float | None) -> str:
    return f"{round((share or 0) * 100):d}%"


def points(value: float) -> str:
    return f"{round(abs(value) * 100):d}"


def day(value: str | date) -> str:
    parsed = date.fromisoformat(value) if isinstance(value, str) else value
    return f"{parsed.day} {parsed.strftime('%b')} {parsed.year}"


def inline_name(name: str) -> str:
    """Lower-case the first letter for mid-sentence use, unless there are other capitals (Wi-Fi)."""
    return name if any(c.isupper() for c in name[1:]) else name[:1].lower() + name[1:]


def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def render(
    insight_type: InsightType,
    *,
    aspect_key: str,
    aspect_name: str,
    property_names: list[str],
    metrics: dict[str, Any],
    period_start: date,
    period_end: date,
) -> dict[str, str]:
    """Returns title, explanation and recommended_action."""
    aspect = inline_name(aspect_name)
    where = _join(property_names)
    span = f"between {day(period_start)} and {day(period_end)}"
    m = metrics

    if insight_type is InsightType.RECURRING_COMPLAINT:
        return {
            "title": f"Recurring complaints about {aspect} at {where}",
            "explanation": (
                f"{m['negative']} of {m['mentions']} reviews that mention {aspect} at {where} "
                f"were negative ({pct(m['negative_share'])}), {span}. "
                "It is a repeated theme, not a single comment."
            ),
            "recommended_action": suggested_action(aspect_key, "complaint"),
        }
    if insight_type is InsightType.STRENGTH:
        return {
            "title": f"{aspect_name} is a strength at {where}",
            "explanation": (
                f"{m['positive']} of {m['mentions']} reviews that mention {aspect} at {where} "
                f"were positive ({pct(m['positive_share'])}), {span}."
            ),
            "recommended_action": suggested_action(aspect_key, "strength"),
        }
    if insight_type is InsightType.EMERGING_NEGATIVE_TREND:
        recent, previous = m["recent_window"], m["previous_window"]
        return {
            "title": f"Complaints about {aspect} are rising at {where}",
            "explanation": (
                f"The share of {aspect} mentions at {where} that were negative rose from "
                f"{pct(m['previous_share'])} ({previous['n']} mentions, {day(previous['from'])} to "
                f"{day(previous['to'])}) to {pct(m['recent_share'])} ({recent['n']} mentions, "
                f"{day(recent['from'])} to {day(recent['to'])}). That is {points(m['difference'])} "
                f"percentage points more; the {m['confidence_percent']}% interval runs from "
                f"{points(m['ci_low'])} to {points(m['ci_high'])} points."
            ),
            "recommended_action": suggested_action(aspect_key, "complaint"),
        }
    if insight_type is InsightType.PROPERTY_ISSUE:
        rest = m["rest"]
        return {
            "title": f"{aspect_name} draws more complaints at {where} than elsewhere",
            "explanation": (
                f"{m['negative']} of {m['mentions']} reviews mentioning {aspect} at {where} were "
                f"negative ({pct(m['negative_share'])}), against {rest['negative']} of "
                f"{rest['mentions']} ({pct(rest['negative_share'])}) at the other properties. The "
                f"gap is {points(m['difference'])} percentage points; the "
                f"{m['confidence_percent']}% interval runs from {points(m['ci_low'])} to "
                f"{points(m['ci_high'])} points."
            ),
            "recommended_action": suggested_action(aspect_key, "complaint"),
        }
    if insight_type is InsightType.CROSS_PROPERTY_ISSUE:
        parts = "; ".join(
            f"{p['name']}: {p['negative']} of {p['mentions']} ({pct(p['negative_share'])})"
            for p in m["per_property"]
        )
        return {
            "title": f"{aspect_name} is a recurring complaint at {m['property_count']} properties",
            "explanation": (
                f"Negative reviews about {aspect}, {span}: {parts}. Together that is "
                f"{m['negative']} of {m['mentions']} mentions ({pct(m['negative_share'])})."
            ),
            "recommended_action": suggested_action(aspect_key, "complaint"),
        }
    return {  # OPPORTUNITY
        "title": f"Guests are divided about {aspect} at {where}",
        "explanation": (
            f"{aspect_name} is mentioned in {m['mentions']} reviews at {where}: {m['positive']} "
            f"positive ({pct(m['positive_share'])}) and {m['negative']} negative "
            f"({pct(m['negative_share'])}), {span}. Opinion is split, so some guests are not "
            "getting the experience others praise."
        ),
        "recommended_action": suggested_action(aspect_key, "opportunity"),
    }
