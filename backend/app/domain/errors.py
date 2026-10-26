"""Rules a request can break. app/errors.py maps each class to a problem response."""

from __future__ import annotations


class DomainError(Exception):
    """Base class of the errors below; never raised itself."""


class NotFound(DomainError):
    """The patient, medication, schedule or dose log doesn't exist."""


class PatientHasLogs(DomainError):
    """A patient's timezone can't change once a dose has been logged (requirements §4.3)."""


class MedicationInactive(DomainError):
    """A deactivated medication can't be reactivated, given schedules or logged (§4.4)."""


class ScheduleHasLogs(DomainError):
    """Once a schedule has dose logs, only its end_date may change, and it can't be deleted."""


class ScheduleOverlap(DomainError):
    """Two schedules of one medication would share a date on a common weekday (§4.4, AC-34)."""


class InvalidField(DomainError):
    """A value breaks a rule that needs stored data, such as end_date before the stored start."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message
