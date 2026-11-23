from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes.imports import build_report
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.common import DataResponse
from app.schemas.imports import ImportReport, RemovedRead
from app.services import demo

router = APIRouter(prefix="/demo", tags=["demo data"])


class DemoStatus(BaseModel):
    loaded: bool
    synthetic_review_count: int
    import_ids: list[int]
    notice: str = (
        "Demo data is SYNTHETIC: invented for demonstration, not genuine guest reviews. "
        "It is stored separately and can be removed at any time."
    )


@router.get("", response_model=DataResponse[DemoStatus])
def get_demo_status(db: Session = Depends(get_db)) -> DataResponse[DemoStatus]:
    return DataResponse(data=DemoStatus(**demo.demo_status(db)))


@router.post("/load", response_model=DataResponse[ImportReport], status_code=201)
def load_demo_data(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> DataResponse[ImportReport]:
    batch = demo.load_demo(db, settings)
    return DataResponse(data=build_report(db, batch))


@router.delete("", response_model=DataResponse[RemovedRead])
def remove_demo_data(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> DataResponse[RemovedRead]:
    return DataResponse(data=RemovedRead(removed_reviews=demo.clear_demo(db, settings)))
