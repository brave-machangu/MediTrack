"""Dose status from the clock (requirements §4.2): AC-07, AC-08 and the status column of the
boundary table in test-strategy.md §3.2.

As in the acceptance criteria: patient in Africa/Harare (UTC+2, no DST), schedule 08:00 every
day, grace 60 minutes. The dose of 2026-11-02 is at 2026-11-02T06:00:00Z.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.scheduling import dose_status, planned_doses
from app.domain.types import DoseStatus, LogStatus, PlannedDose, ScheduleRule
from tests.unit.domain.factories import RULES, make_log, make_schedule, utc

HARARE = ZoneInfo("Africa/Harare")
DOSE_DATE = date(2026, 11, 2)
DOSE_AT = utc(2026, 11, 2, 6)


def harare(day: int, hour: int, minute: int, second: int = 0) -> datetime:
    """A Harare wall-clock time in November 2026, as a UTC instant."""
    return datetime(2026, 11, day, hour, minute, second, tzinfo=HARARE).astimezone(UTC)


def only_dose(now: datetime, schedule: ScheduleRule | None = None) -> PlannedDose:
    doses = planned_doses([schedule or make_schedule()], [], HARARE, DOSE_DATE, now, RULES)
    assert len(doses) == 1
    return doses[0]


def test_dose_before_scheduled_time_is_upcoming_ac07() -> None:
    dose = only_dose(utc(2026, 11, 2, 5, 30))  # 07:30 local
    assert dose.scheduled_for == DOSE_AT
    assert (dose.local_date, dose.local_time) == (DOSE_DATE, "08:00")
    assert dose.status is DoseStatus.UPCOMING


def test_dose_is_upcoming_until_its_scheduled_instant() -> None:
    assert only_dose(harare(2, 7, 59, 59)).status is DoseStatus.UPCOMING


@pytest.mark.parametrize("now", [harare(2, 8, 0), harare(2, 9, 0)], ids=["08:00", "09:00"])
def test_dose_is_due_from_scheduled_time_to_end_of_grace_ac08(now: datetime) -> None:
    assert only_dose(now).status is DoseStatus.DUE


def test_dose_is_missed_one_second_after_grace_ac08() -> None:
    assert only_dose(harare(2, 9, 0, 1)).status is DoseStatus.MISSED


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (harare(2, 6, 59, 59), DoseStatus.UPCOMING),
        (harare(2, 7, 0, 0), DoseStatus.UPCOMING),
        (harare(2, 8, 0, 0), DoseStatus.DUE),
        (harare(2, 9, 0, 0), DoseStatus.DUE),
        (harare(2, 9, 0, 1), DoseStatus.MISSED),
        (harare(3, 8, 0, 0), DoseStatus.MISSED),
        (harare(3, 8, 0, 1), DoseStatus.MISSED),
    ],
    ids=[
        "06:59:59",
        "07:00:00",
        "08:00:00",
        "09:00:00",
        "09:00:01",
        "next-08:00:00",
        "next-08:00:01",
    ],
)
def test_status_boundary_table(now: datetime, expected: DoseStatus) -> None:
    assert only_dose(now).status is expected


@pytest.mark.parametrize(
    ("now", "expected"),
    [(harare(2, 8, 0, 0), DoseStatus.DUE), (harare(2, 8, 0, 1), DoseStatus.MISSED)],
    ids=["at-08:00:00", "at-08:00:01"],
)
def test_grace_zero_is_missed_one_second_after_scheduled_time(
    now: datetime, expected: DoseStatus
) -> None:
    assert only_dose(now, make_schedule(grace_minutes=0)).status is expected


@pytest.mark.parametrize(
    ("now", "expected"),
    [(harare(2, 12, 0, 0), DoseStatus.DUE), (harare(2, 12, 0, 1), DoseStatus.MISSED)],
    ids=["at-12:00:00", "at-12:00:01"],
)
def test_grace_240_is_due_until_four_hours_after(now: datetime, expected: DoseStatus) -> None:
    assert only_dose(now, make_schedule(grace_minutes=240)).status is expected


@pytest.mark.parametrize(
    ("log_status", "expected"),
    [(LogStatus.TAKEN, DoseStatus.TAKEN), (LogStatus.SKIPPED, DoseStatus.SKIPPED)],
)
@pytest.mark.parametrize("now", [harare(2, 7, 30), harare(2, 12, 0)], ids=["before", "after"])
def test_logged_dose_takes_its_status_from_the_log(
    log_status: LogStatus, expected: DoseStatus, now: datetime
) -> None:
    log = make_log(DOSE_AT, log_status, late=True)
    [dose] = planned_doses([make_schedule()], [log], HARARE, DOSE_DATE, now, RULES)
    assert dose.status is expected
    assert dose.late is True
    assert dose.log == log


def test_unlogged_dose_is_not_late_even_when_missed() -> None:
    dose = only_dose(harare(2, 12, 0))
    assert dose.status is DoseStatus.MISSED
    assert dose.late is False
    assert dose.log is None


def test_log_window_opens_an_hour_before_and_closes_a_day_after() -> None:
    dose = only_dose(harare(2, 7, 30))
    assert dose.log_window_opens_at == utc(2026, 11, 2, 5)
    assert dose.log_window_closes_at == utc(2026, 11, 3, 6)


def test_dose_status_compares_instants_not_wall_clock_offsets() -> None:
    # The same instant written in another offset gives the same answer.
    now_in_tokyo = harare(2, 9, 0, 1).astimezone(ZoneInfo("Asia/Tokyo"))
    assert dose_status(DOSE_AT, timedelta(minutes=60), None, now_in_tokyo) is DoseStatus.MISSED
