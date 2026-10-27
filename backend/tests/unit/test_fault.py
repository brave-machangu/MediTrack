"""The incident drill's fault (MT-023): a dose log fails when the random draw is below the rate."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from app.fault import DoseLogFault, InjectedFault

# random.random() returns a value in [0, 1): these are its extremes and its middle.
DRAWS = [0.0, 0.5, 0.9999999999999999]


def draw(value: float) -> Callable[[], float]:
    return lambda: value


@pytest.mark.parametrize("value", DRAWS)
def test_rate_0_never_fails(value: float) -> None:
    DoseLogFault(rate=0, random=draw(value)).maybe_fail()


@pytest.mark.parametrize("value", DRAWS)
def test_rate_1_always_fails(value: float) -> None:
    with pytest.raises(InjectedFault):
        DoseLogFault(rate=1, random=draw(value)).maybe_fail()


def test_a_draw_below_the_rate_fails_and_one_at_the_rate_does_not() -> None:
    with pytest.raises(InjectedFault):
        DoseLogFault(rate=0.5, random=draw(0.49)).maybe_fail()
    DoseLogFault(rate=0.5, random=draw(0.5)).maybe_fail()


def test_the_default_source_is_random() -> None:
    fault = DoseLogFault(rate=0.5)
    outcomes = set()
    for _ in range(200):
        try:
            fault.maybe_fail()
            outcomes.add("ok")
        except InjectedFault:
            outcomes.add("failed")
    # Both outcomes in 200 tries at 50 %; the chance of missing one is 2 in 2**200.
    assert outcomes == {"ok", "failed"}
