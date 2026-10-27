"""An app wired to in-memory exporters, so tests can read every span, metric and log record."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy.exc import OperationalError

from app.clock import FixedClock
from app.config import Settings
from app.main import create_app
from app.telemetry import Exporters, setup_telemetry


@dataclass
class Signals:
    client: TestClient
    spans: InMemorySpanExporter
    metrics: InMemoryMetricReader
    logs: InMemoryLogRecordExporter
    log_lines: io.StringIO

    def finished_spans(self) -> tuple[ReadableSpan, ...]:
        return self.spans.get_finished_spans()

    def metric_points(self, name: str) -> list[tuple[dict[str, Any], Any]]:
        """(attributes, value) of every data point of the named metric."""
        data = self.metrics.get_metrics_data()
        points: list[tuple[dict[str, Any], Any]] = []
        for resource_metrics in data.resource_metrics if data else ():
            for scope_metrics in resource_metrics.scope_metrics:
                for metric in scope_metrics.metrics:
                    if metric.name == name:
                        for point in metric.data.data_points:
                            points.append(
                                (dict(point.attributes or {}), getattr(point, "value", None))
                            )
        return points

    def all_metric_attributes(self) -> list[dict[str, Any]]:
        data = self.metrics.get_metrics_data()
        return [
            dict(point.attributes or {})
            for resource_metrics in (data.resource_metrics if data else ())
            for scope_metrics in resource_metrics.scope_metrics
            for metric in scope_metrics.metrics
            for point in metric.data.data_points
        ]

    def json_lines(self) -> list[dict[str, Any]]:
        return [json.loads(line) for line in self.log_lines.getvalue().splitlines() if line]


def signals_app(database_url: str, clock: FixedClock, **overrides: Any) -> Iterator[Signals]:
    """`overrides` are Settings fields, e.g. fault_dose_log_error_rate=1."""
    settings = Settings(
        database_url=database_url, environment="test", version="test-sha", **overrides
    )
    spans, metrics, logs, lines = (
        InMemorySpanExporter(),
        InMemoryMetricReader(),
        InMemoryLogRecordExporter(),
        io.StringIO(),
    )
    telemetry = setup_telemetry(
        settings, log_stream=lines, exporters=Exporters(spans, metrics, logs, batch=False)
    )
    app = create_app(settings, clock, telemetry)

    @app.get("/_test/db-down")
    def db_down() -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    with TestClient(app, raise_server_exceptions=True) as client:
        yield Signals(client, spans, metrics, logs, lines)
