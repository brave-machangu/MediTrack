"""Medications API (FR-02): AC-03 and AC-04, on SQLite and PostgreSQL."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.clock import FixedClock
from tests.integration.helpers import (
    DEMO_MEDICATION,
    PATIENTS,
    Json,
    add_dose_log,
    add_schedule,
    assert_problem,
    create_medication,
    create_patient,
)

MEDICATIONS = "/api/v1/medications"
MEDICATION_FIELDS = {
    "id",
    "patient_id",
    "name",
    "dosage_label",
    "instructions",
    "active",
    "deactivated_at",
    "created_at",
    "schedules",
}


def medications_of(api: TestClient, patient_id: str, query: str = "") -> list[Json]:
    response = api.get(f"{PATIENTS}/{patient_id}/medications{query}")
    assert response.status_code == 200, response.text
    body: list[Json] = response.json()
    return body


def test_new_medication_is_active_without_schedules_ac03(api: TestClient) -> None:
    patient = create_patient(api)
    response = api.post(
        f"{PATIENTS}/{patient['id']}/medications",
        json={**DEMO_MEDICATION, "instructions": "With food"},
    )

    assert response.status_code == 201
    medication = response.json()
    assert set(medication) == MEDICATION_FIELDS
    assert medication["patient_id"] == patient["id"]
    assert (medication["name"], medication["dosage_label"]) == ("Demo Med Alpha", "1 tablet")
    assert medication["instructions"] == "With food"
    assert (medication["active"], medication["deactivated_at"]) == (True, None)
    assert medication["created_at"] == "2026-11-02T05:30:00Z"
    assert medication["schedules"] == []
    assert medications_of(api, patient["id"]) == [medication]


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({**DEMO_MEDICATION, "name": ""}, "name"),
        ({**DEMO_MEDICATION, "name": "x" * 101}, "name"),
        ({**DEMO_MEDICATION, "name": None}, "name"),
        ({"name": "Demo Med Alpha"}, "dosage_label"),
        ({**DEMO_MEDICATION, "dosage_label": ""}, "dosage_label"),
        ({**DEMO_MEDICATION, "instructions": "x" * 501}, "instructions"),
        ({**DEMO_MEDICATION, "active": False}, "active"),
    ],
    ids=["empty-name", "101-chars", "null-name", "no-label", "empty-label", "501-chars", "extra"],
)
def test_invalid_medication_is_rejected_ac03(api: TestClient, body: Json, field: str) -> None:
    patient = create_patient(api)
    response = api.post(f"{PATIENTS}/{patient['id']}/medications", json=body)
    problem = assert_problem(response, 422, "VALIDATION_ERROR")
    assert [error["field"] for error in problem["errors"]] == [field]
    assert medications_of(api, patient["id"]) == []


@pytest.mark.parametrize("patient_id", [str(uuid4()), "not-a-uuid"], ids=["unknown", "malformed"])
def test_medications_of_missing_patient_are_not_found(api: TestClient, patient_id: str) -> None:
    assert_problem(api.get(f"{PATIENTS}/{patient_id}/medications"), 404, "NOT_FOUND")
    response = api.post(f"{PATIENTS}/{patient_id}/medications", json=DEMO_MEDICATION)
    assert_problem(response, 404, "NOT_FOUND")


def test_deactivated_medication_only_listed_with_include_inactive_ac04(api: TestClient) -> None:
    patient = create_patient(api)
    medication = create_medication(api, patient["id"])

    response = api.patch(f"{MEDICATIONS}/{medication['id']}", json={"active": False})

    assert response.status_code == 200
    deactivated = response.json()
    assert (deactivated["active"], deactivated["deactivated_at"]) == (False, "2026-11-02T05:30:00Z")
    assert medications_of(api, patient["id"]) == []
    assert medications_of(api, patient["id"], "?include_inactive=true") == [deactivated]


def test_reactivation_is_rejected(api: TestClient) -> None:
    medication = create_medication(api, create_patient(api)["id"])
    api.patch(f"{MEDICATIONS}/{medication['id']}", json={"active": False})

    response = api.patch(f"{MEDICATIONS}/{medication['id']}", json={"active": True})

    assert_problem(response, 409, "MEDICATION_INACTIVE")
    assert api.get(f"{MEDICATIONS}/{medication['id']}").json()["active"] is False


def test_deactivating_again_keeps_the_first_deactivation_time(
    api: TestClient, clock: FixedClock
) -> None:
    medication = create_medication(api, create_patient(api)["id"])
    api.patch(f"{MEDICATIONS}/{medication['id']}", json={"active": False})
    clock.advance(timedelta(hours=3))

    response = api.patch(f"{MEDICATIONS}/{medication['id']}", json={"active": False})

    assert response.status_code == 200
    assert response.json()["deactivated_at"] == "2026-11-02T05:30:00Z"


def test_inactive_medication_can_still_be_renamed(api: TestClient) -> None:
    medication = create_medication(api, create_patient(api)["id"])
    api.patch(f"{MEDICATIONS}/{medication['id']}", json={"active": False})
    response = api.patch(f"{MEDICATIONS}/{medication['id']}", json={"name": "Demo Med Beta"})
    assert response.status_code == 200
    assert (response.json()["name"], response.json()["active"]) == ("Demo Med Beta", False)


def test_instructions_are_cleared_by_null_and_kept_when_not_sent(api: TestClient) -> None:
    medication = create_medication(api, create_patient(api)["id"], instructions="With food")
    url = f"{MEDICATIONS}/{medication['id']}"

    assert api.patch(url, json={"dosage_label": "2 tablets"}).json()["instructions"] == "With food"
    assert api.patch(url, json={"instructions": None}).json()["instructions"] is None


def test_medications_are_listed_by_name_ignoring_case(api: TestClient) -> None:
    patient = create_patient(api)
    for name in ("Demo Med Beta", "demo med alpha", "Demo Med Gamma"):
        create_medication(api, patient["id"], name=name)
    names = [medication["name"] for medication in medications_of(api, patient["id"])]
    assert names == ["demo med alpha", "Demo Med Beta", "Demo Med Gamma"]


def test_medication_lists_its_schedules_with_has_dose_logs(api: TestClient, engine: Engine) -> None:
    patient = create_patient(api)
    medication = create_medication(api, patient["id"])
    later = add_schedule(engine, medication["id"], times=["20:00"], start=date(2026, 12, 1))
    earlier = add_schedule(engine, medication["id"], times=["08:00"], start=date(2026, 11, 1))
    add_dose_log(engine, earlier, datetime(2026, 11, 1, 6, tzinfo=UTC))

    schedules = api.get(f"{MEDICATIONS}/{medication['id']}").json()["schedules"]

    assert [(s["id"], s["has_dose_logs"]) for s in schedules] == [(earlier, True), (later, False)]
    assert schedules[0] == {
        "id": earlier,
        "medication_id": medication["id"],
        "times_of_day": ["08:00"],
        "days_of_week": [1, 2, 3, 4, 5, 6, 7],
        "start_date": "2026-11-01",
        "end_date": None,
        "grace_period_minutes": 60,
        "has_dose_logs": True,
    }
    assert medications_of(api, patient["id"])[0]["schedules"] == schedules


@pytest.mark.parametrize(
    "medication_id", [str(uuid4()), "not-a-uuid"], ids=["unknown", "malformed"]
)
def test_missing_medication_is_not_found(api: TestClient, medication_id: str) -> None:
    assert_problem(api.get(f"{MEDICATIONS}/{medication_id}"), 404, "NOT_FOUND")
    response = api.patch(f"{MEDICATIONS}/{medication_id}", json={"name": "Demo Med Beta"})
    assert_problem(response, 404, "NOT_FOUND")


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({}, "request"),
        ({"active": None}, "active"),
        ({"name": None}, "name"),
        ({"name": ""}, "name"),
        ({"patient_id": str(uuid4())}, "patient_id"),
    ],
    ids=["empty-body", "null-active", "null-name", "empty-name", "unknown-field"],
)
def test_invalid_medication_update_is_rejected(api: TestClient, body: Json, field: str) -> None:
    medication = create_medication(api, create_patient(api)["id"])
    response = api.patch(f"{MEDICATIONS}/{medication['id']}", json=body)
    problem = assert_problem(response, 422, "VALIDATION_ERROR")
    assert [error["field"] for error in problem["errors"]] == [field]
    assert api.get(f"{MEDICATIONS}/{medication['id']}").json() == medication
