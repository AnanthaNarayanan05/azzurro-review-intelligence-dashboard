"""Metrics for checking the sentiment and aspect methods against a human-labelled sample.

Pure functions with no database or file access, so the arithmetic can be unit tested against numbers
worked out by hand. The labels must come from a person: the model's own output is never ground truth
(docs/AI_ANALYTICS.md section 7). Nothing here claims a method is accurate; it only measures.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

SENTIMENTS = ("positive", "neutral", "negative")
STANCES = ("positive", "neutral", "negative")

# Below this many labelled reviews the figures are shown but flagged as too few to rely on.
MIN_RELIABLE_SAMPLE = 100


def ratio(numerator: int, denominator: int) -> float | None:
    """None, not 0, when there is nothing to divide by: "no cases" is different from "all wrong"."""
    return numerator / denominator if denominator else None


def f1_score(precision: float | None, recall: float | None) -> float | None:
    if precision is None and recall == 0:
        return 0.0  # humans found cases and the system predicted none of them: F1 is 0, not unknown
    if precision is None or recall is None:
        return None
    total = precision + recall
    return 2 * precision * recall / total if total else 0.0


@dataclass(frozen=True)
class ClassMetrics:
    label: str
    support: int  # how many reviews a human put in this class
    predicted: int  # how many the system put in this class
    true_positive: int
    precision: float | None
    recall: float | None
    f1: float | None


@dataclass(frozen=True)
class SentimentReport:
    n: int
    accuracy: float | None
    macro_f1: float | None
    classes: list[ClassMetrics]
    matrix: dict[str, dict[str, int]]  # matrix[human][system]


def sentiment_report(
    pairs: Iterable[tuple[str, str]], labels: Sequence[str] = SENTIMENTS
) -> SentimentReport:
    """`pairs` are (human label, system label). Classes with no human examples are left out of
    the macro average instead of counting as zero."""
    pairs = list(pairs)
    counts = Counter(pairs)
    matrix = {h: {s: counts[(h, s)] for s in labels} for h in labels}
    classes = []
    for label in labels:
        tp = counts[(label, label)]
        support = sum(counts[(label, s)] for s in labels)
        predicted = sum(counts[(h, label)] for h in labels)
        precision = ratio(tp, predicted)
        recall = ratio(tp, support)
        classes.append(
            ClassMetrics(
                label, support, predicted, tp, precision, recall, f1_score(precision, recall)
            )
        )
    scored = [c.f1 for c in classes if c.support > 0 and c.f1 is not None]
    macro = sum(scored) / len(scored) if scored else None
    correct = sum(counts[(label, label)] for label in labels)
    return SentimentReport(len(pairs), ratio(correct, len(pairs)), macro, classes, matrix)


@dataclass(frozen=True)
class AspectDetection:
    aspect: str
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float | None
    recall: float | None
    f1: float | None


def aspect_detection_report(
    human: Sequence[set[str]], system: Sequence[set[str]], aspects: Sequence[str]
) -> list[AspectDetection]:
    """Per aspect, did the system find the same reviews a human marked as mentioning it?

    Counted per review, as the dashboard counts (a review mentions an aspect once however many
    sentences do)."""
    if len(human) != len(system):
        raise ValueError("human and system label lists must be the same length")
    rows = []
    for aspect in aspects:
        tp = sum(1 for h, s in zip(human, system, strict=True) if aspect in h and aspect in s)
        fp = sum(1 for h, s in zip(human, system, strict=True) if aspect not in h and aspect in s)
        fn = sum(1 for h, s in zip(human, system, strict=True) if aspect in h and aspect not in s)
        precision = ratio(tp, tp + fp)
        recall = ratio(tp, tp + fn)
        rows.append(
            AspectDetection(aspect, tp, fp, fn, precision, recall, f1_score(precision, recall))
        )
    return rows


def stance_accuracy(
    human: Sequence[dict[str, str]], system: Sequence[dict[str, str]]
) -> tuple[int, int, float | None]:
    """Accuracy of the positive / neutral / negative stance on aspects both sides found.

    Returns (correct, compared, accuracy). Aspects only one side found are not compared here: they
    already count against detection precision or recall."""
    correct = compared = 0
    for h, s in zip(human, system, strict=True):
        for aspect in h.keys() & s.keys():
            compared += 1
            correct += h[aspect] == s[aspect]
    return correct, compared, ratio(correct, compared)


def parse_human_aspects(text: str, valid_aspects: Iterable[str]) -> dict[str, str]:
    """Parse "cleanliness:negative; staff_service:positive" into {aspect: stance}.

    Raises ValueError with a message naming the problem, so a typo in a labelling sheet is fixed
    rather than silently read as "no aspect"."""
    valid = set(valid_aspects)
    result: dict[str, str] = {}
    for part in (p.strip() for p in text.replace("\n", ";").split(";")):
        if not part:
            continue
        aspect, _, stance = (piece.strip().lower() for piece in part.partition(":"))
        if aspect not in valid:
            raise ValueError(f"unknown aspect '{aspect}' (use one of: {', '.join(sorted(valid))})")
        if stance not in STANCES:
            raise ValueError(f"aspect '{aspect}' needs a stance of positive, neutral or negative")
        if aspect in result:
            raise ValueError(f"aspect '{aspect}' is listed twice")
        result[aspect] = stance
    return result


def system_stances(mention_labels: Iterable[tuple[str, str]]) -> dict[str, str]:
    """One stance per aspect from the system's mentions, using the dashboard's rule: positive
    mentions minus negative mentions decides (a tie or only neutral mentions is neutral)."""
    balance: dict[str, int] = {}
    for aspect, label in mention_labels:
        balance.setdefault(aspect, 0)
        if label == "positive":
            balance[aspect] += 1
        elif label == "negative":
            balance[aspect] -= 1
    return {
        a: "positive" if b > 0 else "negative" if b < 0 else "neutral" for a, b in balance.items()
    }
