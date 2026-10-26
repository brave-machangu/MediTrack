"""AC-31 and AC-32: the running backend conforms to api/openapi.yaml.

Two complementary tests:
- Schemathesis generates requests for every operation and checks status codes, content
  types, response schemas, and that no undocumented field appears.
- A scripted walk through all operations with real data, so the 2xx shapes are checked too
  (random IDs mostly hit 404), plus one error response of every kind the contract names.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import schemathesis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from schemathesis.specs.openapi.schemas import OpenApiSchema

from app.clock import FixedClock
from tests.contract.strictness import no_undocumented_fields, response_schema, undocumented_fields

lazy_contract = schemathesis.pytest.from_fixture("contract")


# #85: listMedications doesn't document 422 yet; see test_invalid_include_inactive_... below.
@lazy_contract.exclude(operation_id="listMedications").parametrize()
def test_generated_requests_get_documented_responses_ac32(case: schemathesis.Case) -> None:
    case.call_and_validate(additional_checks=[no_undocumented_fields])


class ContractWalk:
    """Sends requests and validates every response against the contract."""

    def __init__(self, client: TestClient, contract: OpenApiSchema) -> None:
        self.client = client
        self.contract = contract
        self.raw: dict[str, Any] = contract.raw_schema
        self.exercised: set[tuple[str, str]] = set()
        self.problem_codes: set[str] = set()

    def call(self, method: str, template: str, expected: int, **request: Any) -> Response:
        """`template` is the contract path; `path=` gives the concrete URL when it has IDs."""
        url = request.pop("path", template)
        response = self.client.request(method, url, **request)
        assert response.status_code == expected, f"{method} {url}: {response.text}"
        self.contract[template][method].validate_response(response)
        media_type = response.headers.get("content-type", "")
        if response.content:
            schema = response_schema(self.raw, template, method, response.status_code, media_type)
            assert schema is not None, f"{method} {template} {response.status_code} has no schema"
            assert undocumented_fields(self.raw, schema, response.json()) == []
        if media_type == "application/problem+json":
            self.problem_codes.add(response.json()["code"])
        self.exercised.add((method.upper(), template))
        return response


@pytest.fixture
def walk(app: FastAPI, contract: OpenApiSchema) -> Iterator[ContractWalk]:
    with TestClient(app, raise_server_exceptions=False) as client:
        yield ContractWalk(client, contract)


def test_every_operation_returns_documented_responses_ac31_ac32(
    walk: ContractWalk, app: FastAPI
) -> None:
    clock = app.state.context.clock
    assert isinstance(clock, FixedClock)  # 2026-11-02 05:30Z = 07:30 in Harare
    PATIENTS = "/api/v1/patients"
    PATIENT = "/api/v1/patients/{patient_id}"
    MEDICATIONS = "/api/v1/patients/{patient_id}/medications"
    MEDICATION = "/api/v1/medications/{medication_id}"
    SCHEDULES = "/api/v1/medications/{medication_id}/schedules"
    SCHEDULE = "/api/v1/schedules/{schedule_id}"
    DOSES = "/api/v1/patients/{patient_id}/doses"
    DOSE_LOGS = "/api/v1/dose-logs"
    DOSE_LOG = "/api/v1/dose-logs/{dose_log_id}"
    MISSED = "/api/v1/patients/{patient_id}/missed-doses"
    ADHERENCE = "/api/v1/patients/{patient_id}/adherence/daily"
    unknown = "00000000-0000-4000-8000-000000000000"

    walk.call("GET", "/healthz", 200)
    walk.call("GET", "/readyz", 200)

    # Patients
    walk.call("GET", PATIENTS, 200)
    patient = walk.call(
        "POST", PATIENTS, 201, json={"display_name": "Demo Patient A", "timezone": "Africa/Harare"}
    ).json()
    p = f"{PATIENTS}/{patient['id']}"
    walk.call(
        "POST", PATIENTS, 422, json={"display_name": "Demo Patient A", "timezone": "Mars/Base"}
    )
    walk.call("GET", PATIENT, 200, path=p)
    walk.call("GET", PATIENT, 404, path=f"{PATIENTS}/{unknown}")
    walk.call("PATCH", PATIENT, 200, path=p, json={"display_name": "Demo Patient B"})
    walk.call("PATCH", PATIENT, 422, path=p, json={})

    # Medications
    medication = walk.call(
        "POST",
        MEDICATIONS,
        201,
        path=f"{p}/medications",
        json={"name": "Demo Med Alpha", "dosage_label": "1 tablet"},
    ).json()
    m = f"/api/v1/medications/{medication['id']}"
    walk.call("GET", MEDICATIONS, 200, path=f"{p}/medications")
    walk.call("GET", MEDICATION, 200, path=m)
    walk.call("PATCH", MEDICATION, 200, path=m, json={"instructions": "With food"})

    # Schedules: one to keep, one to delete
    schedule = walk.call(
        "POST",
        SCHEDULES,
        201,
        path=f"{m}/schedules",
        json={"times_of_day": ["08:00"], "start_date": "2026-11-01"},
    ).json()
    s = f"/api/v1/schedules/{schedule['id']}"
    walk.call(
        "POST",
        SCHEDULES,
        409,
        path=f"{m}/schedules",
        json={"times_of_day": ["09:00"], "start_date": "2026-11-05"},
    )
    walk.call("GET", SCHEDULES, 200, path=f"{m}/schedules")
    walk.call("PATCH", SCHEDULE, 200, path=s, json={"grace_period_minutes": 60})
    other = walk.call(
        "POST",
        MEDICATIONS,
        201,
        path=f"{p}/medications",
        json={"name": "Demo Med Beta", "dosage_label": "5 ml"},
    ).json()
    disposable = walk.call(
        "POST",
        SCHEDULES,
        201,
        path=f"/api/v1/medications/{other['id']}/schedules",
        json={"times_of_day": ["20:00"], "start_date": "2026-11-01"},
    ).json()
    walk.call("DELETE", SCHEDULE, 204, path=f"/api/v1/schedules/{disposable['id']}")
    walk.call("DELETE", SCHEDULE, 404, path=f"/api/v1/schedules/{disposable['id']}")

    # Doses: day view, log, duplicate, unplanned, outside the window, undo
    walk.call("GET", DOSES, 200, path=f"{p}/doses")
    walk.call("GET", DOSES, 422, path=f"{p}/doses?date=2026-13-01")
    clock.set(datetime(2026, 11, 2, 6, 30, tzinfo=UTC))
    dose = {
        "schedule_id": schedule["id"],
        "scheduled_for": "2026-11-02T06:00:00Z",
        "status": "taken",
    }
    log = walk.call("POST", DOSE_LOGS, 201, json=dose).json()
    walk.call("POST", DOSE_LOGS, 409, json=dose)
    walk.call("POST", DOSE_LOGS, 422, json={**dose, "scheduled_for": "2026-11-02T06:30:00Z"})
    # 2026-11-01 08:00 is planned but 24.5 hours ago: outside the log window.
    walk.call("POST", DOSE_LOGS, 422, json={**dose, "scheduled_for": "2026-11-01T06:00:00Z"})
    walk.call("POST", DOSE_LOGS, 404, json={**dose, "schedule_id": unknown})
    walk.call("DELETE", DOSE_LOG, 204, path=f"{DOSE_LOGS}/{log['id']}")
    walk.call("DELETE", DOSE_LOG, 404, path=f"{DOSE_LOGS}/{log['id']}")
    walk.call("POST", DOSE_LOGS, 201, json=dose)

    # Rules that need logs or an inactive medication
    walk.call("PATCH", PATIENT, 409, path=p, json={"timezone": "Europe/London"})
    walk.call("PATCH", SCHEDULE, 409, path=s, json={"times_of_day": ["09:00"]})
    walk.call("DELETE", SCHEDULE, 409, path=s)
    walk.call("PATCH", MEDICATION, 200, path=m, json={"active": False})
    walk.call("PATCH", MEDICATION, 409, path=m, json={"active": True})
    walk.call(
        "POST",
        SCHEDULES,
        409,
        path=f"{m}/schedules",
        json={"times_of_day": ["21:00"], "start_date": "2027-01-01"},
    )

    # Reports
    clock.set(datetime(2026, 11, 3, 12, tzinfo=UTC))
    walk.call("GET", MISSED, 200, path=f"{p}/missed-doses")
    walk.call("GET", MISSED, 422, path=f"{p}/missed-doses?from=2026-11-05&to=2026-11-04")
    walk.call("GET", ADHERENCE, 200, path=f"{p}/adherence/daily?date=2026-11-02")
    walk.call("GET", ADHERENCE, 404, path=f"{PATIENTS}/{unknown}/adherence/daily")

    documented = {
        (method.upper(), path)
        for path, item in walk.raw["paths"].items()
        for method in item
        if method != "parameters"
    }
    assert walk.exercised == documented
    assert walk.problem_codes == {
        "VALIDATION_ERROR",
        "NOT_FOUND",
        "DUPLICATE_DOSE_LOG",
        "DOSE_NOT_PLANNED",
        "OUTSIDE_LOG_WINDOW",
        "SCHEDULE_HAS_LOGS",
        "MEDICATION_INACTIVE",
        "PATIENT_HAS_LOGS",
        "SCHEDULE_OVERLAP",
    }


def test_method_not_allowed_is_a_contract_problem_ac31(walk: ContractWalk) -> None:
    # 405 isn't an operation's documented response; the contract describes it on Problem.
    response = walk.client.delete("/api/v1/patients")
    assert response.status_code == 405
    assert response.headers["content-type"] == "application/problem+json"
    assert {"GET", "POST"} <= {m.strip() for m in response.headers["allow"].split(",")}
    problem_schema = walk.raw["components"]["schemas"]["Problem"]
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"
    assert response.json()["code"] in problem_schema["properties"]["code"]["enum"]
    assert undocumented_fields(walk.raw, problem_schema, response.json()) == []


@pytest.mark.xfail(
    strict=True,
    reason="#85: the contract doesn't document 422 on listMedications yet",
    raises=AssertionError,
)
def test_invalid_include_inactive_is_a_documented_422(walk: ContractWalk) -> None:
    patient = walk.client.post(
        "/api/v1/patients", json={"display_name": "Demo Patient A", "timezone": "UTC"}
    ).json()
    response = walk.client.get(
        f"/api/v1/patients/{patient['id']}/medications?include_inactive=maybe"
    )
    assert response.status_code == 422
    documented = walk.raw["paths"]["/api/v1/patients/{patient_id}/medications"]["get"]["responses"]
    assert "422" in documented
