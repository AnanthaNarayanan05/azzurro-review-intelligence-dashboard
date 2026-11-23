"""Supporting reviews, example sentences and the strength grade of an insight."""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import metrics
from app.models import Aspect, AspectMention
from app.models.base import EvidenceStrength, SentimentLabel

EXAMPLE_LIMIT = 10
STRONG_MIN_REVIEWS = 20
STRONG_MIN_MONTHS = 2
MODERATE_MIN_REVIEWS = 8
_CHUNK = 500


def supporting_reviews(
    db: Session, f: metrics.Filters, aspect_key: str, stance: SentimentLabel | None
) -> list[tuple[int, date]]:
    """Every review behind an insight: (id, date), newest first. It uses the same per-review aspect
    definition as the dashboard and the Reviews explorer, so the counts always agree."""
    sub = metrics.aspect_review_labels(f, aspect_key).subquery()
    stmt = select(sub.c.review_id, sub.c.review_date)
    if stance is SentimentLabel.NEGATIVE:
        stmt = stmt.where(sub.c.balance < 0)
    elif stance is SentimentLabel.POSITIVE:
        stmt = stmt.where(sub.c.balance > 0)
    stmt = stmt.order_by(sub.c.review_date.desc(), sub.c.review_id.desc())
    return [(rid, rdate) for rid, rdate in db.execute(stmt)]


def months_spanned(dates: list[date]) -> int:
    return len({(d.year, d.month) for d in dates})


def grade(supporting: int, months: int, low_sample: bool) -> EvidenceStrength:
    if supporting >= STRONG_MIN_REVIEWS and months >= STRONG_MIN_MONTHS and not low_sample:
        return EvidenceStrength.STRONG
    if supporting >= MODERATE_MIN_REVIEWS:
        return EvidenceStrength.MODERATE
    return EvidenceStrength.LIMITED


def _strongest_per_review(rows: list[tuple[int, str, float]]) -> list[tuple[int, str]]:
    best: dict[int, tuple[float, str]] = {}
    for review_id, text, score in rows:
        magnitude = abs(score)
        if review_id not in best or magnitude > best[review_id][0]:
            best[review_id] = (magnitude, text)
    ordered = sorted(best.items(), key=lambda item: (-item[1][0], item[0]))
    return [(review_id, text) for review_id, (_, text) in ordered]


def _prefer_distinct(candidates: list[tuple[int, str]], limit: int) -> list[tuple[int, str]]:
    """Take distinct wording first so the examples are not ten copies of one sentence."""
    chosen: list[tuple[int, str]] = []
    seen: set[str] = set()
    for review_id, text in candidates:
        if len(chosen) < limit and text.casefold() not in seen:
            chosen.append((review_id, text))
            seen.add(text.casefold())
    for item in candidates:
        if len(chosen) < limit and item not in chosen:
            chosen.append(item)
    return chosen


def select_examples(
    db: Session,
    review_ids: list[int],
    aspect_key: str,
    stance: SentimentLabel | None,
    limit: int = EXAMPLE_LIMIT,
) -> list[dict[str, Any]]:
    """Up to `limit` real sentences, one per review, strongest first. With no stance (split opinion)
    half are positive and half negative."""
    if not review_ids:
        return []
    rows: dict[str, list[tuple[int, str, float]]] = {"positive": [], "negative": [], "neutral": []}
    for start in range(0, len(review_ids), _CHUNK):
        chunk = review_ids[start : start + _CHUNK]
        stmt = (
            select(
                AspectMention.review_id,
                AspectMention.evidence_text,
                AspectMention.score,
                AspectMention.sentiment_label,
            )
            .join(Aspect, Aspect.id == AspectMention.aspect_id)
            .where(Aspect.key == aspect_key, AspectMention.review_id.in_(chunk))
        )
        for review_id, text, score, label in db.execute(stmt):
            rows[label].append((review_id, text, float(score)))

    if stance is not None:
        picked = _prefer_distinct(_strongest_per_review(rows[stance.value]), limit)
    else:
        half = limit // 2
        positive = _prefer_distinct(_strongest_per_review(rows["positive"]), half)
        negative = _prefer_distinct(_strongest_per_review(rows["negative"]), limit - half)
        interleaved: list[tuple[int, str]] = []
        for pair in zip(positive, negative, strict=False):
            interleaved.extend(pair)
        interleaved.extend(positive[len(negative) :] + negative[len(positive) :])
        picked, seen_ids = [], set()
        for item in interleaved:
            if item[0] not in seen_ids:
                seen_ids.add(item[0])
                picked.append(item)

    return [
        {"review_id": review_id, "excerpt": text, "rank": rank}
        for rank, (review_id, text) in enumerate(picked, start=1)
    ]
