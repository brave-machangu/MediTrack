"""Hot paths run a fixed number of SQL statements, however many medications there are
(backend/DESIGN.md §5)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event

from app.api.deps import AppContext
from tests.integration.helpers import PATIENTS, add_schedule, create_medication, create_patient


@contextmanager
def count_statements(api: TestClient) -> Iterator[list[str]]:
    """Collects the statements the app's own engine runs inside the block."""
    context = api.app.state.context
    assert isinstance(context, AppContext)
    statements: list[str] = []

    def record(_conn: object, _cursor: object, statement: str, *_rest: object) -> None:
        statements.append(statement)

    event.listen(context.engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(context.engine, "before_cursor_execute", record)


def patient_with_medications(api: TestClient, engine: Engine, count: int) -> str:
    """A patient whose `count` medications have two schedules each."""
    patient = create_patient(api)
    for number in range(count):
        medication = create_medication(api, patient["id"], name=f"Demo Med {number}")
        add_schedule(engine, medication["id"], times=["08:00"], start=date(2026, 11, 1))
        add_schedule(engine, medication["id"], times=["20:00"], start=date(2027, 1, 1))
    return str(patient["id"])


@pytest.mark.parametrize("medications", [1, 4])
def test_medication_list_statement_count_is_constant(
    api: TestClient, engine: Engine, medications: int
) -> None:
    patient_id = patient_with_medications(api, engine, medications)

    with count_statements(api) as statements:
        response = api.get(f"{PATIENTS}/{patient_id}/medications")

    assert response.status_code == 200
    assert len(response.json()) == medications
    # patient, medications, schedules with has_dose_logs (BEGIN/COMMIT aren't cursor executions)
    assert len(statements) == 3, statements


@pytest.mark.parametrize("medications", [1, 4])
def test_day_view_statement_count_is_constant(
    api: TestClient, engine: Engine, medications: int
) -> None:
    patient_id = patient_with_medications(api, engine, medications)

    with count_statements(api) as statements:
        response = api.get(f"{PATIENTS}/{patient_id}/doses?date=2026-11-02")

    assert response.status_code == 200
    assert len(response.json()["doses"]) == medications
    # patient, schedules joined with their medications, dose logs of the planned instants
    assert len(statements) == 3, statements


@pytest.mark.parametrize("medications", [1, 4])
@pytest.mark.parametrize(
    "path", ["missed-doses?from=2026-11-02&to=2026-11-08", "adherence/daily?date=2026-11-02"]
)
def test_report_statement_count_is_constant(
    api: TestClient, engine: Engine, medications: int, path: str
) -> None:
    patient_id = patient_with_medications(api, engine, medications)

    with count_statements(api) as statements:
        response = api.get(f"{PATIENTS}/{patient_id}/{path}")

    assert response.status_code == 200
    # patient, schedules joined with their medications, dose logs (DESIGN.md §5)
    assert len(statements) == 3, statements
