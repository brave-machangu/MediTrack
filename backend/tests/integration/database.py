"""Run Alembic migrations against a test engine."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def migrate(engine: Engine, revision: str = "head") -> None:
    with engine.begin() as connection:
        command.upgrade(_config(connection), revision)


def downgrade(engine: Engine, revision: str) -> None:
    with engine.begin() as connection:
        command.downgrade(_config(connection), revision)


def _config(connection: Connection) -> Config:
    config = Config(ALEMBIC_INI)
    config.attributes["connection"] = connection
    return config
