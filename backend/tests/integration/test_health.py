"""`/healthz` and `/readyz` against a real (SQLite) database."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_healthz_reports_ok_and_version(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "test-sha"}


def test_readyz_is_ok_when_database_is_reachable(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "test-sha"}


def test_readyz_is_503_when_database_is_unreachable(tmp_path: Path) -> None:
    # SQLite can't create a file inside a directory that doesn't exist.
    missing = (tmp_path / "no-such-dir" / "test.db").as_posix()
    settings = Settings(database_url=f"sqlite:///{missing}", environment="test", version="v1")
    with TestClient(create_app(settings)) as client:
        ready = client.get("/readyz")
        live = client.get("/healthz")
    assert ready.status_code == 503
    assert ready.json() == {"status": "unavailable", "version": "v1"}
    # Liveness must not depend on the database.
    assert live.status_code == 200


def test_generated_docs_are_not_served(client: TestClient) -> None:
    # api/openapi.yaml is the only contract.
    for path in ("/openapi.json", "/docs", "/redoc"):
        assert client.get(path).status_code == 404
