"""Rules for changing schedules (requirements §4.4, Lead decisions Q2 and Q3). Pure functions."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.errors import InvalidField, ScheduleHasLogs

ONE_DAY = timedelta(days=1)
# Every weekday occurs within seven consecutive dates.
LAST_DAY_OF_FIRST_WEEK = timedelta(days=6)


@dataclass(frozen=True, slots=True)
class ScheduleSpan:
    """The part of a schedule that decides whether it overlaps another."""

    days_of_week: frozenset[int]
    start_date: date
    end_date: date | None  # inclusive; None means no end


def overlaps(a: ScheduleSpan, b: ScheduleSpan) -> bool:
    """True when some date lies in both date ranges on a weekday both schedules use (Q2)."""
    shared_weekdays = a.days_of_week & b.days_of_week
    first = max(a.start_date, b.start_date)
    last = first + LAST_DAY_OF_FIRST_WEEK
    for end in (a.end_date, b.end_date):
        if end is not None:
            last = min(last, end)
    day = first
    while day <= last:
        if day.isoweekday() in shared_weekdays:
            return True
        day += ONE_DAY
    return False


def check_date_order(start: date, end: date | None) -> None:
    if end is not None and end < start:
        raise InvalidField("end_date", "must be on or after start_date")


def check_changes_allowed(has_dose_logs: bool, changed_fields: Collection[str]) -> None:
    """With dose logs, only end_date may change. Resending a stored value isn't a change (Q3)."""
    if has_dose_logs and set(changed_fields) - {"end_date"}:
        raise ScheduleHasLogs


def check_end_date_with_logs(end: date | None, today: date, last_logged: date) -> None:
    """A schedule with logs can't end before today or before its latest logged dose, so no
    recorded dose is hidden. No end at all is always fine."""
    if end is not None and end < max(today, last_logged):
        raise InvalidField(
            "end_date", "must be on or after today and the date of the latest recorded dose"
        )
