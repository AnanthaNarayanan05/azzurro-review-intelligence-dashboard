"""Metrics computed from reviews and their stored NLP results.

Definitions (also in docs/AI_ANALYTICS.md):
- Average rating: mean of reviews that have a rating (0-10). Reviews without one are counted as
`missing`.
- Sentiment shares: denominator = reviews with a stored overall sentiment (`analysed`), never all
reviews.
- Aspect counts: a review counts once per aspect. Its label for that aspect is the sign of
  (positive mentions - negative mentions); a tie is neutral.
- Every metric reports its sample size `n`, how many were `missing`, and a `low_sample` flag.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from app.analytics import stats
from app.core.config import Settings
from app.models import Aspect, AspectMention, Property, Review, SentimentResult
from app.models.base import AnalysisStatus, SentimentLabel, TextSegment

DataScope = Literal["genuine", "synthetic", "all"]
RATING_BINS = 10  # bin k covers [k, k+1); the last bin also includes 10


@dataclass(frozen=True)
class Filters:
    property_ids: tuple[int, ...] | None = None
    date_from: date | None = None
    date_to: date | None = None
    data_scope: DataScope = "genuine"

    def clauses(self) -> list[Any]:
        # Deactivated properties are excluded from every figure ("Active (included in analytics)").
        clauses: list[Any] = [
            Review.property_id.in_(select(Property.id).where(Property.is_active.is_(True)))
        ]
        if self.property_ids:
            clauses.append(Review.property_id.in_(self.property_ids))
        if self.date_from:
            clauses.append(Review.review_date >= self.date_from)
        if self.date_to:
            clauses.append(Review.review_date <= self.date_to)
        if self.data_scope == "genuine":
            clauses.append(Review.is_synthetic.is_(False))
        elif self.data_scope == "synthetic":
            clauses.append(Review.is_synthetic.is_(True))
        return clauses


def metric(value: float | None, n: int, *, missing: int = 0, min_sample: int) -> dict[str, Any]:
    """A number never travels without its sample size and a low-sample flag."""
    return {
        "value": stats.round_or_none(value, 2),
        "n": n,
        "missing": missing,
        "low_sample": n < min_sample,
    }


def _share(count: int, denominator: int) -> float | None:
    return round(count / denominator, 4) if denominator else None


# ------------------------------------------------------------------------------------------
# Data scope
# ------------------------------------------------------------------------------------------
def data_summary(db: Session, f: Filters) -> dict[str, Any]:
    active = Review.property_id.in_(select(Property.id).where(Property.is_active.is_(True)))
    rows = dict(
        db.execute(
            select(Review.is_synthetic, func.count()).where(active).group_by(Review.is_synthetic)
        ).all()
    )
    low, high = db.execute(
        select(func.min(Review.review_date), func.max(Review.review_date)).where(*f.clauses())
    ).one()
    return {
        "scope": f.data_scope,
        "genuine_reviews": rows.get(False, 0),
        "synthetic_reviews": rows.get(True, 0),
        "mixed": f.data_scope == "all" and rows.get(True, 0) > 0 and rows.get(False, 0) > 0,
        "first_review_date": low.isoformat() if low else None,
        "last_review_date": high.isoformat() if high else None,
    }


# ------------------------------------------------------------------------------------------
# Ratings
# ------------------------------------------------------------------------------------------
def _rating_rows(db: Session, f: Filters) -> list[tuple[int, float | None]]:
    stmt = select(Review.property_id, Review.rating).where(*f.clauses())
    return [(pid, None if r is None else float(r)) for pid, r in db.execute(stmt)]


def _rating_block(
    ratings: list[float | None], settings: Settings, *, with_ci: bool = False
) -> dict:
    present = [r for r in ratings if r is not None]
    block = metric(
        stats.mean(present),
        len(present),
        missing=len(ratings) - len(present),
        min_sample=settings.min_sample_comparison,
    )
    if with_ci:
        interval = stats.mean_interval(present)
        block["ci_low"] = stats.round_or_none(interval[0]) if interval else None
        block["ci_high"] = stats.round_or_none(interval[1]) if interval else None
    return block


def _rating_distribution(ratings: list[float | None]) -> list[dict[str, Any]]:
    counts = [0] * RATING_BINS
    for r in ratings:
        if r is not None:
            counts[min(int(r), RATING_BINS - 1)] += 1
    total = sum(counts)
    return [
        {
            "label": f"{k}-{k + 1}" if k < RATING_BINS - 1 else f"{k}-10",
            "from": k,
            "to": k + 1,
            "n": counts[k],
            "share": _share(counts[k], total),
        }
        for k in range(RATING_BINS)
    ]


# ------------------------------------------------------------------------------------------
# Sentiment
# ------------------------------------------------------------------------------------------
def _sentiment_counts(db: Session, f: Filters, group_by_property: bool = False):
    columns = [Review.property_id] if group_by_property else []
    stmt = (
        select(*columns, SentimentResult.label, func.count())
        .join(Review, Review.id == SentimentResult.review_id)
        .where(SentimentResult.segment == TextSegment.OVERALL.value, *f.clauses())
        .group_by(*columns, SentimentResult.label)
    )
    return db.execute(stmt).all()


def _sentiment_block(
    counts: dict[str, int], status_counts: dict[str | None, int]
) -> dict[str, Any]:
    analysed = sum(counts.values())
    return {
        "analysed_n": analysed,
        "positive": counts.get(SentimentLabel.POSITIVE.value, 0),
        "neutral": counts.get(SentimentLabel.NEUTRAL.value, 0),
        "negative": counts.get(SentimentLabel.NEGATIVE.value, 0),
        "positive_share": _share(counts.get(SentimentLabel.POSITIVE.value, 0), analysed),
        "neutral_share": _share(counts.get(SentimentLabel.NEUTRAL.value, 0), analysed),
        "negative_share": _share(counts.get(SentimentLabel.NEGATIVE.value, 0), analysed),
        "share_denominator": "reviews with analysed text",
        "not_analysed": {
            "no_text": status_counts.get(AnalysisStatus.NO_TEXT.value, 0),
            "non_english": status_counts.get(AnalysisStatus.NON_ENGLISH.value, 0),
            "pending": status_counts.get(None, 0),
        },
    }


def _status_counts(db: Session, f: Filters, group_by_property: bool = False):
    columns = [Review.property_id] if group_by_property else []
    stmt = (
        select(*columns, Review.analysis_status, func.count())
        .where(*f.clauses())
        .group_by(*columns, Review.analysis_status)
    )
    return db.execute(stmt).all()


# ------------------------------------------------------------------------------------------
# Aspects
# ------------------------------------------------------------------------------------------
def aspect_review_labels(f: Filters, aspect_key: str | None = None) -> Select:
    """One row per (review, aspect) with `balance` = positive mentions - negative mentions."""
    balance = func.sum(
        case(
            (AspectMention.sentiment_label == SentimentLabel.POSITIVE.value, 1),
            (AspectMention.sentiment_label == SentimentLabel.NEGATIVE.value, -1),
            else_=0,
        )
    ).label("balance")
    stmt = (
        select(
            AspectMention.review_id.label("review_id"),
            AspectMention.aspect_id.label("aspect_id"),
            Review.property_id.label("property_id"),
            Review.review_date.label("review_date"),
            balance,
        )
        .join(Review, Review.id == AspectMention.review_id)
        .join(Aspect, Aspect.id == AspectMention.aspect_id)
        .where(Aspect.is_active.is_(True), *f.clauses())
        .group_by(
            AspectMention.review_id, AspectMention.aspect_id, Review.property_id, Review.review_date
        )
    )
    if aspect_key:
        stmt = stmt.where(Aspect.key == aspect_key)
    return stmt


def _analysed_review_count(db: Session, f: Filters) -> dict[int, int]:
    stmt = (
        select(Review.property_id, func.count())
        .where(Review.analysis_status == AnalysisStatus.ANALYSED.value, *f.clauses())
        .group_by(Review.property_id)
    )
    return dict(db.execute(stmt).all())


def _aspect_rows(db: Session, f: Filters, settings: Settings, *, by_property: bool) -> list[dict]:
    sub = aspect_review_labels(f).subquery()
    group_cols = [sub.c.aspect_id] + ([sub.c.property_id] if by_property else [])
    stmt = select(
        *group_cols,
        func.count().label("reviews"),
        func.sum(case((sub.c.balance > 0, 1), else_=0)).label("positive"),
        func.sum(case((sub.c.balance < 0, 1), else_=0)).label("negative"),
        func.sum(case((sub.c.balance == 0, 1), else_=0)).label("neutral"),
    ).group_by(*group_cols)
    aspects = {a.id: a for a in db.scalars(select(Aspect).where(Aspect.is_active.is_(True)))}
    analysed = _analysed_review_count(db, f)
    total_analysed = sum(analysed.values())
    out = []
    for row in db.execute(stmt):
        aspect = aspects.get(row.aspect_id)
        if aspect is None:
            continue
        denominator = analysed.get(row.property_id, 0) if by_property else total_analysed
        reviews = int(row.reviews)
        item = {
            "aspect": aspect.key,
            "display_name": aspect.display_name,
            "mentions": reviews,
            "positive": int(row.positive or 0),
            "neutral": int(row.neutral or 0),
            "negative": int(row.negative or 0),
            "positive_share": _share(int(row.positive or 0), reviews),
            "negative_share": _share(int(row.negative or 0), reviews),
            "mention_rate": _share(reviews, denominator),
            "low_sample": reviews < settings.min_aspect_mentions,
        }
        if by_property:
            item["property_id"] = row.property_id
        out.append(item)
    out.sort(key=lambda a: (-a["mentions"], a["aspect"]))
    return out


def aspect_summary(db: Session, f: Filters, settings: Settings) -> dict[str, Any]:
    items = _aspect_rows(db, f, settings, by_property=False)
    return {
        "items": items,
        "analysed_reviews": sum(_analysed_review_count(db, f).values()),
        "min_mentions": settings.min_aspect_mentions,
        "definition": (
            "A review counts once per aspect. Its label is the sign of "
            "(positive - negative mentions); a tie is neutral. Shares use mentions of that aspect "
            "as the denominator; mention_rate uses reviews with analysed text."
        ),
    }


def _top_aspects(items: list[dict], key: str, settings: Settings, limit: int = 3) -> list[dict]:
    """Strongest praise or criticism, only from aspects with enough mentions to be trusted."""
    eligible = [i for i in items if not i["low_sample"] and i[key] > 0]
    return sorted(eligible, key=lambda i: (-i[key], -i["mentions"], i["aspect"]))[:limit]


def aspect_examples(
    db: Session, f: Filters, aspect_key: str, label: SentimentLabel, limit: int = 3
) -> list[dict[str, Any]]:
    """Real sentences from real reviews: the evidence behind an aspect's numbers."""
    stmt = (
        select(AspectMention, Review.property_id, Review.review_date, Review.is_synthetic)
        .join(Review, Review.id == AspectMention.review_id)
        .join(Aspect, Aspect.id == AspectMention.aspect_id)
        .where(Aspect.key == aspect_key, AspectMention.sentiment_label == label.value, *f.clauses())
        .order_by(func.abs(AspectMention.score).desc(), AspectMention.review_id)
        .limit(limit)
    )
    return [
        {
            "review_id": m.review_id,
            "property_id": pid,
            "review_date": rdate.isoformat(),
            "is_synthetic": synthetic,
            "sentiment": m.sentiment_label,
            "evidence_text": m.evidence_text,
            "matched_term": m.matched_term,
            "source_field": m.source_field,
        }
        for m, pid, rdate, synthetic in db.execute(stmt)
    ]


