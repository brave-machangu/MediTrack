"""Log lines are JSON with a fixed set of fields (operations.md §2.3, security.md §2)."""

from __future__ import annotations

import io
import json
import logging

from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.config import Settings
from app.telemetry import Exporters, JsonFormatter, setup_telemetry


def format_record(**extra: object) -> dict[str, object]:
    record = logging.LogRecord(
        "meditrack", logging.INFO, __file__, 1, "dose_log.created", None, None
    )
    for name, value in extra.items():
        setattr(record, name, value)
    parsed: dict[str, object] = json.loads(JsonFormatter().format(record))
    return parsed


def test_log_line_keeps_only_allowed_fields() -> None:
    line = format_record(
        outcome="created",
        late=False,
        display_name="Demo Patient A",
        note="PRIVACY-CANARY-NOTE",
        patient_id="00000000-0000-4000-8000-000000000000",
    )
    assert set(line) == {"time", "level", "event", "trace_id", "span_id", "outcome", "late"}
    assert (line["event"], line["level"], line["outcome"], line["late"]) == (
        "dose_log.created",
        "info",
        "created",
        False,
    )


def test_log_line_outside_a_request_has_null_trace_ids() -> None:
    line = format_record()
    assert (line["trace_id"], line["span_id"]) == (None, None)


def test_otlp_log_records_keep_only_allowed_fields_and_no_exception() -> None:
    exported = InMemoryLogRecordExporter()
    telemetry = setup_telemetry(
        Settings(database_url="sqlite://"),
        log_stream=io.StringIO(),
        exporters=Exporters(InMemorySpanExporter(), InMemoryMetricReader(), exported, batch=False),
    )
    telemetry.start()
    try:
        error = ValueError("PRIVACY-CANARY-NOTE")
        logging.getLogger("meditrack.test").info(
            "dose_log.created",
            exc_info=(ValueError, error, None),
            extra={"outcome": "created", "note": "PRIVACY-CANARY-NOTE"},
        )
    finally:
        telemetry.stop()

    [record] = exported.get_finished_logs()
    assert record.log_record.body == "dose_log.created"
    assert dict(record.log_record.attributes or {}) == {"outcome": "created"}
