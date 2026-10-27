from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "DATABASE_URL",
        "MEDITRACK_ENV",
        "MEDITRACK_VERSION",
        "MEDITRACK_EARLY_LOG_WINDOW_MINUTES",
        "MEDITRACK_LATE_LOG_LIMIT_MINUTES",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "MEDITRACK_FAULT_DOSE_LOG_ERROR_RATE",
        "APP_ENV",
        "APP_VERSION",
    ):
        monkeypatch.delenv(name, raising=False)


def test_defaults_work_without_any_environment() -> None:
    settings = Settings()
    assert settings.database_url == "sqlite:///./meditrack.db"
    assert settings.environment == "local"
    assert settings.version == "dev"
    assert settings.otlp_endpoint is None  # telemetry is not exported
    assert settings.fault_dose_log_error_rate == 0  # no injected faults


def test_reads_documented_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://meditrack@db/meditrack")
    monkeypatch.setenv("MEDITRACK_ENV", "dev")
    monkeypatch.setenv("MEDITRACK_VERSION", "3f2c1a9")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
    settings = Settings()
    assert settings.database_url == "postgresql+psycopg://meditrack@db/meditrack"
    assert settings.environment == "dev"
    assert settings.version == "3f2c1a9"
    assert settings.otlp_endpoint == "http://otel-collector:4318"


def test_rejects_unknown_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDITRACK_ENV", "staging")
    with pytest.raises(ValidationError):
        Settings()


def test_names_without_the_meditrack_prefix_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    # Renamed in Lead decision Q5 (backend/DESIGN.md); a stale variable must not take effect.
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_VERSION", "stale")
    settings = Settings()
    assert settings.environment == "local"
    assert settings.version == "dev"


def test_log_window_defaults_match_requirements() -> None:
    # requirements §4.2: 60 minutes early, 24 hours late.
    settings = Settings()
    assert (settings.early_log_window_minutes, settings.late_log_limit_minutes) == (60, 1440)


def test_log_window_reads_its_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDITRACK_EARLY_LOG_WINDOW_MINUTES", "30")
    monkeypatch.setenv("MEDITRACK_LATE_LOG_LIMIT_MINUTES", "720")
    settings = Settings()
    assert (settings.early_log_window_minutes, settings.late_log_limit_minutes) == (30, 720)


@pytest.mark.parametrize(
    "name", ["MEDITRACK_EARLY_LOG_WINDOW_MINUTES", "MEDITRACK_LATE_LOG_LIMIT_MINUTES"]
)
def test_negative_log_window_is_rejected(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    monkeypatch.setenv(name, "-1")
    with pytest.raises(ValidationError):
        Settings()


def test_fault_rate_reads_its_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDITRACK_ENV", "dev")
    monkeypatch.setenv("MEDITRACK_FAULT_DOSE_LOG_ERROR_RATE", "0.5")
    assert Settings().fault_dose_log_error_rate == 0.5


@pytest.mark.parametrize("rate", ["-0.1", "1.01", "half"])
def test_fault_rate_outside_0_to_1_is_rejected(monkeypatch: pytest.MonkeyPatch, rate: str) -> None:
    monkeypatch.setenv("MEDITRACK_FAULT_DOSE_LOG_ERROR_RATE", rate)
    with pytest.raises(ValidationError):
        Settings()


def test_production_refuses_an_injected_fault(monkeypatch: pytest.MonkeyPatch) -> None:
    # operations.md §7: faulty images are for the dev drill; production must never run one.
    monkeypatch.setenv("MEDITRACK_ENV", "production")
    monkeypatch.setenv("MEDITRACK_FAULT_DOSE_LOG_ERROR_RATE", "0.01")
    with pytest.raises(ValidationError, match="MEDITRACK_FAULT_DOSE_LOG_ERROR_RATE"):
        Settings()


def test_production_runs_without_a_fault(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDITRACK_ENV", "production")
    monkeypatch.setenv("MEDITRACK_FAULT_DOSE_LOG_ERROR_RATE", "0")
    assert Settings().environment == "production"


def test_the_production_refusal_repeats_no_other_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    # The error is printed at startup; it must not carry DATABASE_URL and its password.
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://meditrack:CANARY-PASSWORD@db/meditrack"
    )
    monkeypatch.setenv("MEDITRACK_ENV", "production")
    monkeypatch.setenv("MEDITRACK_FAULT_DOSE_LOG_ERROR_RATE", "0.5")
    with pytest.raises(ValidationError) as raised:
        Settings()
    message = str(raised.value)
    assert "DATABASE_URL" not in message
    assert "CANARY-PASSWORD" not in message
