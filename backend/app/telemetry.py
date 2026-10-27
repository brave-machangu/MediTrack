"""Telemetry (operations.md §2): traces, metrics and logs that share the request's trace ID.

Tracing always runs in this process, so every response gets an X-Trace-Id even when nothing is
exported (AC-37). Signals leave the process only when OTEL_EXPORTER_OTLP_ENDPOINT is set. The
providers belong to the app, not to OpenTelemetry's global state, so each app (and each test)
gets its own.

Privacy (security.md §2): span attributes, metric attributes and log fields are allowlists.
Whatever an instrumentation library adds beyond them (raw paths and URLs, user agents, peer
addresses, headers, database error messages) is dropped before export.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TextIO

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.instrumentation.sqlalchemy.engine import EngineTracer
from opentelemetry.metrics import CallbackOptions, Counter, Observation
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    LogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.semconv.metrics import MetricInstruments
from opentelemetry.trace import Span, Status, StatusCode, Tracer
from opentelemetry.util.types import Attributes, AttributeValue
from sqlalchemy import Engine
from starlette.datastructures import MutableHeaders
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings

SERVICE_NAME = "meditrack-backend"
LOGGER_NAME = "meditrack"
TRACE_ID_HEADER = "X-Trace-Id"
# A log line carries these fields and nothing else, so names, notes, free text and IDs can't
# reach it (docs/security.md §2).
LOG_FIELDS = (
    "route",
    "method",
    "status_code",
    "error_code",
    "error_type",
    "outcome",
    "late",
    "operation",
)
# The span attributes that are exported. Server spans keep the route template but not the raw
# path, URL, user agent or peer address; database spans keep the statement, whose values are
# placeholders, but not the database user or host. Both the default and the stable HTTP and
# database semantic-convention names are listed.
SPAN_ATTRIBUTES = frozenset(
    {
        "http.method",
        "http.request.method",
        "http.route",
        "http.status_code",
        "http.response.status_code",
        "http.scheme",
        "url.scheme",
        "http.flavor",
        "network.protocol.version",
        "error.type",
        "db.system",
        "db.system.name",
        "db.name",
        "db.namespace",
        "db.operation",
        "db.operation.name",
        "db.statement",
        "db.query.text",
        "meditrack.outcome",
        "meditrack.late",
        "meditrack.error_code",
        "exception.type",
    }
)
# HTTP server metrics: route template, method and status code (operations.md §2.2). Under the
# default semantic conventions the route template is in `http.target`; the asgi instrumentation
# sets it only when a route matched, and never to the raw path.
HTTP_METRIC_ATTRIBUTES = frozenset(
    {
        "http.method",
        "http.request.method",
        "http.status_code",
        "http.response.status_code",
        "http.target",
        "http.route",
    }
)
_FAILURE_KEY = "meditrack.failure"  # in scope["state"]: (error_code, error_type)
_LOG_RECORD_KEYS = frozenset(vars(logging.makeLogRecord({})))

request_logger = logging.getLogger(f"{LOGGER_NAME}.requests")
dose_log_logger = logging.getLogger(f"{LOGGER_NAME}.dose_logs")

InternalErrorResponse = Callable[[Scope, Exception], Response]


class DoseLogOutcome(StrEnum):
    """`meditrack.outcome` (operations.md §2.1). Only `error` counts against the SLO."""

    CREATED = "created"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    ERROR = "error"


DoseLogFailure = Callable[[Exception], tuple[DoseLogOutcome, str]]


def current_trace_id() -> str | None:
    context = trace.get_current_span().get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else None


def current_span_id() -> str | None:
    context = trace.get_current_span().get_span_context()
    return format(context.span_id, "016x") if context.is_valid else None


def record_failure(scope: Scope, error_code: str, error_type: str | None = None) -> None:
    """Remember why the request failed, for its `request.failed` log line."""
    scope.setdefault("state", {})[_FAILURE_KEY] = (error_code, error_type)


def otlp_url(endpoint: str, signal: str) -> str:
    """The signal's URL under OTEL_EXPORTER_OTLP_ENDPOINT, built as the OTLP exporters do."""
    return f"{endpoint.removesuffix('/')}/v1/{signal}"


class TraceContextFilter(logging.Filter):
    """Stamps the current trace and span IDs on a record when it's logged."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = current_trace_id()
        record.span_id = current_span_id()
        return True


class AllowedFieldsFilter(logging.Filter):
    """Hands the OTLP handler a copy of the record with only LOG_FIELDS added to it, and no
    exception (whose message can quote request data). JsonFormatter does the same for stdout."""

    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        fields = {
            key: value
            for key, value in vars(record).items()
            if key in _LOG_RECORD_KEYS or key in LOG_FIELDS
        }
        clean = logging.makeLogRecord(fields)
        clean.exc_info = clean.exc_text = clean.stack_info = None
        return clean


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with only the fields in LOG_FIELDS (operations.md §2.3)."""

    def format(self, record: logging.LogRecord) -> str:
        created = datetime.fromtimestamp(record.created, UTC)
        entry: dict[str, object] = {
            "time": created.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
            "span_id": getattr(record, "span_id", None),
        }
        for field in LOG_FIELDS:
            if hasattr(record, field):
                entry[field] = getattr(record, field)
        return json.dumps(entry)


