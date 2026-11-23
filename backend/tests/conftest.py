"""Test fixtures: each test gets a fresh SQLite database built by the real Alembic migrations."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import build_engine, get_db
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[1]


def run_migrations(database_url: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def _reset_postgres(url: str) -> None:
    """Empty the public schema so every test starts from the real migrations on a clean database."""
    reset_engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with reset_engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    reset_engine.dispose()


@pytest.fixture()
def engine(tmp_path: Path) -> Iterator[Engine]:
    # By default every test uses a throwaway SQLite file. Setting TEST_DATABASE_URL to the URL of
    # an EMPTY, disposable PostgreSQL database runs the same tests against PostgreSQL
    # (docs/DEPLOYMENT.md). It is wiped before each test: never point it at data you want to keep.
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    if url.startswith("postgresql"):
        _reset_postgres(url)
    run_migrations(url)
    test_engine = build_engine(url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture()
def db_session(engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    """Settings with an isolated upload folder so tests never touch real data."""
    return Settings(upload_dir=str(tmp_path / "uploads"), app_env="test")


@pytest.fixture()
def app(engine: Engine, settings: Settings):
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _override_get_db() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = _override_get_db
    return application


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
