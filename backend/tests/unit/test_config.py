from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DATABASE_URL", "APP_ENV", "APP_VERSION"):
        monkeypatch.delenv(name, raising=False)


def test_defaults_work_without_any_environment() -> None:
    settings = Settings()
    assert settings.database_url == "sqlite:///./meditrack.db"
    assert settings.environment == "local"
    assert settings.version == "dev"


def test_reads_documented_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://meditrack@db/meditrack")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("APP_VERSION", "3f2c1a9")
    settings = Settings()
    assert settings.database_url == "postgresql+psycopg://meditrack@db/meditrack"
    assert settings.environment == "dev"
    assert settings.version == "3f2c1a9"


def test_rejects_unknown_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    with pytest.raises(ValidationError):
        Settings()