# ------------------------------------------------------------------------------------------
# Overview, property, comparison
# ------------------------------------------------------------------------------------------
def _property_names(db: Session) -> dict[int, Property]:
    return {p.id: p for p in db.scalars(select(Property).order_by(Property.name))}


def overview(db: Session, f: Filters, settings: Settings) -> dict[str, Any]:
    rating_rows = _rating_rows(db, f)
    ratings = [r for _, r in rating_rows]
    sentiment_counts: dict[str, int] = defaultdict(int)
    for label, n in ((row[0], row[1]) for row in _sentiment_counts(db, f)):
        sentiment_counts[label] += n
    status_counts = {status: n for status, n in (tuple(r) for r in _status_counts(db, f))}

    per_property_ratings: dict[int, list[float | None]] = defaultdict(list)
    for pid, rating in rating_rows:
        per_property_ratings[pid].append(rating)
    names = _property_names(db)
    properties = []
    for pid, values in per_property_ratings.items():
        prop = names.get(pid)
        properties.append(
            {
                "property_id": pid,
                "name": prop.name if prop else f"Property {pid}",
                "reviews": len(values),
                "rating": _rating_block(values, settings),
            }
        )
    properties.sort(key=lambda p: p["name"])

    aspects = aspect_summary(db, f, settings)
    return {
        "dataset": data_summary(db, f),
        "reviews": {"n": len(ratings), "with_text_analysis": sum(sentiment_counts.values())},
        "min_sample": settings.min_sample_comparison,
        "rating": {
            **_rating_block(ratings, settings),
            "distribution": _rating_distribution(ratings),
            "scale": "0-10",
        },
        "sentiment": _sentiment_block(sentiment_counts, status_counts),
        "properties": properties,
        "aspects": {
            "most_praised": _top_aspects(aspects["items"], "positive", settings),
            "most_criticised": _top_aspects(aspects["items"], "negative", settings),
            "min_mentions": settings.min_aspect_mentions,
        },
    }


