"""AC-29: after every endpoint has seen known synthetic values, none of them appears in a span
(name, attribute, event or status), a metric label, an OTLP log record or a log line. Neither do
the IDs of the records involved (docs/security.md §1–2)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine

from app.clock import FixedClock
from tests.integration.signals import Signals, signals_app

CANARIES = (
    "PRIVACY-CANARY-PATIENT",
    "PRIVACY-CANARY-MED",
    "PRIVACY-CANARY-LABEL",
    "PRIVACY-CANARY-INSTRUCTIONS",
    "PRIVACY-CANARY-NOTE",
    "PRIVACY-CANARY-QUERY",
    "PRIVACY-CANARY-PATH",
)


@pytest.fixture
def signals(engine: Engine, database_url: str, clock: FixedClock) -> Iterator[Signals]:
    yield from signals_app(database_url, clock)


def exercise_every_endpoint(signals: Signals, clock: FixedClock) -> list[str]:
    """Call every operation with canary values (and some failing calls); return the IDs used."""
    client = signals.client
    client.get("/healthz")
    client.get("/readyz")
    patient = client.post(
        "/api/v1/patients", json={"display_name": CANARIES[0], "timezone": "Africa/Harare"}
    ).json()
    p = f"/api/v1/patients/{patient['id']}"
    client.get("/api/v1/patients")
    client.get(p)
    client.patch(p, json={"display_name": CANARIES[0] + "-2"})
    medication = client.post(
        f"{p}/medications",
        json={"name": CANARIES[1], "dosage_label": CANARIES[2], "instructions": CANARIES[3]},
    ).json()
    m = f"/api/v1/medications/{medication['id']}"
    client.get(f"{p}/medications?include_inactive=true")
    client.get(m)
    client.patch(m, json={"instructions": CANARIES[3] + "-2"})
    schedule = client.post(
        f"{m}/schedules", json={"times_of_day": ["08:00"], "start_date": "2026-11-01"}
    ).json()
    client.get(f"{m}/schedules")
    client.patch(f"/api/v1/schedules/{schedule['id']}", json={"grace_period_minutes": 30})
    client.post(f"{m}/schedules", json={"times_of_day": ["09:00"], "start_date": "2026-11-05"})
    clock.set(datetime(2026, 11, 2, 6, 30, tzinfo=UTC))
    dose = {
        "schedule_id": schedule["id"],
        "scheduled_for": "2026-11-02T06:00:00Z",
        "status": "taken",
        "note": CANARIES[4],
    }
    log = client.post("/api/v1/dose-logs", json=dose).json()
    client.post("/api/v1/dose-logs", json=dose)  # duplicate
    client.post("/api/v1/dose-logs", json={**dose, "note": CANARIES[4] + "x" * 300})  # 422
    client.get(f"{p}/doses")
    client.get(f"{p}/missed-doses?from=2026-10-30&to=2026-11-02")
    client.get(f"{p}/adherence/daily?date=2026-11-02")
    client.delete(f"/api/v1/dose-logs/{log['id']}")
    client.post("/api/v1/dose-logs", json=dose)
    client.get(f"/api/v1/patients/{CANARIES[6]}?q={CANARIES[5]}")  # malformed ID in the path
    client.get(f"/{CANARIES[6]}?q={CANARIES[5]}")  # unknown route
    client.patch(p, json={"display_name": "", "timezone": CANARIES[0]})  # 422 with canary input
    client.get("/_test/db-down")
    return [patient["id"], medication["id"], schedule["id"], log["id"]]


def test_no_canary_in_logs_spans_or_metrics_ac29(signals: Signals, clock: FixedClock) -> None:
    ids = exercise_every_endpoint(signals, clock)

    spans = signals.finished_spans()
    span_text = [
        repr(
            (
                span.name,
                dict(span.attributes or {}),
                [(event.name, dict(event.attributes or {})) for event in span.events],
                span.status.description,
            )
        )
        for span in spans
    ]
    metric_text = [repr(attributes) for attributes in signals.all_metric_attributes()]
    log_records = signals.logs.get_finished_logs()
    log_text = [
        repr((record.log_record.body, dict(record.log_record.attributes or {})))
        for record in log_records
    ]
    line_text = signals.log_lines.getvalue()

    assert spans and metric_text and log_records and line_text  # every signal was captured
    for haystack in (*span_text, *metric_text, *log_text, line_text):
        for needle in (*CANARIES, *ids):
            assert needle not in haystack
