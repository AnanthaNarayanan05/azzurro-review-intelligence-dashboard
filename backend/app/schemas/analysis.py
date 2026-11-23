from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AnalysisRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    triggered_by: str
    sentiment_engine: str
    aspect_lexicon_version: str
    reviews_processed: int
    status: str
    started_at: datetime
    completed_at: datetime | None


class AnalysisStatusRead(BaseModel):
    engine: str
    lexicon_version: str
    total_reviews: int
    analysed: int
    no_text: int
    non_english: int
    pending: int
    latest_run: AnalysisRunRead | None
    notes: list[str]


class RunRequest(BaseModel):
    scope: Literal["pending", "all"] = "pending"


class RunResultRead(BaseModel):
    run: AnalysisRunRead | None
    processed: int
    analysed: int
    no_text: int
    non_english: int
    aspect_mentions: int
