"""Which doses are planned for a patient-local date: AC-09, AC-10 and AC-35."""

from __future__ import annotations

import time as system_time
from collections.abc import Callable, Iterator
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from app.domain.scheduling import local_today, planned_doses, planned_doses_between
from app.domain.types import PlannedDose, ScheduleRule
from tests.unit.domain.factories import RULES, make_log, make_schedule, utc

HARARE = ZoneInfo("Africa/Harare")
NOW = utc(2026, 11, 2, 5, 30)
MONDAY_TO_FRIDAY = frozenset({1, 2, 3, 4, 5})


def plan(schedule: ScheduleRule, day: date, now: datetime = NOW) -> list[PlannedDose]:
    return planned_doses([schedule], [], HARARE, day, now, RULES)


def test_local_today_is_patient_date_not_utc_date_ac09() -> None:
    now = utc(2026, 11, 1, 23, 30)
    assert now.date() == date(2026, 11, 1)
    assert local_today(now, HARARE) == date(2026, 11, 2)


def test_local_today_west_of_utc_is_the_previous_date() -> None:
    assert local_today(utc(2026, 11, 2, 5), ZoneInfo("America/Los_Angeles")) == date(2026, 11, 1)


@pytest.mark.parametrize(
    ("day", "planned"),
    [
        (date(2026, 11, 1), 0),
        (date(2026, 11, 2), 1),
        (date(2026, 11, 4), 1),
        (date(2026, 11, 5), 0),
    ],
    ids=["day-before-start", "start-date", "end-date", "day-after-end"],
)
def test_no_doses_outside_start_and_end_dates_ac10(day: date, planned: int) -> None:
    schedule = make_schedule(start=date(2026, 11, 2), end=date(2026, 11, 4))
    assert len(plan(schedule, day)) == planned


@pytest.mark.parametrize(
    ("day", "planned"),
    [
        (date(2026, 11, 6), 1),
        (date(2026, 11, 7), 0),
        (date(2026, 11, 8), 0),
        (date(2026, 11, 9), 1),
    ],
    ids=["friday", "saturday", "sunday", "monday"],
)
def test_no_doses_on_excluded_weekdays_ac10(day: date, planned: int) -> None:
    assert len(plan(make_schedule(days=MONDAY_TO_FRIDAY), day)) == planned


@pytest.mark.parametrize(
    ("deactivated_at", "planned"),
    [(utc(2026, 11, 2, 5, 59, 59), 0), (utc(2026, 11, 2, 6), 0), (utc(2026, 11, 2, 6, 0, 1), 1)],
    ids=["second-before-dose", "at-dose-instant", "second-after-dose"],
)
def test_deactivated_medication_plans_only_doses_before_deactivation_ac10(
    deactivated_at: datetime, planned: int
) -> None:
    schedule = make_schedule("08:00", deactivated_at=deactivated_at)
    assert len(plan(schedule, date(2026, 11, 2))) == planned


def test_deactivation_keeps_earlier_doses_of_the_same_day() -> None:
    schedule = make_schedule("08:00", "20:00", deactivated_at=utc(2026, 11, 2, 10))
    assert [dose.local_time for dose in plan(schedule, date(2026, 11, 2))] == ["08:00"]


def test_doses_of_several_schedules_are_ordered_by_instant() -> None:
    evening = make_schedule("20:00", schedule_id=UUID(int=10))
    morning = make_schedule("13:00", "07:00", schedule_id=UUID(int=11))
    doses = planned_doses([evening, morning], [], HARARE, date(2026, 11, 2), NOW, RULES)
    assert [(dose.local_time, dose.schedule_id) for dose in doses] == [
        ("07:00", UUID(int=11)),
        ("13:00", UUID(int=11)),
        ("20:00", UUID(int=10)),
    ]


def test_log_counts_only_for_its_own_schedule_and_instant() -> None:
    other_schedule = make_log(utc(2026, 11, 2, 6), schedule_id=UUID(int=10))
    other_instant = make_log(utc(2026, 11, 1, 6))
    [dose] = planned_doses(
        [make_schedule()], [other_schedule, other_instant], HARARE, date(2026, 11, 2), NOW, RULES
    )
    assert dose.log is None


def test_planned_doses_between_includes_both_end_dates() -> None:
    doses = planned_doses_between(
        [make_schedule()], [], HARARE, date(2026, 11, 2), date(2026, 11, 4), NOW, RULES
    )
    assert [dose.local_date for dose in doses] == [
        date(2026, 11, 2),
        date(2026, 11, 3),
        date(2026, 11, 4),
    ]


@pytest.fixture
def set_process_timezone(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[str], None]]:
    def set_timezone(name: str) -> None:
        monkeypatch.setenv("TZ", name)
        system_time.tzset()

    yield set_timezone
    monkeypatch.undo()
    system_time.tzset()


@pytest.mark.skipif(
    not hasattr(system_time, "tzset"),
    reason="time.tzset() doesn't exist on Windows; the CI matrix covers AC-35 on Linux",
)
def test_results_do_not_depend_on_process_timezone_ac35(
    set_process_timezone: Callable[[str], None],
) -> None:
    results = []
    for process_timezone in ("UTC", "America/Los_Angeles", "Asia/Tokyo"):
        set_process_timezone(process_timezone)
        results.append(
            (
                local_today(utc(2026, 11, 1, 23, 30), HARARE),
                plan(make_schedule("00:30", "08:00", "23:30"), date(2026, 11, 2)),
            )
        )
    assert results[0] == results[1] == results[2]
