"""Missed-dose list (FR-08): AC-22 (default range, contents, order) and AC-23 (range limits)."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from app.domain.errors import InvalidField
from app.domain.scheduling import missed_doses, missed_range, planned_doses_between
from app.domain.types import DoseStatus, LogStatus
from tests.unit.domain.factories import RULES, make_log, make_schedule, utc

TODAY = date(2026, 11, 8)


def test_default_range_is_today_and_six_days_before_ac22() -> None:
    assert missed_range(None, None, TODAY) == (date(2026, 11, 2), TODAY)


def test_only_from_ends_today_and_only_to_starts_six_days_before_today() -> None:
    # The contract's defaults are both relative to today, not to each other.
    assert missed_range(date(2026, 11, 5), None, TODAY) == (date(2026, 11, 5), TODAY)
    assert missed_range(None, date(2026, 11, 4), TODAY) == (date(2026, 11, 2), date(2026, 11, 4))


@pytest.mark.parametrize(
    ("start", "end"),
    [(date(2026, 10, 1), date(2026, 10, 31)), (date(2026, 11, 8), date(2026, 11, 8))],
    ids=["31-days", "one-day"],
)
def test_range_of_one_to_31_days_is_accepted(start: date, end: date) -> None:
    assert missed_range(start, end, TODAY) == (start, end)


def test_range_over_31_days_rejected_ac23() -> None:
    with pytest.raises(InvalidField) as error:
        missed_range(date(2026, 10, 1), date(2026, 11, 1), TODAY)  # 32 days
    assert error.value.field == "to"


def test_from_after_to_rejected_ac23() -> None:
    with pytest.raises(InvalidField) as error:
        missed_range(date(2026, 11, 5), date(2026, 11, 4), TODAY)
    assert error.value.field == "from"


def test_default_from_after_explicit_to_is_rejected() -> None:
    with pytest.raises(InvalidField):
        missed_range(None, date(2026, 10, 1), TODAY)


def test_missed_list_is_unlogged_past_grace_newest_first_ac22() -> None:
    harare = ZoneInfo("Africa/Harare")
    schedule = make_schedule("08:00", "20:00", start=date(2026, 11, 1))
    logs = [
        make_log(utc(2026, 11, 2, 6), LogStatus.TAKEN),
        make_log(utc(2026, 11, 3, 18), LogStatus.SKIPPED, late=True),
    ]
    now = utc(2026, 11, 4, 6, 30)  # 08:30 on 2026-11-04: that morning's dose is still due
    doses = planned_doses_between(
        [schedule], logs, harare, date(2026, 11, 2), date(2026, 11, 4), now, RULES
    )

    missed = missed_doses(doses)

    assert all(dose.status is DoseStatus.MISSED for dose in missed)
    assert [dose.scheduled_for for dose in missed] == [
        utc(2026, 11, 3, 6),
        utc(2026, 11, 2, 18),
    ]


def test_missed_doses_at_the_same_time_keep_a_stable_order() -> None:
    harare = ZoneInfo("Africa/Harare")
    schedules = [
        make_schedule("08:00", schedule_id=UUID(int=20)),
        make_schedule("08:00", schedule_id=UUID(int=10)),
    ]
    doses = planned_doses_between(
        schedules, [], harare, date(2026, 11, 2), date(2026, 11, 2), utc(2026, 11, 3), RULES
    )
    missed = missed_doses(doses)
    assert [dose.schedule_id for dose in missed] == [UUID(int=10), UUID(int=20)]
    assert missed == missed_doses(list(reversed(doses)))


def test_range_bound_is_31_days_including_both_ends() -> None:
    start = date(2026, 10, 1)
    assert missed_range(start, start + timedelta(days=30), TODAY)[1] == date(2026, 10, 31)
