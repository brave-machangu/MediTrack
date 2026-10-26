"""Schedule rules (requirements §4.4): AC-05 (date order), AC-06 (with logs), AC-34 (overlap)
and Lead decisions Q2 and Q3. 2026-11-02 is a Monday."""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.errors import InvalidField, ScheduleHasLogs
from app.domain.schedule_rules import (
    ScheduleSpan,
    check_changes_allowed,
    check_date_order,
    check_end_date_with_logs,
    overlaps,
)

EVERY_DAY = frozenset(range(1, 8))
MON_TO_FRI = frozenset({1, 2, 3, 4, 5})
SAT_SUN = frozenset({6, 7})


def span(start: date, end: date | None = None, days: frozenset[int] = EVERY_DAY) -> ScheduleSpan:
    return ScheduleSpan(days_of_week=days, start_date=start, end_date=end)


OPEN_DAILY_FROM_NOV_1 = span(date(2026, 11, 1))


def test_open_ended_schedule_overlaps_a_later_start_ac34() -> None:
    assert overlaps(OPEN_DAILY_FROM_NOV_1, span(date(2026, 11, 5)))


def test_schedule_ending_the_day_before_does_not_overlap_ac34() -> None:
    ended = span(date(2026, 11, 1), end=date(2026, 11, 5))
    assert not overlaps(ended, span(date(2026, 11, 6)))
    assert overlaps(ended, span(date(2026, 11, 5)))  # starting on the end date still overlaps


def test_disjoint_weekdays_do_not_overlap_ac34() -> None:
    weekdays = span(date(2026, 11, 1), days=MON_TO_FRI)
    weekend = span(date(2026, 11, 1), days=SAT_SUN)
    assert not overlaps(weekdays, weekend)


def test_mon_wed_and_tue_thu_schedules_do_not_overlap() -> None:
    # Lead decision Q2.
    assert not overlaps(
        span(date(2026, 11, 2), days=frozenset({1, 3})),
        span(date(2026, 11, 2), days=frozenset({2, 4})),
    )


def test_shared_weekday_without_a_common_date_does_not_overlap() -> None:
    # Lead decision Q2: both use Sunday, but the only common date is Tuesday 2026-11-03.
    sunday_monday = span(date(2026, 11, 2), end=date(2026, 11, 3), days=frozenset({7, 1}))
    sunday_tuesday = span(date(2026, 11, 3), days=frozenset({7, 2}))
    assert not overlaps(sunday_monday, sunday_tuesday)
    assert not overlaps(sunday_tuesday, sunday_monday)


def test_one_common_date_on_a_shared_weekday_overlaps() -> None:
    monday_only = span(date(2026, 11, 2), end=date(2026, 11, 2), days=frozenset({1}))
    assert overlaps(monday_only, span(date(2026, 10, 1), end=date(2026, 11, 2)))


def test_ranges_far_apart_do_not_overlap() -> None:
    assert not overlaps(span(date(2026, 1, 1), end=date(2026, 1, 31)), span(date(2026, 11, 1)))


@pytest.mark.parametrize("new_end", [date(2026, 11, 10), None], ids=["extended-end", "cleared-end"])
def test_extended_or_cleared_end_date_overlaps_a_later_schedule(new_end: date | None) -> None:
    # Lead decision Q3's condition: changing end_date still runs the overlap check.
    later = span(date(2026, 11, 6))
    assert overlaps(span(date(2026, 11, 1), end=new_end), later)


@pytest.mark.parametrize(
    "end", [None, date(2026, 11, 1), date(2026, 11, 30)], ids=["open", "same-day", "later"]
)
def test_end_date_on_or_after_start_is_accepted_ac05(end: date | None) -> None:
    check_date_order(date(2026, 11, 1), end)


def test_end_date_before_start_is_rejected_ac05() -> None:
    with pytest.raises(InvalidField) as error:
        check_date_order(date(2026, 11, 1), date(2026, 10, 31))
    assert error.value.field == "end_date"


@pytest.mark.parametrize(
    "changed",
    [{"times_of_day"}, {"grace_period_minutes"}, {"days_of_week", "end_date"}, {"start_date"}],
)
def test_only_end_date_may_change_with_logs_ac06(changed: set[str]) -> None:
    with pytest.raises(ScheduleHasLogs):
        check_changes_allowed(True, changed)


@pytest.mark.parametrize("changed", [set(), {"end_date"}])
def test_end_date_alone_or_nothing_may_change_with_logs_ac06(changed: set[str]) -> None:
    check_changes_allowed(True, changed)


def test_anything_may_change_without_logs() -> None:
    check_changes_allowed(False, {"times_of_day", "grace_period_minutes", "start_date"})


TODAY = date(2026, 11, 2)


@pytest.mark.parametrize(
    ("end", "last_logged"),
    [
        (TODAY, date(2026, 11, 1)),
        (date(2026, 11, 3), date(2026, 11, 3)),
        (None, date(2026, 11, 1)),
    ],
    ids=["today", "latest-log-date", "open"],
)
def test_end_date_on_or_after_today_and_latest_log_is_accepted_ac06(
    end: date | None, last_logged: date
) -> None:
    check_end_date_with_logs(end, TODAY, last_logged)


@pytest.mark.parametrize(
    ("end", "last_logged"),
    [(date(2026, 11, 1), date(2026, 11, 1)), (TODAY, date(2026, 11, 3))],
    ids=["before-today", "before-latest-log"],
)
def test_end_date_before_today_or_latest_log_is_rejected_ac06(end: date, last_logged: date) -> None:
    with pytest.raises(InvalidField) as error:
        check_end_date_with_logs(end, TODAY, last_logged)
    assert error.value.field == "end_date"
