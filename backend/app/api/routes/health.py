import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.common import DataResponse
from app.schemas.health import HealthStatus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=DataResponse[HealthStatus],
    summary="Service liveness and database connectivity",
    responses={503: {"description": "Service running but the database is unreachable"}},
)
def health(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DataResponse[HealthStatus]:
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except SQLAlchemyError as exc:
        logger.warning("Health check database probe failed: %s", type(exc).__name__)
        database_ok = False

    if not database_ok:
        response.status_code = 503

    return DataResponse(
        data=HealthStatus(
            status="ok" if database_ok else "degraded",
            version=settings.app_version,
            environment=settings.app_env,
            database="ok" if database_ok else "unavailable",
            database_backend=db.get_bind().dialect.name,
            sentiment_engine=settings.sentiment_engine,
            llm_enabled=settings.llm_enabled,
        )
    )
