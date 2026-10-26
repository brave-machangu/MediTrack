"""Schedule use cases (FR-03, requirements §4.4). Each function is one transaction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import Clock
from app.db.models import DoseLog, Medication, Patient, Schedule
from app.db.repositories import ScheduleRow, lock_medication, schedules_of
from app.domain.errors import MedicationInactive, NotFound, ScheduleHasLogs, ScheduleOverlap
from app.domain.schedule_rules import (
    ScheduleSpan,
    check_changes_allowed,
    check_date_order,
    check_end_date_with_logs,
    overlaps,
)
from app.domain.scheduling import local_today


@dataclass(frozen=True, slots=True)
class ScheduleSpec:
    times_of_day: list[str]
    days_of_week: list[int]
    start_date: date
    end_date: date | None
    grace_period_minutes: int


@dataclass(frozen=True, slots=True)
class ScheduleChanges:
    """A PATCH. None means "not sent"; `end_date` may be sent as null, hence its flag."""

    times_of_day: list[str] | None = None
    days_of_week: list[int] | None = None
    start_date: date | None = None
    grace_period_minutes: int | None = None
    end_date_sent: bool = False
    end_date: date | None = None


# Changes to these can make two schedules overlap.
OVERLAP_FIELDS = frozenset({"days_of_week", "start_date", "end_date"})


def list_schedules(session: Session, medication_id: UUID) -> list[ScheduleRow]:
    with session.begin():
        if session.get(Medication, medication_id) is None:
            raise NotFound
        return schedules_of(session, [medication_id])[medication_id]


def create_schedule(session: Session, medication_id: UUID, spec: ScheduleSpec) -> ScheduleRow:
    # Stored sorted: same meaning, deterministic output, and Q3 can compare values directly.
    schedule = Schedule(
        medication_id=medication_id,
        times_of_day=sorted(spec.times_of_day),
        days_of_week=sorted(spec.days_of_week),
        start_date=spec.start_date,
        end_date=spec.end_date,
        grace_period_minutes=spec.grace_period_minutes,
    )
    with session.begin():
        medication = lock_medication(session, medication_id)
        if medication is None:
            raise NotFound
        if medication.deactivated_at is not None:
            raise MedicationInactive
        check_date_order(schedule.start_date, schedule.end_date)
        _check_no_overlap(session, schedule)
        session.add(schedule)
    return ScheduleRow(schedule, has_dose_logs=False)


def update_schedule(
    session: Session, clock: Clock, schedule_id: UUID, changes: ScheduleChanges
) -> ScheduleRow:
    with session.begin():
        medication_id = session.scalar(
            select(Schedule.medication_id).where(Schedule.id == schedule_id)
        )
        if medication_id is None:
            raise NotFound
        # Lock first, then load the schedule, so the values compared below are current.
        medication = lock_medication(session, medication_id)
        schedule = session.get(Schedule, schedule_id)
        if medication is None or schedule is None:
            raise NotFound

        proposed = _proposed_values(schedule, changes)
        changed = {name for name, value in proposed.items() if getattr(schedule, name) != value}
        has_dose_logs = _has_dose_logs(session, schedule_id)
        check_changes_allowed(has_dose_logs, changed)
        for name in changed:
            setattr(schedule, name, proposed[name])
        check_date_order(schedule.start_date, schedule.end_date)
        if has_dose_logs and "end_date" in changed:
            today, last_logged = _today_and_last_logged_date(
                session, medication, schedule_id, clock
            )
            check_end_date_with_logs(schedule.end_date, today, last_logged)
        if changed & OVERLAP_FIELDS:
            _check_no_overlap(session, schedule)
    return ScheduleRow(schedule, has_dose_logs)


def delete_schedule(session: Session, schedule_id: UUID) -> None:
    with session.begin():
        schedule = session.get(Schedule, schedule_id)
        if schedule is None:
            raise NotFound
        if _has_dose_logs(session, schedule_id):
            raise ScheduleHasLogs
        session.delete(schedule)
        try:
            session.flush()
        except IntegrityError as error:
            # A dose was logged after the check above; the RESTRICT foreign key refused the
            # delete (requirements §4.4).
            raise ScheduleHasLogs from error


def _proposed_values(schedule: Schedule, changes: ScheduleChanges) -> dict[str, object]:
    proposed: dict[str, object] = {}
    if changes.times_of_day is not None:
        proposed["times_of_day"] = sorted(changes.times_of_day)
    if changes.days_of_week is not None:
        proposed["days_of_week"] = sorted(changes.days_of_week)
    if changes.start_date is not None:
        proposed["start_date"] = changes.start_date
    if changes.grace_period_minutes is not None:
        proposed["grace_period_minutes"] = changes.grace_period_minutes
    if changes.end_date_sent:
        proposed["end_date"] = changes.end_date
    return proposed


def _check_no_overlap(session: Session, schedule: Schedule) -> None:
    """Call with the medication row locked (lock_medication), so no other write can race."""
    others = session.scalars(
        select(Schedule).where(
            Schedule.medication_id == schedule.medication_id, Schedule.id != schedule.id
        )
    ).all()
    candidate = _span(schedule)
    if any(overlaps(candidate, _span(other)) for other in others):
        raise ScheduleOverlap


def _span(schedule: Schedule) -> ScheduleSpan:
    return ScheduleSpan(
        days_of_week=frozenset(schedule.days_of_week),
        start_date=schedule.start_date,
        end_date=schedule.end_date,
    )


def _has_dose_logs(session: Session, schedule_id: UUID) -> bool:
    return bool(session.scalar(select(exists().where(DoseLog.schedule_id == schedule_id))))


def _today_and_last_logged_date(
    session: Session, medication: Medication, schedule_id: UUID, clock: Clock
) -> tuple[date, date]:
    """The patient's local today and the local date of the schedule's latest logged dose."""
    patient = session.get(Patient, medication.patient_id)
    latest = session.scalar(
        select(func.max(DoseLog.scheduled_for)).where(DoseLog.schedule_id == schedule_id)
    )
    if patient is None or latest is None:
        raise NotFound  # unreachable: foreign keys, and has_dose_logs was checked
    tz = ZoneInfo(patient.timezone)
    return local_today(clock.now(), tz), local_today(latest, tz)
