"""Telemetry (operations.md §2): a trace ID on every response, and log lines that carry it.

Tracing always runs in this process, so every response gets an X-Trace-Id even when nothing is
exported (AC-37). The providers belong to the app, not to OpenTelemetry's global state, so each
app (and each test) gets its own.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TextIO

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Status, StatusCode
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
_FAILURE_KEY = "meditrack.failure"  # in scope["state"]: (error_code, error_type)

request_logger = logging.getLogger(f"{LOGGER_NAME}.requests")

InternalErrorResponse = Callable[[Scope, Exception], Response]


def current_trace_id() -> str | None:
    context = trace.get_current_span().get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else None


def current_span_id() -> str | None:
    context = trace.get_current_span().get_span_context()
    return format(context.span_id, "016x") if context.is_valid else None


def record_failure(scope: Scope, error_code: str, error_type: str | None = None) -> None:
    """Remember why the request failed, for its `request.failed` log line."""
    scope.setdefault("state", {})[_FAILURE_KEY] = (error_code, error_type)


class TraceContextFilter(logging.Filter):
    """Stamps the current trace and span IDs on a record when it's logged."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = current_trace_id()
        record.span_id = current_span_id()
        return True


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


@dataclass(frozen=True, slots=True)
class Telemetry:
    tracer_provider: TracerProvider
    log_handler: logging.Handler

    def start(self) -> None:
        logger = logging.getLogger(LOGGER_NAME)
        logger.setLevel(logging.INFO)
        logger.addHandler(self.log_handler)

    def stop(self) -> None:
        logging.getLogger(LOGGER_NAME).removeHandler(self.log_handler)
        self.tracer_provider.shutdown()


def setup_telemetry(settings: Settings, *, log_stream: TextIO | None = None) -> Telemetry:
    """Log lines go to `log_stream` (stdout by default), where the log collector reads them."""
    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
            "service.version": settings.version,
            "deployment.environment": settings.environment,
        }
    )
    handler = logging.StreamHandler(log_stream or sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(TraceContextFilter())
    return Telemetry(tracer_provider=TracerProvider(resource=resource), log_handler=handler)


def instrument(app: FastAPI, telemetry: Telemetry, internal_error: InternalErrorResponse) -> None:
    """Call after the routes and error handlers are in place, before the app starts."""
    app.add_middleware(TelemetryMiddleware, internal_error=internal_error)
    # Wraps the whole middleware stack, so a span is open while any response is built.
    FastAPIInstrumentor.instrument_app(app, tracer_provider=telemetry.tracer_provider)


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
