"""The app on a migrated SQLite database, with a fixed clock, and the contract bound to it."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import schemathesis
from fastapi import FastAPI
from schemathesis.config import SchemathesisConfig
from schemathesis.specs.openapi.schemas import OpenApiSchema

from app.clock import FixedClock
from app.config import Settings
from app.db.session import make_engine
from app.main import create_app
from tests.integration.database import migrate

CONTRACT = Path(__file__).resolve().parents[3] / "api" / "openapi.yaml"


@pytest.fixture
def app(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'contract.db').as_posix()}"
    engine = make_engine(url)
    migrate(engine)
    engine.dispose()
    settings = Settings(database_url=url, environment="test", version="contract")
    yield create_app(settings, FixedClock(datetime(2026, 11, 2, 5, 30, tzinfo=UTC)))


@pytest.fixture
def contract(app: FastAPI) -> OpenApiSchema:
    config = SchemathesisConfig.from_dict(
        {
            "checks": {
                "positive_data_acceptance": {
                    "expected-statuses": ["2xx", "404", "409", "422"],
                }
            },
            "generation": {"max-examples": 25},
        }
    )
    schema = schemathesis.openapi.from_path(CONTRACT, config=config)
    schema.app = app
    return schema
