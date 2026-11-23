"""Grounding validator: insight text may only say what the stored metrics and evidence support.

It is independent of how the text was produced. Template text goes through it today; any future
language-model wording would have to pass the same check before being stored.
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
REQUIRED_FIELDS = ("title", "explanation", "recommended_action")


@dataclass
class GroundingResult:
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def _key(value: float) -> float:
    return round(float(value), 3)


def allowed_numbers(metrics: Mapping[str, Any]) -> set[float]:
    """Every number the text may quote: each numeric value in the metrics, the percentages of
    values between 0 and 1, and the parts of any ISO date."""
    allowed: set[float] = set()

    def visit(node: Any) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            allowed.add(_key(node))
            if isinstance(node, float) and -1 <= node <= 1:
                allowed.add(_key(round(abs(node) * 100)))
                allowed.add(_key(round(abs(node) * 100, 1)))
            return
        if isinstance(node, str):
            match = _ISO_DATE.match(node)
            if match:
                for part in match.groups():
                    allowed.add(_key(int(part)))
            return
        if isinstance(node, Mapping):
            for value in node.values():
                visit(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                visit(value)

    visit(metrics)
    return allowed


def _strip_names(text: str, names: Iterable[str]) -> str:
    """Names (a property called 'Hotel 54') are data, not claims, so their digits are ignored."""
    for name in sorted({n for n in names if n}, key=len, reverse=True):
        text = text.replace(name, " ")
    return text


def check_grounding(
    fields: Mapping[str, str],
    metrics: Mapping[str, Any],
    *,
    cited_review_ids: Iterable[int],
    evidence_review_ids: Iterable[int],
    known_names: Iterable[str] = (),
) -> GroundingResult:
    result = GroundingResult()
    for name in REQUIRED_FIELDS:
        if not str(fields.get(name, "")).strip():
            result.problems.append(f"{name} is missing")

    evidence = set(evidence_review_ids)
    outside = sorted(set(cited_review_ids) - evidence)
    if outside:
        result.problems.append(f"cites review ids outside the evidence set: {outside}")

    allowed = allowed_numbers(metrics)
    names = list(known_names)
    for name in REQUIRED_FIELDS:
        text = _strip_names(str(fields.get(name, "")), names)
        for token in _NUMBER.findall(text):
            if _key(float(token)) not in allowed:
                result.problems.append(f"{name} quotes {token}, which is not in the metrics")
    return result
