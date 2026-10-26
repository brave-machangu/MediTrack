"""Concurrent requests on PostgreSQL, where transactions really run side by side.

These tests use only the `postgresql` database; without MEDITRACK_TEST_POSTGRES_URL they are
skipped with that reason (or fail when MEDITRACK_REQUIRE_POSTGRES=1).
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx2 import ASGITransport, AsyncClient, Response

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
