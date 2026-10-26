"""Builders for domain values in unit tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from app.domain.types import DoseRules, LoggedDose, LogStatus, ScheduleRule

SCHEDULE_ID = UUID(int=1)
MEDICATION_ID = UUID(int=2)
EVERY_DAY = frozenset(range(1, 8))
# The defaults in requirements §4.2.
RULES = DoseRules(early_log_window=timedelta(minutes=60), late_log_limit=timedelta(minutes=1440))


def utc(*parts: int) -> datetime:
    """utc(2026, 11, 2, 6) == 2026-11-02T06:00:00Z."""
    year, month, day, *rest = parts
    return datetime(year, month, day, *rest, tzinfo=UTC)


def make_schedule(
    *times: str,
    days: frozenset[int] = EVERY_DAY,
    start: date = date(2000, 1, 1),
    end: date | None = None,
    grace_minutes: int = 60,
    deactivated_at: datetime | None = None,
    schedule_id: UUID = SCHEDULE_ID,
) -> ScheduleRule:
    return ScheduleRule(
        schedule_id=schedule_id,
        medication_id=MEDICATION_ID,
        times_of_day=tuple(time.fromisoformat(t) for t in times or ("08:00",)),
        days_of_week=days,
        start_date=start,
        end_date=end,
        grace=timedelta(minutes=grace_minutes),
        medication_deactivated_at=deactivated_at,
    )


def make_log(
    scheduled_for: datetime,
    status: LogStatus = LogStatus.TAKEN,
    *,
    late: bool = False,
    schedule_id: UUID = SCHEDULE_ID,
) -> LoggedDose:
    return LoggedDose(
        dose_log_id=UUID(int=99),
        schedule_id=schedule_id,
        scheduled_for=scheduled_for,
        status=status,
        recorded_at=scheduled_for + timedelta(minutes=5),
        late=late,
    )