def property_detail(
    db: Session, property_id: int, f: Filters, settings: Settings
) -> dict[str, Any]:
    scoped = Filters((property_id,), f.date_from, f.date_to, f.data_scope)
    result = overview(db, scoped, settings)
    items = aspect_summary(db, scoped, settings)["items"]
    praise = _top_aspects(items, "positive", settings)
    complaints = _top_aspects(items, "negative", settings)
    result["top_praise"] = [
        {**a, "examples": aspect_examples(db, scoped, a["aspect"], SentimentLabel.POSITIVE)}
        for a in praise
    ]
    result["top_complaints"] = [
        {**a, "examples": aspect_examples(db, scoped, a["aspect"], SentimentLabel.NEGATIVE)}
        for a in complaints
    ]
    return result


def comparison(db: Session, f: Filters, settings: Settings) -> dict[str, Any]:
    names = _property_names(db)
    wanted = set(f.property_ids) if f.property_ids else set(names)

    ratings_by_property: dict[int, list[float | None]] = defaultdict(list)
    for pid, rating in _rating_rows(db, f):
        ratings_by_property[pid].append(rating)
    sentiment_by_property: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for pid, label, n in _sentiment_counts(db, f, group_by_property=True):
        sentiment_by_property[pid][label] += n
    status_by_property: dict[int, dict[str | None, int]] = defaultdict(dict)
    for pid, status, n in _status_counts(db, f, group_by_property=True):
        status_by_property[pid][status] = n
    aspect_by_property: dict[int, list[dict]] = defaultdict(list)
    for item in _aspect_rows(db, f, settings, by_property=True):
        aspect_by_property[item["property_id"]].append(item)

    rows = []
    for pid in sorted(wanted, key=lambda i: names[i].name if i in names else ""):
        prop = names.get(pid)
        if prop is None or not prop.is_active:
            continue
        values = ratings_by_property.get(pid, [])
        rows.append(
            {
                "property_id": pid,
                "name": prop.name,
                "reviews": len(values),
                "rating": _rating_block(values, settings, with_ci=True),
                "sentiment": _sentiment_block(sentiment_by_property[pid], status_by_property[pid]),
                "aspects": sorted(aspect_by_property.get(pid, []), key=lambda a: a["aspect"]),
            }
        )

    return {
        "dataset": data_summary(db, f),
        "properties": rows,
        "rating_ranking": _rating_ranking(rows, ratings_by_property, settings),
        "min_sample": settings.min_sample_comparison,
        "min_aspect_mentions": settings.min_aspect_mentions,
        "note": (
            "Best and worst are named only when at least two properties have enough rated "
            "reviews AND their 95% intervals do not overlap. Otherwise the difference could be "
            "chance."
        ),
    }


