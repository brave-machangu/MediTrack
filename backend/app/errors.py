"""RFC 9457 problem+json errors with the `code` values from api/openapi.yaml (AC-31).

Every error the API returns goes through this module: domain errors, FastAPI's own request
validation errors, unknown routes and methods, database outages and unhandled exceptions.
Problem bodies never contain request data, SQL or stack traces.
"""

from __future__ import annotations

import logging
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

from app.domain.errors import DomainError, MedicationInactive, NotFound, PatientHasLogs

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
    # trace_id is added by the telemetry middleware in MT-022.
    return JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE, headers=headers)


def _field_path(location: Sequence[int | str]) -> str:
    """('body', 'times_of_day', 0) -> 'times_of_day[0]'; the 'body'/'query' prefix is dropped."""
    prefixes = {"body", "query", "path"}
    parts = list(location[1:] if location and location[0] in prefixes else location)
    path = ""
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else (f".{part}" if path else str(part))
    return path or "request"


async def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    problem = DOMAIN_PROBLEMS[type(exc)]
    return problem_response(problem.status, problem.code, problem.title, detail=problem.detail)


async def _handle_validation(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = exc.errors()
    # A malformed ID in the path can't name an existing resource (api/openapi.yaml).
    if details and all(tuple(detail["loc"][:1]) == ("path",) for detail in details):
        return problem_response(404, ErrorCode.NOT_FOUND, "Not found")
    # Only the location and pydantic's message: never echo the submitted value.
    errors: list[FieldError] = [
        {"field": _field_path(detail["loc"]), "message": str(detail["msg"])} for detail in details
    ]
    return problem_response(422, ErrorCode.VALIDATION_ERROR, "Request is invalid", errors=errors)


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
        return problem_response(404, ErrorCode.NOT_FOUND, "Not found")
    if exc.status_code == 405:
        return problem_response(
            405,
            ErrorCode.METHOD_NOT_ALLOWED,
            "Method not allowed",
            headers={"Allow": _allowed_methods(request, routes)},
        )
    if exc.status_code >= 500:
        return problem_response(exc.status_code, ErrorCode.INTERNAL_ERROR, "Internal error")
    return problem_response(exc.status_code, ErrorCode.VALIDATION_ERROR, "Request is invalid")


async def _handle_database_error(request: Request, exc: Exception) -> JSONResponse:
    unreachable = isinstance(exc, OperationalError | PoolTimeoutError) or (
        isinstance(exc, DBAPIError) and exc.connection_invalidated
    )
    if not unreachable:
        return await _handle_unexpected(request, exc)
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


def install_error_handlers(app: FastAPI, routes: Sequence[Route]) -> None:
    """`routes` are the app's routes, used to list the permitted methods on a 405."""

    async def handle_http(request: Request, exc: Exception) -> JSONResponse:
        return _http_problem(request, exc, routes)

    app.add_exception_handler(DomainError, _handle_domain_error)
    app.add_exception_handler(RequestValidationError, _handle_validation)
    app.add_exception_handler(StarletteHTTPException, handle_http)
    app.add_exception_handler(DBAPIError, _handle_database_error)
    app.add_exception_handler(PoolTimeoutError, _handle_database_error)
    app.add_exception_handler(Exception, _handle_unexpected)