def _allowed(attributes: Attributes) -> dict[str, AttributeValue]:
    return {key: value for key, value in (attributes or {}).items() if key in SPAN_ATTRIBUTES}


def scrub(span: ReadableSpan) -> ReadableSpan:
    """The span with only SPAN_ATTRIBUTES, and no status description: the SQLAlchemy
    instrumentation puts the database's error message there, which can quote key values."""
    return ReadableSpan(
        name=span.name,
        context=span.context,
        parent=span.parent,
        resource=span.resource,
        attributes=_allowed(span.attributes),
        events=[
            Event(event.name, _allowed(event.attributes), event.timestamp) for event in span.events
        ],
        links=span.links,
        kind=span.kind,
        status=Status(span.status.status_code),
        start_time=span.start_time,
        end_time=span.end_time,
        instrumentation_scope=span.instrumentation_scope,
    )


class ScrubbingSpanExporter(SpanExporter):
    """Exports through `exporter` after `scrub`. Every exporter the app uses is wrapped in one."""

    def __init__(self, exporter: SpanExporter) -> None:
        self.exporter = exporter

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return self.exporter.export([scrub(span) for span in spans])

    def shutdown(self) -> None:
        self.exporter.shutdown()


@dataclass(frozen=True, slots=True)
class Exporters:
    """Where the signals go: OTLP in a deployment, memory in tests."""

    spans: SpanExporter
    metrics: MetricReader
    logs: LogRecordExporter
    # Batching suits a network exporter; tests export each signal as it ends, to read it at once.
    batch: bool = True


def otlp_exporters(endpoint: str) -> Exporters:
    # Headers (e.g. an auth token) come from OTEL_EXPORTER_OTLP_HEADERS, read by the exporters.
    return Exporters(
        spans=OTLPSpanExporter(endpoint=otlp_url(endpoint, "traces")),
        metrics=PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=otlp_url(endpoint, "metrics"))
        ),
        logs=OTLPLogExporter(endpoint=otlp_url(endpoint, "logs")),
    )


@dataclass(slots=True)
class DoseLogAttempt:
    late: bool | None = None  # set by the route once the dose log exists


@dataclass(frozen=True, slots=True)
class Telemetry:
    tracer_provider: TracerProvider
    meter_provider: MeterProvider
    logger_provider: LoggerProvider
    log_handlers: tuple[logging.Handler, ...]
    exporting: bool
    tracer: Tracer
    dose_log_attempts: Counter
    db_errors: Counter

    def start(self) -> None:
        logger = logging.getLogger(LOGGER_NAME)
        logger.setLevel(logging.INFO)
        for handler in self.log_handlers:
            logger.addHandler(handler)

    def stop(self) -> None:
        logger = logging.getLogger(LOGGER_NAME)
        for handler in self.log_handlers:
            logger.removeHandler(handler)
        self.logger_provider.shutdown()
        self.tracer_provider.shutdown()
        self.meter_provider.shutdown()

    def trace_engine(self, engine: Engine) -> None:
        """Database spans and connection-pool metrics for `engine`.

        EngineTracer is what SQLAlchemyInstrumentor attaches to an engine. Using it directly
        avoids the instrumentor, which is a process-wide singleton and also patches
        sqlalchemy.create_engine. EngineTracer never records bound parameters, and the SQL
        commenter stays off.
        """
        meter = self.meter_provider.get_meter(__name__)
        connections_usage = meter.create_up_down_counter(
            name=MetricInstruments.DB_CLIENT_CONNECTIONS_USAGE,
            unit="connections",
            description="Connections in the state given by the state attribute.",
        )
        # The instrumentation has no type hints; strict mypy flags this ignore once it does.
        EngineTracer(  # type: ignore[no-untyped-call]
            self.tracer, engine, connections_usage, enable_commenter=False
        )

    def count_db_error(self, *, write: bool) -> None:
        self.db_errors.add(1, {"operation": "write" if write else "read"})

    @contextmanager
    def dose_log_attempt(self, failure: DoseLogFailure) -> Iterator[DoseLogAttempt]:
        """The `dose_log.create` span, attempts counter and `dose_log.<outcome>` log event.

        `failure` maps an exception to its outcome and contract code. The exception is always
        re-raised for the error handlers; this only records it.
        """
        with self.tracer.start_as_current_span(
            "dose_log.create", record_exception=False, set_status_on_exception=False
        ) as span:
            attempt = DoseLogAttempt()
            try:
                yield attempt
            except Exception as error:  # recorded, then re-raised
                outcome, error_code = failure(error)
                self._record_dose_log(span, outcome, error_code=error_code)
                raise
            self._record_dose_log(span, DoseLogOutcome.CREATED, late=attempt.late)

    def _record_dose_log(
        self,
        span: Span,
        outcome: DoseLogOutcome,
        *,
        late: bool | None = None,
        error_code: str | None = None,
    ) -> None:
        fields: dict[str, object] = {"outcome": outcome.value}
        span.set_attribute("meditrack.outcome", outcome.value)
        if late is not None:
            fields["late"] = late
            span.set_attribute("meditrack.late", late)
        if error_code is not None:
            fields["error_code"] = error_code
            span.set_attribute("meditrack.error_code", error_code)
        if outcome is DoseLogOutcome.ERROR:
            span.set_status(Status(StatusCode.ERROR))
        self.dose_log_attempts.add(1, {"outcome": outcome.value})
        level = logging.ERROR if outcome is DoseLogOutcome.ERROR else logging.INFO
        dose_log_logger.log(level, f"dose_log.{outcome.value}", extra=fields)


