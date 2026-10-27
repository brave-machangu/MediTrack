"""The signals in operations.md §2: the dose-log span, counter and log events, database error
counter, build info, HTTP metrics by route template, and database spans without parameters."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import NoReturn

import pytest
from opentelemetry.trace import StatusCode
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from app.clock import FixedClock
from app.config import Settings
from app.services import doses as dose_service
from app.telemetry import otlp_url, setup_telemetry
from tests.integration.signals import Signals, signals_app


@pytest.fixture
def signals(engine: Engine, database_url: str, clock: FixedClock) -> Iterator[Signals]:
    yield from signals_app(database_url, clock)


def schedule_for_today(signals: Signals, clock: FixedClock) -> dict[str, str]:
    client = signals.client
    patient = client.post(
        "/api/v1/patients", json={"display_name": "Demo Patient A", "timezone": "Africa/Harare"}
    ).json()
    medication = client.post(
        f"/api/v1/patients/{patient['id']}/medications",
        json={"name": "Demo Med Alpha", "dosage_label": "1 tablet"},
    ).json()
    schedule = client.post(
        f"/api/v1/medications/{medication['id']}/schedules",
        json={"times_of_day": ["08:00"], "start_date": "2026-11-01"},
    ).json()
    clock.set(datetime(2026, 11, 2, 7, 30, tzinfo=UTC))  # 09:30 in Harare: past the grace
    return {
        "schedule_id": schedule["id"],
        "scheduled_for": "2026-11-02T06:00:00Z",
        "status": "taken",
    }


def test_dose_log_attempts_are_counted_by_outcome_only(signals: Signals, clock: FixedClock) -> None:
    dose = schedule_for_today(signals, clock)
    signals.client.post("/api/v1/dose-logs", json=dose)  # created (late)
    signals.client.post("/api/v1/dose-logs", json=dose)  # duplicate
    signals.client.post("/api/v1/dose-logs", json={**dose, "scheduled_for": "2026-11-02T06:30:00Z"})

    points = signals.metric_points("meditrack.dose_log.attempts")

    assert sorted((attributes["outcome"], value) for attributes, value in points) == [
        ("created", 1),
        ("duplicate", 1),
        ("rejected", 1),
    ]
    assert all(set(attributes) == {"outcome"} for attributes, _ in points)


def test_dose_log_span_records_outcome_late_and_error_code(
    signals: Signals, clock: FixedClock
) -> None:
    dose = schedule_for_today(signals, clock)
    signals.client.post("/api/v1/dose-logs", json=dose)
    signals.client.post("/api/v1/dose-logs", json=dose)

    spans = [span for span in signals.finished_spans() if span.name == "dose_log.create"]

    assert [dict(span.attributes or {}) for span in spans] == [
        {"meditrack.outcome": "created", "meditrack.late": True},
        {"meditrack.outcome": "duplicate", "meditrack.error_code": "DUPLICATE_DOSE_LOG"},
    ]


def test_dose_log_events_carry_the_request_trace_id(signals: Signals, clock: FixedClock) -> None:
    dose = schedule_for_today(signals, clock)
    created = signals.client.post("/api/v1/dose-logs", json=dose)
    duplicate = signals.client.post("/api/v1/dose-logs", json=dose)

    events = {
        line["event"]: line
        for line in signals.json_lines()
        if line["event"].startswith("dose_log.")
    }

    assert events["dose_log.created"]["trace_id"] == created.headers["x-trace-id"]
    assert (events["dose_log.created"]["outcome"], events["dose_log.created"]["late"]) == (
        "created",
        True,
    )
    assert events["dose_log.duplicate"]["trace_id"] == duplicate.headers["x-trace-id"]
    assert events["dose_log.duplicate"]["error_code"] == "DUPLICATE_DOSE_LOG"


@pytest.mark.parametrize(
    ("error", "status", "code", "db_errors"),
    [
        (
            lambda: OperationalError("INSERT", {}, Exception("connection refused")),
            503,
            "SERVICE_UNAVAILABLE",
            [({"operation": "write"}, 1)],
        ),
        (lambda: RuntimeError("unexpected"), 500, "INTERNAL_ERROR", []),
    ],
    ids=["database-down", "unexpected"],
)
def test_a_dose_log_that_fails_with_5xx_counts_as_an_error(
    signals: Signals,
    clock: FixedClock,
    monkeypatch: pytest.MonkeyPatch,
    error: Callable[[], Exception],
    status: int,
    code: str,
    db_errors: list[object],
) -> None:
    dose = schedule_for_today(signals, clock)

    def fail(*args: object, **kwargs: object) -> NoReturn:
        raise error()

    monkeypatch.setattr(dose_service, "create_dose_log", fail)

    response = signals.client.post("/api/v1/dose-logs", json=dose)

    assert (response.status_code, response.json()["code"]) == (status, code)
    assert signals.metric_points("meditrack.dose_log.attempts") == [({"outcome": "error"}, 1)]
    assert signals.metric_points("meditrack.db.errors") == db_errors
    [span] = [span for span in signals.finished_spans() if span.name == "dose_log.create"]
    assert dict(span.attributes or {}) == {
        "meditrack.outcome": "error",
        "meditrack.error_code": code,
    }
    assert span.status.status_code is StatusCode.ERROR
    [event] = [line for line in signals.json_lines() if line["event"] == "dose_log.error"]
    assert (event["level"], event["error_code"]) == ("error", code)


def test_database_errors_are_counted_by_operation(signals: Signals) -> None:
    response = signals.client.get("/_test/db-down")
    assert response.status_code == 503
    assert signals.metric_points("meditrack.db.errors") == [({"operation": "read"}, 1)]


def test_build_info_reports_version_and_environment(signals: Signals) -> None:
    signals.client.get("/healthz")
    assert signals.metric_points("meditrack.build.info") == [
        ({"version": "test-sha", "environment": "test"}, 1)
    ]


def test_http_metrics_carry_only_route_template_method_and_status(signals: Signals) -> None:
    signals.client.get("/api/v1/patients/00000000-0000-4000-8000-000000000000")
    signals.client.get("/no-such-route")

    durations = [attributes for attributes, _ in signals.metric_points("http.server.duration")]

    # Under the default semantic conventions the route template is in http.target.
    assert sorted(durations, key=len, reverse=True) == [
        {
            "http.method": "GET",
            "http.status_code": 404,
            "http.target": "/api/v1/patients/{patient_id}",
        },
        {"http.method": "GET", "http.status_code": 404},  # no route matched, so no target
    ]


def test_server_spans_keep_the_route_and_drop_the_raw_url(signals: Signals) -> None:
    signals.client.get(
        "/api/v1/patients/00000000-0000-4000-8000-000000000000?q=1", headers={"user-agent": "UA"}
    )
    [server] = [span for span in signals.finished_spans() if span.kind.name == "SERVER"]
    assert server.name == "GET /api/v1/patients/{patient_id}"
    assert dict(server.attributes or {}) == {
        "http.scheme": "http",
        "http.flavor": "1.1",
        "http.method": "GET",
        "http.route": "/api/v1/patients/{patient_id}",
        "http.status_code": 404,
    }


def test_database_calls_are_traced_without_parameters(signals: Signals) -> None:
    signals.client.post(
        "/api/v1/patients", json={"display_name": "Demo Patient A", "timezone": "Africa/Harare"}
    )
    statements = [
        str((span.attributes or {}).get("db.statement", ""))
        for span in signals.finished_spans()
        if span.kind.name == "CLIENT"
    ]
    inserts = [
        statement for statement in statements if statement.startswith("INSERT INTO patients")
    ]
    assert inserts
    assert all("Demo Patient A" not in statement for statement in statements)


def test_export_is_off_without_an_endpoint() -> None:
    telemetry = setup_telemetry(Settings(database_url="sqlite://"))
    assert telemetry.exporting is False


@pytest.mark.parametrize("base", ["http://collector:4318", "http://collector:4318/"])
def test_otlp_signal_urls_follow_the_spec(base: str) -> None:
    # OTEL_EXPORTER_OTLP_ENDPOINT is a base URL; each signal adds its own path.
    assert otlp_url(base, "traces") == "http://collector:4318/v1/traces"
    assert otlp_url(base, "logs") == "http://collector:4318/v1/logs"
