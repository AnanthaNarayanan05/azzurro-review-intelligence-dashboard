"""Rules that turn stored analytics into insight candidates.

Every threshold is here, returned with each insight (`metrics.thresholds`) and documented in
docs/AI_ANALYTICS.md section 8. They are starting points, not validated values, and are not tuned to
any dataset. Property and aspect names never appear in this file: both come from the data.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import metrics, stats
from app.analytics.metrics import MIN_SHARE_CHANGE, DataScope, Filters
from app.core.config import Settings
from app.models import Property
from app.models.base import InsightScope, InsightType, SentimentLabel
from app.services.insights import evidence

COMPLAINT_NEGATIVE_SHARE = 0.40
STRENGTH_POSITIVE_SHARE = 0.80
OPPORTUNITY_MIN_SHARE = 0.30  # each side of a split opinion must reach this share
CONFIDENCE_PERCENT = 95


@dataclass(frozen=True)
class Thresholds:
    min_descriptive: int  # mentions needed for rules that only count and compare shares
    min_inferential: int  # observations per side for rules that claim a real difference
    complaint_negative_share: float = COMPLAINT_NEGATIVE_SHARE
    strength_positive_share: float = STRENGTH_POSITIVE_SHARE
    opportunity_min_share: float = OPPORTUNITY_MIN_SHARE
    min_share_difference: float = MIN_SHARE_CHANGE
    trend_granularity: str = "month"

    @classmethod
    def from_settings(cls, settings: Settings) -> "Thresholds":
        return cls(
            min_descriptive=settings.min_aspect_mentions,
            min_inferential=settings.min_sample_comparison,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "min_mentions": self.min_descriptive,
            "min_observations_per_side": self.min_inferential,
            "complaint_negative_share": self.complaint_negative_share,
            "strength_positive_share": self.strength_positive_share,
            "opportunity_min_share": self.opportunity_min_share,
            "min_share_difference": self.min_share_difference,
            "trend_granularity": self.trend_granularity,
        }


@dataclass
class Candidate:
    insight_type: InsightType
    scope: InsightScope
    aspect_key: str
    aspect_name: str
    property_ids: list[int]
    period_start: date
    period_end: date
    stance: SentimentLabel | None
    metrics: dict[str, Any]
    supporting: list[tuple[int, date]] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Discovery:
    candidates: list[Candidate] = field(default_factory=list)
    as_of: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    checked_property_aspects: int = 0
    below_mention_floor: int = 0
    comparisons_skipped_too_few: int = 0


def _filter_block(
    property_ids: list[int],
    aspect: str,
    stance: SentimentLabel | None,
    start: date,
    end: date,
    scope: DataScope,
) -> dict[str, Any]:
    """The exact filter that reproduces the supporting reviews in the Reviews explorer."""
    return {
        "property_ids": sorted(property_ids),
        "aspect": aspect,
        "aspect_sentiment": stance.value if stance else None,
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "data_scope": scope,
    }


def _count_block(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "mentions": row["mentions"],
        "positive": row["positive"],
        "neutral": row["neutral"],
        "negative": row["negative"],
        "positive_share": row["positive_share"],
        "negative_share": row["negative_share"],
    }


def find_candidates(db: Session, settings: Settings, data_scope: DataScope) -> Discovery:
    base = Filters(data_scope=data_scope)
    summary = metrics.data_summary(db, base)
    found = Discovery()
    if not summary["first_review_date"]:
        return found
    start = date.fromisoformat(summary["first_review_date"])
    end = date.fromisoformat(summary["last_review_date"])
    found.as_of, found.period_start, found.period_end = end, start, end

    th = Thresholds.from_settings(settings)
    names = {p.id: p.name for p in db.scalars(select(Property))}
    rows = metrics.aspect_rows(db, base, settings, by_property=True)
    totals = {r["aspect"]: r for r in metrics.aspect_rows(db, base, settings, by_property=False)}

    def candidate(
        kind: InsightType,
        scope: InsightScope,
        row: dict[str, Any],
        property_ids: list[int],
        stance: SentimentLabel | None,
        extra: dict[str, Any],
        window: tuple[date, date] | None = None,
    ) -> Candidate:
        period = window or (start, end)
        filters = _filter_block(property_ids, row["aspect"], stance, *period, data_scope)
        f = Filters(tuple(property_ids), period[0], period[1], data_scope)
        supporting = evidence.supporting_reviews(db, f, row["aspect"], stance)
        return Candidate(
            insight_type=kind,
            scope=scope,
            aspect_key=row["aspect"],
            aspect_name=row["display_name"],
            property_ids=sorted(property_ids),
            period_start=period[0],
            period_end=period[1],
            stance=stance,
            metrics={
                "rule": kind.value,
                **extra,
                "thresholds": th.as_dict(),
                "filters": filters,
            },
            supporting=supporting,
        )

    complaints: dict[str, list[tuple[dict[str, Any], Candidate]]] = defaultdict(list)

    for row in rows:
        found.checked_property_aspects += 1
        pid = row["property_id"]
        if row["mentions"] < th.min_descriptive:
            found.below_mention_floor += 1
            continue
        counts = _count_block(row)

        if (
            row["negative"] >= th.min_descriptive
            and (row["negative_share"] or 0) >= th.complaint_negative_share
        ):
            made = candidate(
                InsightType.RECURRING_COMPLAINT,
                InsightScope.PROPERTY,
                row,
                [pid],
                SentimentLabel.NEGATIVE,
                counts,
            )
            found.candidates.append(made)
            complaints[row["aspect"]].append((row, made))

        if (row["positive_share"] or 0) >= th.strength_positive_share:
            found.candidates.append(
                candidate(
                    InsightType.STRENGTH,
                    InsightScope.PROPERTY,
                    row,
                    [pid],
                    SentimentLabel.POSITIVE,
                    counts,
                )
            )

        negative_share = row["negative_share"] or 0
        if (
            th.opportunity_min_share <= negative_share < th.complaint_negative_share
            and (row["positive_share"] or 0) >= th.opportunity_min_share
        ):
            found.candidates.append(
                candidate(InsightType.OPPORTUNITY, InsightScope.PROPERTY, row, [pid], None, counts)
            )

        # Inferential rules: only with enough observations for the 95% intervals to hold.
        total = totals.get(row["aspect"])
        if total is None:
            continue
        rest_n = total["mentions"] - row["mentions"]
        rest_negative = total["negative"] - row["negative"]
        if row["mentions"] < th.min_inferential or rest_n < th.min_inferential:
            found.comparisons_skipped_too_few += 1
        else:
            diff = stats.difference_of_proportions(
                row["negative"], row["mentions"], rest_negative, rest_n
            )
            if diff and stats.excludes_zero(diff) and diff["difference"] >= th.min_share_difference:
                found.candidates.append(
                    candidate(
                        InsightType.PROPERTY_ISSUE,
                        InsightScope.PROPERTY,
                        row,
                        [pid],
                        SentimentLabel.NEGATIVE,
                        counts
                        | {
                            "rest": {
                                "mentions": rest_n,
                                "negative": rest_negative,
                                "negative_share": round(rest_negative / rest_n, 4),
                            },
                            "difference": stats.round_or_none(diff["difference"], 4),
                            "ci_low": stats.round_or_none(diff["ci_low"], 4),
                            "ci_high": stats.round_or_none(diff["ci_high"], 4),
                            "confidence_percent": CONFIDENCE_PERCENT,
                        },
                    )
                )

        if row["mentions"] < 2 * settings.min_sample_trend_window:
            found.comparisons_skipped_too_few += 1
        else:
            trend = metrics.trends(
                db,
                Filters((pid,), data_scope=data_scope),
                settings,
                metric_name="aspect_negative_share",
                granularity=th.trend_granularity,  # type: ignore[arg-type]
                aspect_key=row["aspect"],
                window=None,
                as_of=end,
            )["change"]
            if trend["status"] == "insufficient_data":
                found.comparisons_skipped_too_few += 1
            elif trend["status"] == "increase":
                window = (
                    date.fromisoformat(trend["recent_window"]["from"]),
                    date.fromisoformat(trend["recent_window"]["to"]),
                )
                found.candidates.append(
                    candidate(
                        InsightType.EMERGING_NEGATIVE_TREND,
                        InsightScope.PROPERTY,
                        row,
                        [pid],
                        SentimentLabel.NEGATIVE,
                        {
                            "recent_window": trend["recent_window"],
                            "previous_window": trend["previous_window"],
                            "recent_share": trend["recent_value"],
                            "previous_share": trend["previous_value"],
                            "difference": trend["difference"],
                            "ci_low": trend["ci_low"],
                            "ci_high": trend["ci_high"],
                            "practical_threshold": trend["practical_threshold"],
                            "confidence_percent": CONFIDENCE_PERCENT,
                        },
                        window=window,
                    )
                )

    # The same complaint at two or more properties is a portfolio-level issue.
    for entries in complaints.values():
        if len(entries) < 2:
            continue
        ids = [r["property_id"] for r, _ in entries]
        mentions = sum(r["mentions"] for r, _ in entries)
        negative = sum(r["negative"] for r, _ in entries)
        positive = sum(r["positive"] for r, _ in entries)
        neutral = sum(r["neutral"] for r, _ in entries)
        first_row = entries[0][0]
        found.candidates.append(
            candidate(
                InsightType.CROSS_PROPERTY_ISSUE,
                InsightScope.MULTI_PROPERTY,
                first_row,
                ids,
                SentimentLabel.NEGATIVE,
                {
                    "mentions": mentions,
                    "positive": positive,
                    "neutral": neutral,
                    "negative": negative,
                    "positive_share": round(positive / mentions, 4),
                    "negative_share": round(negative / mentions, 4),
                    "property_count": len(ids),
                    "per_property": [
                        {
                            "property_id": r["property_id"],
                            "name": names.get(r["property_id"], ""),
                            "mentions": r["mentions"],
                            "negative": r["negative"],
                            "negative_share": r["negative_share"],
                        }
                        for r, _ in entries
                    ],
                },
            )
        )
    return found
