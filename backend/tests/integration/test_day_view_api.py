"""Day view, `GET /api/v1/patients/{patient_id}/doses` (FR-04): AC-09, AC-10 and the AC-34 day
views, on SQLite and PostgreSQL. The patient is in Africa/Harare (UTC+2) unless stated."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.clock import FixedClock
from app.config import Settings
from app.main import create_app
from tests.integration.helpers import (
    PATIENTS,
    Json,
    add_dose_log,
    assert_problem,
    create_medication,
    create_patient,
)

PLANNED_DOSE_FIELDS = {
    "schedule_id",
    "medication_id",
    "medication_name",
    "dosage_label",
    "instructions",
    "scheduled_for",
    "local_date",
    "local_time",
    "status",
    "late",
    "log_window_opens_at",
    "log_window_closes_at",
    "dose_log_id",
    "recorded_at",
}


def add_schedule(api: TestClient, medication_id: str, **fields: object) -> Json:
    body = {"times_of_day": ["08:00"], "start_date": "2026-11-01", **fields}
    response = api.post(f"/api/v1/medications/{medication_id}/schedules", json=body)
    assert response.status_code == 201, response.text
    schedule: Json = response.json()
    return schedule


def day_view(api: TestClient, patient_id: str, day: str | None = None) -> Json:
    query = f"?date={day}" if day else ""
    response = api.get(f"{PATIENTS}/{patient_id}/doses{query}")
    assert response.status_code == 200, response.text
    body: Json = response.json()
    return body


def test_day_view_defaults_to_patient_local_date_ac09(api: TestClient, clock: FixedClock) -> None:
    patient = create_patient(api)
    add_schedule(api, create_medication(api, patient["id"])["id"])
    clock.set(datetime(2026, 11, 1, 23, 30, tzinfo=UTC))  # already 2026-11-02 01:30 in Harare

    view = day_view(api, patient["id"])

    assert (view["patient_id"], view["timezone"]) == (patient["id"], "Africa/Harare")
    assert (view["date"], view["generated_at"]) == ("2026-11-02", "2026-11-01T23:30:00Z")
    assert [dose["scheduled_for"] for dose in view["doses"]] == ["2026-11-02T06:00:00Z"]


def test_planned_dose_has_every_contract_field(api: TestClient) -> None:
    patient = create_patient(api)
    medication = create_medication(api, patient["id"], instructions="With food")
    schedule = add_schedule(api, medication["id"])

    [dose] = day_view(api, patient["id"], "2026-11-02")["doses"]  # clock: 07:30 local

    assert set(dose) == PLANNED_DOSE_FIELDS
    assert dose == {
        "schedule_id": schedule["id"],
        "medication_id": medication["id"],
        "medication_name": "Demo Med Alpha",
        "dosage_label": "1 tablet",
        "instructions": "With food",
        "scheduled_for": "2026-11-02T06:00:00Z",
        "local_date": "2026-11-02",
        "local_time": "08:00",
        "status": "upcoming",
        "late": False,
        "log_window_opens_at": "2026-11-02T05:00:00Z",
        "log_window_closes_at": "2026-11-03T06:00:00Z",
        "dose_log_id": None,
        "recorded_at": None,
    }


def test_status_comes_from_the_server_clock(api: TestClient, clock: FixedClock) -> None:
    patient = create_patient(api)
    add_schedule(api, create_medication(api, patient["id"])["id"])
    clock.set(datetime(2026, 11, 2, 7, 0, 1, tzinfo=UTC))  # 09:00:01 local, past the grace
    assert day_view(api, patient["id"])["doses"][0]["status"] == "missed"


def test_logged_doses_show_their_logs(api: TestClient, engine: Engine) -> None:
    patient = create_patient(api)
    schedule = add_schedule(
        api, create_medication(api, patient["id"])["id"], times_of_day=["08:00", "20:00"]
    )
    for hour in (6, 18):  # 08:00 and 20:00 local
        add_dose_log(engine, schedule["id"], datetime(2026, 11, 2, hour, tzinfo=UTC))

    doses = day_view(api, patient["id"], "2026-11-02")["doses"]

    assert [(dose["local_time"], dose["status"]) for dose in doses] == [
        ("08:00", "taken"),
        ("20:00", "taken"),
    ]
    assert all(dose["dose_log_id"] is not None for dose in doses)
    assert doses[1]["recorded_at"] == "2026-11-02T18:00:00Z"


def test_doses_are_ordered_by_time_then_medication_name(api: TestClient) -> None:
    patient = create_patient(api)
    for name, time in (
        ("Demo Med Beta", "08:00"),
        ("demo med alpha", "08:00"),
        ("Demo Med Gamma", "07:00"),
    ):
        add_schedule(
            api, create_medication(api, patient["id"], name=name)["id"], times_of_day=[time]
        )

    doses = day_view(api, patient["id"], "2026-11-02")["doses"]

    assert [(dose["local_time"], dose["medication_name"]) for dose in doses] == [
        ("07:00", "Demo Med Gamma"),
        ("08:00", "demo med alpha"),
        ("08:00", "Demo Med Beta"),
    ]


def test_day_views_follow_a_schedule_change_ac34(api: TestClient) -> None:
    patient = create_patient(api)
    medication_id = create_medication(api, patient["id"])["id"]
    old = add_schedule(api, medication_id, times_of_day=["08:00"])
    api.patch(f"/api/v1/schedules/{old['id']}", json={"end_date": "2026-11-05"})
    add_schedule(api, medication_id, times_of_day=["09:00"], start_date="2026-11-06")

    on_old_end = day_view(api, patient["id"], "2026-11-05")["doses"]
    on_new_start = day_view(api, patient["id"], "2026-11-06")["doses"]

    assert [dose["local_time"] for dose in on_old_end] == ["08:00"]
    assert [dose["local_time"] for dose in on_new_start] == ["09:00"]


def test_deactivated_medication_keeps_only_earlier_doses_ac10(
    api: TestClient, clock: FixedClock
) -> None:
    patient = create_patient(api)
    medication = create_medication(api, patient["id"])
    add_schedule(api, medication["id"], times_of_day=["08:00", "20:00"])
    clock.set(datetime(2026, 11, 2, 10, tzinfo=UTC))  # 12:00 local
    api.patch(f"/api/v1/medications/{medication['id']}", json={"active": False})

    today = day_view(api, patient["id"], "2026-11-02")["doses"]
    tomorrow = day_view(api, patient["id"], "2026-11-03")["doses"]

    assert [dose["local_time"] for dose in today] == ["08:00"]
    assert tomorrow == []


def test_dst_gap_dose_is_shown_at_the_shifted_local_time(api: TestClient) -> None:
    patient = create_patient(api, timezone="Europe/London")
    add_schedule(api, create_medication(api, patient["id"])["id"], times_of_day=["01:30", "02:30"])

    doses = day_view(api, patient["id"], "2027-03-28")["doses"]

    assert [(dose["scheduled_for"], dose["local_time"]) for dose in doses] == [
        ("2027-03-28T01:30:00Z", "02:30")
    ]


def test_dose_shifted_past_midnight_shows_on_the_next_day(api: TestClient) -> None:
    # Lead decision Q1: in America/Nuuk the clocks jump from 23:00 Saturday 2026-03-28 to
    # 00:00 Sunday, so the Saturday 23:30 dose happens on Sunday at 00:30, even though the
    # schedule ends on Saturday.
    patient = create_patient(api, timezone="America/Nuuk")
    medication_id = create_medication(api, patient["id"])["id"]
    add_schedule(
        api, medication_id, times_of_day=["23:30"], start_date="2026-03-01", end_date="2026-03-28"
    )

    saturday = day_view(api, patient["id"], "2026-03-28")["doses"]
    sunday = day_view(api, patient["id"], "2026-03-29")["doses"]

    assert saturday == []
    assert [(dose["scheduled_for"], dose["local_date"], dose["local_time"]) for dose in sunday] == [
        ("2026-03-29T01:30:00Z", "2026-03-29", "00:30")
    ]


@pytest.mark.parametrize("patient_id", [str(uuid4()), "not-a-uuid"], ids=["unknown", "malformed"])
def test_day_view_of_missing_patient_is_not_found(api: TestClient, patient_id: str) -> None:
    # The route exists (200 for a real patient), so the 404 is about the patient.
    day_view(api, create_patient(api)["id"])
    assert_problem(api.get(f"{PATIENTS}/{patient_id}/doses"), 404, "NOT_FOUND")


def test_invalid_date_is_rejected(api: TestClient) -> None:
    patient = create_patient(api)
    problem = assert_problem(
        api.get(f"{PATIENTS}/{patient['id']}/doses?date=2026-13-01"), 422, "VALIDATION_ERROR"
    )
    assert [error["field"] for error in problem["errors"]] == ["date"]


@pytest.fixture
def api_with_short_early_window(
    engine: Engine, database_url: str, clock: FixedClock
) -> Iterator[TestClient]:
    settings = Settings(
        database_url=database_url,
        environment="test",
        version="test-sha",
        early_log_window_minutes=30,
        late_log_limit_minutes=120,
    )
    with TestClient(create_app(settings, clock), raise_server_exceptions=False) as client:
        yield client


def test_log_window_comes_from_settings(api_with_short_early_window: TestClient) -> None:
    api = api_with_short_early_window
    patient = create_patient(api)
    add_schedule(api, create_medication(api, patient["id"])["id"])

    [dose] = day_view(api, patient["id"], "2026-11-02")["doses"]

    assert dose["log_window_opens_at"] == "2026-11-02T05:30:00Z"
    assert dose["log_window_closes_at"] == "2026-11-02T08:00:00Z"
