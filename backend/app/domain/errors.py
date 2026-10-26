"""Rules a request can break. app/errors.py maps each class to a problem response."""

from __future__ import annotations


class DomainError(Exception):
    """Base class of the errors below; never raised itself."""


class NotFound(DomainError):
    """The patient, medication, schedule or dose log doesn't exist."""


class PatientHasLogs(DomainError):
    """A patient's timezone can't change once a dose has been logged (requirements §4.3)."""
