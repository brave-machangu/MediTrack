"""Database fixtures: every test using them runs on SQLite and on PostgreSQL.

PostgreSQL tests need MEDITRACK_TEST_POSTGRES_URL (a throwaway server, see backend/README.md).
Without it they are skipped with that reason, unless MEDITRACK_REQUIRE_POSTGRES=1 (CI), which
turns the skip into a failure.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url

from app.clock import FixedClock
from app.config import Settings
from app.db.session import make_engine
from app.main import create_app
from tests.integration.database import downgrade, migrate

POSTGRES_URL_VARIABLE = "MEDITRACK_TEST_POSTGRES_URL"
REQUIRE_POSTGRES_VARIABLE = "MEDITRACK_REQUIRE_POSTGRES"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """A new, empty database on the test server, dropped at the end of the session."""
    server_url = os.environ.get(POSTGRES_URL_VARIABLE)
    if not server_url:
        reason = f"{POSTGRES_URL_VARIABLE} is not set (needs a throwaway PostgreSQL server)"
        if os.environ.get(REQUIRE_POSTGRES_VARIABLE) == "1":
            pytest.fail(reason)
        pytest.skip(reason)
    name = f"meditrack_test_{uuid4().hex[:12]}"
    admin = create_engine(server_url, isolation_level="AUTOCOMMIT")
    # Identifiers can't be bound parameters; the name is generated above, then quoted.
    quoted_name = admin.dialect.identifier_preparer.quote(name)
    with admin.connect() as connection:
        connection.exec_driver_sql(f"CREATE DATABASE {quoted_name}")
    try:
        yield make_url(server_url).set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as connection:
            connection.exec_driver_sql(f"DROP DATABASE IF EXISTS {quoted_name} WITH (FORCE)")
        admin.dispose()


@pytest.fixture(params=["sqlite", "postgresql"])
def database_url(request: pytest.FixtureRequest, tmp_path: Path) -> str:
    if request.param == "sqlite":
        return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    url: str = request.getfixturevalue("postgres_url")
    return url


@pytest.fixture
def empty_engine(database_url: str) -> Iterator[Engine]:
    """An engine on a database without MediTrack tables."""
    engine = make_engine(database_url)
    downgrade(engine, "base")  # the PostgreSQL database is shared by the whole session
    yield engine
    downgrade(engine, "base")
    engine.dispose()


@pytest.fixture
def engine(empty_engine: Engine) -> Engine:
    """An engine on a database migrated to the latest revision."""
    migrate(empty_engine)
    return empty_engine


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(datetime(2026, 11, 2, 5, 30, tzinfo=UTC))


@pytest.fixture
def api(engine: Engine, database_url: str, clock: FixedClock) -> Iterator[TestClient]:
    """The app on a migrated database, with a fixed clock."""
    settings = Settings(database_url=database_url, environment="test", version="test-sha")
    # raise_server_exceptions=False: assert on the 500 response, not the raised error.
    with TestClient(create_app(settings, clock), raise_server_exceptions=False) as client:
        yield client
