"""Bound values never reach logs through database errors (Lead decision: hide_parameters,
docs/security.md §2)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Medication

CANARIES = ("PRIVACY-CANARY-MED", "PRIVACY-CANARY-LABEL", "PRIVACY-CANARY-NOTE")


def test_database_error_log_contains_no_canary_value(
    engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    medication = Medication(
        patient_id=uuid4(),  # no such patient: the INSERT fails on the foreign key
        name=CANARIES[0],
        dosage_label=CANARIES[1],
        instructions=CANARIES[2],
        created_at=datetime(2026, 11, 2, tzinfo=UTC),
    )
    with Session(engine) as session:
        session.add(medication)
        with pytest.raises(IntegrityError) as error:
            session.flush()

    logging.getLogger("meditrack.test").error("insert failed", exc_info=error.value)

    assert "INSERT INTO medications" in caplog.text  # the error and its SQL were logged
    assert "SQL parameters hidden" in caplog.text
    for canary in CANARIES:
        assert canary not in caplog.text
