from collections.abc import Iterator

from fastapi import Query
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.database import get_db


def test_health_reports_ok_with_database(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["database_backend"] in {
        "sqlite",
        "postgresql",
    }  # postgresql when TEST_DATABASE_URL is set
    assert data["sentiment_engine"] == "vader"
    assert isinstance(data["llm_enabled"], bool)


def test_health_reports_degraded_when_database_unreachable(app, client: TestClient) -> None:
    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

        def get_bind(self):
            class _Bind:
                class dialect:  # noqa: N801
                    name = "sqlite"

            return _Bind()

    def _broken_db() -> Iterator[BrokenSession]:
        yield BrokenSession()

    app.dependency_overrides[get_db] = _broken_db
    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["data"]["status"] == "degraded"
    assert response.json()["data"]["database"] == "unavailable"


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "Not Found", "details": []}
    }


def test_wrong_method_uses_error_envelope(client: TestClient) -> None:
    response = client.post("/api/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_validation_error_uses_error_envelope(app, client: TestClient) -> None:
    @app.get("/api/_test/validated")
    def _validated(page: int = Query(ge=1)) -> dict:
        return {"page": page}

    response = client.get("/api/_test/validated", params={"page": 0})

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["location"] == ["query", "page"]


def test_unexpected_error_does_not_leak_internals(app, client: TestClient) -> None:
    @app.get("/api/_test/boom")
    def _boom() -> dict:
        raise RuntimeError("secret connection string postgresql://user:pw@host/db")

    response = client.get("/api/_test/boom")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "secret" not in response.text
    assert "postgresql" not in response.text


def test_cors_allows_configured_frontend_origin(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})

    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_rejects_unknown_origin(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_openapi_documentation_is_served(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]
