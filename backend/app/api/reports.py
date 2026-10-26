"""Missed-dose and adherence routes (api/openapi.yaml, tag `reports`)."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import ClockDep, DoseRulesDep, SessionDep
from app.api.schemas import DailyAdherenceOut, PlannedDoseOut
from app.services import reports

router = APIRouter(tags=["reports"])


@router.get("/api/v1/patients/{patient_id}/missed-doses", operation_id="listMissedDoses")
def list_missed_doses(
    patient_id: UUID,
    session: SessionDep,
    clock: ClockDep,
    rules: DoseRulesDep,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
) -> list[PlannedDoseOut]:
    views = reports.list_missed_doses(session, clock, rules, patient_id, start, end)
    return [PlannedDoseOut.from_view(view) for view in views]


@router.get("/api/v1/patients/{patient_id}/adherence/daily", operation_id="getDailyAdherence")
def get_daily_adherence(
    patient_id: UUID,
    session: SessionDep,
    clock: ClockDep,
    rules: DoseRulesDep,
    local_date: Annotated[date | None, Query(alias="date")] = None,
) -> DailyAdherenceOut:
    view = reports.daily_adherence(session, clock, rules, patient_id, local_date)
    return DailyAdherenceOut.from_view(view)
