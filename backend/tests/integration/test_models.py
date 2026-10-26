"""MT-013: what the database itself guarantees, on SQLite and PostgreSQL."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.db.models import DoseLog, Medication, Patient, Schedule

HARARE = ZoneInfo("Africa/Harare")
CREATED = datetime(2026, 11, 1, 6, tzinfo=UTC)
DOSE_AT = datetime(2026, 11, 2, 6, tzinfo=UTC)


def add_schedule(engine: Engine) -> UUID:
    """A synthetic patient, medication and daily 08:00 schedule; returns the schedule id."""
    with Session(engine) as session, session.begin():
        patient = Patient(
            display_name="Demo Patient A", timezone="Africa/Harare", created_at=CREATED
        )
        session.add(patient)
        session.flush()
        medication = Medication(
            patient_id=patient.id,
            name="Demo Med Alpha",
            dosage_label="1 tablet",
            created_at=CREATED,
        )
        session.add(medication)
        session.flush()
        schedule = Schedule(
            medication_id=medication.id,
            times_of_day=["08:00", "20:00"],
            days_of_week=[1, 3, 5],
            start_date=date(2026, 11, 1),
            grace_period_minutes=60,
        )
        session.add(schedule)
        session.flush()
        return schedule.id


def dose_log(schedule_id: UUID, scheduled_for: datetime, status: str = "taken") -> DoseLog:
    return DoseLog(
        schedule_id=schedule_id,
        scheduled_for=scheduled_for,
        status=status,
        recorded_at=DOSE_AT,
        late=False,
    )


def test_datetimes_read_back_as_aware_utc(engine: Engine) -> None:
    written = datetime(2026, 11, 2, 8, tzinfo=HARARE)  # 06:00Z, written in another offset
    with Session(engine) as session, session.begin():
        session.add(
            Patient(display_name="Demo Patient A", timezone="Africa/Harare", created_at=written)
        )
    with Session(engine) as session:
        read = session.scalars(select(Patient.created_at)).one()
    assert read == datetime(2026, 11, 2, 6, tzinfo=UTC)
    assert read.tzinfo is UTC


def test_naive_datetime_is_rejected(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(
            Patient(display_name="Demo Patient A", timezone="UTC", created_at=datetime(2026, 11, 2))
        )
        with pytest.raises(StatementError) as error:
            session.flush()
    assert isinstance(error.value.orig, TypeError)


def test_same_instant_in_another_offset_is_a_duplicate_dose_log(engine: Engine) -> None:
    schedule_id = add_schedule(engine)
    with Session(engine) as session, session.begin():
        session.add(dose_log(schedule_id, DOSE_AT))
    with Session(engine) as session:
        session.add(dose_log(schedule_id, DOSE_AT.astimezone(HARARE), status="skipped"))
        with pytest.raises(IntegrityError):
            session.flush()
    with Session(engine) as session:
        assert session.scalars(select(DoseLog.status)).all() == ["taken"]


def test_schedule_with_logs_cannot_be_deleted(engine: Engine) -> None:
    schedule_id = add_schedule(engine)
    with Session(engine) as session, session.begin():
        session.add(dose_log(schedule_id, DOSE_AT))
    with Session(engine) as session, pytest.raises(IntegrityError):
        session.execute(delete(Schedule).where(Schedule.id == schedule_id))


@pytest.mark.parametrize(
    ("model", "column", "value"),
    [
        (Schedule, "end_date", date(2026, 10, 31)),
        (Schedule, "grace_period_minutes", 241),
        (Schedule, "grace_period_minutes", -1),
        (DoseLog, "status", "lost"),
    ],
    ids=["end-before-start", "grace-241", "grace-minus-1", "unknown-status"],
)
def test_check_constraints_reject_invalid_rows(
    engine: Engine, model: type[Schedule | DoseLog], column: str, value: object
) -> None:
    schedule_id = add_schedule(engine)
    if model is DoseLog:
        with Session(engine) as session, session.begin():
            session.add(dose_log(schedule_id, DOSE_AT))
    with Session(engine) as session, pytest.raises(IntegrityError):
        row_id = schedule_id if model is Schedule else session.scalars(select(DoseLog.id)).one()
        row = session.get(model, row_id)
        assert row is not None
        setattr(row, column, value)
        session.flush()


def test_json_columns_round_trip_lists(engine: Engine) -> None:
    schedule_id = add_schedule(engine)
    with Session(engine) as session:
        schedule = session.get(Schedule, schedule_id)
        assert schedule is not None
        assert (schedule.times_of_day, schedule.days_of_week) == (["08:00", "20:00"], [1, 3, 5])
