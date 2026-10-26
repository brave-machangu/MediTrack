"""Concurrent requests on PostgreSQL, where transactions really run side by side.

These tests use only the `postgresql` database; without MEDITRACK_TEST_POSTGRES_URL they are
skipped with that reason (or fail when MEDITRACK_REQUIRE_POSTGRES=1).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from threading import Thread
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from httpx2 import ASGITransport, AsyncClient, Response
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import FixedClock
from app.db.models import DoseLog
from tests.integration.helpers import create_medication, create_patient

POSTGRES_ONLY = pytest.mark.parametrize("database_url", ["postgresql"], indirect=True)


async def post_concurrently(
    api: TestClient, url: str, bodies: list[dict[str, object]]
) -> list[Response]:
    # The endpoints are sync, so the ASGI app runs them in worker threads: real parallel
    # transactions, unlike TestClient's one-request-at-a-time calls.
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return list(await asyncio.gather(*(client.post(url, json=body) for body in bodies)))


@POSTGRES_ONLY
def test_concurrent_overlapping_schedules_one_created_ac34(api: TestClient) -> None:
    medication_id = create_medication(api, create_patient(api)["id"])["id"]
    bodies: list[dict[str, object]] = [
        {"times_of_day": [f"{hour:02d}:00"], "start_date": "2026-11-01"} for hour in range(8, 13)
    ]

    responses = asyncio.run(
        post_concurrently(api, f"/api/v1/medications/{medication_id}/schedules", bodies)
    )

    assert sorted(response.status_code for response in responses) == [201, 409, 409, 409, 409]
    assert len(api.get(f"/api/v1/medications/{medication_id}/schedules").json()) == 1


@POSTGRES_ONLY
def test_ten_parallel_posts_create_exactly_one_log_ac18(
    api: TestClient, clock: FixedClock, engine: Engine
) -> None:
    patient = create_patient(api)
    medication = create_medication(api, patient["id"])
    schedule = api.post(
        f"/api/v1/medications/{medication['id']}/schedules",
        json={"times_of_day": ["08:00"], "start_date": "2026-11-01"},
    ).json()
    clock.set(datetime(2026, 11, 2, 6, 30, tzinfo=UTC))  # 08:30 in Harare, inside the window
    body = {
        "schedule_id": schedule["id"],
        "scheduled_for": "2026-11-02T06:00:00Z",
        "status": "taken",
    }

    responses = asyncio.run(post_concurrently(api, "/api/v1/dose-logs", [body] * 10))

    assert sorted(response.status_code for response in responses) == [201] + [409] * 9
    assert {response.json()["code"] for response in responses if response.status_code == 409} == {
        "DUPLICATE_DOSE_LOG"
    }
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(DoseLog)) == 1


@POSTGRES_ONLY
def test_constraint_stops_a_second_insert_that_skipped_every_check_ac18(
    api: TestClient, engine: Engine
) -> None:
    # Two transactions insert the same dose with no application check at all. The second one
    # waits on the first's uncommitted row in the unique index, then fails when it commits:
    # the database, not app code, prevents the duplicate (ADR-003).
    patient = create_patient(api)
    medication = create_medication(api, patient["id"])
    schedule_id = api.post(
        f"/api/v1/medications/{medication['id']}/schedules",
        json={"times_of_day": ["08:00"], "start_date": "2026-11-01"},
    ).json()["id"]
    dose_at = datetime(2026, 11, 2, 6, tzinfo=UTC)

    def new_log() -> DoseLog:
        return DoseLog(
            schedule_id=UUID(schedule_id),
            scheduled_for=dose_at,
            status="taken",
            recorded_at=dose_at,
            late=False,
        )

    outcome: list[str] = []

    def second_insert() -> None:
        with Session(engine) as session:
            session.add(new_log())
            try:
                session.commit()
                outcome.append("committed")
            except IntegrityError:
                outcome.append("duplicate")

    with Session(engine) as first:
        first.add(new_log())
        first.flush()  # holds the index entry until commit
        thread = Thread(target=second_insert)
        thread.start()
        first.commit()
    thread.join(timeout=30)

    assert not thread.is_alive()
    assert outcome == ["duplicate"]
