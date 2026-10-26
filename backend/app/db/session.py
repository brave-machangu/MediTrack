"""Database engine and sessions."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry


def make_engine(database_url: str) -> Engine:
    engine = create_engine(
        database_url,
        # Replaces dead pooled connections after a database restart.
        pool_pre_ping=True,
        # Keeps bound values (names, notes) out of exception text, which can reach logs
        # (docs/security.md §2).
        hide_parameters=True,
    )
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def database_is_reachable(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


def _enable_sqlite_foreign_keys(dbapi_connection: DBAPIConnection, _: ConnectionPoolEntry) -> None:
    # SQLite ignores foreign keys unless asked, so ON DELETE RESTRICT would do nothing.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
