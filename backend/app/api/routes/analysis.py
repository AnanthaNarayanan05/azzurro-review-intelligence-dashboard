from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.nlp.aspects import load_lexicon
from app.analytics.nlp.sentiment import VaderEngine
from app.core.database import get_db
from app.models import AnalysisRun, Review
from app.models.base import AnalysisStatus, AnalysisTrigger
from app.schemas.analysis import AnalysisRunRead, AnalysisStatusRead, RunRequest, RunResultRead
from app.schemas.common import DataResponse, ListResponse, PageMeta
from app.services import analysis

router = APIRouter(prefix="/analysis", tags=["analysis"])

NOTES = [
    "Sentiment uses VADER, an English-only lexicon method. Its accuracy on this project's data "
    "has not been evaluated.",
    "Reviews written in another language, or with no substantive text, are counted but not scored.",
]


@router.get("/status", response_model=DataResponse[AnalysisStatusRead])
def get_status(db: Session = Depends(get_db)) -> DataResponse[AnalysisStatusRead]:
    counts = dict(
        db.execute(
            select(Review.analysis_status, func.count()).group_by(Review.analysis_status)
        ).all()
    )
    latest = analysis.latest_completed_run(db)
    return DataResponse(
        data=AnalysisStatusRead(
            engine=VaderEngine().name,
            lexicon_version=load_lexicon().version,
            total_reviews=sum(counts.values()),
            analysed=counts.get(AnalysisStatus.ANALYSED.value, 0),
            no_text=counts.get(AnalysisStatus.NO_TEXT.value, 0),
            non_english=counts.get(AnalysisStatus.NON_ENGLISH.value, 0),
            pending=counts.get(None, 0),
            latest_run=AnalysisRunRead.model_validate(latest) if latest else None,
            notes=NOTES,
        )
    )


@router.post("/run", response_model=DataResponse[RunResultRead])
def run_analysis(
    body: RunRequest | None = None, db: Session = Depends(get_db)
) -> DataResponse[RunResultRead]:
    """Score reviews now. `pending` handles new or changed reviews; `all` re-scores everything."""
    summary = analysis.run_analysis(
        db, scope=(body or RunRequest()).scope, triggered_by=AnalysisTrigger.MANUAL
    )
    return DataResponse(
        data=RunResultRead(
            run=AnalysisRunRead.model_validate(summary.run) if summary.run else None,
            processed=summary.processed,
            analysed=summary.analysed,
            no_text=summary.no_text,
            non_english=summary.non_english,
            aspect_mentions=summary.mentions,
        )
    )


@router.get("/runs", response_model=ListResponse[AnalysisRunRead])
def list_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ListResponse[AnalysisRunRead]:
    total = db.scalar(select(func.count()).select_from(AnalysisRun)) or 0
    rows = db.scalars(
        select(AnalysisRun)
        .order_by(AnalysisRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ListResponse(
        data=[AnalysisRunRead.model_validate(r) for r in rows],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )
