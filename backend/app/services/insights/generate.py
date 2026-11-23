"""Generate and store insights: rules -> evidence -> template wording -> grounding check -> save."""

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.analytics.metrics import DataScope, Filters
from app.core.config import Settings
from app.models import Aspect, Insight, InsightEvidence, InsightProperty, Property, Review
from app.models.base import GenerationMethod
from app.services import analysis
from app.services.insights import evidence, grounding, rules, wording

logger = logging.getLogger(__name__)


@dataclass
class GenerationSummary:
    data_scope: str
    as_of: date | None
    created: int = 0
    replaced: int = 0
    rejected_by_validator: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    checked_property_aspects: int = 0
    below_mention_floor: int = 0
    comparisons_skipped_too_few: int = 0
    notes: list[str] = field(default_factory=list)


def scope_fingerprint(db: Session, data_scope: DataScope) -> dict[str, int | None]:
    """What the insights were computed from. If it changes, the insights are out of date."""
    run = analysis.latest_completed_run(db)
    reviews = (
        db.scalar(
            select(func.count())
            .select_from(Review)
            .where(*Filters(data_scope=data_scope).clauses())
        )
        or 0
    )
    return {"analysis_run_id": run.id if run else None, "reviews_in_scope": reviews}


def generate(db: Session, settings: Settings, data_scope: DataScope) -> GenerationSummary:
    """Replace the insights of one data scope with a fresh generation, in one transaction."""
    found = rules.find_candidates(db, settings, data_scope)
    summary = GenerationSummary(
        data_scope=data_scope,
        as_of=found.as_of,
        checked_property_aspects=found.checked_property_aspects,
        below_mention_floor=found.below_mention_floor,
        comparisons_skipped_too_few=found.comparisons_skipped_too_few,
    )
    if found.as_of is None:
        summary.notes.append(
            "There are no reviews in this data scope, so there is nothing to analyse."
        )

    names = {p.id: p.name for p in db.scalars(select(Property))}
    aspects = {a.key: a.id for a in db.scalars(select(Aspect))}
    run = analysis.latest_completed_run(db)
    fingerprint = scope_fingerprint(db, data_scope)
    low_floor = settings.min_aspect_mentions

    built: list[Insight] = []
    for candidate in found.candidates:
        review_ids = [rid for rid, _ in candidate.supporting]
        candidate.examples = evidence.select_examples(
            db, review_ids, candidate.aspect_key, candidate.stance
        )
        months = evidence.months_spanned([d for _, d in candidate.supporting])
        mentions = candidate.metrics.get("mentions", len(review_ids))
        strength = evidence.grade(len(review_ids), months, low_sample=mentions < low_floor)
        candidate.metrics["evidence"] = {
            "supporting_reviews": len(review_ids),
            "months_spanned": months,
            "strength_rule": (
                f"strong: {evidence.STRONG_MIN_REVIEWS}+ supporting reviews over "
                f"{evidence.STRONG_MIN_MONTHS}+ months; moderate: {evidence.MODERATE_MIN_REVIEWS}+"
            ),
        }
        candidate.metrics["generation"] = {
            "as_of": found.as_of.isoformat() if found.as_of else None,
            **fingerprint,
            "sentiment_engine": run.sentiment_engine if run else None,
            "lexicon_version": run.aspect_lexicon_version if run else None,
        }

        property_names = [names.get(pid, "") for pid in candidate.property_ids]
        text = wording.render(
            candidate.insight_type,
            aspect_key=candidate.aspect_key,
            aspect_name=candidate.aspect_name,
            property_names=property_names,
            metrics=candidate.metrics,
            period_start=candidate.period_start,
            period_end=candidate.period_end,
        )
        evidence_ids = {e["review_id"] for e in candidate.examples}
        check = grounding.check_grounding(
            text,
            candidate.metrics,
            cited_review_ids=evidence_ids,
            evidence_review_ids=evidence_ids,
            known_names=[
                *property_names,
                candidate.aspect_name,
                wording.inline_name(candidate.aspect_name),
            ],
        )
        if not check.ok or not review_ids:
            summary.rejected_by_validator += 1
            logger.warning(
                "Insight candidate rejected (%s): %s",
                candidate.insight_type.value,
                "; ".join(check.problems) or "no supporting reviews",
            )
            continue

        insight = Insight(
            analysis_run_id=run.id if run else None,
            insight_type=candidate.insight_type.value,
            scope=candidate.scope.value,
            data_scope=data_scope,
            aspect_id=aspects.get(candidate.aspect_key),
            title=text["title"][:200],
            explanation=text["explanation"],
            recommended_action=text["recommended_action"],
            supporting_review_count=len(review_ids),
            period_start=candidate.period_start,
            period_end=candidate.period_end,
            evidence_strength=strength.value,
            metrics=candidate.metrics,
            generation_method=GenerationMethod.TEMPLATE.value,
            properties=[InsightProperty(property_id=pid) for pid in candidate.property_ids],
            evidence=[
                InsightEvidence(review_id=e["review_id"], excerpt=e["excerpt"], rank=e["rank"])
                for e in candidate.examples
            ],
        )
        built.append(insight)

    # Replace only after everything was built, so a failure leaves the previous insights intact.
    try:
        old = db.scalars(select(Insight.id).where(Insight.data_scope == data_scope)).all()
        summary.replaced = len(old)
        if old:
            db.execute(delete(InsightEvidence).where(InsightEvidence.insight_id.in_(old)))
            db.execute(delete(InsightProperty).where(InsightProperty.insight_id.in_(old)))
            db.execute(delete(Insight).where(Insight.id.in_(old)))
        db.add_all(built)
        db.commit()
    except Exception:
        db.rollback()
        raise

    summary.created = len(built)
    summary.by_type = dict(Counter(i.insight_type for i in built))
    if found.as_of and not built:
        summary.notes.append(
            "No rule found enough evidence. That is a valid result, not an error: "
            "the rules need a minimum number of mentions before they say anything."
        )
    return summary
