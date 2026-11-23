"""Pre-processing: placeholder detection and sentence splitting.

The original review text is never modified; analysis works on the sentences produced here.
"""

import re
import unicodedata

# A sentence ends at . ! ? (optionally followed by closing quotes/brackets) or at a line break or
# bullet.
_SPLIT = re.compile(
    r"(?<=[.!?])[\"')\]]*\s+(?=[\"'(\[]?[A-Z0-9])|[\r\n]+|\s+[•*·▪‣–—-]\s+|^[•*·▪‣-]\s+"
)
_NON_WORD = re.compile(r"[^\w\s]|_", re.UNICODE)
_SPACES = re.compile(r"\s+")
MAX_SENTENCE_CHARS = 500


def normalise_answer(text: str) -> str:
    """Lower-case, strip punctuation and collapse spaces: used to recognise placeholder answers."""
    folded = unicodedata.normalize("NFKC", text).lower()
    return _SPACES.sub(" ", _NON_WORD.sub(" ", folded)).strip()


def is_placeholder(text: str, placeholders: frozenset[str]) -> bool:
    """True when the text carries no substantive content, e.g. "Nothing", "N/A", "-" or empty."""
    normalised = normalise_answer(text)
    if not normalised:  # empty, or only punctuation / symbols
        return True
    return normalised in placeholders


def split_sentences(text: str) -> list[str]:
    """Split review text into sentences. Rule-based and deliberately simple (see
    AI_ANALYTICS.md)."""
    sentences: list[str] = []
    for part in _SPLIT.split(text.strip()):
        cleaned = _SPACES.sub(" ", part).strip()
        if cleaned and any(ch.isalnum() for ch in cleaned):
            sentences.append(cleaned[:MAX_SENTENCE_CHARS])
    return sentences


def substantive_sentences(text: str | None, placeholders: frozenset[str]) -> list[str]:
    """Sentences worth scoring: none when the field is empty or a placeholder answer."""
    if text is None or is_placeholder(text, placeholders):
        return []
    return [s for s in split_sentences(text) if not is_placeholder(s, placeholders)]