def setup_telemetry(
    settings: Settings, *, log_stream: TextIO | None = None, exporters: Exporters | None = None
) -> Telemetry:
    """Log lines go to `log_stream` (stdout by default), where the log collector reads them.
    Spans, metrics and log records go to `exporters`, or OTLP when an endpoint is set."""
    if exporters is None and settings.otlp_endpoint:
        exporters = otlp_exporters(settings.otlp_endpoint)
    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
            "service.version": settings.version,
            "deployment.environment": settings.environment,
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[exporters.metrics] if exporters else [],
        views=[View(instrument_name="http.server.*", attribute_keys=set(HTTP_METRIC_ATTRIBUTES))],
    )
    logger_provider = LoggerProvider(resource=resource)

    json_handler = logging.StreamHandler(log_stream or sys.stdout)
    json_handler.setFormatter(JsonFormatter())
    json_handler.addFilter(TraceContextFilter())
    handlers: list[logging.Handler] = [json_handler]
    if exporters is not None:
        span_exporter = ScrubbingSpanExporter(exporters.spans)
        if exporters.batch:
            tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporters.logs))
        else:
            tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
            logger_provider.add_log_record_processor(SimpleLogRecordProcessor(exporters.logs))
        otlp_handler = LoggingHandler(logger_provider=logger_provider)
        otlp_handler.addFilter(AllowedFieldsFilter())
        handlers.append(otlp_handler)

    meter = meter_provider.get_meter(__name__)
    build = {"version": settings.version, "environment": settings.environment}

    def observe_build(_: CallbackOptions) -> Iterable[Observation]:
        return [Observation(1, build)]

    meter.create_observable_gauge(
        "meditrack.build.info",
        callbacks=[observe_build],
        description="1 for the running release; shows which version is live.",
    )
    return Telemetry(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        logger_provider=logger_provider,
        log_handlers=tuple(handlers),
        exporting=exporters is not None,
        tracer=tracer_provider.get_tracer(__name__),
        dose_log_attempts=meter.create_counter(
            "meditrack.dose_log.attempts",
            description="Dose recording attempts by outcome; the SLI for the alert.",
        ),
        db_errors=meter.create_counter(
            "meditrack.db.errors", description="Database errors that failed a request."
        ),
    )


def instrument(app: FastAPI, telemetry: Telemetry, internal_error: InternalErrorResponse) -> None:
    """Call after the routes and error handlers are in place, before the app starts."""
    app.add_middleware(TelemetryMiddleware, internal_error=internal_error)
    # Wraps the whole middleware stack, so a span is open while any response is built. The
    # per-message "send"/"receive" spans add nothing here.
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=telemetry.tracer_provider,
        meter_provider=telemetry.meter_provider,
        exclude_spans=["send", "receive"],
    )


class TelemetryMiddleware:
    """Adds X-Trace-Id to every response, logs one `request.failed` line per error response, and
    is the single top-level handler for unexpected exceptions (DESIGN.md §4).

    Answering the 500 here keeps the exception from reaching Starlette's ServerErrorMiddleware,
    which would re-raise it for the server to log with its message, and messages from Pydantic or
    SQLAlchemy can contain request data.
    """

    def __init__(self, app: ASGIApp, internal_error: InternalErrorResponse) -> None:
        self.app = app
        self.internal_error = internal_error

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        response_started = False

        async def send_with_trace_id(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                trace_id = current_trace_id()
                if trace_id is not None:
                    MutableHeaders(scope=message).append(TRACE_ID_HEADER, trace_id)
                if message["status"] >= 400:
                    _log_failure(scope, message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace_id)
        except Exception as error:  # the one broad handler: anything unexpected becomes a 500
            if response_started:
                raise
            span = trace.get_current_span()
            span.set_status(Status(StatusCode.ERROR))
            span.set_attribute("error.type", type(error).__name__)
            await self.internal_error(scope, error)(scope, receive, send_with_trace_id)


def _log_failure(scope: Scope, status: int) -> None:
    error_code, error_type = scope.get("state", {}).get(_FAILURE_KEY, (None, None))
    route = scope.get("route")
    fields: dict[str, object] = {"method": scope["method"], "status_code": status}
    # The route template, never the path, which can contain IDs (security.md §2).
    if route is not None:
        fields["route"] = route.path
    if error_code is not None:
        fields["error_code"] = error_code
    if error_type is not None:
        fields["error_type"] = error_type
    level = logging.ERROR if status >= 500 else logging.INFO
    request_logger.log(level, "request.failed", extra=fields)
