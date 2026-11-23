"""Start the API on a brand-new throwaway database, for the browser end-to-end tests.

Usage (from backend/): python -m scripts.e2e_server --port 8100 --origin http://localhost:3100

Each start builds an empty database with the real Alembic migrations in a temporary folder, so the
tests never touch data/processed/azzurro.db or the real upload folder, and every run starts clean.
"""

import argparse
import os
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--origin", default="http://localhost:3100")
    args = parser.parse_args()

    workdir = Path(tempfile.mkdtemp(prefix="azzurro-e2e-"))
    os.environ["DATABASE_URL"] = f"sqlite:///{(workdir / 'e2e.db').as_posix()}"
    os.environ["UPLOAD_DIR"] = str(workdir / "uploads")
    os.environ["CORS_ORIGINS"] = args.origin
    os.environ["APP_ENV"] = "test"

    import uvicorn
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(config, "head")

    print(f"E2E database: {workdir}", flush=True)
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
