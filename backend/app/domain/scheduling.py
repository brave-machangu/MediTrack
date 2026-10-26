"""Planned doses, DST policy and dose status (requirements §4.2–§4.3, ADR-002, ADR-004).

Pure functions. Instants are timezone-aware UTC datetimes and `now` is always passed in.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.domain.errors import DoseNotPlanned, MedicationInactive, OutsideLogWindow
from app.domain.types import (
    DoseRules,
    DoseStatus,
    LoggedDose,
    LogStatus,
    PlannedDose,
    ScheduleRule,
)

ONE_DAY = timedelta(days=1)


def local_today(now: datetime, tz: ZoneInfo) -> date:
    """The patient's calendar date at `now` (requirements §4.3, AC-09)."""
    return now.astimezone(tz).date()


def local_to_utc(local_date: date, local_time: time, tz: ZoneInfo) -> datetime:
    """Convert a patient-local wall time to a UTC instant.

    fold=0 applies the UTC offset in effect before a transition: in a DST gap the dose moves
    forward by the length of the gap, and in an overlap it is the first occurrence.
    """
    return datetime.combine(local_date, local_time, tzinfo=tz).replace(fold=0).astimezone(UTC)


def dose_status(
    scheduled_for: datetime, grace: timedelta, log: LoggedDose | None, now: datetime
) -> DoseStatus:
    """Status of one planned dose at `now` (requirements §4.2)."""
    if log is not None:
        return DoseStatus.TAKEN if log.status == LogStatus.TAKEN else DoseStatus.SKIPPED
    if now < scheduled_for:
        return DoseStatus.UPCOMING
    if now <= scheduled_for + grace:
        return DoseStatus.DUE
    return DoseStatus.MISSED


def log_window(scheduled_for: datetime, rules: DoseRules) -> tuple[datetime, datetime]:
    """First and last instant at which the dose can be logged, both inclusive."""
    return scheduled_for - rules.early_log_window, scheduled_for + rules.late_log_limit


def is_late(scheduled_for: datetime, grace: timedelta, recorded_at: datetime) -> bool:
    """A dose recorded after its grace period ends is late (requirements §4.2)."""
    return recorded_at > scheduled_for + grace


def check_can_log(
    schedule: ScheduleRule, scheduled_for: datetime, tz: ZoneInfo, now: datetime, rules: DoseRules
) -> None:
    """Raises unless `scheduled_for` can be recorded at `now`. The checks run in a fixed order
    (DESIGN.md §0): inactive medication, not a planned dose, outside the log window."""
    if schedule.medication_deactivated_at is not None:
        raise MedicationInactive
    planned = planned_doses([schedule], [], tz, scheduled_for.astimezone(tz).date(), now, rules)
    if scheduled_for not in {dose.scheduled_for for dose in planned}:
        raise DoseNotPlanned
    opens_at, closes_at = log_window(scheduled_for, rules)
    if not opens_at <= now <= closes_at:
        raise OutsideLogWindow


def planned_doses(
    schedules: Sequence[ScheduleRule],
    logs: Sequence[LoggedDose],
    tz: ZoneInfo,
    local_date: date,
    now: datetime,
    rules: DoseRules,
) -> list[PlannedDose]:
    """The doses that happen on patient-local `local_date`, ordered by instant."""
    logs_by_dose = {(log.schedule_id, log.scheduled_for): log for log in logs}
    doses: list[PlannedDose] = []
    for schedule in schedules:
        for instant in _instants_on(schedule, tz, local_date):
            log = logs_by_dose.get((schedule.schedule_id, instant))
            opens_at, closes_at = log_window(instant, rules)
            doses.append(
                PlannedDose(
                    schedule_id=schedule.schedule_id,
                    medication_id=schedule.medication_id,
                    scheduled_for=instant,
                    local_date=local_date,
                    local_time=instant.astimezone(tz).strftime("%H:%M"),
                    status=dose_status(instant, schedule.grace, log, now),
                    late=log.late if log is not None else False,
                    log_window_opens_at=opens_at,
                    log_window_closes_at=closes_at,
                    log=log,
                )
            )
    doses.sort(key=_by_instant)
    return doses


def planned_doses_between(
    schedules: Sequence[ScheduleRule],
    logs: Sequence[LoggedDose],
    tz: ZoneInfo,
    first: date,
    last: date,
    now: datetime,
    rules: DoseRules,
) -> list[PlannedDose]:
    """`planned_doses` for every date from `first` to `last`, both inclusive.

    Each instant has exactly one local date, so no dose appears twice in the result.
    """
    doses: list[PlannedDose] = []
    day = first
    while day <= last:
        doses += planned_doses(schedules, logs, tz, day, now, rules)
        day += ONE_DAY
    return doses


def _instants_on(schedule: ScheduleRule, tz: ZoneInfo, local_date: date) -> list[datetime]:
    """The schedule's instants whose local date is `local_date`, each listed once."""
    instants: set[datetime] = set()
    # A DST gap can push a time past midnight, so a dose on `local_date` may come from the
    # previous configured date (DESIGN.md Q1). No gap is longer than a day, and fold=0 never
    # moves a time backwards, so the previous date is the only other one to look at.
    for configured_date in (local_date - ONE_DAY, local_date):
        if not _scheduled_on(schedule, configured_date):
            continue
        for local_time in schedule.times_of_day:
            instant = local_to_utc(configured_date, local_time, tz)
            if instant.astimezone(tz).date() != local_date:
                continue
            deactivated_at = schedule.medication_deactivated_at
            if deactivated_at is not None and instant >= deactivated_at:
                continue  # Only doses before deactivation are planned (requirements §4.4).
            instants.add(instant)
    return sorted(instants)


def _scheduled_on(schedule: ScheduleRule, configured_date: date) -> bool:
    """Start date, end date and weekdays apply to the date the user configured."""
    if configured_date < schedule.start_date:
        return False
    if schedule.end_date is not None and configured_date > schedule.end_date:
        return False
    return configured_date.isoweekday() in schedule.days_of_week


def _by_instant(dose: PlannedDose) -> tuple[datetime, UUID]:
    return dose.scheduled_for, dose.schedule_id
