"""Settings read from environment variables. Names are listed in backend/README.md."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Fixed by api/openapi.yaml (ScheduleCreate.grace_period_minutes), so not configurable.
GRACE_PERIOD_DEFAULT_MINUTES = 60
GRACE_PERIOD_MAX_MINUTES = 240


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", populate_by_name=True)

    database_url: str = Field(default="sqlite:///./meditrack.db", alias="DATABASE_URL")
    environment: Literal["local", "test", "ci", "dev", "production"] = Field(
        default="local", alias="MEDITRACK_ENV"
    )
    version: str = Field(default="dev", alias="MEDITRACK_VERSION")
    # Log window (requirements §4.2): how early and how late a dose can be recorded.
    early_log_window_minutes: int = Field(
        default=60, ge=0, alias="MEDITRACK_EARLY_LOG_WINDOW_MINUTES"
    )
    late_log_limit_minutes: int = Field(
        default=1440, ge=0, alias="MEDITRACK_LATE_LOG_LIMIT_MINUTES"
    )
    # The OTLP/HTTP base URL (the standard OpenTelemetry name). Unset: nothing is exported.
    otlp_endpoint: str | None = Field(default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    # The incident drill's faulty release (MT-023): the share of POST /dose-logs that fail.
    fault_dose_log_error_rate: float = Field(
        default=0, ge=0, le=1, alias="MEDITRACK_FAULT_DOSE_LOG_ERROR_RATE"
    )

    @field_validator("fault_dose_log_error_rate")
    @classmethod
    def _no_fault_in_production(cls, rate: float, info: ValidationInfo) -> float:
        # The drill runs on dev; a faulty image in production fails to start instead. A field
        # validator, so the error repeats only the rate, never the other settings (DATABASE_URL);
        # `environment` is declared above, so it is already in info.data.
        if info.data.get("environment") == "production" and rate > 0:
            raise ValueError("must be 0 when MEDITRACK_ENV=production")
        return rate
