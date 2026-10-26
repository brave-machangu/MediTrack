"""Local times to UTC instants around DST changes (requirements §4.3, ADR-004): AC-11, AC-12,
zones east and west of UTC, and the known edge case of a gap that crosses midnight
(DESIGN.md Q1). Every expected instant was checked independently with zoneinfo.
"""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.domain.scheduling import local_to_utc, planned_doses, planned_doses_between
from app.domain.types import ScheduleRule
from tests.unit.domain.factories import RULES, make_schedule, utc

LONDON = ZoneInfo("Europe/London")
NUUK = ZoneInfo("America/Nuuk")  # 2026-03-28: clocks jump from 23:00 Saturday to 00:00 Sunday
APIA = ZoneInfo("Pacific/Apia")  # 2011-12-30 doesn't exist: 29 Dec was followed by 31 Dec
NOW = utc(2026, 1, 1)


def plan(schedule: ScheduleRule, tz: ZoneInfo, day: date) -> list[tuple[datetime, date, str]]:
    doses = planned_doses([schedule], [], tz, day, NOW, RULES)
    return [(dose.scheduled_for, dose.local_date, dose.local_time) for dose in doses]


def test_london_gap_shifts_dose_forward_ac11() -> None:
    assert plan(make_schedule("01:30"), LONDON, date(2027, 3, 28)) == [
        (utc(2027, 3, 28, 1, 30), date(2027, 3, 28), "02:30")
    ]


def test_london_gap_merges_two_times_into_one_dose_ac11() -> None:
    assert plan(make_schedule("01:30", "02:30"), LONDON, date(2027, 3, 28)) == [
        (utc(2027, 3, 28, 1, 30), date(2027, 3, 28), "02:30")
    ]


def test_london_overlap_plans_first_occurrence_once_ac12() -> None:
    assert plan(make_schedule("01:30"), LONDON, date(2026, 10, 25)) == [
        (utc(2026, 10, 25, 0, 30), date(2026, 10, 25), "01:30")
    ]


def test_local_to_utc_uses_the_offset_before_a_transition() -> None:
    assert local_to_utc(date(2027, 3, 28), time(1, 30), LONDON) == utc(2027, 3, 28, 1, 30)
    assert local_to_utc(date(2026, 10, 25), time(1, 30), LONDON) == utc(2026, 10, 25, 0, 30)


def test_tokyo_dose_falls_on_the_previous_utc_date() -> None:
    assert plan(make_schedule("08:00"), ZoneInfo("Asia/Tokyo"), date(2026, 11, 2)) == [
        (utc(2026, 11, 1, 23), date(2026, 11, 2), "08:00")
    ]


def test_new_york_dose_follows_daylight_saving_time() -> None:
    new_york = ZoneInfo("America/New_York")
    assert plan(make_schedule("08:00"), new_york, date(2026, 7, 1)) == [
        (utc(2026, 7, 1, 12), date(2026, 7, 1), "08:00")
    ]
    assert plan(make_schedule("08:00"), new_york, date(2026, 12, 1)) == [
        (utc(2026, 12, 1, 13), date(2026, 12, 1), "08:00")
    ]


def test_nuuk_saturday_2330_and_sunday_0030_are_one_dose_on_sunday() -> None:
    schedule = make_schedule("00:30", "23:30")
    saturday, sunday = date(2026, 3, 28), date(2026, 3, 29)
    assert plan(schedule, NUUK, saturday) == [(utc(2026, 3, 28, 2, 30), saturday, "00:30")]
    assert plan(schedule, NUUK, sunday) == [
        (utc(2026, 3, 29, 1, 30), sunday, "00:30"),
        (utc(2026, 3, 30, 0, 30), sunday, "23:30"),
    ]
    both_days = planned_doses_between([schedule], [], NUUK, saturday, sunday, NOW, RULES)
    assert len({dose.scheduled_for for dose in both_days}) == len(both_days) == 3


def test_shifted_dose_follows_the_bounds_of_its_configured_date() -> None:
    saturday, sunday = date(2026, 3, 28), date(2026, 3, 29)
    ends_saturday = make_schedule("23:30", end=saturday)
    starts_sunday = make_schedule("23:30", start=sunday)
    assert plan(ends_saturday, NUUK, sunday) == [(utc(2026, 3, 29, 1, 30), sunday, "00:30")]
    assert plan(starts_sunday, NUUK, sunday) == [(utc(2026, 3, 30, 0, 30), sunday, "23:30")]


def test_apia_skipped_day_plans_each_instant_once() -> None:
    schedule = make_schedule("08:00")
    assert plan(schedule, APIA, date(2011, 12, 29)) == [
        (utc(2011, 12, 29, 18), date(2011, 12, 29), "08:00")
    ]
    assert plan(schedule, APIA, date(2011, 12, 30)) == []
    assert plan(schedule, APIA, date(2011, 12, 31)) == [
        (utc(2011, 12, 30, 18), date(2011, 12, 31), "08:00")
    ]
    three_days = planned_doses_between(
        [schedule], [], APIA, date(2011, 12, 29), date(2011, 12, 31), NOW, RULES
    )
    assert len({dose.scheduled_for for dose in three_days}) == len(three_days) == 2
