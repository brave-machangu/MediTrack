"""RFC 9457 problem+json errors with the `code` values from api/openapi.yaml (AC-31).

Every error the API returns goes through this module, including FastAPI's own
request-validation errors, unknown routes, database outages and unhandled exceptions.
Problem bodies never contain request data, SQL or stack traces.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("meditrack.errors")

PROBLEM_MEDIA_TYPE = "application/problem+json"


class ErrorCode(StrEnum):
    """Mirror of `Problem.code` in api/openapi.yaml. Keep the two in sync."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    DUPLICATE_DOSE_LOG = "DUPLICATE_DOSE_LOG"
    DOSE_NOT_PLANNED = "DOSE_NOT_PLANNED"
    OUTSIDE_LOG_WINDOW = "OUTSIDE_LOG_WINDOW"
    SCHEDULE_HAS_LOGS = "SCHEDULE_HAS_LOGS"
    MEDICATION_INACTIVE = "MEDICATION_INACTIVE"
    PATIENT_HAS_LOGS = "PATIENT_HAS_LOGS"
    SCHEDULE_OVERLAP = "SCHEDULE_OVERLAP"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ProblemError(Exception):
    """Raise from services or routers to return a problem+json response."""

    def __init__(
        self,
        status: int,
        code: ErrorCode,
        title: str,
        detail: str | None = None,
        errors: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(title)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.errors = errors


def problem_response(
    status: int,
    code: ErrorCode,
    title: str,
    detail: str | None = None,
    errors: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {"type": "about:blank", "title": title, "status": status, "code": code}
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = errors
    # trace_id is added by the telemetry middleware in MT-022.
    return JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE, headers=headers)


def _field_path(location: tuple[Any, ...]) -> str:
    """('body', 'times_of_day', 0) -> 'times_of_day[0]'; the 'body'/'query' prefix is dropped."""
    prefixes = {"body", "query", "path"}
    parts = list(location[1:] if location and location[0] in prefixes else location)
    path = ""
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else (f".{part}" if path else str(part))
    return path or "request"


async def _handle_problem(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ProblemError)
    return problem_response(exc.status, exc.code, exc.title, exc.detail, exc.errors)


async def _handle_validation(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Only the location and pydantic's message: never echo the submitted value.
    errors = [
        {"field": _field_path(tuple(err.get("loc", ()))), "message": str(err.get("msg", "Invalid"))}
        for err in exc.errors()
    ]
    return problem_response(422, ErrorCode.VALIDATION_ERROR, "Request is invalid", errors=errors)


async def _handle_http(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    if exc.status_code == 404:
        return problem_response(404, ErrorCode.NOT_FOUND, "Not found")
    if exc.status_code >= 500:
        return problem_response(exc.status_code, ErrorCode.INTERNAL_ERROR, "Internal error")
    # Other client errors (e.g. 405) have no dedicated contract code.
    return problem_response(exc.status_code, ErrorCode.VALIDATION_ERROR, "Request is invalid")


async def _handle_database_unavailable(_: Request, exc: Exception) -> JSONResponse:
    logger.error("database unavailable", extra={"error_type": type(exc).__name__})
    return problem_response(
        503,
        ErrorCode.SERVICE_UNAVAILABLE,
        "Service temporarily unavailable",
        headers={"Retry-After": "5"},
    )


async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled error", extra={"error_type": type(exc).__name__})
    return problem_response(500, ErrorCode.INTERNAL_ERROR, "Internal error")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ProblemError, _handle_problem)
    app.add_exception_handler(RequestValidationError, _handle_validation)
    app.add_exception_handler(StarletteHTTPException, _handle_http)
    app.add_exception_handler(OperationalError, _handle_database_unavailable)
    app.add_exception_handler(PoolTimeoutError, _handle_database_unavailable)
    app.add_exception_handler(Exception, _handle_unexpected)
