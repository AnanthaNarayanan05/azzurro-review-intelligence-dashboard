"""Builds small, hand-countable datasets straight in the database (no NLP involved), so every
insight rule can be checked against numbers worked out on paper."""

from datetime import date, timedelta
from decimal import Decimal
from itertools import count

from sqlalchemy.orm import Session

from app.analytics.nlp.aspects import load_lexicon
from app.models import AnalysisRun, AspectMention, ImportBatch, Property, Review
from app.models.base import AnalysisStatus, RunStatus
from app.services import analysis

_hashes = count(1)


class World:
    """Properties, one analysis run and helpers to add reviews with chosen aspect stances."""

    def __init__(self, db: Session, names: tuple[str, ...] = ("Alpha", "Beta", "Gamma")) -> None:
        self.db = db
        self.aspects = analysis.sync_aspects(db, load_lexicon())
        self.properties = {}
        for index, name in enumerate(names, start=1):
            prop = Property(code=f"P{index}", name=name)
            db.add(prop)
            self.properties[name] = prop
        self.batch = ImportBatch(filename="t.csv", file_sha256="0" * 64, source_type="csv")
        self.run = AnalysisRun(
            triggered_by="manual",
            sentiment_engine="vader",
            aspect_lexicon_version="test",
            status=RunStatus.COMPLETED.value,
        )
        db.add_all([self.batch, self.run])
        db.commit()

    def pid(self, name: str) -> int:
        return self.properties[name].id

    def add(
        self,
        property_name: str,
        aspect: str,
        label: str,
        n: int,
        dates: list[date],
        *,
        synthetic: bool = False,
    ) -> list[int]:
        """Add `n` reviews, each with one mention of `aspect` labelled `label`."""
        ids = []
        for i in range(n):
            review = Review(
                property_id=self.pid(property_name),
                import_id=self.batch.id,
                review_date=dates[i % len(dates)],
                rating=Decimal("7.0"),
                positive_text=f"{aspect} {label} review {i}",
                content_hash=f"{next(_hashes):064d}",
                is_synthetic=synthetic,
                analysis_status=AnalysisStatus.ANALYSED.value,
                analysed_run_id=self.run.id,
            )
            self.db.add(review)
            self.db.flush()
            self.db.add(
                AspectMention(
                    review_id=review.id,
                    aspect_id=self.aspects[aspect],
                    analysis_run_id=self.run.id,
                    source_field="positive",
                    sentiment_label=label,
                    score=Decimal("0.6") if label == "positive" else Decimal("-0.6"),
                    evidence_text=f"The {aspect} was {label}, said guest {review.id}.",
                    matched_term=aspect,
                )
            )
            ids.append(review.id)
        self.db.commit()
        return ids


JAN_FEB = [date(2026, 1, 10), date(2026, 1, 25), date(2026, 2, 8), date(2026, 2, 20)]


def basic_world(db: Session) -> World:
    """Alpha and Beta both have a cleanliness complaint, Gamma has a staff strength, a split opinion
    about Wi-Fi, and one aspect with too few mentions to say anything."""
    w = World(db)
    # Alpha cleanliness: 14 mentions, 10 negative (71 %), 4 positive.
    w.add("Alpha", "cleanliness", "negative", 10, JAN_FEB)
    w.add("Alpha", "cleanliness", "positive", 4, JAN_FEB)
    # Beta cleanliness: 12 mentions, 10 negative (83 %), 2 positive.
    w.add("Beta", "cleanliness", "negative", 10, JAN_FEB)
    w.add("Beta", "cleanliness", "positive", 2, JAN_FEB)
    # Gamma staff: 20 mentions, 17 positive (85 %), 3 negative.
    w.add("Gamma", "staff_service", "positive", 17, JAN_FEB)
    w.add("Gamma", "staff_service", "negative", 3, JAN_FEB)
    # Gamma Wi-Fi: 12 mentions, 8 positive (67 %) and 4 negative (33 %): split opinion, below the
    # complaint line (and 4 negatives is below the floor of 10 anyway).
    w.add("Gamma", "wifi_connectivity", "positive", 8, JAN_FEB)
    w.add("Gamma", "wifi_connectivity", "negative", 4, JAN_FEB)
    # Gamma location: 5 mentions, all negative: below the 10-mention floor.
    w.add("Gamma", "location", "negative", 5, JAN_FEB)
    return w


def months(year: int, month_numbers: list[int], day: int = 15) -> list[date]:
    return [date(year, m, day) for m in month_numbers] + [
        date(year, m, day) + timedelta(days=2) for m in month_numbers
    ]
