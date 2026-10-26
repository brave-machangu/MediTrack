"""Builders and assertions shared by the API tests. Synthetic data only."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db.models import DoseLog, Medication, Schedule

# A parsed JSON body: its shape is exactly what each test asserts, so it stays untyped.
Json = dict[str, Any]

PATIENTS = "/api/v1/patients"
DEMO_PATIENT = {"display_name": "Demo Patient A", "timezone": "Africa/Harare"}
DEMO_MEDICATION = {"name": "Demo Med Alpha", "dosage_label": "1 tablet"}
EVERY_DAY = [1, 2, 3, 4, 5, 6, 7]


def create_patient(api: TestClient, **fields: str) -> Json:
    response = api.post(PATIENTS, json={**DEMO_PATIENT, **fields})
    assert response.status_code == 201, response.text
    body: Json = response.json()
    return body


def create_medication(api: TestClient, patient_id: str, **fields: str | None) -> Json:
    response = api.post(f"{PATIENTS}/{patient_id}/medications", json={**DEMO_MEDICATION, **fields})
    assert response.status_code == 201, response.text
    body: Json = response.json()
    return body


def assert_problem(response: Response, status: int, code: str) -> Json:
    assert response.status_code == status, response.text
    assert response.headers["content-type"] == "application/problem+json"
    body: Json = response.json()
    assert (body["status"], body["code"]) == (status, code)
    return body


def add_schedule(
    engine: Engine,
    medication_id: str,
    *,
    times: list[str] | None = None,
    start: date = date(2026, 11, 1),
) -> str:
    """Store a schedule directly, for tests that run before or without the schedules API."""
    with Session(engine) as session, session.begin():
        schedule = Schedule(
            medication_id=UUID(medication_id),
            times_of_day=times or ["08:00"],
            days_of_week=EVERY_DAY,
            start_date=start,
            grace_period_minutes=60,
        )
        session.add(schedule)
        session.flush()
        return str(schedule.id)


def add_dose_log(engine: Engine, schedule_id: str, scheduled_for: datetime) -> None:
    """Store a dose log directly; the dose-log endpoint arrives in MT-016."""
    with Session(engine) as session, session.begin():
        session.add(
            DoseLog(
                schedule_id=UUID(schedule_id),
                scheduled_for=scheduled_for,
                status="taken",
                recorded_at=scheduled_for,
                late=False,
            )
        )


def add_logged_dose(engine: Engine, patient_id: str) -> None:
    """A medication, a daily 08:00 schedule and one logged dose (2026-11-01 08:00 Harare)."""
    with Session(engine) as session, session.begin():
        medication = Medication(
            patient_id=UUID(patient_id),
            name="Demo Med Alpha",
            dosage_label="1 tablet",
            created_at=datetime(2026, 11, 1, tzinfo=UTC),
        )
        session.add(medication)
        session.flush()
        medication_id = str(medication.id)
    schedule_id = add_schedule(engine, medication_id)
    add_dose_log(engine, schedule_id, datetime(2026, 11, 1, 6, tzinfo=UTC))
