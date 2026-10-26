"""Alembic environment. The database URL comes from Settings (DATABASE_URL).

Tests pass an open connection in `config.attributes["connection"]` instead.
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import Connection

from app.config import Settings
from app.db.models import Base
from app.db.session import make_engine


def _configure_and_run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        # SQLite can't ALTER most things; batch mode rebuilds the table instead.
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = context.config.attributes.get("connection")
    if isinstance(connection, Connection):
        _configure_and_run(connection)
        return
    engine = make_engine(Settings().database_url)
    try:
        with engine.connect() as new_connection:
            _configure_and_run(new_connection)
    finally:
        engine.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=Settings().database_url,
        target_metadata=Base.metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
