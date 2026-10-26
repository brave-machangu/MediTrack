"""Value types for the pure domain functions (backend/DESIGN.md §3).

Instants are timezone-aware UTC datetimes. Dates are patient-local calendar dates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from uuid import UUID


class DoseStatus(StrEnum):
    """`DoseStatus` in api/openapi.yaml."""

    UPCOMING = "upcoming"
    DUE = "due"
    MISSED = "missed"
    TAKEN = "taken"
    SKIPPED = "skipped"


class LogStatus(StrEnum):
    """What a dose log records (`DoseLog.status` in api/openapi.yaml)."""

    TAKEN = "taken"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class DoseRules:
    """Log-window limits from requirements §4.2. Values come from Settings."""

    early_log_window: timedelta
    late_log_limit: timedelta


@dataclass(frozen=True, slots=True)
class ScheduleRule:
    """What planning needs to know about one schedule and its medication."""

    schedule_id: UUID
    medication_id: UUID
    times_of_day: tuple[time, ...]
    days_of_week: frozenset[int]  # ISO weekdays, 1 = Monday
    start_date: date
    end_date: date | None  # inclusive; None means no end
    grace: timedelta
    medication_deactivated_at: datetime | None


@dataclass(frozen=True, slots=True)
class LoggedDose:
    """A stored dose log."""

    dose_log_id: UUID
    schedule_id: UUID
    scheduled_for: datetime
    status: LogStatus
    recorded_at: datetime
    late: bool


@dataclass(frozen=True, slots=True)
class PlannedDose:
    """One computed occurrence of a schedule (requirements §4.1). Never stored."""

    schedule_id: UUID
    medication_id: UUID
    scheduled_for: datetime
    local_date: date  # the patient-local date the dose happens on (DESIGN.md Q1)
    local_time: str  # "HH:MM" of scheduled_for in the patient's timezone
    status: DoseStatus
    late: bool
    log_window_opens_at: datetime
    log_window_closes_at: datetime
    log: LoggedDose | None
