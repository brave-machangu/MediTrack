"""Missed doses and daily adherence (FR-08, FR-09). Each function is one transaction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.clock import Clock
from app.db.models import Patient
from app.domain.adherence import DailySummary, daily_summary
from app.domain.scheduling import local_today, missed_doses, missed_range
from app.domain.types import DoseRules
from app.services.doses import DoseView, day_view, load_patient, plan_between


@dataclass(frozen=True, slots=True)
class AdherenceView:
    patient: Patient
    local_date: date
    summary: DailySummary


def list_missed_doses(
    session: Session,
    clock: Clock,
    rules: DoseRules,
    patient_id: UUID,
    start: date | None,
    end: date | None,
) -> list[DoseView]:
    """Doses that are missed right now in a range of local dates, newest first (AC-22)."""
    now = clock.now()
    with session.begin():
        patient = load_patient(session, patient_id)
        first, last = missed_range(start, end, local_today(now, ZoneInfo(patient.timezone)))
        views = plan_between(session, patient, first, last, now, rules)
    by_dose = {(view.dose.schedule_id, view.dose.scheduled_for): view for view in views}
    missed = missed_doses(view.dose for view in views)
    return [by_dose[(dose.schedule_id, dose.scheduled_for)] for dose in missed]


def daily_adherence(
    session: Session, clock: Clock, rules: DoseRules, patient_id: UUID, local_date: date | None
) -> AdherenceView:
    """The summary of one local date; by default the patient's own today."""
    day = day_view(session, clock, rules, patient_id, local_date)
    summary = daily_summary([view.dose for view in day.doses])
    return AdherenceView(day.patient, day.local_date, summary)
