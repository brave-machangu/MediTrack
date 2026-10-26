"""Daily adherence summary (requirements §4.5): AC-25, the backend half of AC-26, and AC-42."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from app.domain.adherence import DailySummary, adherence_percent, daily_summary
from app.domain.scheduling import planned_doses
from app.domain.types import DoseStatus, LoggedDose, LogStatus, PlannedDose
from tests.unit.domain.factories import RULES, SCHEDULE_ID, make_log, make_schedule, utc

HARARE = ZoneInfo("Africa/Harare")
DAY = date(2026, 11, 2)


def dose(status: DoseStatus, *, late: bool = False) -> PlannedDose:
    """A planned dose that only carries what the summary reads."""
    scheduled_for = utc(2026, 11, 2, 6)
    log = None
    if status in (DoseStatus.TAKEN, DoseStatus.SKIPPED):
        log = LoggedDose(
            dose_log_id=UUID(int=99),
            schedule_id=SCHEDULE_ID,
            scheduled_for=scheduled_for,
            status=LogStatus(status.value),
            recorded_at=scheduled_for + timedelta(minutes=5),
            late=late,
        )
    return PlannedDose(
        schedule_id=SCHEDULE_ID,
        medication_id=UUID(int=2),
        scheduled_for=scheduled_for,
        local_date=DAY,
        local_time="08:00",
        status=status,
        late=late,
        log_window_opens_at=scheduled_for - RULES.early_log_window,
        log_window_closes_at=scheduled_for + RULES.late_log_limit,
        log=log,
    )


def test_summary_counts_and_percent_ac25() -> None:
    # 4 planned: 08:00 taken on time, 10:00 taken late, 12:00 skipped, 14:00 never logged.
    schedule = make_schedule("08:00", "10:00", "12:00", "14:00")
    logs = [
        make_log(utc(2026, 11, 2, 6), LogStatus.TAKEN),
        make_log(utc(2026, 11, 2, 8), LogStatus.TAKEN, late=True),
        make_log(utc(2026, 11, 2, 10), LogStatus.SKIPPED),
    ]
    now = utc(2026, 11, 2, 18)  # 20:00 local: the 14:00 dose is past its grace
    doses = planned_doses([schedule], logs, HARARE, DAY, now, RULES)

    assert daily_summary(doses) == DailySummary(
        planned=4,
        taken=2,
        taken_late=1,
        skipped=1,
        missed=1,
        pending=0,
        adherence_percent=Decimal("50.0"),
    )


def test_percent_is_null_with_only_upcoming_doses_ac26() -> None:
    summary = daily_summary([dose(DoseStatus.UPCOMING), dose(DoseStatus.UPCOMING)])
    assert summary.adherence_percent is None
    assert (summary.planned, summary.pending) == (2, 2)


def test_due_doses_are_pending_and_not_scored() -> None:
    summary = daily_summary([dose(DoseStatus.DUE), dose(DoseStatus.UPCOMING)])
    assert (summary.pending, summary.missed) == (2, 0)
    assert summary.adherence_percent is None


def test_day_without_doses_has_zero_counts_and_null_percent() -> None:
    assert daily_summary([]) == DailySummary(
        planned=0, taken=0, taken_late=0, skipped=0, missed=0, pending=0, adherence_percent=None
    )


def test_late_skipped_dose_is_not_counted_as_taken_late() -> None:
    summary = daily_summary([dose(DoseStatus.SKIPPED, late=True)])
    assert (summary.skipped, summary.taken, summary.taken_late) == (1, 0, 0)


def test_pending_doses_do_not_change_the_percent() -> None:
    summary = daily_summary(
        [dose(DoseStatus.TAKEN), dose(DoseStatus.MISSED), dose(DoseStatus.UPCOMING)]
    )
    assert summary.adherence_percent == Decimal("50.0")


@pytest.mark.parametrize(
    ("taken", "skipped", "missed", "expected"),
    [
        (1, 0, 15, "6.3"),  # AC-42: 6.25; round() would give 6.2
        (2, 1, 0, "66.7"),  # AC-42
        (1, 0, 79, "1.3"),  # 1.25
        (1, 7, 0, "12.5"),
        (1, 2, 0, "33.3"),
        (3, 0, 0, "100.0"),
        (0, 1, 1, "0.0"),
    ],
)
def test_percent_rounds_half_up_to_one_decimal_ac42(
    taken: int, skipped: int, missed: int, expected: str
) -> None:
    result = adherence_percent(taken, skipped, missed)
    assert result is not None
    assert str(result) == expected


def test_percent_is_null_when_nothing_is_scored() -> None:
    assert adherence_percent(0, 0, 0) is None
