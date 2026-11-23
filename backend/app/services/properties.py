"""Property helpers: matching raw names from files to properties, and code generation."""

import difflib
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Property, PropertyAlias
from app.services.ingestion.normalise import normalise_for_match

SIMILARITY_THRESHOLD = 0.86


@dataclass(frozen=True)
class PropertyMatch:
    property_id: int
    match_type: str  # "alias" | "name" | "code" | "similar"


class PropertyIndex:
    """In-memory lookup built once per request from the properties and aliases tables."""

    def __init__(self, db: Session) -> None:
        self._exact: dict[str, PropertyMatch] = {}
        self._names: dict[str, int] = {}
        self.ids: set[int] = set()
        for prop in db.scalars(select(Property)):
            self.ids.add(prop.id)
            name_key = normalise_for_match(prop.name)
            self._exact[name_key] = PropertyMatch(prop.id, "name")
            self._exact.setdefault(normalise_for_match(prop.code), PropertyMatch(prop.id, "code"))
            self._names[name_key] = prop.id
        for alias in db.scalars(select(PropertyAlias)):
            self._exact[alias.alias_normalised] = PropertyMatch(alias.property_id, "alias")

    def exact(self, raw_value: str) -> PropertyMatch | None:
        return self._exact.get(normalise_for_match(raw_value))

    def suggest(self, raw_value: str) -> PropertyMatch | None:
        """Exact match, else the single closest property name above a similarity threshold."""
        found = self.exact(raw_value)
        if found:
            return found
        close = difflib.get_close_matches(
            normalise_for_match(raw_value), list(self._names), n=1, cutoff=SIMILARITY_THRESHOLD
        )
        return PropertyMatch(self._names[close[0]], "similar") if close else None


def make_code(name: str, existing_codes: set[str]) -> str:
    """Derive a short unique code from a property name, e.g. 'Olympic Hotel' -> 'olympic-hotel'."""
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:28] or "property"
    code, counter = base, 2
    while code in existing_codes:
        code = f"{base}-{counter}"
        counter += 1
    return code
