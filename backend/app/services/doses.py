"""Planned-dose use cases (FR-04, requirements §4.2–§4.3). Each function is one transaction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.clock import Clock
from app.db.models import DoseLog, Medication, Patient, Schedule
from app.db.repositories import dose_logs_between, schedules_of_patient
from app.domain.errors import NotFound
from app.domain.scheduling import local_today, planned_doses
from app.domain.types import DoseRules, LoggedDose, LogStatus, PlannedDose, ScheduleRule

ONE_DAY = timedelta(days=1)


@dataclass(frozen=True, slots=True)
class DoseView:
    dose: PlannedDose
    medication: Medication


@dataclass(frozen=True, slots=True)
class DayView:
    patient: Patient
    local_date: date
    generated_at: datetime
    doses: list[DoseView]


def day_view(
    session: Session, clock: Clock, rules: DoseRules, patient_id: UUID, local_date: date | None
) -> DayView:
    """The patient's planned doses for a local date; by default the patient's own today (AC-09)."""
    now = clock.now()
    with session.begin():
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise NotFound
        tz = ZoneInfo(patient.timezone)
        day = local_date or local_today(now, tz)
        # A dose on `day` can come from the previous configured date (DESIGN.md Q1).
        rows = schedules_of_patient(session, patient_id, day - ONE_DAY, day)
        schedules = [schedule_rule(schedule, medication) for schedule, medication in rows]
        # Plan once to learn which instants to fetch logs for, then again with the logs.
        unlogged = planned_doses(schedules, [], tz, day, now, rules)
        logs: list[LoggedDose] = []
        if unlogged:
            stored = dose_logs_between(
                session,
                [schedule.schedule_id for schedule in schedules],
                unlogged[0].scheduled_for,
                unlogged[-1].scheduled_for,
            )
            logs = [logged_dose(log) for log in stored]
        doses = planned_doses(schedules, logs, tz, day, now, rules)
    medications = {schedule.id: medication for schedule, medication in rows}
    views = [DoseView(dose, medications[dose.schedule_id]) for dose in doses]
    views.sort(
        key=lambda view: (
            view.dose.scheduled_for,
            view.medication.name.casefold(),
            view.medication.name,
            view.dose.schedule_id,
        )
    )
    return DayView(patient, day, now, views)


def schedule_rule(schedule: Schedule, medication: Medication) -> ScheduleRule:
    return ScheduleRule(
        schedule_id=schedule.id,
        medication_id=medication.id,
        times_of_day=tuple(time.fromisoformat(value) for value in schedule.times_of_day),
        days_of_week=frozenset(schedule.days_of_week),
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        grace=timedelta(minutes=schedule.grace_period_minutes),
        medication_deactivated_at=medication.deactivated_at,
    )


def logged_dose(log: DoseLog) -> LoggedDose:
    return LoggedDose(
        dose_log_id=log.id,
        schedule_id=log.schedule_id,
        scheduled_for=log.scheduled_for,
        status=LogStatus(log.status),
        recorded_at=log.recorded_at,
        late=log.late,
    )
