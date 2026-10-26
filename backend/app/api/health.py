"""Liveness and readiness probes (`/healthz`, `/readyz` in api/openapi.yaml)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db.session import database_is_reachable

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: Literal["ok", "unavailable"]
    version: str


@router.get("/healthz", operation_id="getLiveness")
def get_liveness(request: Request) -> HealthStatus:
    # Never touches the database: a slow or down database must not restart the process.
    return HealthStatus(status="ok", version=request.app.state.settings.version)


@router.get("/readyz", operation_id="getReadiness", response_model=HealthStatus)
def get_readiness(request: Request) -> JSONResponse:
    version = request.app.state.settings.version
    if database_is_reachable(request.app.state.engine):
        return JSONResponse(HealthStatus(status="ok", version=version).model_dump())
    # The contract returns HealthStatus (not problem+json) from this probe.
    return JSONResponse(
        HealthStatus(status="unavailable", version=version).model_dump(), status_code=503
    )
