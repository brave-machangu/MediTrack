"""Whether a dose can be logged now, and whether it's late (requirements §4.2): AC-15, AC-16 and
the log column of the boundary table in test-strategy.md §3.2.

Patient in Africa/Harare (UTC+2), schedule 08:00 every day, grace 60 minutes. The dose of
2026-11-02 is at 06:00Z.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.errors import DomainError, DoseNotPlanned, MedicationInactive, OutsideLogWindow
from app.domain.scheduling import check_can_log, is_late
from app.domain.types import ScheduleRule
from tests.unit.domain.factories import RULES, make_schedule, utc

HARARE = ZoneInfo("Africa/Harare")
DOSE_AT = utc(2026, 11, 2, 6)
GRACE = timedelta(minutes=60)


def harare(day: int, hour: int, minute: int, second: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, second, tzinfo=HARARE).astimezone(UTC)


def test_log_after_grace_is_late_ac15() -> None:
    assert is_late(DOSE_AT, GRACE, harare(2, 9, 30)) is True


@pytest.mark.parametrize(
    ("recorded_at", "late"),
    [(harare(2, 9, 0, 0), False), (harare(2, 9, 0, 1), True), (harare(2, 7, 0), False)],
    ids=["end-of-grace", "second-after-grace", "early"],
)
def test_lateness_boundary(recorded_at: datetime, late: bool) -> None:
    assert is_late(DOSE_AT, GRACE, recorded_at) is late


@pytest.mark.parametrize(
    ("now", "allowed"),
    [
        (harare(2, 6, 59, 59), False),
        (harare(2, 7, 0, 0), True),
        (harare(2, 8, 0, 0), True),
        (harare(2, 9, 0, 0), True),
        (harare(2, 9, 0, 1), True),
        (harare(3, 8, 0, 0), True),
        (harare(3, 8, 0, 1), False),
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
def test_log_window_boundary_table(now: datetime, allowed: bool) -> None:
    if allowed:
        check_can_log(make_schedule(), DOSE_AT, HARARE, now, RULES)
    else:
        with pytest.raises(OutsideLogWindow):
            check_can_log(make_schedule(), DOSE_AT, HARARE, now, RULES)


def test_log_more_than_an_hour_early_is_outside_window_ac16() -> None:
    with pytest.raises(OutsideLogWindow):
        check_can_log(make_schedule(), DOSE_AT, HARARE, DOSE_AT - timedelta(minutes=61), RULES)


def test_log_more_than_a_day_late_is_outside_window_ac16() -> None:
    with pytest.raises(OutsideLogWindow):
        check_can_log(make_schedule(), DOSE_AT, HARARE, DOSE_AT + timedelta(days=2), RULES)


@pytest.mark.parametrize(
    ("schedule", "scheduled_for"),
    [
        (make_schedule(), utc(2026, 11, 2, 6, 1)),  # not a planned time
        (make_schedule(), utc(2026, 11, 2, 6, 0, 0, 1)),  # a microsecond off
        (make_schedule(days=frozenset({2, 3, 4, 5, 6, 7})), DOSE_AT),  # Monday is excluded
        (make_schedule(start=date(2026, 11, 3)), DOSE_AT),  # before start_date
        (make_schedule(end=date(2026, 11, 1)), DOSE_AT),  # after end_date
    ],
    ids=["off-time", "microsecond", "excluded-weekday", "before-start", "after-end"],
)
def test_unplanned_instant_is_not_planned_ac16(
    schedule: ScheduleRule, scheduled_for: datetime
) -> None:
    with pytest.raises(DoseNotPlanned):
        check_can_log(schedule, scheduled_for, HARARE, harare(2, 8, 30), RULES)


def test_planned_instant_written_in_another_offset_can_be_logged() -> None:
    in_tokyo = DOSE_AT.astimezone(ZoneInfo("Asia/Tokyo"))
    check_can_log(make_schedule(), in_tokyo, HARARE, harare(2, 8, 30), RULES)


def test_inactive_medication_cannot_be_logged_even_for_an_earlier_dose_ac19() -> None:
    schedule = make_schedule(deactivated_at=utc(2026, 11, 2, 7))  # after the 06:00Z dose
    with pytest.raises(MedicationInactive):
        check_can_log(schedule, DOSE_AT, HARARE, harare(2, 9, 30), RULES)


@pytest.mark.parametrize(
    ("schedule", "expected"),
    [
        (make_schedule(deactivated_at=utc(2026, 11, 1)), MedicationInactive),
        (make_schedule(), DoseNotPlanned),
    ],
    ids=["inactive-before-not-planned", "not-planned-before-window"],
)
def test_checks_run_in_the_documented_order(
    schedule: ScheduleRule, expected: type[DomainError]
) -> None:
    # DESIGN.md §0: MEDICATION_INACTIVE, then DOSE_NOT_PLANNED, then OUTSIDE_LOG_WINDOW.
    # The instant is unplanned and the clock is days past any window.
    scheduled_for, now = utc(2026, 11, 2, 6, 1), harare(5, 8, 0)
    with pytest.raises(expected):
        check_can_log(schedule, scheduled_for, HARARE, now, RULES)


def test_dst_shifted_doses_can_be_logged() -> None:
    london = ZoneInfo("Europe/London")
    check_can_log(
        make_schedule("01:30"), utc(2027, 3, 28, 1, 30), london, utc(2027, 3, 28, 2), RULES
    )
    nuuk = ZoneInfo("America/Nuuk")
    ends_saturday = make_schedule("23:30", end=date(2026, 3, 28))
    check_can_log(ends_saturday, utc(2026, 3, 29, 1, 30), nuuk, utc(2026, 3, 29, 2), RULES)
