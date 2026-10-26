"""Daily adherence summary (requirements §4.5)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.types import DoseStatus, PlannedDose

ONE_DECIMAL_PLACE = Decimal("0.1")


@dataclass(frozen=True, slots=True)
class DailySummary:
    planned: int
    taken: int  # includes taken_late
    taken_late: int
    skipped: int
    missed: int
    pending: int  # upcoming + due
    adherence_percent: Decimal | None


def daily_summary(doses: Sequence[PlannedDose]) -> DailySummary:
    """Counts and adherence for the planned doses of one patient-local date."""
    statuses = Counter(dose.status for dose in doses)
    taken = statuses[DoseStatus.TAKEN]
    skipped = statuses[DoseStatus.SKIPPED]
    missed = statuses[DoseStatus.MISSED]
    return DailySummary(
        planned=len(doses),
        taken=taken,
        taken_late=sum(1 for dose in doses if dose.status == DoseStatus.TAKEN and dose.late),
        skipped=skipped,
        missed=missed,
        pending=statuses[DoseStatus.UPCOMING] + statuses[DoseStatus.DUE],
        adherence_percent=adherence_percent(taken, skipped, missed),
    )


def adherence_percent(taken: int, skipped: int, missed: int) -> Decimal | None:
    """taken / (taken + skipped + missed) × 100, or None when nothing can be scored yet.

    Rounded half-up, not with round(), which rounds half to even: 1 of 16 is 6.25 → 6.3 (AC-42).
    """
    scored = taken + skipped + missed
    if scored == 0:
        return None
    return (Decimal(taken * 100) / Decimal(scored)).quantize(
        ONE_DECIMAL_PLACE, rounding=ROUND_HALF_UP
    )
