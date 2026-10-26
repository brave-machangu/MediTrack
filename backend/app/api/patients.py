"""`/api/v1/patients` routes (api/openapi.yaml, tag `patients`)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import ClockDep, SessionDep
from app.api.schemas import PatientCreate, PatientOut, PatientUpdate
from app.services import patients

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.get("", operation_id="listPatients")
def list_patients(session: SessionDep) -> list[PatientOut]:
    return [PatientOut.model_validate(patient) for patient in patients.list_patients(session)]


@router.post("", operation_id="createPatient", status_code=201)
def create_patient(body: PatientCreate, session: SessionDep, clock: ClockDep) -> PatientOut:
    patient = patients.create_patient(
        session, clock, display_name=body.display_name, timezone=body.timezone
    )
    return PatientOut.model_validate(patient)


@router.get("/{patient_id}", operation_id="getPatient")
def get_patient(patient_id: UUID, session: SessionDep) -> PatientOut:
    return PatientOut.model_validate(patients.get_patient(session, patient_id))


@router.patch("/{patient_id}", operation_id="updatePatient")
def update_patient(patient_id: UUID, body: PatientUpdate, session: SessionDep) -> PatientOut:
    patient = patients.update_patient(
        session, patient_id, display_name=body.display_name, timezone=body.timezone
    )
    return PatientOut.model_validate(patient)
