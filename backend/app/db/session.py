"""Database engine. Models and migrations arrive in MT-013."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def make_engine(database_url: str) -> Engine:
    # pre_ping replaces dead pooled connections after a database restart.
    return create_engine(database_url, pool_pre_ping=True)


def database_is_reachable(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True
