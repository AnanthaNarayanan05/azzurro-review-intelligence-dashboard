"""Analysis runs: score reviews with the sentiment engine and aspect detector and store the results.

Results are stored (not computed per request) so the dashboard is fast and every number can be
traced to the
run, engine and lexicon version that produced it.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.analytics.nlp.aspects import Lexicon, load_lexicon
from app.analytics.nlp.review_analysis import analyse_review
from app.analytics.nlp.sentiment import SentimentEngine, VaderEngine
from app.core.errors import AppError
from app.models import AnalysisRun, Aspect, AspectMention, Review, SentimentResult
from app.models.base import AnalysisStatus, AnalysisTrigger, RunStatus

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
Scope = Literal["pending", "all"]


@dataclass
class RunSummary:
    run: AnalysisRun | None
    processed: int = 0
    analysed: int = 0
    no_text: int = 0
    non_english: int = 0
    mentions: int = 0


def sync_aspects(db: Session, lexicon: Lexicon) -> dict[str, int]:
    """Make the `aspects` table match the lexicon file. Returns key -> aspect id."""
    existing = {a.key: a for a in db.scalars(select(Aspect))}
    wanted = {a.key for a in lexicon.aspects}
    for definition in lexicon.aspects:
        row = existing.get(definition.key)
        if row is None:
            db.add(Aspect(key=definition.key, display_name=definition.display_name, is_active=True))
        else:
            row.display_name = definition.display_name
            row.is_active = True
    for key, row in existing.items():
        if key not in wanted:
            row.is_active = False  # keep history; stop reporting on it
    db.flush()
    return {a.key: a.id for a in db.scalars(select(Aspect))}


def latest_completed_run(db: Session) -> AnalysisRun | None:
    return db.scalar(
        select(AnalysisRun)
        .where(AnalysisRun.status == RunStatus.COMPLETED.value)
        .order_by(AnalysisRun.id.desc())
        .limit(1)
    )


def _effective_scope(db: Session, scope: Scope, engine: SentimentEngine, lexicon: Lexicon) -> Scope:
    """Results from different engines or lexicon versions must not be mixed, so a change forces a
    full run."""
    last = latest_completed_run(db)
    if last is not None and (
        last.sentiment_engine != engine.name or last.aspect_lexicon_version != lexicon.version
    ):
        return "all"
    return scope


def pending_count(db: Session) -> int:
    return (
        db.scalar(select(func.count()).select_from(Review).where(Review.analysis_status.is_(None)))
        or 0
    )


def run_analysis(
    db: Session,
    *,
    scope: Scope = "pending",
    triggered_by: AnalysisTrigger = AnalysisTrigger.MANUAL,
    engine: SentimentEngine | None = None,
    lexicon: Lexicon | None = None,
) -> RunSummary:
    """Score reviews. `pending` = reviews not processed yet (or changed since); `all` = every
    review.

    Everything is written in one transaction: if anything fails, the previous results are left
    untouched
    and a failed run is recorded.
    """
    engine = engine or VaderEngine()
    lexicon = lexicon or load_lexicon()
    scope = _effective_scope(db, scope, engine, lexicon)

    review_filter = [] if scope == "all" else [Review.analysis_status.is_(None)]
    todo = db.scalar(select(func.count()).select_from(Review).where(*review_filter)) or 0
    if todo == 0 and triggered_by is AnalysisTrigger.IMPORT:
        return RunSummary(run=None)  # nothing to do after an import: do not litter the run history

    summary = RunSummary(run=None)
    try:
        aspect_ids = sync_aspects(db, lexicon)
        run = AnalysisRun(
            triggered_by=triggered_by.value,
            sentiment_engine=engine.name,
            aspect_lexicon_version=lexicon.version,
            status=RunStatus.RUNNING.value,
        )
        db.add(run)
        db.flush()
        summary.run = run

        last_id = 0
        while True:
            reviews = list(
                db.scalars(
                    select(Review)
                    .where(Review.id > last_id, *review_filter)
                    .order_by(Review.id)
                    .limit(BATCH_SIZE)
                )
            )
            if not reviews:
                break
            last_id = reviews[-1].id
            _process_batch(db, reviews, run, engine, lexicon, aspect_ids, summary)

        run.reviews_processed = summary.processed
        run.status = RunStatus.COMPLETED.value
        run.completed_at = datetime.now(UTC)
        db.commit()
        return summary
    except Exception as exc:
        db.rollback()
        logger.exception("analysis run failed")
        failed = AnalysisRun(
            triggered_by=triggered_by.value,
            sentiment_engine=engine.name,
            aspect_lexicon_version=lexicon.version,
            status=RunStatus.FAILED.value,
            completed_at=datetime.now(UTC),
        )
        db.add(failed)
        db.commit()
        raise AppError(
            500, "ANALYSIS_FAILED", "The analysis failed. Previous results were left unchanged."
        ) from exc


def _process_batch(
    db: Session,
    reviews: list[Review],
    run: AnalysisRun,
    engine: SentimentEngine,
    lexicon: Lexicon,
    aspect_ids: dict[str, int],
    summary: RunSummary,
) -> None:
    ids = [r.id for r in reviews]
    # Replace any earlier results for these reviews (re-run, or content changed by a re-import).
    db.execute(delete(SentimentResult).where(SentimentResult.review_id.in_(ids)))
    db.execute(delete(AspectMention).where(AspectMention.review_id.in_(ids)))

    for review in reviews:
        analysis = analyse_review(
            positive_text=review.positive_text,
            negative_text=review.negative_text,
            body_text=review.body_text,
            language=review.language,
            lexicon=lexicon,
            engine=engine,
        )
        review.analysis_status = analysis.status.value
        review.analysed_run_id = run.id
        if analysis.language_was_detected and review.language is None:
            review.language = analysis.language
            review.language_detected = True

        summary.processed += 1
        if analysis.status is AnalysisStatus.NO_TEXT:
            summary.no_text += 1
            continue
        if analysis.status is AnalysisStatus.NON_ENGLISH:
            summary.non_english += 1
            continue

        summary.analysed += 1
        for segment in [*analysis.segments, analysis.overall]:
            if segment is None:
                continue
            db.add(
                SentimentResult(
                    review_id=review.id,
                    analysis_run_id=run.id,
                    segment=segment.segment.value,
                    label=segment.label.value,
                    score=round(segment.score, 4),
                    model_name=engine.name,
                )
            )
        for mention in analysis.mentions:
            summary.mentions += 1
            db.add(
                AspectMention(
                    review_id=review.id,
                    aspect_id=aspect_ids[mention.aspect_key],
                    analysis_run_id=run.id,
                    source_field=mention.source_field.value,
                    sentiment_label=mention.label.value,
                    score=round(mention.score, 4),
                    evidence_text=mention.evidence_text,
                    matched_term=mention.matched_term[:100],
                )
            )
    db.flush()


def analyse_after_import(db: Session) -> None:
    """Score newly imported reviews. A failure here must not fail the import: the reviews are
    already saved
    and the failed run is recorded, so the user can re-run the analysis from the Settings page."""
    try:
        run_analysis(db, scope="pending", triggered_by=AnalysisTrigger.IMPORT)
    except AppError:
        logger.warning("analysis after import failed; reviews are saved and can be analysed later")
