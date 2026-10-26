"""Recording and undoing doses, `POST /api/v1/dose-logs` and `DELETE /api/v1/dose-logs/{id}`
(FR-05 to FR-07): AC-14 to AC-17, AC-19, AC-20 and the log rows of the boundary table in
test-strategy.md §3.2, on SQLite and PostgreSQL.

Patient in Africa/Harare (UTC+2), schedule 08:00 every day from 2026-11-01, grace 60 minutes.
The 2026-11-02 dose is at 06:00Z.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.clock import FixedClock
from app.db.models import DoseLog
from tests.integration.helpers import (
    PATIENTS,
    Json,
    assert_problem,
    create_medication,
    create_patient,
)

DOSE_LOGS = "/api/v1/dose-logs"
HARARE = ZoneInfo("Africa/Harare")
DOSE_AT = "2026-11-02T06:00:00Z"


def harare(day: int, hour: int, minute: int, second: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, second, tzinfo=HARARE).astimezone(UTC)


@pytest.fixture
def setup(api: TestClient) -> Json:
    """A patient with a daily 08:00 schedule; returns ids."""
    patient = create_patient(api)
    medication = create_medication(api, patient["id"])
    response = api.post(
        f"/api/v1/medications/{medication['id']}/schedules",
        json={"times_of_day": ["08:00"], "start_date": "2026-11-01"},
    )
    assert response.status_code == 201, response.text
    return {
        "patient_id": patient["id"],
        "medication_id": medication["id"],
        "schedule_id": response.json()["id"],
    }


def log_dose(api: TestClient, setup: Json, **fields: object) -> Json:
    body = {
        "schedule_id": setup["schedule_id"],
        "scheduled_for": DOSE_AT,
        "status": "taken",
        **fields,
    }
    response = api.post(DOSE_LOGS, json=body)
    assert response.status_code == 201, response.text
    created: Json = response.json()
    return created


def dose_on_nov_2(api: TestClient, setup: Json) -> Json:
    response = api.get(f"{PATIENTS}/{setup['patient_id']}/doses?date=2026-11-02")
    assert response.status_code == 200, response.text
    [dose] = response.json()["doses"]
    result: Json = dose
    return result


def stored_logs(engine: Engine) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(DoseLog)) or 0


def test_logging_a_due_dose_shows_it_taken_ac14(
    api: TestClient, clock: FixedClock, setup: Json
) -> None:
    clock.set(harare(2, 8, 30))
    response = api.post(
        DOSE_LOGS,
        json={"schedule_id": setup["schedule_id"], "scheduled_for": DOSE_AT, "status": "taken"},
    )

    assert response.status_code == 201
    log = response.json()
    assert log == {
        "id": log["id"],
        "schedule_id": setup["schedule_id"],
        "scheduled_for": DOSE_AT,
        "status": "taken",
        "recorded_at": "2026-11-02T06:30:00Z",
        "late": False,
        "note": None,
    }
    dose = dose_on_nov_2(api, setup)
    assert (dose["status"], dose["late"], dose["dose_log_id"]) == ("taken", False, log["id"])


def test_dose_logged_after_grace_is_marked_late_ac15(
    api: TestClient, clock: FixedClock, setup: Json
) -> None:
    clock.set(harare(2, 9, 30))
    assert log_dose(api, setup)["late"] is True
    dose = dose_on_nov_2(api, setup)
    assert (dose["status"], dose["late"]) == ("taken", True)


def test_skipped_dose_with_note(api: TestClient, clock: FixedClock, setup: Json) -> None:
    clock.set(harare(2, 8, 30))
    log = log_dose(api, setup, status="skipped", note="Felt unwell")
    assert (log["status"], log["note"]) == ("skipped", "Felt unwell")
    assert dose_on_nov_2(api, setup)["status"] == "skipped"


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (harare(2, 6, 59, 59), "OUTSIDE_LOG_WINDOW"),
        (harare(2, 7, 0, 0), False),
        (harare(2, 8, 0, 0), False),
        (harare(2, 9, 0, 0), False),
        (harare(2, 9, 0, 1), True),
        (harare(3, 8, 0, 0), True),
        (harare(3, 8, 0, 1), "OUTSIDE_LOG_WINDOW"),
    ],
    ids=[
        "06:59:59",
        "07:00:00",
        "08:00:00",
        "09:00:00",
        "09:00:01",
        "next-08:00:00",
        "next-08:00:01",
    ],
)
def test_log_boundary_table(
    api: TestClient, clock: FixedClock, setup: Json, now: datetime, expected: str | bool
) -> None:
    # expected: the problem code, or the `late` flag of the 201 response.
    clock.set(now)
    body = {"schedule_id": setup["schedule_id"], "scheduled_for": DOSE_AT, "status": "taken"}
    response = api.post(DOSE_LOGS, json=body)
    if isinstance(expected, str):
        assert_problem(response, 422, expected)
    else:
        assert response.status_code == 201
        assert response.json()["late"] is expected


def test_logging_outside_the_window_is_rejected_ac16(
    api: TestClient, clock: FixedClock, setup: Json, engine: Engine
) -> None:
    body = {"schedule_id": setup["schedule_id"], "scheduled_for": DOSE_AT, "status": "taken"}
    clock.set(harare(2, 6, 58))  # 62 minutes early
    assert_problem(api.post(DOSE_LOGS, json=body), 422, "OUTSIDE_LOG_WINDOW")
    clock.set(harare(4, 8, 0))  # two days late
    assert_problem(api.post(DOSE_LOGS, json=body), 422, "OUTSIDE_LOG_WINDOW")
    assert stored_logs(engine) == 0


def test_logging_an_unplanned_time_is_rejected_ac16(
    api: TestClient, clock: FixedClock, setup: Json, engine: Engine
) -> None:
    clock.set(harare(2, 8, 30))
    body = {
        "schedule_id": setup["schedule_id"],
        "scheduled_for": "2026-11-02T06:30:00Z",
        "status": "taken",
    }
    assert_problem(api.post(DOSE_LOGS, json=body), 422, "DOSE_NOT_PLANNED")
    assert stored_logs(engine) == 0


def test_duplicate_log_is_rejected_and_the_first_is_unchanged_ac17(
    api: TestClient, clock: FixedClock, setup: Json, engine: Engine
) -> None:
    clock.set(harare(2, 8, 30))
    first = log_dose(api, setup)
    clock.set(harare(2, 8, 45))

    same = api.post(
        DOSE_LOGS,
        json={"schedule_id": setup["schedule_id"], "scheduled_for": DOSE_AT, "status": "skipped"},
    )
    # The same instant written with Harare's offset is the same dose.
    same_in_local_time = api.post(
        DOSE_LOGS,
        json={
            "schedule_id": setup["schedule_id"],
            "scheduled_for": "2026-11-02T08:00:00+02:00",
            "status": "taken",
        },
    )

    assert_problem(same, 409, "DUPLICATE_DOSE_LOG")
    assert_problem(same_in_local_time, 409, "DUPLICATE_DOSE_LOG")
    dose = dose_on_nov_2(api, setup)
    assert (dose["dose_log_id"], dose["status"], dose["recorded_at"]) == (
        first["id"],
        "taken",
        "2026-11-02T06:30:00Z",
    )
    assert stored_logs(engine) == 1


def test_logging_for_an_inactive_medication_is_rejected_ac19(
    api: TestClient, clock: FixedClock, setup: Json
) -> None:
    clock.set(harare(2, 8, 30))
    api.patch(f"/api/v1/medications/{setup['medication_id']}", json={"active": False})
    body = {"schedule_id": setup["schedule_id"], "scheduled_for": DOSE_AT, "status": "taken"}
    assert_problem(api.post(DOSE_LOGS, json=body), 409, "MEDICATION_INACTIVE")


def test_undo_restores_the_time_based_status_and_allows_logging_again_ac20(
    api: TestClient, clock: FixedClock, setup: Json
) -> None:
    clock.set(harare(2, 8, 30))
    first = log_dose(api, setup)

    response = api.delete(f"{DOSE_LOGS}/{first['id']}")

    assert response.status_code == 204
    assert response.content == b""
    dose = dose_on_nov_2(api, setup)
    assert (dose["status"], dose["dose_log_id"], dose["recorded_at"]) == ("due", None, None)
    again = log_dose(api, setup, status="skipped")
    assert again["id"] != first["id"]
    assert_problem(api.delete(f"{DOSE_LOGS}/{first['id']}"), 404, "NOT_FOUND")


@pytest.mark.parametrize("dose_log_id", [str(uuid4()), "not-a-uuid"], ids=["unknown", "malformed"])
def test_undoing_a_missing_log_is_not_found(api: TestClient, dose_log_id: str) -> None:
    assert_problem(api.delete(f"{DOSE_LOGS}/{dose_log_id}"), 404, "NOT_FOUND")


def test_logging_for_a_missing_schedule_is_not_found(api: TestClient) -> None:
    body = {"schedule_id": str(uuid4()), "scheduled_for": DOSE_AT, "status": "taken"}
    assert_problem(api.post(DOSE_LOGS, json=body), 404, "NOT_FOUND")


def test_instant_sent_with_an_offset_is_returned_in_utc(
    api: TestClient, clock: FixedClock, setup: Json
) -> None:
    clock.set(harare(2, 8, 30))
    assert (
        log_dose(api, setup, scheduled_for="2026-11-02T08:00:00+02:00")["scheduled_for"] == DOSE_AT
    )


@pytest.mark.parametrize(
    ("fields", "field"),
    [
        ({"scheduled_for": "2026-11-02T06:00:00"}, "scheduled_for"),
        ({"status": "lost"}, "status"),
        ({"status": None}, "status"),
        ({"note": "x" * 281}, "note"),
        ({"schedule_id": "not-a-uuid"}, "schedule_id"),
        ({"recorded_at": DOSE_AT}, "recorded_at"),
    ],
    ids=["naive-instant", "unknown-status", "null-status", "281-chars", "bad-schedule-id", "extra"],
)
def test_invalid_dose_log_is_rejected(
    api: TestClient, clock: FixedClock, setup: Json, engine: Engine, fields: Json, field: str
) -> None:
    clock.set(harare(2, 8, 30))
    body = {
        "schedule_id": setup["schedule_id"],
        "scheduled_for": DOSE_AT,
        "status": "taken",
        **fields,
    }
    problem = assert_problem(api.post(DOSE_LOGS, json=body), 422, "VALIDATION_ERROR")
    assert [error["field"] for error in problem["errors"]] == [field]
    assert stored_logs(engine) == 0
