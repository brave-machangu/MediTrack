"""Schedule routes (api/openapi.yaml, tag `schedules`)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response

from app.api.deps import ClockDep, SessionDep
from app.api.schemas import ScheduleCreate, ScheduleOut, ScheduleUpdate
from app.services import schedules
from app.services.schedules import ScheduleChanges, ScheduleSpec

router = APIRouter(tags=["schedules"])


@router.get("/api/v1/medications/{medication_id}/schedules", operation_id="listSchedules")
def list_schedules(medication_id: UUID, session: SessionDep) -> list[ScheduleOut]:
    return [ScheduleOut.from_row(row) for row in schedules.list_schedules(session, medication_id)]


@router.post(
    "/api/v1/medications/{medication_id}/schedules",
    operation_id="createSchedule",
    status_code=201,
)
def create_schedule(medication_id: UUID, body: ScheduleCreate, session: SessionDep) -> ScheduleOut:
    spec = ScheduleSpec(
        times_of_day=body.times_of_day,
        days_of_week=body.days_of_week,
        start_date=body.start_date,
        end_date=body.end_date,
        grace_period_minutes=body.grace_period_minutes,
    )
    return ScheduleOut.from_row(schedules.create_schedule(session, medication_id, spec))


@router.patch("/api/v1/schedules/{schedule_id}", operation_id="updateSchedule")
def update_schedule(
    schedule_id: UUID, body: ScheduleUpdate, session: SessionDep, clock: ClockDep
) -> ScheduleOut:
    changes = ScheduleChanges(
        times_of_day=body.times_of_day,
        days_of_week=body.days_of_week,
        start_date=body.start_date,
        grace_period_minutes=body.grace_period_minutes,
        end_date_sent="end_date" in body.model_fields_set,
        end_date=body.end_date,
    )
    return ScheduleOut.from_row(schedules.update_schedule(session, clock, schedule_id, changes))


@router.delete("/api/v1/schedules/{schedule_id}", operation_id="deleteSchedule", status_code=204)
def delete_schedule(schedule_id: UUID, session: SessionDep) -> Response:
    schedules.delete_schedule(session, schedule_id)
    return Response(status_code=204)
