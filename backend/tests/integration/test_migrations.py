"""MT-013: the Alembic migration, on SQLite and PostgreSQL."""

from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import CheckConstraint, Engine, inspect

from app.db.models import Base
from tests.integration.database import downgrade, migrate

APP_TABLES = {"patients", "medications", "schedules", "dose_logs"}


def app_tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_upgrade_downgrade_upgrade(empty_engine: Engine) -> None:
    migrate(empty_engine)
    assert app_tables(empty_engine) == APP_TABLES
    downgrade(empty_engine, "-1")
    assert app_tables(empty_engine) == set()
    migrate(empty_engine)
    assert app_tables(empty_engine) == APP_TABLES


def test_migration_matches_models(engine: Engine) -> None:
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert differences == []


def test_unique_constraint_exists(engine: Engine) -> None:
    constraints = {
        constraint["name"]: constraint["column_names"]
        for constraint in inspect(engine).get_unique_constraints("dose_logs")
    }
    assert constraints["uq_dose_log_schedule_time"] == ["schedule_id", "scheduled_for"]


def test_check_constraint_names_match_the_models(engine: Engine) -> None:
    # compare_metadata() doesn't look at CHECK constraints, so compare their names directly.
    for table in ("schedules", "dose_logs"):
        expected = {
            constraint.name
            for constraint in Base.metadata.tables[table].constraints
            if isinstance(constraint, CheckConstraint)
        }
        reflected = {
            constraint["name"] for constraint in inspect(engine).get_check_constraints(table)
        }
        assert reflected == expected
