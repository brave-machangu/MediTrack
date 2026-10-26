"""AC-39: property-based checks of the DST policy over random IANA zones, dates from 2000 to
2040 and schedule times.

Random dates rarely land on a DST change, so half of the examples pick a date on or next to a
change of UTC offset. A failure prints a `@reproduce_failure` blob (test-strategy.md §3.3).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from functools import cache
from zoneinfo import ZoneInfo, available_timezones

from hypothesis import example, given, settings
from hypothesis import strategies as st

from app.domain.scheduling import planned_doses, planned_doses_between
from tests.unit.domain.factories import RULES, make_schedule, utc

ZONES = sorted(available_timezones())
NOW = utc(2020, 1, 1)
ONE_DAY = timedelta(days=1)


@cache
def offset_change_dates(zone: str, year: int) -> tuple[date, ...]:
    """Dates in `year` next to a change of the zone's UTC offset (sampled at local noon)."""
    tz = ZoneInfo(zone)
    found: list[date] = []
    day = date(year, 1, 1)
    previous = datetime.combine(day - ONE_DAY, time(12), tzinfo=tz).utcoffset()
    while day.year == year:
        offset = datetime.combine(day, time(12), tzinfo=tz).utcoffset()
        if offset != previous:
            found += [day - ONE_DAY, day]
        previous = offset
        day += ONE_DAY
    return tuple(found)


@st.composite
def zones_and_dates(draw: st.DrawFn) -> tuple[ZoneInfo, date]:
    zone = draw(st.sampled_from(ZONES))
    year = draw(st.integers(min_value=2000, max_value=2040))
    changes = offset_change_dates(zone, year)
    if changes and draw(st.booleans()):
        day = draw(st.sampled_from(changes))
    else:
        day = draw(st.dates(min_value=date(year, 1, 1), max_value=date(year, 12, 31)))
    return ZoneInfo(zone), day


schedule_times = st.lists(
    st.builds(time, st.integers(min_value=0, max_value=23), st.integers(min_value=0, max_value=59)),
    min_size=1,
    max_size=12,
    unique=True,
)


def exists(day: date, local_time: time, tz: ZoneInfo) -> bool:
    """False for a wall time inside a gap, where fold=0 has the smaller offset (PEP 495)."""
    first = datetime.combine(day, local_time, tzinfo=tz)
    second = first.replace(fold=1)
    offset_first, offset_second = first.utcoffset(), second.utcoffset()
    assert offset_first is not None and offset_second is not None
    return offset_first >= offset_second


LONDON_GAP = (ZoneInfo("Europe/London"), date(2027, 3, 28))
NUUK_GAP = (ZoneInfo("America/Nuuk"), date(2026, 3, 28))
APIA_SKIPPED_DAY = (ZoneInfo("Pacific/Apia"), date(2011, 12, 30))


@settings(max_examples=300, deadline=None, print_blob=True)
@given(zone_and_date=zones_and_dates(), times=schedule_times)
@example(zone_and_date=LONDON_GAP, times=[time(1, 30), time(2, 30)])
@example(zone_and_date=NUUK_GAP, times=[time(0, 30), time(23, 30)])
@example(zone_and_date=APIA_SKIPPED_DAY, times=[time(8, 0)])
def test_no_schedule_plans_one_instant_twice_ac39(
    zone_and_date: tuple[ZoneInfo, date], times: list[time]
) -> None:
    tz, day = zone_and_date
    schedule = make_schedule(*(t.strftime("%H:%M") for t in times))
    doses = planned_doses_between([schedule], [], tz, day - ONE_DAY, day + ONE_DAY, NOW, RULES)
    instants = [dose.scheduled_for for dose in doses]
    assert len(instants) == len(set(instants))


@settings(max_examples=300, deadline=None, print_blob=True)
@given(zone_and_date=zones_and_dates(), times=schedule_times)
@example(zone_and_date=LONDON_GAP, times=[time(1, 30), time(2, 30)])
@example(zone_and_date=(ZoneInfo("Europe/London"), date(2026, 10, 25)), times=[time(1, 30)])
@example(zone_and_date=NUUK_GAP, times=[time(0, 30), time(23, 30)])
def test_existing_local_times_round_trip_ac39(
    zone_and_date: tuple[ZoneInfo, date], times: list[time]
) -> None:
    tz, day = zone_and_date
    schedule = make_schedule(*(t.strftime("%H:%M") for t in times))
    doses = planned_doses([schedule], [], tz, day, NOW, RULES)
    shown = {dose.local_time for dose in doses}
    for local_time in times:
        if exists(day, local_time, tz):
            assert local_time.strftime("%H:%M") in shown
    for dose in doses:
        local = dose.scheduled_for.astimezone(tz)
        assert (local.date(), local.strftime("%H:%M")) == (dose.local_date, dose.local_time)
        assert dose.local_date == day
