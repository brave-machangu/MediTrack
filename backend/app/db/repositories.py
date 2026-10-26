"""Queries shared by several use cases. Each runs one statement, however many rows it covers
(backend/DESIGN.md §5)."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.db.models import DoseLog, Medication, Schedule


@dataclass(frozen=True, slots=True)
class ScheduleRow:
    schedule: Schedule
    has_dose_logs: bool


def schedules_of(
    session: Session, medication_ids: Collection[UUID]
) -> dict[UUID, list[ScheduleRow]]:
    """The schedules of these medications, ordered by start date, with `has_dose_logs`."""
    by_medication: dict[UUID, list[ScheduleRow]] = {
        medication_id: [] for medication_id in medication_ids
    }
    if not by_medication:
        return by_medication
    logged = exists().where(DoseLog.schedule_id == Schedule.id).label("has_dose_logs")
    query = (
        select(Schedule, logged)
        .where(Schedule.medication_id.in_(by_medication))
        .order_by(Schedule.start_date, Schedule.id)
    )
    for schedule, has_dose_logs in session.execute(query):
        by_medication[schedule.medication_id].append(ScheduleRow(schedule, bool(has_dose_logs)))
    return by_medication


def lock_medication(session: Session, medication_id: UUID) -> Medication | None:
    """Loads the medication and locks its row until the transaction ends.

    Every write that can change which schedules overlap takes this lock first, so two such
    writes for one medication run one after the other (DESIGN.md §2). SQLite ignores the lock;
    it allows only one writer at a time anyway.
    """
    query = select(Medication).where(Medication.id == medication_id).with_for_update()
    return session.scalars(query).one_or_none()


def schedules_of_patient(
    session: Session, patient_id: UUID, first: date, last: date
) -> list[tuple[Schedule, Medication]]:
    """The patient's schedules (with their medications) whose date range touches first..last."""
    query = (
        select(Schedule, Medication)
        .join(Medication, Schedule.medication_id == Medication.id)
        .where(
            Medication.patient_id == patient_id,
            Schedule.start_date <= last,
            or_(Schedule.end_date.is_(None), Schedule.end_date >= first),
        )
    )
    return [(schedule, medication) for schedule, medication in session.execute(query)]


def dose_logs_between(
    session: Session, schedule_ids: Collection[UUID], first: datetime, last: datetime
) -> list[DoseLog]:
    """Logs of these schedules for doses scheduled from first to last, both inclusive."""
    if not schedule_ids:
        return []
    query = select(DoseLog).where(
        DoseLog.schedule_id.in_(schedule_ids),
        DoseLog.scheduled_for >= first,
        DoseLog.scheduled_for <= last,
    )
    return list(session.scalars(query))
