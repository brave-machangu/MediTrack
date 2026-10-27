"""Fault injection for the incident drill (operations.md §7, drill A; MT-023).

An image built with FAULT_DOSE_LOG_ERROR_RATE > 0 fails that share of POST /dose-logs with
500 INTERNAL_ERROR, before anything is written. The deploy workflow labels such images, and
Settings refuses a rate above 0 in production.
"""

from __future__ import annotations

import random as _random
from collections.abc import Callable
from dataclasses import dataclass


class InjectedFault(Exception):
    """Raised on purpose. It is answered like any unexpected error, and logged by type."""


@dataclass(frozen=True, slots=True)
class DoseLogFault:
    rate: float
    # Returns a value in [0, 1). Tests pass a fixed one.
    random: Callable[[], float] = _random.random

    def maybe_fail(self) -> None:
        if self.random() < self.rate:
            raise InjectedFault