def _rating_ranking(
    rows: list[dict], ratings: dict[int, list[float | None]], settings: Settings
) -> dict:
    eligible = [
        r for r in rows if not r["rating"]["low_sample"] and r["rating"]["ci_low"] is not None
    ]
    if len(eligible) < 2:
        return {
            "status": "insufficient_data",
            "reason": (
                f"Fewer than two properties have {settings.min_sample_comparison} "
                "or more rated reviews."
            ),
            "best": None,
            "worst": None,
            "ordered": [],
        }
    ordered = sorted(eligible, key=lambda r: -r["rating"]["value"])
    best, worst = ordered[0], ordered[-1]
    separated = best["rating"]["ci_low"] > worst["rating"]["ci_high"]
    return {
        "status": "ranked" if separated else "difference_not_significant",
        "reason": None
        if separated
        else "The intervals of the highest and lowest property overlap.",
        "best": best["property_id"] if separated else None,
        "worst": worst["property_id"] if separated else None,
        "ordered": [r["property_id"] for r in ordered],
    }


# ------------------------------------------------------------------------------------------
# Trends
# ------------------------------------------------------------------------------------------
TrendMetric = Literal[
    "volume",
    "avg_rating",
    "sentiment_positive_share",
    "sentiment_negative_share",
    "aspect_negative_share",
]
Granularity = Literal["week", "month"]
DEFAULT_WINDOW = {"week": 4, "month": 3}
# Beyond statistical significance a change must also be big enough to matter in practice.
MIN_RATING_CHANGE = 0.3  # rating points on the 0-10 scale
MIN_SHARE_CHANGE = 0.05  # 5 percentage points


