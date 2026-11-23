"""Rule-based aspect detection driven by `aspect_lexicon.json`.

An aspect is mentioned in a sentence when one of its terms matches on word boundaries. This misses
implicit
mentions and can mis-assign ambiguous words; both limits are documented in docs/AI_ANALYTICS.md.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.analytics.nlp.preprocess import normalise_answer

LEXICON_PATH = Path(__file__).with_name("aspect_lexicon.json")


@dataclass(frozen=True)
class AspectDefinition:
    key: str
    display_name: str
    terms: tuple[str, ...]
    exclusions: tuple[str, ...]
    _term_patterns: tuple[tuple[str, re.Pattern[str]], ...] = field(repr=False, default=())
    _exclusion_pattern: re.Pattern[str] | None = field(repr=False, default=None)


@dataclass(frozen=True)
class Lexicon:
    version: str
    aspects: tuple[AspectDefinition, ...]
    placeholders: frozenset[str]


@dataclass(frozen=True)
class AspectMatch:
    aspect_key: str
    term: str


def _term_regex(term: str) -> re.Pattern[str]:
    """`clean*` -> any word starting with clean; everything else matches the whole word or
    phrase."""
    wildcard = term.endswith("*")
    body = re.escape(term.rstrip("*").lower()).replace(r"\ ", r"\s+")
    suffix = r"\w*" if wildcard else ""
    return re.compile(rf"(?<!\w){body}{suffix}(?!\w)", re.IGNORECASE)


def _exclusion_regex(phrases: tuple[str, ...]) -> re.Pattern[str] | None:
    if not phrases:
        return None
    parts = [re.escape(p.lower()).replace(r"\ ", r"\s+") for p in phrases]
    alternatives = "|".join(parts)
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", re.IGNORECASE)


def load_lexicon(path: Path = LEXICON_PATH) -> Lexicon:
    raw = json.loads(path.read_text(encoding="utf-8"))
    aspects = []
    for item in raw["aspects"]:
        terms = tuple(dict.fromkeys(t.strip() for t in item["terms"] if t.strip()))
        exclusions = tuple(item.get("exclusions", []))
        aspects.append(
            AspectDefinition(
                key=item["key"],
                display_name=item["display_name"],
                terms=terms,
                exclusions=exclusions,
                _term_patterns=tuple((t, _term_regex(t)) for t in terms),
                _exclusion_pattern=_exclusion_regex(exclusions),
            )
        )
    keys = [a.key for a in aspects]
    if len(keys) != len(set(keys)):
        raise ValueError("aspect_lexicon.json contains a duplicate aspect key")
    placeholders = frozenset(normalise_answer(p) for p in raw["placeholders"]["any"])
    return Lexicon(version=str(raw["version"]), aspects=tuple(aspects), placeholders=placeholders)


def detect_aspects(sentence: str, lexicon: Lexicon) -> list[AspectMatch]:
    """All aspects mentioned in one sentence, with the first matching term of each."""
    matches: list[AspectMatch] = []
    for aspect in lexicon.aspects:
        text = sentence
        if aspect._exclusion_pattern is not None:
            text = aspect._exclusion_pattern.sub(" ", text)
        for term, pattern in aspect._term_patterns:
            if pattern.search(text):
                matches.append(AspectMatch(aspect.key, term))
                break
    return matches
