from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.clock import FixedClock, SystemClock


def test_system_clock_returns_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_fixed_clock_returns_the_instant_it_was_given() -> None:
    instant = datetime(2026, 11, 2, 5, 30, tzinfo=UTC)
    assert FixedClock(instant).now() == instant


def test_fixed_clock_normalises_other_offsets_to_utc() -> None:
    harare = timezone(timedelta(hours=2))
    clock = FixedClock(datetime(2026, 11, 2, 7, 30, tzinfo=harare))
    assert clock.now() == datetime(2026, 11, 2, 5, 30, tzinfo=UTC)
    assert clock.now().tzinfo == UTC


def test_fixed_clock_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError):
        FixedClock(datetime(2026, 11, 2, 5, 30))
    clock = FixedClock(datetime(2026, 11, 2, 5, 30, tzinfo=UTC))
    with pytest.raises(ValueError):
        clock.set(datetime(2026, 11, 2, 6, 0))


def test_fixed_clock_moves_only_when_told() -> None:
    clock = FixedClock(datetime(2026, 11, 2, 5, 30, tzinfo=UTC))
    clock.advance(timedelta(minutes=90, seconds=1))
    assert clock.now() == datetime(2026, 11, 2, 7, 0, 1, tzinfo=UTC)
    clock.set(datetime(2026, 11, 3, tzinfo=UTC))
    assert clock.now() == datetime(2026, 11, 3, tzinfo=UTC)
