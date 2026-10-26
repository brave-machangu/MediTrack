"""Planned-dose and dose-log routes (api/openapi.yaml, tag `doses`)."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import ClockDep, DoseRulesDep, SessionDep
from app.api.schemas import DayDosesOut
from app.services import doses

router = APIRouter(tags=["doses"])


@router.get("/api/v1/patients/{patient_id}/doses", operation_id="listPlannedDoses")
def list_planned_doses(
    patient_id: UUID,
    session: SessionDep,
    clock: ClockDep,
    rules: DoseRulesDep,
    local_date: Annotated[date | None, Query(alias="date")] = None,
) -> DayDosesOut:
    return DayDosesOut.from_view(doses.day_view(session, clock, rules, patient_id, local_date))
