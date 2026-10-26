"""Liveness and readiness probes (`/healthz`, `/readyz` in api/openapi.yaml)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.deps import ContextDep
from app.db.session import database_is_reachable

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: Literal["ok", "unavailable"]
    version: str


@router.get("/healthz", operation_id="getLiveness")
def get_liveness(context: ContextDep) -> HealthStatus:
    # Never touches the database: a slow or down database must not restart the process.
    return HealthStatus(status="ok", version=context.settings.version)


@router.get("/readyz", operation_id="getReadiness", response_model=HealthStatus)
def get_readiness(context: ContextDep) -> JSONResponse:
    version = context.settings.version
    if database_is_reachable(context.engine):
        return JSONResponse(HealthStatus(status="ok", version=version).model_dump())
    # The contract returns HealthStatus (not problem+json) from this probe.
    return JSONResponse(
        HealthStatus(status="unavailable", version=version).model_dump(), status_code=503
    )
