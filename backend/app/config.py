"""Settings read from environment variables. Names are listed in backend/README.md."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", populate_by_name=True)

    database_url: str = Field(default="sqlite:///./meditrack.db", alias="DATABASE_URL")
    environment: Literal["local", "test", "ci", "dev", "production"] = Field(
        default="local", alias="APP_ENV"
    )
    version: str = Field(default="dev", alias="APP_VERSION")
