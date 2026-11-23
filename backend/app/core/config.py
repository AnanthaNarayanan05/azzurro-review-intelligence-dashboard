"""Application settings, loaded from environment variables and the repository-root `.env` file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_SQLITE_PATH = REPO_ROOT / "data" / "processed" / "azzurro.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Azzurro Review Intelligence API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "test", "production"] = "development"

    # Empty means: SQLite file at <repo>/data/processed/azzurro.db
    database_url: str = ""

    # Stored as a comma-separated string so it can be set from a plain env var.
    cors_origins: str = "http://localhost:3000"

    # Empty means <repo>/data/uploads (git-ignored). A file lives here only between preview and
    # commit, then it is deleted.
    upload_dir: str = ""

    max_upload_mb: int = Field(default=20, gt=0, le=200)
    max_import_rows: int = Field(default=100_000, gt=0)
    default_rating_scale_max: float = Field(default=10, gt=0)
    min_sample_comparison: int = Field(default=30, ge=1)
    min_sample_trend_window: int = Field(default=30, ge=1)
    # An aspect needs at least this many reviews mentioning it before its sentiment split is
    # trusted.
    min_aspect_mentions: int = Field(default=10, ge=1)

    sentiment_engine: Literal["vader", "transformer"] = "vader"
    transformer_model_name: str = ""

    llm_provider: str = "none"
    llm_model: str = ""
    llm_api_key: str = Field(default="", repr=False)
    llm_timeout_seconds: int = Field(default=30, gt=0)

    @field_validator("llm_provider")
    @classmethod
    def _normalise_provider(cls, value: str) -> str:
        return (value or "none").strip().lower()

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

    @property
    def resolved_upload_dir(self) -> Path:
        return Path(self.upload_dir) if self.upload_dir else REPO_ROOT / "data" / "uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider != "none" and bool(self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
