"""Medication use cases (FR-02, requirements §4.4). Each function is one transaction."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import Clock
from app.db.models import Medication, Patient
from app.db.repositories import ScheduleRow, lock_medication, schedules_of
from app.domain.errors import MedicationInactive, NotFound


@dataclass(frozen=True, slots=True)
class MedicationView:
    medication: Medication
    schedules: list[ScheduleRow]


@dataclass(frozen=True, slots=True)
class MedicationChanges:
    """A PATCH. None means "not sent"; `instructions` may be sent as null, hence its flag."""

    name: str | None = None
    dosage_label: str | None = None
    active: bool | None = None
    instructions_sent: bool = False
    instructions: str | None = None


def list_medications(
    session: Session, patient_id: UUID, *, include_inactive: bool
) -> list[MedicationView]:
    with session.begin():
        if session.get(Patient, patient_id) is None:
            raise NotFound
        query = select(Medication).where(Medication.patient_id == patient_id)
        if not include_inactive:
            query = query.where(Medication.deactivated_at.is_(None))
        medications = session.scalars(query).all()
        schedules = schedules_of(session, [medication.id for medication in medications])
    # Sorted here rather than in SQL, so the order doesn't depend on the database's collation.
    ordered = sorted(medications, key=lambda m: (m.name.casefold(), m.name, m.id))
    return [MedicationView(medication, schedules[medication.id]) for medication in ordered]


def create_medication(
    session: Session,
    clock: Clock,
    patient_id: UUID,
    *,
    name: str,
    dosage_label: str,
    instructions: str | None,
) -> MedicationView:
    with session.begin():
        if session.get(Patient, patient_id) is None:
            raise NotFound
        medication = Medication(
            patient_id=patient_id,
            name=name,
            dosage_label=dosage_label,
            instructions=instructions,
            created_at=clock.now(),
        )
        session.add(medication)
    return MedicationView(medication, [])


def get_medication(session: Session, medication_id: UUID) -> MedicationView:
    with session.begin():
        medication = session.get(Medication, medication_id)
        if medication is None:
            raise NotFound
        schedules = schedules_of(session, [medication_id])[medication_id]
    return MedicationView(medication, schedules)


def update_medication(
    session: Session, clock: Clock, medication_id: UUID, changes: MedicationChanges
) -> MedicationView:
    with session.begin():
        medication = lock_medication(session, medication_id)
        if medication is None:
            raise NotFound
        inactive = medication.deactivated_at is not None
        # Deactivation is one-way in v1; deactivating again keeps the first time.
        if changes.active is True and inactive:
            raise MedicationInactive
        if changes.active is False and not inactive:
            medication.deactivated_at = clock.now()
        if changes.name is not None:
            medication.name = changes.name
        if changes.dosage_label is not None:
            medication.dosage_label = changes.dosage_label
        if changes.instructions_sent:
            medication.instructions = changes.instructions
        session.flush()
        schedules = schedules_of(session, [medication_id])[medication_id]
    return MedicationView(medication, schedules)
