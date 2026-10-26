"""SQLAlchemy models for the tables in backend/DESIGN.md §2 (requirements §4.1).

The schema itself is created by Alembic (alembic/versions); a test checks that the migration
and these models agree.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Dialect,
    ForeignKey,
    Integer,
    MetaData,
    String,
    UniqueConstraint,
    Uuid,
    column,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.config import GRACE_PERIOD_MAX_MINUTES

NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class UtcDateTime(TypeDecorator[datetime]):
    """Stores instants as UTC and always reads them back timezone-aware, on both databases.

    SQLite has no timezone type and stores text, so values are written as naive UTC: one
    instant is then always one string, which keeps comparisons and unique constraints right.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.utcoffset() is None:
            raise TypeError("UtcDateTime columns need timezone-aware datetimes")
        value = value.astimezone(UTC)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


# Services recognise a duplicate dose by this constraint's name (DESIGN.md §4).
DOSE_LOG_UNIQUE_NAME = "uq_dose_log_schedule_time"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(80))
    timezone: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    dosage_label: Mapped[str] = mapped_column(String(100))
    instructions: Mapped[str | None] = mapped_column(String(500))
    # NULL means active. The API's `active` is derived from it, so the two can't disagree.
    deactivated_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = (
        CheckConstraint(
            column("end_date").is_(None) | (column("end_date") >= column("start_date")),
            name="end_after_start",
        ),
        CheckConstraint(
            column("grace_period_minutes").between(0, GRACE_PERIOD_MAX_MINUTES),
            name="grace_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    medication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medications.id", ondelete="RESTRICT"), index=True
    )
    # JSON instead of arrays so the schema works on SQLite and PostgreSQL (ADR-005).
    times_of_day: Mapped[list[str]] = mapped_column(JSON)
    days_of_week: Mapped[list[int]] = mapped_column(JSON)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    grace_period_minutes: Mapped[int] = mapped_column(Integer)


class DoseLog(Base):
    __tablename__ = "dose_logs"
    __table_args__ = (
        # Duplicate prevention (ADR-003). Its index leads with schedule_id, so schedule_id
        # needs no index of its own.
        UniqueConstraint("schedule_id", "scheduled_for", name=DOSE_LOG_UNIQUE_NAME),
        CheckConstraint(column("status").in_(["taken", "skipped"]), name="status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # RESTRICT: a schedule with logs can't be deleted (requirements §4.4).
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.id", ondelete="RESTRICT"))
    scheduled_for: Mapped[datetime] = mapped_column(UtcDateTime)
    status: Mapped[str] = mapped_column(String(7))
    recorded_at: Mapped[datetime] = mapped_column(UtcDateTime)
    late: Mapped[bool] = mapped_column(Boolean)
    note: Mapped[str | None] = mapped_column(String(280))
