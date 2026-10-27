"""Build-time fault injection for the incident drill (MT-023, operations.md §7 drill A).

With MEDITRACK_FAULT_DOSE_LOG_ERROR_RATE at 1, every POST /dose-logs fails with 500
INTERNAL_ERROR, records nothing and counts as an `error` attempt (the alert's SLI). At 0, the
default, none does. No other endpoint is affected.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine

from app.clock import FixedClock
from tests.integration.helpers import (
    PATIENTS,
    Json,
    assert_problem,
    create_medication,
    create_patient,
)
from tests.integration.signals import Signals, signals_app

DOSE_LOGS = "/api/v1/dose-logs"


@pytest.fixture
def faulty(engine: Engine, database_url: str, clock: FixedClock) -> Iterator[Signals]:
    yield from signals_app(database_url, clock, fault_dose_log_error_rate=1)


@pytest.fixture
def healthy(engine: Engine, database_url: str, clock: FixedClock) -> Iterator[Signals]:
    yield from signals_app(database_url, clock)


def todays_dose(signals: Signals, clock: FixedClock) -> tuple[Json, Json]:
    """A patient with a daily 08:00 schedule (Africa/Harare), at 08:30 local on 2026-11-02."""
    client = signals.client
    patient = create_patient(client)
    medication = create_medication(client, patient["id"])
    response = client.post(
        f"/api/v1/medications/{medication['id']}/schedules",
        json={"times_of_day": ["08:00"], "start_date": "2026-11-01"},
    )
    assert response.status_code == 201, response.text
    clock.set(datetime(2026, 11, 2, 6, 30, tzinfo=UTC))
    dose = {"schedule_id": response.json()["id"], "scheduled_for": "2026-11-02T06:00:00Z"}
    return patient, {**dose, "status": "taken"}


def test_at_rate_1_every_dose_log_fails_and_records_nothing(
    faulty: Signals, clock: FixedClock
) -> None:
    patient, dose = todays_dose(faulty, clock)

    for _ in range(3):
        assert_problem(faulty.client.post(DOSE_LOGS, json=dose), 500, "INTERNAL_ERROR")

    day = faulty.client.get(f"{PATIENTS}/{patient['id']}/doses?date=2026-11-02").json()
    assert [planned["dose_log_id"] for planned in day["doses"]] == [None]
    assert faulty.metric_points("meditrack.dose_log.attempts") == [({"outcome": "error"}, 3)]
    failures = {
        (line["status_code"], line["error_code"], line["error_type"])
        for line in faulty.json_lines()
        if line["event"] == "request.failed"
    }
    assert failures == {(500, "INTERNAL_ERROR", "InjectedFault")}


def test_at_rate_1_every_other_endpoint_still_works(faulty: Signals, clock: FixedClock) -> None:
    patient, _ = todays_dose(faulty, clock)
    client = faulty.client
    p = f"{PATIENTS}/{patient['id']}"

    statuses = [
        client.get("/healthz").status_code,
        client.get("/readyz").status_code,
        client.get(PATIENTS).status_code,
        client.get(f"{p}/medications").status_code,
        client.get(f"{p}/doses").status_code,
        client.get(f"{p}/missed-doses").status_code,
        client.get(f"{p}/adherence/daily").status_code,
        client.delete(f"{DOSE_LOGS}/00000000-0000-4000-8000-000000000000").status_code,
    ]

    assert statuses == [200, 200, 200, 200, 200, 200, 200, 404]


def test_at_the_default_rate_0_dose_logs_succeed(healthy: Signals, clock: FixedClock) -> None:
    _, dose = todays_dose(healthy, clock)
    assert healthy.client.post(DOSE_LOGS, json=dose).status_code == 201
    assert healthy.metric_points("meditrack.dose_log.attempts") == [({"outcome": "created"}, 1)]
