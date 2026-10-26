"""Synthetic demo data (FR-10, FR-14): `python -m app.seed [--reset]`.

Without --reset, a patient whose display name already exists is left alone: running the seed
twice adds nothing, and it never deletes anything (AC-33). With --reset, every patient,
medication, schedule and dose log is replaced by the seed in one transaction, so a failure
part-way leaves the previous data as it was (decision D1, AC-41). Deploys and the nightly
reset run it with --reset.

All dates come from the Clock, so the history always covers the seven days before today.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.clock import Clock, SystemClock
from app.config import GRACE_PERIOD_DEFAULT_MINUTES, Settings
from app.db.models import DoseLog, Medication, Patient, Schedule
from app.db.session import make_engine, make_session_factory
from app.domain.scheduling import is_late, local_today, planned_doses_between
from app.domain.types import DoseRules
from app.services.doses import schedule_rule

logger = logging.getLogger("meditrack.seed")

# The alert probe finds its patient by this name on every run (operations.md §4).
PROBE_PATIENT_NAME = "Probe Patient"
HISTORY_DAYS = 7
EVERY_DAY = (1, 2, 3, 4, 5, 6, 7)
# What happened to each past dose, in turn. "missed" means nothing was recorded.
OUTCOMES = ("taken", "taken", "late", "skipped", "missed")
ON_TIME_AFTER = timedelta(minutes=10)
LATE_AFTER = timedelta(hours=2)  # past the 60-minute grace, so the log is late


@dataclass(frozen=True, slots=True)
class SeedMedication:
    name: str
    dosage_label: str
    instructions: str | None
    times_of_day: tuple[str, ...]
    days_of_week: tuple[int, ...] = EVERY_DAY
    history: bool = True


@dataclass(frozen=True, slots=True)
class SeedPatient:
    display_name: str
    timezone: str
    medications: tuple[SeedMedication, ...]


# Synthetic names only (requirements §3, test-strategy.md §5).
SEED = (
    SeedPatient(
        "Demo Patient A",
        "Africa/Harare",
        (
            SeedMedication("Demo Med Alpha", "1 tablet", "With food", ("08:00", "20:00")),
            SeedMedication("Demo Med Beta", "500 mg, 1 tablet", None, ("08:00",)),
        ),
    ),
    SeedPatient(
        "Demo Patient B",
        "America/New_York",
        (
            SeedMedication("Demo Med Gamma", "5 ml", "Shake well", ("09:00",)),
            SeedMedication("Demo Med Delta", "1 capsule", None, ("21:00",), days_of_week=(1, 3, 5)),
        ),
    ),
    # A dose every two hours and no history: some dose is always inside its log window, so
    # the probe can record one at any time (operations.md §4).
    SeedPatient(
        PROBE_PATIENT_NAME,
        "UTC",
        (
            SeedMedication(
                "Probe Med",
                "1 unit",
                None,
                tuple(f"{hour:02d}:00" for hour in range(0, 24, 2)),
                history=False,
            ),
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class SeedResult:
    added: int
    already_present: int


def seed(
    session_factory: sessionmaker[Session], clock: Clock, rules: DoseRules, *, reset: bool
) -> SeedResult:
    now = clock.now()
    with session_factory() as session, session.begin():
        if reset:
            # Children first: every foreign key is ON DELETE RESTRICT.
            for model in (DoseLog, Schedule, Medication, Patient):
                session.execute(delete(model))
        present = set(session.scalars(select(Patient.display_name)))
        missing = [patient for patient in SEED if patient.display_name not in present]
        for patient in missing:
            _add_patient(session, patient, now, rules)
    return SeedResult(added=len(missing), already_present=len(SEED) - len(missing))


def _add_patient(session: Session, spec: SeedPatient, now: datetime, rules: DoseRules) -> None:
    patient = Patient(display_name=spec.display_name, timezone=spec.timezone, created_at=now)
    session.add(patient)
    session.flush()
    tz = ZoneInfo(spec.timezone)
    today = local_today(now, tz)
    start = today - timedelta(days=HISTORY_DAYS)
    for spec_medication in spec.medications:
        medication = Medication(
            patient_id=patient.id,
            name=spec_medication.name,
            dosage_label=spec_medication.dosage_label,
            instructions=spec_medication.instructions,
            created_at=now,
        )
        session.add(medication)
        session.flush()
        schedule = Schedule(
            medication_id=medication.id,
            times_of_day=sorted(spec_medication.times_of_day),
            days_of_week=sorted(spec_medication.days_of_week),
            start_date=start,
            end_date=None,
            grace_period_minutes=GRACE_PERIOD_DEFAULT_MINUTES,
        )
        session.add(schedule)
        session.flush()
        if spec_medication.history:
            _add_history(session, schedule, medication, tz, now, rules)


def _add_history(
    session: Session,
    schedule: Schedule,
    medication: Medication,
    tz: ZoneInfo,
    now: datetime,
    rules: DoseRules,
) -> None:
    """Logs for the planned doses of the seven days before today, with mixed outcomes."""
    rule = schedule_rule(schedule, medication)
    today = local_today(now, tz)
    past = planned_doses_between(
        [rule], [], tz, today - timedelta(days=HISTORY_DAYS), today - timedelta(days=1), now, rules
    )
    for index, dose in enumerate(past):
        outcome = OUTCOMES[index % len(OUTCOMES)]
        if outcome == "missed":
            continue
        recorded_at = dose.scheduled_for + (LATE_AFTER if outcome == "late" else ON_TIME_AFTER)
        session.add(
            DoseLog(
                schedule_id=schedule.id,
                scheduled_for=dose.scheduled_for,
                status="skipped" if outcome == "skipped" else "taken",
                recorded_at=recorded_at,
                late=is_late(dose.scheduled_for, rule.grace, recorded_at),
                note=None,
            )
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.seed", description=__doc__.splitlines()[0])
    parser.add_argument(
        "--reset",
        action="store_true",
        help="replace all patients, medications, schedules and dose logs with the seed",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = Settings()
    rules = DoseRules(
        early_log_window=timedelta(minutes=settings.early_log_window_minutes),
        late_log_limit=timedelta(minutes=settings.late_log_limit_minutes),
    )
    engine = make_engine(settings.database_url)
    try:
        result = seed(make_session_factory(engine), SystemClock(), rules, reset=args.reset)
    finally:
        engine.dispose()
    # Counts only: no patient names in logs (docs/security.md §2).
    logger.info(
        "seed: %d patients added, %d already present (reset=%s)",
        result.added,
        result.already_present,
        args.reset,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
