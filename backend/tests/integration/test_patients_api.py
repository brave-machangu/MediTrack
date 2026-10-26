"""Patients API (FR-01): AC-01, AC-02 and AC-13, on SQLite and PostgreSQL."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db.models import DoseLog, Medication, Schedule

# A parsed JSON body: its shape is exactly what each test asserts, so it stays untyped.
Json = dict[str, Any]

PATIENTS = "/api/v1/patients"
DEMO_PATIENT = {"display_name": "Demo Patient A", "timezone": "Africa/Harare"}


def create_patient(api: TestClient, **fields: str) -> Json:
    response = api.post(PATIENTS, json={**DEMO_PATIENT, **fields})
    assert response.status_code == 201, response.text
    body: Json = response.json()
    return body


def assert_problem(response: Response, status: int, code: str) -> Json:
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body: Json = response.json()
    assert (body["status"], body["code"]) == (status, code)
    return body


def add_dose_log(engine: Engine, patient_id: str) -> None:
    """Record one dose for the patient directly; the dose-log endpoint arrives in MT-016."""
    created = datetime(2026, 11, 1, tzinfo=UTC)
    with Session(engine) as session, session.begin():
        medication = Medication(
            patient_id=UUID(patient_id),
            name="Demo Med Alpha",
            dosage_label="1 tablet",
            created_at=created,
        )
        session.add(medication)
        session.flush()
        schedule = Schedule(
            medication_id=medication.id,
            times_of_day=["08:00"],
            days_of_week=[1, 2, 3, 4, 5, 6, 7],
            start_date=date(2026, 11, 1),
            grace_period_minutes=60,
        )
        session.add(schedule)
        session.flush()
        session.add(
            DoseLog(
                schedule_id=schedule.id,
                scheduled_for=datetime(2026, 11, 1, 6, tzinfo=UTC),
                status="taken",
                recorded_at=datetime(2026, 11, 1, 6, 5, tzinfo=UTC),
                late=False,
            )
        )


def test_created_patient_is_listed_ac01(api: TestClient) -> None:
    response = api.post(PATIENTS, json=DEMO_PATIENT)

    assert response.status_code == 201
    patient = response.json()
    assert set(patient) == {"id", "display_name", "timezone", "created_at"}
    assert UUID(patient["id"]).version == 4
    assert (patient["display_name"], patient["timezone"]) == ("Demo Patient A", "Africa/Harare")
    assert patient["created_at"] == "2026-11-02T05:30:00Z"  # the fixed clock, in UTC
    assert api.get(PATIENTS).json() == [patient]


def test_patients_are_listed_by_display_name_ignoring_case(api: TestClient) -> None:
    for name in ("Demo Patient B", "demo patient a", "Demo Patient C"):
        create_patient(api, display_name=name)
    names = [patient["display_name"] for patient in api.get(PATIENTS).json()]
    assert names == ["demo patient a", "Demo Patient B", "Demo Patient C"]


def test_invalid_timezone_returns_validation_error_on_timezone_field_ac02(api: TestClient) -> None:
    response = api.post(PATIENTS, json={**DEMO_PATIENT, "timezone": "Mars/Base"})

    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert body["errors"][0]["field"] == "timezone"
    assert "Mars/Base" not in response.text
    assert api.get(PATIENTS).json() == []


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({**DEMO_PATIENT, "timezone": "europe/london"}, "timezone"),
        ({**DEMO_PATIENT, "display_name": ""}, "display_name"),
        ({**DEMO_PATIENT, "display_name": "x" * 81}, "display_name"),
        ({**DEMO_PATIENT, "display_name": None}, "display_name"),
        ({"display_name": "Demo Patient A"}, "timezone"),
        ({**DEMO_PATIENT, "email": "demo@example.org"}, "email"),
    ],
    ids=["wrong-case-zone", "empty-name", "81-chars", "null-name", "no-zone", "unknown-field"],
)
def test_invalid_new_patient_is_rejected(api: TestClient, body: Json, field: str) -> None:
    problem = assert_problem(api.post(PATIENTS, json=body), 422, "VALIDATION_ERROR")
    assert [error["field"] for error in problem["errors"]] == [field]


def test_patient_can_be_read(api: TestClient) -> None:
    patient = create_patient(api)
    response = api.get(f"{PATIENTS}/{patient['id']}")
    assert response.status_code == 200
    assert response.json() == patient


@pytest.mark.parametrize("patient_id", [str(uuid4()), "not-a-uuid"], ids=["unknown", "malformed"])
def test_missing_patient_is_not_found(api: TestClient, patient_id: str) -> None:
    assert_problem(api.get(f"{PATIENTS}/{patient_id}"), 404, "NOT_FOUND")
    patch = api.patch(f"{PATIENTS}/{patient_id}", json={"display_name": "Demo Patient B"})
    assert_problem(patch, 404, "NOT_FOUND")


def test_display_name_can_be_changed(api: TestClient) -> None:
    patient = create_patient(api)
    response = api.patch(f"{PATIENTS}/{patient['id']}", json={"display_name": "Demo Patient B"})
    assert response.status_code == 200
    assert response.json() == {**patient, "display_name": "Demo Patient B"}
    assert api.get(f"{PATIENTS}/{patient['id']}").json()["display_name"] == "Demo Patient B"


def test_timezone_change_allowed_without_logs_ac13(api: TestClient) -> None:
    patient = create_patient(api)
    response = api.patch(f"{PATIENTS}/{patient['id']}", json={"timezone": "Europe/London"})
    assert response.status_code == 200
    assert response.json()["timezone"] == "Europe/London"


def test_timezone_change_rejected_once_logged_ac13(api: TestClient, engine: Engine) -> None:
    patient = create_patient(api)
    add_dose_log(engine, patient["id"])

    response = api.patch(f"{PATIENTS}/{patient['id']}", json={"timezone": "Europe/London"})

    assert_problem(response, 409, "PATIENT_HAS_LOGS")
    assert api.get(f"{PATIENTS}/{patient['id']}").json()["timezone"] == "Africa/Harare"


def test_name_change_with_unchanged_timezone_allowed_once_logged(
    api: TestClient, engine: Engine
) -> None:
    patient = create_patient(api)
    add_dose_log(engine, patient["id"])
    response = api.patch(
        f"{PATIENTS}/{patient['id']}",
        json={"display_name": "Demo Patient B", "timezone": "Africa/Harare"},
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "Demo Patient B"


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({}, "request"),
        ({"timezone": None}, "timezone"),
        ({"display_name": None}, "display_name"),
        ({"timezone": "Mars/Base"}, "timezone"),
        ({"nickname": "Demo"}, "nickname"),
    ],
    ids=["empty-body", "null-zone", "null-name", "unknown-zone", "unknown-field"],
)
def test_invalid_patient_update_is_rejected(api: TestClient, body: Json, field: str) -> None:
    patient = create_patient(api)
    problem = assert_problem(
        api.patch(f"{PATIENTS}/{patient['id']}", json=body), 422, "VALIDATION_ERROR"
    )
    assert [error["field"] for error in problem["errors"]] == [field]
    assert api.get(f"{PATIENTS}/{patient['id']}").json() == patient
