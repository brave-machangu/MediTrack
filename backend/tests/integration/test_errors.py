"""Every error path returns problem+json with a contract code (AC-31)."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError

from app.config import Settings
from app.domain.errors import PatientHasLogs
from app.errors import ErrorCode
from app.main import create_app

CONTRACT_CODES = {code.value for code in ErrorCode}


class _Body(BaseModel):
    times_of_day: list[str] = Field(min_length=1)
    grace_period_minutes: int = Field(ge=0, le=240)


@pytest.fixture
def app_with_test_routes(settings: Settings) -> FastAPI:
    """The real app plus routes that trigger each error path."""
    app = create_app(settings)

    @app.post("/_test/validate")
    def validate(body: _Body) -> dict[str, str]:
        return {"ok": "yes"}

    @app.get("/_test/items/{item_id}")
    def item(item_id: UUID) -> dict[str, str]:
        return {"id": str(item_id)}

    @app.get("/_test/conflict")
    def conflict() -> None:
        raise PatientHasLogs

    @app.get("/_test/crash")
    def crash() -> None:
        raise RuntimeError("secret internal detail")

    @app.get("/_test/db-down")
    def db_down() -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    @app.get("/_test/db-connection-lost")
    def db_connection_lost() -> None:
        raise DBAPIError("SELECT 1", {}, Exception("server closed"), connection_invalidated=True)

    @app.get("/_test/db-integrity")
    def db_integrity() -> None:
        raise IntegrityError("INSERT INTO patients", {}, Exception("violates a constraint"))

    return app


@pytest.fixture
def test_client(app_with_test_routes: FastAPI) -> Iterator[TestClient]:
    with TestClient(app_with_test_routes, raise_server_exceptions=False) as client:
        yield client


def _assert_problem(response_json: dict[str, object], status: int, code: ErrorCode) -> None:
    assert response_json["status"] == status
    assert response_json["code"] == code
    assert response_json["code"] in CONTRACT_CODES
    assert isinstance(response_json["title"], str)


def test_unknown_route_is_not_found_problem(test_client: TestClient) -> None:
    response = test_client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    _assert_problem(response.json(), 404, ErrorCode.NOT_FOUND)


def test_wrong_method_is_method_not_allowed_with_allow_header(test_client: TestClient) -> None:
    response = test_client.delete("/healthz")
    assert response.status_code == 405
    assert response.headers["content-type"] == "application/problem+json"
    assert "GET" in response.headers["allow"]
    _assert_problem(response.json(), 405, ErrorCode.METHOD_NOT_ALLOWED)


def test_allow_header_lists_every_method_of_the_path(test_client: TestClient) -> None:
    # GET and POST on /api/v1/patients are separate routes; Allow must name both.
    response = test_client.delete("/api/v1/patients")
    assert response.status_code == 405
    assert {"GET", "POST"} <= {method.strip() for method in response.headers["allow"].split(",")}


def test_validation_error_lists_fields_without_echoing_values(test_client: TestClient) -> None:
    response = test_client.post(
        "/_test/validate",
        json={"times_of_day": [], "grace_period_minutes": "PRIVACY-CANARY-NOTE"},
    )
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    _assert_problem(body, 422, ErrorCode.VALIDATION_ERROR)
    assert {error["field"] for error in body["errors"]} == {"times_of_day", "grace_period_minutes"}
    assert "PRIVACY-CANARY-NOTE" not in response.text


def test_malformed_id_in_path_is_not_found(test_client: TestClient) -> None:
    response = test_client.get("/_test/items/PRIVACY-CANARY-NOTE")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    _assert_problem(response.json(), 404, ErrorCode.NOT_FOUND)
    assert "PRIVACY-CANARY-NOTE" not in response.text


def test_domain_error_maps_to_its_status_and_code(test_client: TestClient) -> None:
    response = test_client.get("/_test/conflict")
    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    _assert_problem(response.json(), 409, ErrorCode.PATIENT_HAS_LOGS)


def test_unhandled_error_is_internal_error_without_details(test_client: TestClient) -> None:
    response = test_client.get("/_test/crash")
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    _assert_problem(response.json(), 500, ErrorCode.INTERNAL_ERROR)
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text


@pytest.mark.parametrize("path", ["/_test/db-down", "/_test/db-connection-lost"])
def test_database_outage_is_service_unavailable(test_client: TestClient, path: str) -> None:
    response = test_client.get(path)
    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["retry-after"] == "5"
    _assert_problem(response.json(), 503, ErrorCode.SERVICE_UNAVAILABLE)
    assert "SELECT 1" not in response.text


def test_other_database_error_is_internal_error(test_client: TestClient) -> None:
    response = test_client.get("/_test/db-integrity")
    assert response.status_code == 500
    _assert_problem(response.json(), 500, ErrorCode.INTERNAL_ERROR)
    assert "INSERT INTO" not in response.text


@pytest.mark.parametrize(
    "body",
    [bytes([0x80]), bytes([0xFF]), b"{not json"],
    ids=["lone-continuation-byte", "lone-0xff", "malformed-json"],
)
def test_unreadable_body_is_a_validation_error(test_client: TestClient, body: bytes) -> None:
    # The contract documents 422 for invalid requests, never 400 (found by the contract test).
    response = test_client.post(
        "/api/v1/patients", content=body, headers={"content-type": "application/json"}
    )
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    _assert_problem(response.json(), 422, ErrorCode.VALIDATION_ERROR)
