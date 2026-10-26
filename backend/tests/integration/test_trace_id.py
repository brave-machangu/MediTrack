"""AC-37: every response carries X-Trace-Id; problem bodies and the request's log records carry
the same trace ID. Also: an unexpected error never escapes to the server's own log."""

from __future__ import annotations

import io
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.main import create_app
from app.telemetry import setup_telemetry

TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
SPAN_ID = re.compile(r"^[0-9a-f]{16}$")


@dataclass
class Traced:
    client: TestClient
    logs: io.StringIO

    def log_lines(self) -> list[dict[str, object]]:
        return [json.loads(line) for line in self.logs.getvalue().splitlines() if line]


@pytest.fixture
def traced(settings: Settings) -> Iterator[Traced]:
    logs = io.StringIO()
    app: FastAPI = create_app(settings, telemetry=setup_telemetry(settings, log_stream=logs))

    @app.get("/_test/crash")
    def crash() -> None:
        raise RuntimeError("PRIVACY-CANARY-NOTE")

    @app.get("/_test/db-down")
    def db_down() -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    # raise_server_exceptions=True: an exception that escaped the app would fail the request.
    with TestClient(app, raise_server_exceptions=True) as client:
        yield Traced(client, logs)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/healthz"),
        ("GET", "/readyz"),
        ("GET", "/api/v1/patients/not-a-uuid"),
        ("DELETE", "/api/v1/patients"),
        ("POST", "/api/v1/patients"),
        ("GET", "/_test/crash"),
        ("GET", "/_test/db-down"),
        ("GET", "/no/such/route"),
    ],
    ids=["200", "readyz", "404", "405", "422", "500", "503", "unknown-route"],
)
def test_every_response_has_a_trace_id_header_ac37(traced: Traced, method: str, path: str) -> None:
    response = traced.client.request(method, path, json={})
    assert TRACE_ID.match(response.headers["x-trace-id"])


@pytest.mark.parametrize(
    ("method", "path", "status"),
    [
        ("GET", "/api/v1/patients/not-a-uuid", 404),
        ("DELETE", "/api/v1/patients", 405),
        ("POST", "/api/v1/patients", 422),
        ("GET", "/_test/crash", 500),
        ("GET", "/_test/db-down", 503),
    ],
)
def test_problem_trace_id_equals_the_header_and_the_log_record_ac37(
    traced: Traced, method: str, path: str, status: int
) -> None:
    response = traced.client.request(method, path, json={})

    assert response.status_code == status
    trace_id = response.headers["x-trace-id"]
    assert response.json()["trace_id"] == trace_id
    [record] = [line for line in traced.log_lines() if line["event"] == "request.failed"]
    assert (record["trace_id"], record["status_code"]) == (trace_id, status)
    assert SPAN_ID.match(str(record["span_id"]))


def test_each_request_gets_its_own_trace_id(traced: Traced) -> None:
    ids = {traced.client.get("/healthz").headers["x-trace-id"] for _ in range(3)}
    assert len(ids) == 3


def test_unexpected_error_is_answered_here_and_logged_by_type_only(traced: Traced) -> None:
    response = traced.client.get("/_test/crash")  # would raise in the client if it escaped

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    [record] = traced.log_lines()
    assert record == {
        "time": record["time"],
        "level": "error",
        "event": "request.failed",
        "trace_id": response.headers["x-trace-id"],
        "span_id": record["span_id"],
        "route": "/_test/crash",
        "method": "GET",
        "status_code": 500,
        "error_code": "INTERNAL_ERROR",
        "error_type": "RuntimeError",
    }
    assert "PRIVACY-CANARY-NOTE" not in traced.logs.getvalue() + response.text


def test_failed_request_log_names_the_route_template_not_the_path(traced: Traced) -> None:
    traced.client.get("/api/v1/patients/00000000-0000-4000-8000-000000000000")
    [record] = traced.log_lines()
    assert record["route"] == "/api/v1/patients/{patient_id}"
    assert "00000000-0000-4000-8000-000000000000" not in traced.logs.getvalue()


def test_successful_requests_write_no_log_lines(traced: Traced) -> None:
    traced.client.get("/healthz")
    assert traced.log_lines() == []
