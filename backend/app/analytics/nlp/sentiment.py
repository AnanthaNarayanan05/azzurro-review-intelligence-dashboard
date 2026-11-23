"""Sentiment engine. VADER is the baseline: fast, deterministic and explainable, but English-only.

No accuracy is claimed for it on this project's data until it has been evaluated on a
human-labelled sample
(see docs/AI_ANALYTICS.md section 7).
"""

from importlib.metadata import PackageNotFoundError, version
from typing import Protocol

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.models.base import SentimentLabel

# VADER's published thresholds. Re-check on the labelled sample before relying on them.
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05


class SentimentEngine(Protocol):
    name: str

    def score(self, text: str) -> float:
        """A score from -1 (most negative) to +1 (most positive)."""
        ...


class VaderEngine:
    def __init__(self) -> None:
        try:
            package_version = version("vaderSentiment")
        except PackageNotFoundError:  # pragma: no cover - installed package always has metadata
            package_version = "unknown"
        self.name = f"vader-{package_version}"
        self._analyser = SentimentIntensityAnalyzer()

    def score(self, text: str) -> float:
        return float(self._analyser.polarity_scores(text)["compound"])


def label_for(score: float) -> SentimentLabel:
    if score >= POSITIVE_THRESHOLD:
        return SentimentLabel.POSITIVE
    if score <= NEGATIVE_THRESHOLD:
        return SentimentLabel.NEGATIVE
    return SentimentLabel.NEUTRAL


def mean(values: list[float]) -> float:
    return sum(values) / len(values)
