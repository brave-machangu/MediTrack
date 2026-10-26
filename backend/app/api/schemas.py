"""Request and response models that mirror the schemas in api/openapi.yaml.

Request models reject unknown fields (`additionalProperties: false`). The contract test
(MT-018) checks the responses against the contract itself.
"""

from __future__ import annotations

import datetime as dt
from datetime import date, datetime
from functools import cache
from importlib import resources
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.config import GRACE_PERIOD_DEFAULT_MINUTES, GRACE_PERIOD_MAX_MINUTES
from app.db.repositories import ScheduleRow
from app.domain.types import DoseStatus
from app.services.doses import DayView, DoseView
from app.services.medications import MedicationView


@cache
def _iana_timezones() -> frozenset[str]:
    # The pinned tzdata package's own list, identical on every OS. zoneinfo's
    # available_timezones() also scans the system zone directory, which on Linux holds
    # "localtime" (the server's zone), and results must never depend on that (NFR-09).
    zones = resources.files("tzdata").joinpath("zones").read_text(encoding="utf-8")
    return frozenset(zones.split())


def _check_timezone(name: str) -> str:
    # Exact, case-sensitive match. ZoneInfo() alone would accept "europe/london" on a
    # case-insensitive file system and reject it on Linux.
    if name not in _iana_timezones():
        raise ValueError("must be an IANA timezone name, such as Africa/Harare")
    return name


def _reject_null(value: object) -> object:
    if value is None:
        raise ValueError("can't be null")
    return value


Timezone = Annotated[str, AfterValidator(_check_timezone)]
DisplayName = Annotated[str, Field(min_length=1, max_length=80)]
MedicationName = Annotated[str, Field(min_length=1, max_length=100)]
DosageLabel = Annotated[str, Field(min_length=1, max_length=100)]
Instructions = Annotated[str, Field(max_length=500)]


def _no_duplicates[T](values: list[T]) -> list[T]:
    if len(set(values)) != len(values):
        raise ValueError("must not contain duplicates")
    return values


LocalTime = Annotated[str, StringConstraints(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")]
# Strict: the contract says integer, so "1" or true is rejected rather than converted.
Weekday = Annotated[int, Field(strict=True, ge=1, le=7)]
TimesOfDay = Annotated[
    list[LocalTime], Field(min_length=1, max_length=12), AfterValidator(_no_duplicates)
]
DaysOfWeek = Annotated[
    list[Weekday], Field(min_length=1, max_length=7), AfterValidator(_no_duplicates)
]
GraceMinutes = Annotated[int, Field(strict=True, ge=0, le=GRACE_PERIOD_MAX_MINUTES)]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PartialUpdate(RequestModel):
    """A PATCH body: at least one field (`minProperties: 1`). A field that wasn't sent is None,
    so subclasses reject an explicit null for fields the contract doesn't mark nullable.
    """

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("send at least one field")
        return self


class PatientCreate(RequestModel):
    display_name: DisplayName
    timezone: Timezone


class PatientUpdate(PartialUpdate):
    display_name: DisplayName | None = None
    timezone: Timezone | None = None

    _not_null = field_validator("display_name", "timezone", mode="before")(_reject_null)


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    timezone: str
    created_at: datetime


class MedicationCreate(RequestModel):
    name: MedicationName
    dosage_label: DosageLabel
    instructions: Instructions | None = None


class MedicationUpdate(PartialUpdate):
    name: MedicationName | None = None
    dosage_label: DosageLabel | None = None
    instructions: Instructions | None = None  # nullable: null clears it
    active: bool | None = None

    _not_null = field_validator("name", "dosage_label", "active", mode="before")(_reject_null)


class ScheduleCreate(RequestModel):
    times_of_day: TimesOfDay
    days_of_week: DaysOfWeek = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7])
    start_date: date
    end_date: date | None = None
    grace_period_minutes: GraceMinutes = GRACE_PERIOD_DEFAULT_MINUTES


class ScheduleUpdate(PartialUpdate):
    times_of_day: TimesOfDay | None = None
    days_of_week: DaysOfWeek | None = None
    start_date: date | None = None
    end_date: date | None = None  # nullable: null removes the end
    grace_period_minutes: GraceMinutes | None = None

    _not_null = field_validator(
        "times_of_day", "days_of_week", "start_date", "grace_period_minutes", mode="before"
    )(_reject_null)


class ScheduleOut(BaseModel):
    id: UUID
    medication_id: UUID
    times_of_day: list[str]
    days_of_week: list[int]
    start_date: date
    end_date: date | None
    grace_period_minutes: int
    has_dose_logs: bool

    @classmethod
    def from_row(cls, row: ScheduleRow) -> Self:
        schedule = row.schedule
        return cls(
            id=schedule.id,
            medication_id=schedule.medication_id,
            times_of_day=schedule.times_of_day,
            days_of_week=schedule.days_of_week,
            start_date=schedule.start_date,
            end_date=schedule.end_date,
            grace_period_minutes=schedule.grace_period_minutes,
            has_dose_logs=row.has_dose_logs,
        )


class MedicationOut(BaseModel):
    id: UUID
    patient_id: UUID
    name: str
    dosage_label: str
    instructions: str | None
    active: bool
    deactivated_at: datetime | None
    created_at: datetime
    schedules: list[ScheduleOut]

    @classmethod
    def from_view(cls, view: MedicationView) -> Self:
        medication = view.medication
        return cls(
            id=medication.id,
            patient_id=medication.patient_id,
            name=medication.name,
            dosage_label=medication.dosage_label,
            instructions=medication.instructions,
            active=medication.deactivated_at is None,
            deactivated_at=medication.deactivated_at,
            created_at=medication.created_at,
            schedules=[ScheduleOut.from_row(row) for row in view.schedules],
        )


class PlannedDoseOut(BaseModel):
    schedule_id: UUID
    medication_id: UUID
    medication_name: str
    dosage_label: str
    instructions: str | None
    scheduled_for: datetime
    local_date: date
    local_time: str
    status: DoseStatus
    late: bool
    log_window_opens_at: datetime
    log_window_closes_at: datetime
    dose_log_id: UUID | None
    recorded_at: datetime | None

    @classmethod
    def from_view(cls, view: DoseView) -> Self:
        dose, medication = view.dose, view.medication
        return cls(
            schedule_id=dose.schedule_id,
            medication_id=dose.medication_id,
            medication_name=medication.name,
            dosage_label=medication.dosage_label,
            instructions=medication.instructions,
            scheduled_for=dose.scheduled_for,
            local_date=dose.local_date,
            local_time=dose.local_time,
            status=dose.status,
            late=dose.late,
            log_window_opens_at=dose.log_window_opens_at,
            log_window_closes_at=dose.log_window_closes_at,
            dose_log_id=dose.log.dose_log_id if dose.log else None,
            recorded_at=dose.log.recorded_at if dose.log else None,
        )


class DayDosesOut(BaseModel):
    patient_id: UUID
    date: dt.date  # `dt.` because the field itself is called `date`
    timezone: str
    generated_at: datetime
    doses: list[PlannedDoseOut]

    @classmethod
    def from_view(cls, view: DayView) -> Self:
        return cls(
            patient_id=view.patient.id,
            date=view.local_date,
            timezone=view.patient.timezone,
            generated_at=view.generated_at,
            doses=[PlannedDoseOut.from_view(dose) for dose in view.doses],
        )