def bucket_start(day: date, granularity: Granularity) -> date:
    """Weeks run Monday to Sunday (the Monday is the bucket's label). Review dates are calendar
    dates as
    supplied by the source; no time-zone conversion is applied."""
    if granularity == "week":
        return day - timedelta(days=day.weekday())
    return day.replace(day=1)


def bucket_end(start: date, granularity: Granularity) -> date:
    """Last day of the bucket (inclusive)."""
    if granularity == "week":
        return start + timedelta(days=6)
    nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return nxt - timedelta(days=1)


def _next_bucket(start: date, granularity: Granularity) -> date:
    return bucket_end(start, granularity) + timedelta(days=1)


def _observations(
    db: Session, f: Filters, metric_name: TrendMetric, aspect_key: str | None
) -> list[tuple[date, float]]:
    if metric_name == "volume":
        return [(d, 1.0) for (d,) in db.execute(select(Review.review_date).where(*f.clauses()))]
    if metric_name == "avg_rating":
        stmt = select(Review.review_date, Review.rating).where(
            Review.rating.is_not(None), *f.clauses()
        )
        return [(d, float(r)) for d, r in db.execute(stmt)]
    if metric_name in ("sentiment_positive_share", "sentiment_negative_share"):
        target = "positive" if metric_name == "sentiment_positive_share" else "negative"
        stmt = (
            select(Review.review_date, SentimentResult.label)
            .join(Review, Review.id == SentimentResult.review_id)
            .where(SentimentResult.segment == TextSegment.OVERALL.value, *f.clauses())
        )
        return [(d, 1.0 if label == target else 0.0) for d, label in db.execute(stmt)]
    sub = aspect_review_labels(f, aspect_key).subquery()
    stmt = select(sub.c.review_date, sub.c.balance)
    return [(d, 1.0 if balance < 0 else 0.0) for d, balance in db.execute(stmt)]


def _aggregate(values: list[float], metric_name: TrendMetric) -> float | None:
    if metric_name == "volume":
        return float(len(values))
    return stats.mean(values)


