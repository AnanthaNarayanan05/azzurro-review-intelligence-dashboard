"""Time import, analysis, the dashboard endpoints and insight generation on SYNTHETIC data.

Run from backend/ (nothing is written to the real database or upload folder):

    .venv/Scripts/python.exe -m scripts.benchmark --reviews 10000

It builds a throwaway SQLite database and upload folder in a temporary directory, so results are
for SQLite on this machine only. Endpoint timings are in-process (FastAPI TestClient), so they
exclude network time. The dataset is generated demo text (a few dozen distinct sentences
repeated), which is a fair test of volume but not of how the real text will behave.
Compare the figures with NFR-3 in docs/REQUIREMENTS.md.
"""

import argparse
import os
import statistics
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path


def build_csv(target: int) -> bytes:
    from app.services.demo_data import generate_rows, load_demo_properties, rows_to_csv

    properties = load_demo_properties()
    rows: list[dict] = []
    anchor = date(2026, 11, 23)
    seed = 1
    while len(rows) < target:
        # A different seed and anchor each round gives different dates and wording choices.
        rows.extend(generate_rows(properties, anchor - timedelta(days=(seed % 5)), seed=seed))
        seed += 1
    rows = rows[:target]
    for index, row in enumerate(rows, start=1):  # unique IDs across rounds
        row["Review ID"] = f"BENCH-{index:07d}"
    return rows_to_csv(rows)


def timed(label: str, fn, results: list[tuple[str, float]]):
    start = time.perf_counter()
    value = fn()
    elapsed = time.perf_counter() - start
    results.append((label, elapsed))
    print(f"  {label:<46} {elapsed:8.2f} s")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reviews", type=int, default=10000)
    parser.add_argument(
        "--repeats", type=int, default=5, help="runs per endpoint (median reported)"
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="an EMPTY, disposable PostgreSQL database to measure instead of SQLite; its public "
        "schema is wiped first, so never point it at data you want to keep",
    )
    args = parser.parse_args()

    workdir = Path(tempfile.mkdtemp(prefix="azzurro-bench-"))
    os.environ["DATABASE_URL"] = (
        args.database_url or f"sqlite:///{(workdir / 'bench.db').as_posix()}"
    )
    os.environ["UPLOAD_DIR"] = str(workdir / "uploads")
    os.environ["MAX_IMPORT_ROWS"] = str(max(args.reviews, 100000))
    os.environ["APP_ENV"] = "test"

    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, func, select, text

    from app.core.config import get_settings, normalise_database_url
    from app.core.database import SessionLocal
    from app.main import create_app
    from app.models import Property, Review
    from app.models.base import AnalysisTrigger
    from app.services import analysis
    from app.services.demo_data import load_demo_properties
    from app.services.ingestion import pipeline
    from app.services.ingestion.mapping import suggest_mapping
    from app.services.ingestion.normalise import normalise_for_match

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    database_url = normalise_database_url(os.environ["DATABASE_URL"])
    if database_url.startswith("postgresql"):
        reset = create_engine(database_url, isolation_level="AUTOCOMMIT")
        with reset.connect() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
        reset.dispose()
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    settings = get_settings()
    results: list[tuple[str, float]] = []
    backend_name = "PostgreSQL" if database_url.startswith("postgresql") else "SQLite"
    print(f"Benchmark: {args.reviews:,} synthetic reviews on {backend_name} (workdir {workdir})")

    data = timed("generate CSV", lambda: build_csv(args.reviews), results)
    print(f"  CSV size: {len(data) / 1_000_000:.1f} MB")

    with SessionLocal() as db:
        mapping_ids = {}
        for demo in load_demo_properties():
            prop = Property(name=demo.name, code=demo.code)
            db.add(prop)
            db.flush()
            mapping_ids[demo.name] = prop.id
        db.commit()

        preview = timed(
            "import: parse and preview",
            lambda: pipeline.create_preview(db, settings, "bench.csv", data),
            results,
        )
        mapping = {k: v for k, v in suggest_mapping(preview.table.columns).items() if v}
        request = pipeline.CommitRequest(
            column_mapping=mapping,
            property_mapping={
                raw: pid for raw, pid in mapping_ids.items() if normalise_for_match(raw)
            },
            date_format="iso",
            is_synthetic=True,
            remember_aliases=False,
        )
        batch = timed(
            "import: validate, de-duplicate, store",
            lambda: pipeline.commit_import(db, settings, preview.batch.id, request),
            results,
        )
        print(
            f"  imported {batch.imported_rows:,}, rejected {batch.rejected_rows:,}, "
            f"duplicates {batch.duplicate_rows:,}"
        )
        timed(
            "analysis: sentiment + aspects",
            lambda: analysis.run_analysis(db, scope="pending", triggered_by=AnalysisTrigger.MANUAL),
            results,
        )
        total = db.scalar(select(func.count()).select_from(Review))
        print(f"  reviews in database: {total:,}")

    client = TestClient(create_app())
    scope = {"data_scope": "synthetic"}
    endpoints = {
        "GET /analytics/overview": ("/api/analytics/overview", scope),
        "GET /analytics/comparison": ("/api/analytics/comparison", scope),
        "GET /analytics/aspects": ("/api/analytics/aspects", scope),
        "GET /analytics/trends (rating, month)": ("/api/analytics/trends", scope),
        "GET /analytics/trends (aspect share, week)": (
            "/api/analytics/trends",
            {
                **scope,
                "metric": "aspect_negative_share",
                "aspect": "cleanliness",
                "granularity": "week",
            },
        ),
        "GET /reviews (page 1)": ("/api/reviews", scope),
        "GET /reviews (text search)": ("/api/reviews", {**scope, "q": "breakfast"}),
        "GET /reviews (aspect filter)": (
            "/api/reviews",
            {**scope, "aspect": "cleanliness", "aspect_sentiment": "negative"},
        ),
    }
    print(f"\nEndpoint latency (median and slowest of {args.repeats} runs, in-process):")
    slowest_median = 0.0
    for label, (path, params) in endpoints.items():
        samples = []
        for _ in range(args.repeats):
            start = time.perf_counter()
            response = client.get(path, params=params)
            samples.append(time.perf_counter() - start)
            assert response.status_code == 200, (label, response.status_code, response.text[:200])
        median = statistics.median(samples)
        slowest_median = max(slowest_median, median)
        print(f"  {label:<46} median {median:6.3f} s   max {max(samples):6.3f} s")

    print()
    response = timed(
        "insights: generate (synthetic scope)",
        lambda: client.post("/api/insights/generate", json=scope),
        results,
    )
    assert response.status_code == 200, response.text[:200]
    print(f"  created {response.json()['data']['created']} insights")
    start = time.perf_counter()
    assert client.get("/api/insights", params=scope).status_code == 200
    print(f"  {'GET /insights':<46} {time.perf_counter() - start:8.3f} s")

    print(
        f"\nSlowest endpoint median: {slowest_median:.3f} s "
        "(NFR-3 target: under 1 s up to ~50,000 reviews)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
