"""Missed doses and daily adherence (FR-08, FR-09): AC-22 to AC-26 and AC-42 through HTTP, on
SQLite and PostgreSQL. The patient is in Africa/Harare (UTC+2)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.clock import FixedClock
from tests.integration.helpers import (
    PATIENTS,
    Json,
    assert_problem,
    create_medication,
    create_patient,
)

HARARE = ZoneInfo("Africa/Harare")


def harare(month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=HARARE).astimezone(UTC)


def schedule(
    api: TestClient, medication_id: str, times: list[str], start: str = "2026-10-25"
) -> str:
    body = {"times_of_day": times, "start_date": start}
    response = api.post(f"/api/v1/medications/{medication_id}/schedules", json=body)
    assert response.status_code == 201, response.text
    schedule_id: str = response.json()["id"]
    return schedule_id


def log(api: TestClient, schedule_id: str, scheduled_for: datetime, status: str = "taken") -> None:
    body = {
        "schedule_id": schedule_id,
        "scheduled_for": scheduled_for.isoformat().replace("+00:00", "Z"),
        "status": status,
    }
    response = api.post("/api/v1/dose-logs", json=body)
    assert response.status_code == 201, response.text


def missed(api: TestClient, patient_id: str, query: str = "") -> list[Json]:
    response = api.get(f"{PATIENTS}/{patient_id}/missed-doses{query}")
    assert response.status_code == 200, response.text
    body: list[Json] = response.json()
    return body


def adherence(api: TestClient, patient_id: str, query: str = "") -> Json:
    response = api.get(f"{PATIENTS}/{patient_id}/adherence/daily{query}")
    assert response.status_code == 200, response.text
    body: Json = response.json()
    return body


def test_missed_list_default_range_ac22(api: TestClient, clock: FixedClock) -> None:
    patient = create_patient(api)
    schedule_id = schedule(api, create_medication(api, patient["id"])["id"], ["08:00"])
    clock.set(harare(11, 4, 9, 30))
    log(api, schedule_id, harare(11, 4, 8))  # today's dose logged (late), so not missed
    clock.set(harare(11, 8, 7, 30))  # Sunday 07:30: today's 08:00 is still upcoming

    doses = missed(api, patient["id"])

    # Today and the six days before: 2026-11-02 … 2026-11-08, newest first, only unlogged doses
    # past their grace. Doses before 2026-11-02 are missed too, but outside the default range.
    assert [dose["local_date"] for dose in doses] == [
        "2026-11-07",
        "2026-11-06",
        "2026-11-05",
        "2026-11-03",
        "2026-11-02",
    ]
    assert {dose["status"] for dose in doses} == {"missed"}
    assert set(doses[0]) >= {"medication_name", "log_window_opens_at", "dose_log_id"}


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("?from=2026-10-01&to=2026-11-01", "to"),  # 32 days
        ("?from=2026-11-05&to=2026-11-04", "from"),
        ("?from=not-a-date", "from"),
        ("?to=2026-11-31", "to"),
    ],
    ids=["32-days", "from-after-to", "bad-from", "bad-to"],
)
def test_invalid_missed_range_rejected_ac23(api: TestClient, query: str, field: str) -> None:
    patient = create_patient(api)
    response = api.get(f"{PATIENTS}/{patient['id']}/missed-doses{query}")
    problem = assert_problem(response, 422, "VALIDATION_ERROR")
    assert [error["field"] for error in problem["errors"]] == [field]


def test_range_of_31_days_is_accepted_ac23(api: TestClient, clock: FixedClock) -> None:
    patient = create_patient(api)
    schedule(api, create_medication(api, patient["id"])["id"], ["08:00"], start="2026-10-01")
    clock.set(harare(11, 8, 7, 30))
    doses = missed(api, patient["id"], "?from=2026-10-01&to=2026-10-31")
    assert len(doses) == 31
    assert (doses[0]["local_date"], doses[-1]["local_date"]) == ("2026-10-31", "2026-10-01")


def test_dose_logged_late_leaves_the_missed_list_ac24(api: TestClient, clock: FixedClock) -> None:
    patient = create_patient(api)
    schedule_id = schedule(
        api, create_medication(api, patient["id"])["id"], ["08:00"], start="2026-11-02"
    )
    clock.set(harare(11, 2, 12))
    assert [dose["local_date"] for dose in missed(api, patient["id"])] == ["2026-11-02"]

    log(api, schedule_id, harare(11, 2, 8))

    assert missed(api, patient["id"]) == []


def test_daily_adherence_matches_the_summary_ac25(api: TestClient, clock: FixedClock) -> None:
    patient = create_patient(api)
    schedule_id = schedule(
        api, create_medication(api, patient["id"])["id"], ["08:00", "10:00", "12:00", "14:00"]
    )
    clock.set(harare(11, 2, 8, 30))
    log(api, schedule_id, harare(11, 2, 8))  # taken on time
    clock.set(harare(11, 2, 13, 30))
    log(api, schedule_id, harare(11, 2, 10))  # taken late
    log(api, schedule_id, harare(11, 2, 12), "skipped")
    clock.set(harare(11, 2, 20))  # the 14:00 dose is now missed

    summary = adherence(api, patient["id"], "?date=2026-11-02")

    assert summary == {
        "patient_id": patient["id"],
        "date": "2026-11-02",
        "timezone": "Africa/Harare",
        "planned": 4,
        "taken": 2,
        "taken_late": 1,
        "skipped": 1,
        "missed": 1,
        "pending": 0,
        "adherence_percent": 50.0,
    }


def test_adherence_is_null_with_only_upcoming_doses_ac26(
    api: TestClient, clock: FixedClock
) -> None:
    patient = create_patient(api)
    schedule(api, create_medication(api, patient["id"])["id"], ["08:00", "20:00"])
    clock.set(harare(11, 2, 7))
    summary = adherence(api, patient["id"])
    assert (summary["date"], summary["pending"], summary["adherence_percent"]) == (
        "2026-11-02",
        2,
        None,
    )


def test_adherence_rounds_half_up_through_the_api_ac42(api: TestClient, clock: FixedClock) -> None:
    # 1 taken + 15 missed = 6.25 % → 6.3 (round() would give 6.2). Two schedules on two
    # medications, because one schedule holds at most 12 times.
    patient = create_patient(api)
    first_twelve = [f"{hour:02d}:00" for hour in range(12)]
    alpha = schedule(
        api, create_medication(api, patient["id"], name="Demo Med Alpha")["id"], first_twelve
    )
    schedule(
        api,
        create_medication(api, patient["id"], name="Demo Med Beta")["id"],
        ["12:00", "13:00", "14:00", "15:00"],
    )
    clock.set(harare(11, 2, 0, 30))
    log(api, alpha, harare(11, 2, 0))
    clock.set(harare(11, 2, 23))

    summary = adherence(api, patient["id"], "?date=2026-11-02")

    assert (summary["planned"], summary["taken"], summary["missed"]) == (16, 1, 15)
    assert summary["adherence_percent"] == 6.3


@pytest.mark.parametrize("patient_id", [str(uuid4()), "not-a-uuid"], ids=["unknown", "malformed"])
def test_reports_of_missing_patient_are_not_found(api: TestClient, patient_id: str) -> None:
    real = create_patient(api)
    missed(api, real["id"])  # the routes exist, so a 404 is about the patient
    adherence(api, real["id"])
    assert_problem(api.get(f"{PATIENTS}/{patient_id}/missed-doses"), 404, "NOT_FOUND")
    assert_problem(api.get(f"{PATIENTS}/{patient_id}/adherence/daily"), 404, "NOT_FOUND")


def test_invalid_adherence_date_is_rejected(api: TestClient) -> None:
    patient = create_patient(api)
    response = api.get(f"{PATIENTS}/{patient['id']}/adherence/daily?date=2026-02-30")
    problem = assert_problem(response, 422, "VALIDATION_ERROR")
    assert [error["field"] for error in problem["errors"]] == ["date"]
