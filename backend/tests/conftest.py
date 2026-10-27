from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _no_telemetry_export(monkeypatch: pytest.MonkeyPatch) -> None:
    # Settings reads the environment, so a developer's own collector setting must not make
    # test apps export. Tests that export set an endpoint of their own.
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        environment="test",
        version="test-sha",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    # raise_server_exceptions=False: assert on the 500 response, not the raised error.
    with TestClient(create_app(settings), raise_server_exceptions=False) as test_client:
        yield test_client