def trends(
    db: Session,
    f: Filters,
    settings: Settings,
    *,
    metric_name: TrendMetric,
    granularity: Granularity,
    aspect_key: str | None,
    window: int | None,
    as_of: date,
) -> dict[str, Any]:
    window = window or DEFAULT_WINDOW[granularity]
    observations = _observations(db, f, metric_name, aspect_key)
    by_bucket: dict[date, list[float]] = defaultdict(list)
    for day, value in observations:
        if day <= as_of:
            by_bucket[bucket_start(day, granularity)].append(value)

    # Only complete periods are compared: a half-finished week would always look like a drop.
    last_complete = None
    cursor = bucket_start(as_of, granularity)
    if bucket_end(cursor, granularity) <= as_of:
        last_complete = cursor
    else:
        last_complete = bucket_start(cursor - timedelta(days=1), granularity)

    series: list[dict[str, Any]] = []
    if by_bucket:
        start, current = min(by_bucket), min(by_bucket)
        end = max(max(by_bucket), last_complete)
        while current <= end:
            values = by_bucket.get(current, [])
            n = len(values)
            series.append(
                {
                    "period_start": current.isoformat(),
                    "period_end": bucket_end(current, granularity).isoformat(),
                    "n": n,
                    "value": stats.round_or_none(_aggregate(values, metric_name), 4),
                    "complete": bucket_end(current, granularity) <= as_of,
                    "low_sample": n < settings.min_sample_trend_window and metric_name != "volume",
                }
            )
            current = _next_bucket(current, granularity)
        del start

    change = _trend_change(by_bucket, metric_name, granularity, window, last_complete, settings)
    return {
        "metric": metric_name,
        "granularity": granularity,
        "aspect": aspect_key,
        "as_of": as_of.isoformat(),
        "window_periods": window,
        "min_sample": settings.min_sample_trend_window,
        "week_definition": "Monday to Sunday" if granularity == "week" else "calendar month",
        "series": series,
        "change": change,
        "dataset": data_summary(db, f),
    }


def _window_values(
    by_bucket: dict[date, list[float]],
    last: date,
    periods: int,
    granularity: Granularity,
    offset: int,
) -> tuple[list[float], date, date]:
    """Observations of `periods` complete buckets ending `offset` buckets before `last`."""
    end = last
    for _ in range(offset):
        end = bucket_start(end - timedelta(days=1), granularity)
    start = end
    for _ in range(periods - 1):
        start = bucket_start(start - timedelta(days=1), granularity)
    values: list[float] = []
    cursor = start
    while cursor <= end:
        values.extend(by_bucket.get(cursor, []))
        cursor = _next_bucket(cursor, granularity)
    return values, start, bucket_end(end, granularity)


def _trend_change(
    by_bucket: dict[date, list[float]],
    metric_name: TrendMetric,
    granularity: Granularity,
    window: int,
    last_complete: date,
    settings: Settings,
) -> dict[str, Any]:
    recent, r_start, r_end = _window_values(by_bucket, last_complete, window, granularity, 0)
    previous, p_start, p_end = _window_values(by_bucket, last_complete, window, granularity, window)
    base = {
        "recent_window": {"from": r_start.isoformat(), "to": r_end.isoformat(), "n": len(recent)},
        "previous_window": {
            "from": p_start.isoformat(),
            "to": p_end.isoformat(),
            "n": len(previous),
        },
    }
    if metric_name == "volume":
        # Volume is a count, not a sample: report the change without a significance claim.
        change = len(recent) - len(previous)
        return base | {
            "status": "descriptive",
            "recent_value": len(recent),
            "previous_value": len(previous),
            "difference": change,
            "relative_change": _share(change, len(previous)),
        }

    minimum = settings.min_sample_trend_window
    if len(recent) < minimum or len(previous) < minimum:
        return base | {
            "status": "insufficient_data",
            "reason": f"Each window needs at least {minimum} observations.",
        }

    if metric_name == "avg_rating":
        interval = stats.difference_of_means(recent, previous)
        practical = MIN_RATING_CHANGE
        recent_value, previous_value = stats.mean(recent), stats.mean(previous)
    else:
        interval = stats.difference_of_proportions(
            int(sum(recent)), len(recent), int(sum(previous)), len(previous)
        )
        practical = MIN_SHARE_CHANGE
        recent_value, previous_value = stats.mean(recent), stats.mean(previous)
    if interval is None:
        return base | {"status": "insufficient_data", "reason": "Not enough variation to estimate."}

    meaningful = stats.excludes_zero(interval) and abs(interval["difference"]) >= practical
    direction = "no_significant_change"
    if meaningful:
        direction = "increase" if interval["difference"] > 0 else "decrease"
    return base | {
        "status": direction,
        "recent_value": stats.round_or_none(recent_value, 4),
        "previous_value": stats.round_or_none(previous_value, 4),
        "difference": stats.round_or_none(interval["difference"], 4),
        "ci_low": stats.round_or_none(interval["ci_low"], 4),
        "ci_high": stats.round_or_none(interval["ci_high"], 4),
        "practical_threshold": practical,
    }
