"""The only place that reads the current time (AGENTS.md rule 6).

Everything else receives a Clock (or a `now` value) so that time-based rules are
deterministic in tests.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the current instant as a timezone-aware UTC datetime."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """A clock that only moves when told to. For tests."""

    def __init__(self, instant: datetime) -> None:
        self._now = _require_aware_utc(instant)

    def now(self) -> datetime:
        return self._now

    def set(self, instant: datetime) -> None:
        self._now = _require_aware_utc(instant)

    def advance(self, delta: timedelta) -> None:
        self._now = self._now + delta


def _require_aware_utc(instant: datetime) -> datetime:
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("FixedClock needs a timezone-aware datetime")
    return instant.astimezone(UTC)
