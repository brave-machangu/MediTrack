"""Medication routes (api/openapi.yaml, tag `medications`)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import ClockDep, SessionDep
from app.api.schemas import MedicationCreate, MedicationOut, MedicationUpdate
from app.services import medications
from app.services.medications import MedicationChanges

router = APIRouter(tags=["medications"])


@router.get("/api/v1/patients/{patient_id}/medications", operation_id="listMedications")
def list_medications(
    patient_id: UUID, session: SessionDep, include_inactive: bool = False
) -> list[MedicationOut]:
    views = medications.list_medications(session, patient_id, include_inactive=include_inactive)
    return [MedicationOut.from_view(view) for view in views]


@router.post(
    "/api/v1/patients/{patient_id}/medications",
    operation_id="createMedication",
    status_code=201,
)
def create_medication(
    patient_id: UUID, body: MedicationCreate, session: SessionDep, clock: ClockDep
) -> MedicationOut:
    view = medications.create_medication(
        session,
        clock,
        patient_id,
        name=body.name,
        dosage_label=body.dosage_label,
        instructions=body.instructions,
    )
    return MedicationOut.from_view(view)


@router.get("/api/v1/medications/{medication_id}", operation_id="getMedication")
def get_medication(medication_id: UUID, session: SessionDep) -> MedicationOut:
    return MedicationOut.from_view(medications.get_medication(session, medication_id))


@router.patch("/api/v1/medications/{medication_id}", operation_id="updateMedication")
def update_medication(
    medication_id: UUID, body: MedicationUpdate, session: SessionDep, clock: ClockDep
) -> MedicationOut:
    changes = MedicationChanges(
        name=body.name,
        dosage_label=body.dosage_label,
        active=body.active,
        instructions_sent="instructions" in body.model_fields_set,
        instructions=body.instructions,
    )
    return MedicationOut.from_view(
        medications.update_medication(session, clock, medication_id, changes)
    )
