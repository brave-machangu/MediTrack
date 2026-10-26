"""Synthetic demo seed (FR-10, FR-14): AC-33, AC-41 and the alert probe's patient, on SQLite
and PostgreSQL."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app import seed as seed_module
from app.clock import FixedClock
from app.db.models import DoseLog, Medication, Patient, Schedule
from app.db.session import make_engine, make_session_factory
from app.domain.scheduling import local_today, planned_doses
from app.domain.types import DoseRules
from app.seed import PROBE_PATIENT_NAME, seed
from app.services.doses import schedule_rule
from tests.integration.database import migrate

NOW = datetime(2026, 11, 2, 5, 30, tzinfo=UTC)
RULES = DoseRules(early_log_window=timedelta(minutes=60), late_log_limit=timedelta(minutes=1440))
DEMO_PATIENTS = {"Demo Patient A", "Demo Patient B"}


def run_seed(engine: Engine, *, reset: bool = False, now: datetime = NOW) -> None:
    seed(make_session_factory(engine), FixedClock(now), RULES, reset=reset)


def counts(engine: Engine) -> dict[str, int]:
    with Session(engine) as session:
        return {
            model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
            for model in (Patient, Medication, Schedule, DoseLog)
        }


def all_ids(engine: Engine) -> set[UUID]:
    with Session(engine) as session:
        return {
            row_id
            for model in (Patient, Medication, Schedule, DoseLog)
            for row_id in session.scalars(select(model.id))
        }


def add_other_patient(engine: Engine) -> UUID:
    with Session(engine) as session, session.begin():
        patient = Patient(display_name="Someone Typed This", timezone="UTC", created_at=NOW)
        session.add(patient)
        session.flush()
        return patient.id


def test_seed_loads_two_demo_patients_with_four_medications_and_the_probe_ac33(
    engine: Engine,
) -> None:
    run_seed(engine)

    with Session(engine) as session:
        names = set(session.scalars(select(Patient.display_name)))
        demo_medications = session.scalars(
            select(Medication.name)
            .join(Patient, Medication.patient_id == Patient.id)
            .where(Patient.display_name.in_(DEMO_PATIENTS))
        ).all()
        statuses = {(log.status, log.late) for log in session.scalars(select(DoseLog))}

    assert names == DEMO_PATIENTS | {PROBE_PATIENT_NAME}
    assert len(demo_medications) == 4
    # Mixed history: on time, late, skipped (and missed doses, checked below).
    assert statuses == {("taken", False), ("taken", True), ("skipped", False)}


def test_history_covers_the_seven_days_before_today_with_missed_doses(engine: Engine) -> None:
    run_seed(engine)

    with Session(engine) as session:
        rows = session.execute(
            select(Schedule, Medication, Patient)
            .join(Medication, Schedule.medication_id == Medication.id)
            .join(Patient, Medication.patient_id == Patient.id)
            .where(Patient.display_name.in_(DEMO_PATIENTS))
        ).all()
        logged = {(log.schedule_id, log.scheduled_for) for log in session.scalars(select(DoseLog))}

    missed = 0
    for schedule, medication, patient in rows:
        tz = ZoneInfo(patient.timezone)
        today = local_today(NOW, tz)
        for day in range(1, 8):
            for dose in planned_doses(
                [schedule_rule(schedule, medication)],
                [],
                tz,
                today - timedelta(days=day),
                NOW,
                RULES,
            ):
                missed += (schedule.id, dose.scheduled_for) not in logged
        # Nothing is logged for today or later.
        assert all(
            local_today(scheduled_for, tz) < today
            for schedule_id, scheduled_for in logged
            if schedule_id == schedule.id
        )
    assert missed > 0


def test_second_run_adds_nothing_ac33(engine: Engine) -> None:
    run_seed(engine)
    before = (counts(engine), all_ids(engine))
    run_seed(engine, now=NOW + timedelta(days=1))
    assert (counts(engine), all_ids(engine)) == before


def test_seed_without_reset_never_deletes(engine: Engine) -> None:
    other = add_other_patient(engine)
    run_seed(engine)
    assert other in all_ids(engine)


def test_reset_replaces_every_row_with_the_seed_ac41(engine: Engine) -> None:
    run_seed(engine)
    seed_counts = counts(engine)
    other = add_other_patient(engine)
    earlier = all_ids(engine)

    run_seed(engine, reset=True)

    assert counts(engine) == seed_counts
    assert all_ids(engine).isdisjoint(earlier)
    assert other not in all_ids(engine)


def test_reset_twice_gives_the_same_counts_ac41(engine: Engine) -> None:
    run_seed(engine, reset=True)
    first = counts(engine)
    run_seed(engine, reset=True)
    assert counts(engine) == first


def test_failed_reset_keeps_the_previous_data_ac41(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_seed(engine)
    add_other_patient(engine)
    before = (counts(engine), all_ids(engine))
    real_add_patient = seed_module._add_patient
    added: list[str] = []

    def fail_on_second_patient(*args: object, **kwargs: object) -> None:
        added.append("patient")
        if len(added) == 2:
            raise RuntimeError("simulated failure part-way through the seed")
        real_add_patient(*args, **kwargs)

    monkeypatch.setattr(seed_module, "_add_patient", fail_on_second_patient)
    with pytest.raises(RuntimeError):
        run_seed(engine, reset=True)

    assert (counts(engine), all_ids(engine)) == before


def test_probe_patient_always_has_an_unlogged_dose_in_its_log_window(engine: Engine) -> None:
    run_seed(engine)
    with Session(engine) as session:
        schedule, medication, patient = session.execute(
            select(Schedule, Medication, Patient)
            .join(Medication, Schedule.medication_id == Medication.id)
            .join(Patient, Medication.patient_id == Patient.id)
            .where(Patient.display_name == PROBE_PATIENT_NAME)
        ).one()
    assert schedule.times_of_day == [f"{hour:02d}:00" for hour in range(0, 24, 2)]
    assert schedule.days_of_week == [1, 2, 3, 4, 5, 6, 7]
    rule = schedule_rule(schedule, medication)
    tz = ZoneInfo(patient.timezone)

    # Every 20 minutes for two days after seeding, the probe can log some dose of today.
    for step in range(0, 2 * 24 * 3):
        now = NOW + timedelta(minutes=20 * step)
        doses = planned_doses([rule], [], tz, local_today(now, tz), now, RULES)
        assert any(dose.log_window_opens_at <= now <= dose.log_window_closes_at for dose in doses)


def test_only_synthetic_names_are_used(engine: Engine) -> None:
    run_seed(engine)
    with Session(engine) as session:
        patients = set(session.scalars(select(Patient.display_name)))
        medications = set(session.scalars(select(Medication.name)))
        notes = set(session.scalars(select(DoseLog.note)))
    assert patients == {"Demo Patient A", "Demo Patient B", "Probe Patient"}
    assert all(name.startswith(("Demo Med ", "Probe Med")) for name in medications)
    assert notes == {None}


def test_seed_command_runs_twice_without_duplicates(tmp_path: Path) -> None:
    # The verification from the issue: `uv run python -m app.seed` twice adds nothing.
    url = f"sqlite:///{(tmp_path / 'cli.db').as_posix()}"
    engine = make_engine(url)
    migrate(engine)
    backend = Path(__file__).resolve().parents[2]
    env = {**os.environ, "DATABASE_URL": url}

    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-m", "app.seed"], cwd=backend, env=env, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
    assert "Demo Patient" not in result.stderr + result.stdout  # no names in the output
    assert counts(engine)["patients"] == 3
    engine.dispose()


def test_schedules_start_seven_days_before_today(engine: Engine) -> None:
    # 2026-11-02 in Harare, New York (00:30 EST) and UTC alike, so the history has 7 days to fill.
    run_seed(engine)
    with Session(engine) as session:
        starts = set(session.scalars(select(Schedule.start_date)))
    assert starts == {date(2026, 10, 26)}
