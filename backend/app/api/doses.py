"""Planned-dose and dose-log routes (api/openapi.yaml, tag `doses`)."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.api.deps import ClockDep, DoseLogFaultDep, DoseRulesDep, SessionDep, TelemetryDep
from app.api.schemas import DayDosesOut, DoseLogCreate, DoseLogOut
from app.errors import dose_log_failure
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


@router.post("/api/v1/dose-logs", operation_id="createDoseLog", status_code=201)
def create_dose_log(
    body: DoseLogCreate,
    session: SessionDep,
    clock: ClockDep,
    rules: DoseRulesDep,
    telemetry: TelemetryDep,
    fault: DoseLogFaultDep,
) -> DoseLogOut:
    with telemetry.dose_log_attempt(dose_log_failure) as attempt:
        fault.maybe_fail()  # the incident drill only (MT-023); the rate is 0 otherwise
        log = doses.create_dose_log(
            session,
            clock,
            rules,
            schedule_id=body.schedule_id,
            scheduled_for=body.scheduled_for,
            status=body.status,
            note=body.note,
        )
        attempt.late = log.late
    return DoseLogOut.from_row(log)


@router.delete("/api/v1/dose-logs/{dose_log_id}", operation_id="deleteDoseLog", status_code=204)
def delete_dose_log(dose_log_id: UUID, session: SessionDep) -> Response:
    doses.delete_dose_log(session, dose_log_id)
    return Response(status_code=204)
