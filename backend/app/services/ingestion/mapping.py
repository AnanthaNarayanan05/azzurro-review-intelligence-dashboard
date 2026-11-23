"""Internal review fields and automatic suggestions for mapping file columns onto them."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ImportField:
    key: str
    label: str
    description: str
    synonyms: tuple[str, ...]


# Reviewer names are deliberately not importable: the dashboard has no use for personal names.
IMPORT_FIELDS: tuple[ImportField, ...] = (
    ImportField(
        "external_review_id",
        "Review ID",
        "The source platform's own ID for the review. Makes re-imports exact.",
        ("review id", "reviewid", "review_id", "external id", "id", "uuid", "review number"),
    ),
    ImportField(
        "property",
        "Property",
        "Which hotel the review is for.",
        ("property", "property name", "hotel", "hotel name", "accommodation", "listing"),
    ),
    ImportField(
        "review_date",
        "Review date",
        "When the review was written.",
        (
            "review date",
            "date",
            "reviewed",
            "date of review",
            "date posted",
            "published",
            "review posted",
            "created",
        ),
    ),
    ImportField(
        "rating",
        "Rating",
        "The overall score given by the guest.",
        ("rating", "score", "review score", "reviewer score", "overall", "stars", "guest rating"),
    ),
    ImportField("title", "Title", "The review headline.", ("title", "headline", "review title")),
    ImportField(
        "positive_text",
        "Positive text",
        "What the guest liked.",
        ("positive review", "positive", "liked", "pros", "what guests liked", "good", "likes"),
    ),
    ImportField(
        "negative_text",
        "Negative text",
        "What the guest disliked.",
        (
            "negative review",
            "negative",
            "disliked",
            "cons",
            "what guests disliked",
            "bad",
            "dislikes",
        ),
    ),
    ImportField(
        "body_text",
        "Review text",
        "A single free-text review body.",
        ("review", "review text", "text", "comment", "comments", "body", "content", "feedback"),
    ),
    ImportField("language", "Language", "Language code.", ("language", "lang", "locale")),
    ImportField(
        "traveller_type",
        "Traveller type",
        "e.g. couple, solo, family.",
        ("traveller type", "traveler type", "guest type", "trip type", "group type"),
    ),
    ImportField(
        "reviewer_country",
        "Reviewer country",
        "Country of the guest.",
        ("country", "reviewer country", "guest country", "nationality"),
    ),
    ImportField(
        "room_type", "Room type", "Room booked.", ("room type", "room", "room name", "unit type")
    ),
    ImportField(
        "stay_nights",
        "Nights stayed",
        "Length of stay.",
        ("nights", "stay nights", "length of stay", "nights stayed", "number of nights"),
    ),
    ImportField(
        "source_url",
        "Source URL",
        "Link to the original review, where one exists.",
        ("url", "source url", "review url", "link"),
    ),
)
FIELD_KEYS = tuple(f.key for f in IMPORT_FIELDS)
TEXT_FIELD_KEYS = ("positive_text", "negative_text", "body_text", "title")


def _canon(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", header.lower()).strip()


def suggest_mapping(columns: list[str]) -> dict[str, str | None]:
    """Suggest {field: column} using exact header matches, then a looser containment match.

    A column is used at most once. This is only a suggestion; the user always confirms it.
    """
    canon = {col: _canon(col) for col in columns}
    used: set[str] = set()
    result: dict[str, str | None] = {f.key: None for f in IMPORT_FIELDS}

    # Pass 1: exact synonym match (in the order the synonyms are listed).
    for spec in IMPORT_FIELDS:
        for synonym in spec.synonyms:
            match = next(
                (c for c in columns if c not in used and canon[c] == _canon(synonym)), None
            )
            if match:
                result[spec.key] = match
                used.add(match)
                break

    # Pass 2: header contains a synonym (e.g. "Hotel Name (display)"), for fields still unmapped.
    for spec in IMPORT_FIELDS:
        if result[spec.key] is not None:
            continue
        for synonym in spec.synonyms:
            wanted = f" {_canon(synonym)} "
            match = next((c for c in columns if c not in used and wanted in f" {canon[c]} "), None)
            if match and len(_canon(synonym)) > 3:  # avoid "id"/"bad" matching inside longer words
                result[spec.key] = match
                used.add(match)
                break
    return result
