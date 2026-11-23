"""Text normalisation and the stable content fingerprint used for duplicate detection."""

import hashlib
import re
import unicodedata
from datetime import date
from decimal import Decimal

_WHITESPACE = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^\w\s]", re.UNICODE)


def clean_text(value: object) -> str | None:
    """Trim a cell value. Empty or whitespace-only becomes None. Inner text is left untouched."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalise_for_match(value: str | None) -> str:
    """Lower-case, unicode-fold, drop punctuation and collapse whitespace.

    Used for comparing names ("Olympic Hotel  Paddington" == "olympic hotel paddington") and for
    fingerprinting review text. Never used to alter what is stored or shown.
    """
    if not value:
        return ""
    folded = unicodedata.normalize("NFKC", value).casefold()
    folded = _NON_WORD.sub(" ", folded)
    return _WHITESPACE.sub(" ", folded).strip()


def content_hash(
    *,
    source: str,
    property_id: int,
    review_date: date,
    rating: Decimal | None,
    title: str | None,
    positive_text: str | None,
    negative_text: str | None,
    body_text: str | None,
) -> str:
    """Stable SHA-256 over what makes a review "the same review".

    Source, property, date, normalised rating and normalised text. Formatting differences
    (case, punctuation, spacing) do not change the fingerprint; any change to the wording,
    date, rating or property does.
    """
    parts = [
        source.casefold(),
        str(property_id),
        review_date.isoformat(),
        f"{rating:.2f}" if rating is not None else "",
        normalise_for_match(title),
        normalise_for_match(positive_text),
        normalise_for_match(negative_text),
        normalise_for_match(body_text),
    ]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
