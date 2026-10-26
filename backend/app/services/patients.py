"""Patient use cases (FR-01). Each function is one transaction."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.clock import Clock
from app.db.models import DoseLog, Medication, Patient, Schedule
from app.domain.errors import NotFound, PatientHasLogs


def list_patients(session: Session) -> list[Patient]:
    with session.begin():
        patients = session.scalars(select(Patient)).all()
    # Sorted here rather than in SQL: SQLite and PostgreSQL collate text differently, and the
    # order must not depend on the database.
    return sorted(
        patients,
        key=lambda patient: (patient.display_name.casefold(), patient.display_name, patient.id),
    )


def create_patient(session: Session, clock: Clock, *, display_name: str, timezone: str) -> Patient:
    patient = Patient(display_name=display_name, timezone=timezone, created_at=clock.now())
    with session.begin():
        session.add(patient)
    return patient


def get_patient(session: Session, patient_id: UUID) -> Patient:
    with session.begin():
        return _get(session, patient_id)


def update_patient(
    session: Session, patient_id: UUID, *, display_name: str | None, timezone: str | None
) -> Patient:
    """None means "not sent"; neither field is nullable in the contract."""
    with session.begin():
        patient = _get(session, patient_id)
        if timezone is not None and timezone != patient.timezone:
            # Planned doses are computed on read, so a new timezone would move doses that
            # are already logged to other local times (requirements §4.3).
            if _has_dose_logs(session, patient_id):
                raise PatientHasLogs
            patient.timezone = timezone
        if display_name is not None:
            patient.display_name = display_name
    return patient


def _get(session: Session, patient_id: UUID) -> Patient:
    patient = session.get(Patient, patient_id)
    if patient is None:
        raise NotFound
    return patient


def _has_dose_logs(session: Session, patient_id: UUID) -> bool:
    logged = (
        exists()
        .where(DoseLog.schedule_id == Schedule.id)
        .where(Schedule.medication_id == Medication.id)
        .where(Medication.patient_id == patient_id)
    )
    return bool(session.scalar(select(logged)))
