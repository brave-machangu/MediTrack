"""RFC 9457 problem+json errors with the `code` values from api/openapi.yaml (AC-31).

Every error the API returns goes through this module: domain errors, FastAPI's own request
validation errors, unknown routes and methods, database outages and unhandled exceptions.
Problem bodies never contain request data, SQL or stack traces.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import NamedTuple, NotRequired, TypedDict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match, Route
from starlette.types import Scope

from app.domain.errors import (
    DomainError,
    DoseNotPlanned,
    DuplicateDoseLog,
    InvalidField,
    MedicationInactive,
    NotFound,
    OutsideLogWindow,
    PatientHasLogs,
    ScheduleHasLogs,
    ScheduleOverlap,
)
from app.telemetry import DoseLogOutcome, Telemetry, current_trace_id, record_failure

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
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class FieldError(TypedDict):
    field: str
    message: str


class ProblemBody(TypedDict):
    type: str
    title: str
    status: int
    code: ErrorCode
    detail: NotRequired[str]
    errors: NotRequired[list[FieldError]]
    trace_id: NotRequired[str]


class Problem(NamedTuple):
    status: int
    code: ErrorCode
    title: str
    detail: str | None = None


# The response for every domain error (backend/DESIGN.md §4).
DOMAIN_PROBLEMS: dict[type[DomainError], Problem] = {
    NotFound: Problem(404, ErrorCode.NOT_FOUND, "Not found"),
    PatientHasLogs: Problem(
        409,
        ErrorCode.PATIENT_HAS_LOGS,
        "The timezone can't change after doses have been recorded",
    ),
    MedicationInactive: Problem(409, ErrorCode.MEDICATION_INACTIVE, "Medication is inactive"),
    ScheduleHasLogs: Problem(
        409,
        ErrorCode.SCHEDULE_HAS_LOGS,
        "The schedule has recorded doses; only its end date can change",
    ),
    ScheduleOverlap: Problem(
        409,
        ErrorCode.SCHEDULE_OVERLAP,
        "Schedule overlaps an existing schedule",
        # The text of the contract's example, which the UI shows next to the form (AC-34).
        detail=(
            "This medication already has a schedule on those days. "
            "End the current schedule first; the new one can start the next day."
        ),
    ),
    InvalidField: Problem(422, ErrorCode.VALIDATION_ERROR, "Request is invalid"),
    DoseNotPlanned: Problem(422, ErrorCode.DOSE_NOT_PLANNED, "No dose is planned at that time"),
    OutsideLogWindow: Problem(
        422, ErrorCode.OUTSIDE_LOG_WINDOW, "This dose can't be recorded at this time"
    ),
    DuplicateDoseLog: Problem(409, ErrorCode.DUPLICATE_DOSE_LOG, "Dose already recorded"),
}


def problem_response(
    status: int,
    code: ErrorCode,
    title: str,
    *,
    detail: str | None = None,
    errors: list[FieldError] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body: ProblemBody = {"type": "about:blank", "title": title, "status": status, "code": code}
    if detail is not None:
        body["detail"] = detail
    if errors:
        body["errors"] = errors
    # The same ID as the X-Trace-Id header, which the telemetry middleware adds (AC-37).
    trace_id = current_trace_id()
    if trace_id is not None:
        body["trace_id"] = trace_id
    return JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE, headers=headers)


def _problem(
    scope: Scope,
    status: int,
    code: ErrorCode,
    title: str,
    *,
    detail: str | None = None,
    errors: list[FieldError] | None = None,
    headers: Mapping[str, str] | None = None,
    error_type: str | None = None,
) -> JSONResponse:
    record_failure(scope, code, error_type)
    return problem_response(status, code, title, detail=detail, errors=errors, headers=headers)


def _field_path(location: Sequence[int | str]) -> str:
    """('body', 'times_of_day', 0) -> 'times_of_day[0]'; the 'body'/'query' prefix is dropped."""
    prefixes = {"body", "query", "path"}
    parts = list(location[1:] if location and location[0] in prefixes else location)
    path = ""
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else (f".{part}" if path else str(part))
    return path or "request"


async def _handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    problem = DOMAIN_PROBLEMS[type(exc)]
    errors: list[FieldError] | None = None
    if isinstance(exc, InvalidField):
        errors = [{"field": exc.field, "message": exc.message}]
    return _problem(
        request.scope,
        problem.status,
        problem.code,
        problem.title,
        detail=problem.detail,
        errors=errors,
    )


async def _handle_validation(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = exc.errors()
    # A malformed ID in the path can't name an existing resource (api/openapi.yaml).
    if details and all(tuple(detail["loc"][:1]) == ("path",) for detail in details):
        return _problem(request.scope, 404, ErrorCode.NOT_FOUND, "Not found")
    # Only the location and pydantic's message: never echo the submitted value.
    errors: list[FieldError] = [
        {"field": _field_path(detail["loc"]), "message": str(detail["msg"])} for detail in details
    ]
    return _problem(
        request.scope, 422, ErrorCode.VALIDATION_ERROR, "Request is invalid", errors=errors
    )


def _allowed_methods(request: Request, routes: Sequence[Route]) -> str:
    """Every method the requested path supports (RFC 9110 §15.5.6).

    Starlette's own Allow header names only the first route that matched the path, and here
    each method of a path is a separate route.
    """
    methods: set[str] = set()
    for route in routes:
        match, _ = route.matches(request.scope)
        if match is not Match.NONE and route.methods:
            methods |= route.methods
    return ", ".join(sorted(methods))


def _http_problem(request: Request, exc: Exception, routes: Sequence[Route]) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    if exc.status_code == 404:
        return _problem(request.scope, 404, ErrorCode.NOT_FOUND, "Not found")
    if exc.status_code == 405:
        return _problem(
            request.scope,
            405,
            ErrorCode.METHOD_NOT_ALLOWED,
            "Method not allowed",
            headers={"Allow": _allowed_methods(request, routes)},
        )
    if exc.status_code == 400:
        # FastAPI's answer to a body it can't decode at all. The contract documents 422 for
        # every invalid request, so this is a validation error like any other.
        errors: list[FieldError] = [{"field": "request", "message": "body is not valid JSON"}]
        return _problem(
            request.scope, 422, ErrorCode.VALIDATION_ERROR, "Request is invalid", errors=errors
        )
    if exc.status_code >= 500:
        return _problem(request.scope, exc.status_code, ErrorCode.INTERNAL_ERROR, "Internal error")
    return _problem(
        request.scope, exc.status_code, ErrorCode.VALIDATION_ERROR, "Request is invalid"
    )


def _database_unreachable(exc: Exception) -> bool:
    return isinstance(exc, OperationalError | PoolTimeoutError) or (
        isinstance(exc, DBAPIError) and exc.connection_invalidated
    )


def dose_log_failure(exc: Exception) -> tuple[DoseLogOutcome, ErrorCode]:
    """The outcome and `code` of a failed dose log, as the handlers here will answer it."""
    if isinstance(exc, DomainError):
        code = DOMAIN_PROBLEMS[type(exc)].code
        if code is ErrorCode.DUPLICATE_DOSE_LOG:
            return DoseLogOutcome.DUPLICATE, code
        return DoseLogOutcome.REJECTED, code
    if _database_unreachable(exc):
        return DoseLogOutcome.ERROR, ErrorCode.SERVICE_UNAVAILABLE
    return DoseLogOutcome.ERROR, ErrorCode.INTERNAL_ERROR


def _database_problem(request: Request, exc: Exception, telemetry: Telemetry) -> JSONResponse:
    # A request that changes data counts as a write, even if a read inside it failed.
    telemetry.count_db_error(write=request.method not in {"GET", "HEAD"})
    if not _database_unreachable(exc):
        return internal_error_response(request.scope, exc)
    return _problem(
        request.scope,
        503,
        ErrorCode.SERVICE_UNAVAILABLE,
        "Service temporarily unavailable",
        headers={"Retry-After": "5"},
        error_type=type(exc).__name__,
    )


def internal_error_response(scope: Scope, exc: Exception) -> JSONResponse:
    """500 INTERNAL_ERROR for an unexpected error. Only its type is logged, never its message."""
    return _problem(
        scope, 500, ErrorCode.INTERNAL_ERROR, "Internal error", error_type=type(exc).__name__
    )


def install_error_handlers(app: FastAPI, routes: Sequence[Route], telemetry: Telemetry) -> None:
    """`routes` are the app's routes, used to list the permitted methods on a 405."""

    async def handle_http(request: Request, exc: Exception) -> JSONResponse:
        return _http_problem(request, exc, routes)

    async def handle_database(request: Request, exc: Exception) -> JSONResponse:
        return _database_problem(request, exc, telemetry)

    app.add_exception_handler(DomainError, _handle_domain_error)
    app.add_exception_handler(RequestValidationError, _handle_validation)
    app.add_exception_handler(StarletteHTTPException, handle_http)
    app.add_exception_handler(DBAPIError, handle_database)
    app.add_exception_handler(PoolTimeoutError, handle_database)
    # Anything else is answered by the telemetry middleware (internal_error_response).
