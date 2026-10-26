from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


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
