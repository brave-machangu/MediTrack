# MediTrack backend — design note

Status: **approved by the Lead on 2026-10-26** (Phase A), with the decisions and conditions in §0.
Scope: the whole backend, MT-010 to MT-023. Owner: Backend agent.

Behaviour comes from [requirements.md](../docs/requirements.md), [acceptance-criteria.md](../docs/acceptance-criteria.md) and [api/openapi.yaml](../api/openapi.yaml). If this note disagrees with them, the note is wrong.

## 0. Lead decisions (2026-10-26)

The rest of this note follows these decisions.

| # | Question | Decision | Follow-up |
|---|---|---|---|
| Q1 | Which local date does a DST-gap-shifted dose belong to? | **The local date on which its instant falls**, the same date its `local_time` is shown on. Start date, end date and weekdays still apply to the date the user configured. Two times of one schedule that land on one instant are planned once. Examples: in `America/Nuuk`, Saturday 2026-03-28 `23:30` and Sunday `00:30` become one dose, shown on Sunday. `Pacific/Apia` skipped 2011-12-30, so `08:00` on 30 and 31 Dec map to one instant. Planning per configured date would show the same dose on two days and count it twice in adherence. | Docs issue #43 (requirements §4.3); Nuuk and Apia unit tests in MT-011 |
| Q2 | When do two schedules overlap "on a shared weekday"? | **When at least one calendar date lies in both date ranges and its weekday is in both `days_of_week`.** Mon/Wed and Tue/Thu schedules of one medication don't overlap. Neither do schedules that share a weekday but whose common date range never reaches it. | Unit + integration tests (§7) |
| Q3 | A schedule has logs, and a PATCH resends unchanged fields with a new `end_date`. | **Only fields whose value changes** count towards 409 `SCHEDULE_HAS_LOGS`. `end_date: null` (reopen) is allowed. **Condition:** extending or clearing `end_date` still runs the overlap check, and returns 409 `SCHEDULE_OVERLAP` if it would collide with a later schedule. | Tests for extending and for clearing (§7) |
| Q4 | Malformed ID in a path (`/api/v1/patients/abc`) | **404 `NOT_FOUND`.** A malformed ID can't name an existing resource, and `getPatient`, `getMedication`, `deleteSchedule` and `deleteDoseLog` don't document 422. | Contract-change issue #44 (one line in the contract description) |
| Q5 | Environment variable names | Rename `APP_ENV` → `MEDITRACK_ENV` and `APP_VERSION` → `MEDITRACK_VERSION`. `DATABASE_URL` keeps its conventional name (§6). | #40 merged without it; done in the follow-up PR on branch `mt-010-env-prefix` |
| Q6 | Dependencies beyond the fixed stack | **Approved:** `tzdata` and `psycopg[binary]` (runtime), `hypothesis` (dev), OpenTelemetry in MT-022. | §8 |
| Q7 | Fault image label for MT-023 | The **Platform build step** adds `docker build --label meditrack.fault=true` when the fault rate is > 0. The Dockerfile only passes the build arg on to the app. | Backlog issue #45 (MT-023 and MT-032 criteria) |
| — | `hide_parameters=True` on the engine | **Adopted**, with a test showing a database error log contains no canary value. | MT-013 (§9) |

Interpretations that need no decision (the docs and contract already settle them, or nothing depends on the choice):

- `late` is `false` for a dose that has no log. A dose of a deactivated medication is planned only if `scheduled_for < deactivated_at` (strictly less).
- `times_of_day` and `days_of_week` are stored and returned sorted. The meaning is the same, and the output is deterministic.
- Missed-dose defaults follow the contract literally: `from` defaults to 6 days before **today** (not before `to`), and `to` defaults to today.
- Checks on `POST /dose-logs` run in this order: 404 → `MEDICATION_INACTIVE` → `DOSE_NOT_PLANNED` → `OUTSIDE_LOG_WINDOW` → insert (constraint → `DUPLICATE_DOSE_LOG`). One consequence: a repeat POST more than 24 h after the dose gets 422, not 409. The frontend only retries within seconds (AC-36).
- An inactive medication's name, dosage label and instructions stay editable. `active: false` sent again is a no-op 200 that keeps the original `deactivated_at`. `active: true` returns 409 (contract).
- String limits are exactly the contract's (`minLength`/`maxLength`). Values are not trimmed: the contract doesn't say to.

## 1. Module layout

Follows [architecture.md §3](../docs/architecture.md#3-backend-structure). Imports flow one way: `api → services → (domain, db)`. `domain` imports only the standard library.

```
backend/
  pyproject.toml uv.lock README.md DESIGN.md alembic.ini
  Dockerfile .dockerignore          MT-021: non-root, tzdata from the wheel, GIT_SHA build arg
  alembic/env.py                    URL from Settings; naming convention from app.db.models
  alembic/versions/0001_initial.py  the four tables in §2 (MT-013)
  app/
    main.py              create_app(settings, clock): wiring only (routers, handlers, engine)
    config.py            Settings from the environment; rule constants fixed by the contract
    clock.py             Clock, SystemClock, FixedClock: the only reader of the system time
    errors.py            ErrorCode (mirror of Problem.code), DomainError→problem table, all handlers
    telemetry.py         MT-022: OTel setup, X-Trace-Id, privacy-safe attributes, JSON logs
    seed.py              MT-019: python -m app.seed [--reset]
    api/
      deps.py            request-scoped Session, Clock and Settings dependencies
      schemas.py         Pydantic models mirroring contract schemas; requests use extra="forbid"
      health.py          /healthz, /readyz
      patients.py        /api/v1/patients, /api/v1/patients/{patient_id}
      medications.py     /api/v1/patients/{patient_id}/medications, /api/v1/medications/{medication_id}
      schedules.py       /api/v1/medications/{medication_id}/schedules, /api/v1/schedules/{schedule_id}
      doses.py           /api/v1/patients/{patient_id}/doses, /api/v1/dose-logs[/{dose_log_id}]
      reports.py         /api/v1/patients/{patient_id}/missed-doses, .../adherence/daily
    domain/
      types.py           frozen dataclasses and enums used by the domain functions (§3)
      errors.py          DomainError subclasses; no HTTP status, no FastAPI
      scheduling.py      local today, local→UTC policy, planned doses, status, log window, lateness
      schedule_rules.py  overlap, what may change once a schedule has logs, end-date floor
      adherence.py       daily summary, half-up rounding
    services/
      patients.py medications.py schedules.py doses.py reports.py
                         one function per use case = one transaction (`with session.begin()`);
                         load rows → call domain → write; IntegrityError → domain error
    db/
      models.py          DeclarativeBase + naming convention, UtcDateTime type, four models
      session.py         engine (pre-ping, hide_parameters, SQLite FK pragma), sessionmaker, readiness
      repositories.py    plain query functions for the hot paths (§5); unique-violation helper
```

No generic repository class, no `utils.py`, no event bus. Endpoints are sync `def`s on a sync SQLAlchemy engine, so FastAPI runs them in its worker threads. AC-18 needs real parallel transactions, and this gives them without async database code.

## 2. Schema

All four tables are created in one Alembic revision (MT-013). The metadata has a naming convention, so constraint names are predictable (`pk_`, `fk_`, `ix_`, `uq_`, `ck_`). IDs are UUID4s generated in Python (`default=uuid4`), stored as `sa.Uuid`: native `uuid` on PostgreSQL, `CHAR(32)` on SQLite.

**patients**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | Uuid | no | PK |
| `display_name` | String(80) | no | |
| `timezone` | String(64) | no | Must be in `zoneinfo.available_timezones()` (exact case; see §8 `tzdata`) |
| `created_at` | UtcDateTime | no | From the Clock |

**medications**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | Uuid | no | PK |
| `patient_id` | Uuid | no | FK → `patients.id`, `ON DELETE RESTRICT`; index `ix_medications_patient_id` |
| `name` | String(100) | no | |
| `dosage_label` | String(100) | no | Display text only |
| `instructions` | String(500) | yes | |
| `deactivated_at` | UtcDateTime | yes | NULL = active. The API's `active` is derived as `deactivated_at IS NULL`, so the two can never disagree and no CHECK is needed |
| `created_at` | UtcDateTime | no | |

**schedules**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | Uuid | no | PK |
| `medication_id` | Uuid | no | FK → `medications.id`, `ON DELETE RESTRICT`; index `ix_schedules_medication_id` |
| `times_of_day` | JSON | no | Sorted list of `"HH:MM"` (ADR-005: JSON, not arrays) |
| `days_of_week` | JSON | no | Sorted list of ISO weekdays 1–7 |
| `start_date` | Date | no | Patient-local |
| `end_date` | Date | yes | Inclusive; NULL = no end |
| `grace_period_minutes` | Integer | no | |

Checks: `ck_schedules_end_after_start` (`end_date IS NULL OR end_date >= start_date`) and `ck_schedules_grace_range` (`grace_period_minutes BETWEEN 0 AND 240`, the contract's limits). The API validates both first. The checks are a backstop.

**dose_logs**

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | Uuid | no | PK |
| `schedule_id` | Uuid | no | FK → `schedules.id`, `ON DELETE RESTRICT`: a schedule with logs can't be deleted even if the service check were bypassed |
| `scheduled_for` | UtcDateTime | no | |
| `status` | String(7) | no | `ck_dose_logs_status`: `status IN ('taken', 'skipped')`. A string plus CHECK instead of a PostgreSQL ENUM: portable (ADR-005), and adding a value later needs no `ALTER TYPE` |
| `recorded_at` | UtcDateTime | no | From the Clock |
| `late` | Boolean | no | Stored at insert. It can't go stale: grace can't change once logs exist (requirements §4.4) |
| `note` | String(280) | yes | |

**`uq_dose_log_schedule_time UNIQUE (schedule_id, scheduled_for)`** enforces duplicate prevention (ADR-003). Its index leads with `schedule_id`, so it also serves "logs of these schedules between two instants". No separate index is needed.

**Schedule-overlap rule (AC-34).** No portable constraint can express "overlapping date ranges on a shared weekday". It would need a PostgreSQL exclusion constraint over ranges and arrays, which ADR-005 rules out. The service enforces the rule instead, and makes it race-safe on PostgreSQL:

1. `SELECT … FROM medications WHERE id = :id FOR UPDATE` locks the parent row. Every schedule create and PATCH, and medication deactivation, takes this lock first.
2. It reads the medication's other schedules and runs `find_overlap` (§3) on the schedule as it would be after the write. On PATCH this happens whenever `days_of_week`, `start_date` or `end_date` changes. That includes an `end_date`-only change on a schedule with logs: extending or clearing the end can collide with a later schedule (Q3 condition).
3. It writes and commits.

Two concurrent writes for one medication therefore run one after the other. The second sees the first's row and gets 409 (test `test_concurrent_overlapping_schedules_one_created_ac34`, PostgreSQL). SQLite ignores `FOR UPDATE`, and pysqlite runs the SELECTs outside a transaction, so this rule is not race-safe on SQLite. That's acceptable: SQLite only serves tests and single-user development (ADR-005).

**UTC on both databases.** `UtcDateTime` is a `TypeDecorator` over `DateTime(timezone=True)`, which is `timestamptz` on PostgreSQL and text on SQLite.

- On write, a naive value raises `TypeError` (a programming error), and an aware value is converted to UTC. On SQLite the tzinfo is then dropped, so every stored value is one fixed-format UTC string. That keeps SQLite's text comparisons and the unique constraint correct: one instant is always one string.
- On read, a naive value (SQLite) gets `tzinfo=UTC`, and an aware value (PostgreSQL) goes through `.astimezone(UTC)`.

`test_datetimes_read_back_as_aware_utc` runs on both databases. `PRAGMA foreign_keys=ON` is set on every SQLite connection, so RESTRICT holds there too.

Known accepted races, rare enough not to lock for: a timezone change racing with a patient's first dose log, and an `end_date` change racing with a log for a dose after the new end. Both need two writes within milliseconds on one record, and neither duplicates a dose.

## 3. Domain functions

All pure and fully typed. Instants are aware UTC `datetime`s, and `now` is always a parameter.

```python
# app/domain/types.py
class DoseStatus(StrEnum):
    UPCOMING, DUE, MISSED, TAKEN, SKIPPED  # values as in the contract


class LogStatus(StrEnum):
    TAKEN, SKIPPED


@dataclass(frozen=True, slots=True)
class DoseRules:
    early_log_window: timedelta  # Settings.early_log_window_minutes, default 60
    late_log_limit: timedelta  # Settings.late_log_limit_minutes, default 1440


@dataclass(frozen=True, slots=True)
class ScheduleRule:
    schedule_id: UUID
    medication_id: UUID
    times_of_day: tuple[time, ...]
    days_of_week: frozenset[int]  # ISO, 1 = Monday
    start_date: date
    end_date: date | None  # inclusive; None = no end
    grace: timedelta
    medication_deactivated_at: datetime | None


@dataclass(frozen=True, slots=True)
class LoggedDose:
    dose_log_id: UUID
    schedule_id: UUID
    scheduled_for: datetime
    status: LogStatus
    recorded_at: datetime
    late: bool


@dataclass(frozen=True, slots=True)
class PlannedDose:
    schedule_id: UUID
    medication_id: UUID
    scheduled_for: datetime
    local_date: date  # local date of scheduled_for (Q1)
    local_time: str  # "HH:MM" of scheduled_for in the patient's zone
    status: DoseStatus
    late: bool
    log_window_opens_at: datetime
    log_window_closes_at: datetime
    log: LoggedDose | None  # gives dose_log_id and recorded_at


@dataclass(frozen=True, slots=True)
class ScheduleSpan:  # what the overlap rule needs
    schedule_id: UUID | None  # None while creating
    days_of_week: frozenset[int]
    start_date: date
    end_date: date | None


@dataclass(frozen=True, slots=True)
class DailySummary:
    planned: int
    taken: int
    taken_late: int
    skipped: int
    missed: int
    pending: int
    adherence_percent: Decimal | None
```

```python
# app/domain/scheduling.py
def local_today(now: datetime, tz: ZoneInfo) -> date
def local_to_utc(local_date: date, local_time: time, tz: ZoneInfo) -> datetime
def planned_doses(schedules: Sequence[ScheduleRule], logs: Sequence[LoggedDose], tz: ZoneInfo,
                  local_date: date, now: datetime, rules: DoseRules) -> list[PlannedDose]
def planned_doses_between(schedules: Sequence[ScheduleRule], logs: Sequence[LoggedDose], tz: ZoneInfo,
                          first: date, last: date, now: datetime, rules: DoseRules) -> list[PlannedDose]
def dose_status(scheduled_for: datetime, grace: timedelta, log: LoggedDose | None,
                now: datetime) -> DoseStatus
def log_window(scheduled_for: datetime, rules: DoseRules) -> tuple[datetime, datetime]
def is_late(scheduled_for: datetime, grace: timedelta, recorded_at: datetime) -> bool
def check_can_log(schedule: ScheduleRule, scheduled_for: datetime, tz: ZoneInfo,
                  now: datetime, rules: DoseRules) -> None
    # raises MedicationInactive, DoseNotPlanned, OutsideLogWindow, checked in that order
def missed_doses(doses: Iterable[PlannedDose]) -> list[PlannedDose]       # status missed, newest first
def missed_range(start: date | None, end: date | None, today: date) -> tuple[date, date]
    # defaults today−6 … today; raises InvalidField if start > end or end − start > 30 days

# app/domain/schedule_rules.py
def find_overlap(candidate: ScheduleSpan, others: Iterable[ScheduleSpan]) -> ScheduleSpan | None
def check_date_order(start_date: date, end_date: date | None) -> None               # InvalidField
def check_changes_allowed(has_logs: bool, changed_fields: frozenset[str]) -> None    # ScheduleHasLogs
def check_end_date_with_logs(new_end: date | None, today: date, last_logged: date) -> None  # InvalidField

# app/domain/adherence.py
def daily_summary(doses: Sequence[PlannedDose]) -> DailySummary
def adherence_percent(taken: int, skipped: int, missed: int) -> Decimal | None
    # Decimal(taken * 100) / denominator, quantize(Decimal("0.1"), ROUND_HALF_UP); None if denominator is 0
```

Status rules exactly as in requirements §4.2:

- A log decides `taken` or `skipped`.
- Otherwise: `now < s` → `upcoming`; `s <= now <= s + grace` → `due`; later → `missed`.
- `late` is `recorded_at > s + grace`.
- The log window is `[s − early, s + late_limit]`, closed at both ends.

**DST algorithm** (requirements §4.3, ADR-004) for patient-local date `D`:

1. For each schedule, each configured date `N ∈ {D−1, D}` that is within `start_date…end_date` and on a listed weekday, and each time `t`, compute `instant = datetime.combine(N, t, tzinfo=tz).astimezone(UTC)`. `fold=0` is the default: in a gap the pre-transition offset applies, so the dose moves forward by the gap; in an overlap this gives the first occurrence.
2. Keep the instant only if `instant.astimezone(tz).date() == D` (Q1), and, for a deactivated medication, only if `instant < deactivated_at`.
3. Deduplicate on `(schedule_id, instant)`. For example, `["01:30", "02:30"]` in London on 2027-03-28 both map to `01:30Z`, giving one dose.
4. Set `local_time = instant.astimezone(tz)` as `HH:MM`. Compute status and window from the instant, grace, log and `now`.

`N = D−1` is enough because `fold=0` never moves a time backwards, and no zone has a gap longer than 24 h. I checked every zone from 1970 to 2040: the largest gap is exactly 24 h (Kwajalein, Kanton, Kiritimati). Checked by hand with `zoneinfo`: London `01:30` on 2027-03-28 → `01:30Z`, shown as `02:30` (AC-11). London `01:30` on 2026-10-25 → `00:30Z` (AC-12).

`planned_doses_between` is `planned_doses` for each date from `first` to `last`, concatenated. Each instant has exactly one local date, so a range never contains a duplicate. `check_can_log` plans the local date of `scheduled_for` for that one schedule and requires an exact instant match.

The Test agent's acceptance tests (MT-008) import these names. If a name has to change, the change is agreed in the issue first.

## 4. Error mapping

One table in `app/errors.py` maps each `DomainError` subclass to an HTTP status, a contract `code` and a fixed title. Problem bodies contain `type`, `title`, `status`, `code`, an optional fixed `detail`, `errors[]` for validation, and `trace_id` (MT-022). They never contain submitted values, SQL, exception text or stack traces.

| Raised by | Exception | HTTP | `code` |
|---|---|---|---|
| Any service lookup | `NotFound` | 404 | `NOT_FOUND` |
| Request parsing (Pydantic, `extra="forbid"`, timezone and `HH:MM` validators) | `RequestValidationError` | 422 | `VALIDATION_ERROR`, `errors[].field` such as `timezone` or `times_of_day[0]` |
| Request parsing, errors only in path parameters (Q4) | `RequestValidationError` | 404 | `NOT_FOUND` |
| `missed_range` | `InvalidField` | 422 | `VALIDATION_ERROR` (`from`/`to`) |
| `check_date_order` | `InvalidField` | 422 | `VALIDATION_ERROR` (`end_date`) |
| `check_end_date_with_logs` | `InvalidField` | 422 | `VALIDATION_ERROR` (`end_date`) |
| `check_can_log` | `DoseNotPlanned` | 422 | `DOSE_NOT_PLANNED` |
| `check_can_log` | `OutsideLogWindow` | 422 | `OUTSIDE_LOG_WINDOW` |
| `check_can_log`; schedule create; medication `active: true` | `MedicationInactive` | 409 | `MEDICATION_INACTIVE` |
| `services.doses`: `IntegrityError` on `uq_dose_log_schedule_time` | `DuplicateDoseLog` | 409 | `DUPLICATE_DOSE_LOG` |
| `check_changes_allowed`; schedule delete with logs | `ScheduleHasLogs` | 409 | `SCHEDULE_HAS_LOGS` |
| `find_overlap` result (create and PATCH) | `ScheduleOverlap` | 409 | `SCHEDULE_OVERLAP`, `detail` = the contract example text |
| Patient timezone change with logs | `PatientHasLogs` | 409 | `PATIENT_HAS_LOGS` |
| Database unreachable: `OperationalError`, pool `TimeoutError`, `DBAPIError` with `connection_invalidated` | — | 503 | `SERVICE_UNAVAILABLE`, `Retry-After: 5` |
| Starlette routing | `HTTPException` 404 / 405 | 404 / 405 | `NOT_FOUND` / `METHOD_NOT_ALLOWED` with an `Allow` header listing every method of the path (contract change #47) |
| FastAPI body parsing: a body it can't decode at all (FastAPI raises 400) | `HTTPException` 400 | 422 | `VALIDATION_ERROR`, field `request` (the contract documents 422, never 400; found by the MT-018 contract test) |
| MT-023 fault injection | `InjectedFault` | 500 | `INTERNAL_ERROR` |
| Anything else, including any other `IntegrityError` | `Exception`, caught by `TelemetryMiddleware` (MT-022) | 500 | `INTERNAL_ERROR`; only the exception type is logged |

The `except Exception` in `TelemetryMiddleware` (app/telemetry.py) is the only broad handler in the code base. `Telemetry.dose_log_attempt` also catches broadly, but only to record the attempt's outcome, and it always re-raises. Services catch only `IntegrityError`, and only translate it when the violated constraint is `uq_dose_log_schedule_time`: `diag.constraint_name` on psycopg, the constraint's columns in the message on SQLite. Anything else is re-raised. The exact psycopg attribute gets checked against the installed version at MT-016. Every failure rolls back, because `session.begin()` exits on the exception.

## 5. Hot-path query plan

The statement count is fixed and doesn't grow with the number of medications, schedules or days. Proof: `tests/integration/test_query_counts.py` counts statements with a `before_cursor_execute` listener (confirmed present in SQLAlchemy 2.1.6) for 1 and for 4 medications.

| Endpoint | Statements | What they are |
|---|---|---|
| Day view `GET …/doses` | **3** | ① patient by id (404, timezone) ② schedules JOIN medications for the patient with `start_date <= D` and `end_date IS NULL OR end_date >= D−1` (a safe superset: the domain filters exactly) ③ dose logs `WHERE schedule_id IN (…) AND scheduled_for BETWEEN first AND last planned instant` (skipped when nothing is planned) |
| Missed doses `GET …/missed-doses` | **3** | Same three, with ② and ③ bounded by `from−1 … to`. All days are computed in memory from one fetch |
| Daily adherence `GET …/adherence/daily` | **3** | Same as the day view |
| Record dose `POST /dose-logs` | **2** | ① schedule JOIN medication JOIN patient (grace, dates, timezone, `deactivated_at`) ② INSERT; a duplicate fails here on the constraint |
| Undo `DELETE /dose-logs/{id}` | **2** | SELECT by primary key, DELETE |
| Medication list / get | **3** | ① patient (or medication) ② medications ③ their schedules (`selectinload`) with `EXISTS (SELECT 1 FROM dose_logs WHERE schedule_id = schedules.id)` as a column for `has_dose_logs` |
| Schedule create / PATCH | **3–4** | lock medication `FOR UPDATE`, sibling schedules (+ logs check on PATCH), write |

N+1 traps this avoids: lazy-loading `schedule.medication` per row (② uses a JOIN), one `has_dose_logs` query per schedule, and one query per day in the missed-dose range.

## 6. Configuration and interface

This is the stable interface for the Platform and Frontend agents, copied into `backend/README.md`. Changing anything here needs an **"Interface change"** section in the PR.

| Need | Command or endpoint |
|---|---|
| Run | `uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000` (the frontend dev proxy expects `localhost:8000`) |
| Migrate | `uv run alembic upgrade head`, a separate step. The app never migrates on start |
| Seed | `uv run python -m app.seed` (idempotent, never deletes, includes "Probe Patient"); `uv run python -m app.seed --reset` replaces all rows in one transaction (AC-41) |
| Health | `GET /healthz` → `{"status": "ok", "version": "<MEDITRACK_VERSION>"}`, never touches the database; `GET /readyz` → 200 or 503 after `SELECT 1` |
| Build args | `GIT_SHA` → `MEDITRACK_VERSION` (MT-021); `FAULT_DOSE_LOG_ERROR_RATE` → `MEDITRACK_FAULT_DOSE_LOG_ERROR_RATE` (MT-023). The `meditrack.fault=true` label is added by the Platform build step, not the Dockerfile (Q7) |

| Variable | Meaning | Default | Example |
|---|---|---|---|
| `DATABASE_URL` | SQLAlchemy URL. The conventional name is kept on purpose: hosted platforms (deployment fallback B) inject it | `sqlite:///./meditrack.db` | `postgresql+psycopg://meditrack:<password>@db:5432/meditrack` |
| `MEDITRACK_ENV` | `local`, `test`, `ci`, `dev` or `production`; becomes `deployment.environment` | `local` | `production` |
| `MEDITRACK_VERSION` | Build version for `/healthz` and `service.version` | `dev` | `3f2c1a9` |
| `MEDITRACK_EARLY_LOG_WINDOW_MINUTES` | How early a dose can be logged (requirements §4.2) | `60` | `60` |
| `MEDITRACK_LATE_LOG_LIMIT_MINUTES` | How late a dose can still be logged | `1440` | `1440` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Standard OpenTelemetry name, read by `Settings`. The exporters get `<endpoint>/v1/<signal>`, built the way the SDK builds it. Unset = telemetry not exported (MT-022) | unset | `http://otel-collector:4318` |
| `MEDITRACK_FAULT_DOSE_LOG_ERROR_RATE` | Share (0–1) of `POST /dose-logs` that return 500, for the incident drill (MT-023) | `0` | `0.5` |
| `MEDITRACK_TEST_POSTGRES_URL` | Tests only: PostgreSQL for integration tests. Unset → PostgreSQL-only tests **skip with a reason** | unset | `postgresql+psycopg://postgres:<password>@localhost:5433/postgres` |
| `MEDITRACK_REQUIRE_POSTGRES` | Tests only: `1` turns those skips into failures. CI sets it, so AC-18 can't be skipped there | unset | `1` |

No variable holds a secret by default. The deployed `DATABASE_URL` contains a password and comes from a GitHub Environment secret (security §3).

The contract fixes some numbers, so they are named constants in `app/config.py`, not settings: changing them would break the contract.

- `GRACE_PERIOD_DEFAULT_MINUTES = 60`
- `GRACE_PERIOD_MAX_MINUTES = 240`
- `MISSED_RANGE_MAX_DAYS = 31` (in `app/domain/scheduling.py`, next to the rule, so the domain needs no settings import)
- `MISSED_RANGE_DEFAULT_DAYS = 7` (same place)

## 7. Test plan

Levels follow [test-strategy.md](../docs/test-strategy.md). Every test gets its time from `FixedClock`, passed in through `create_app(settings, clock)`. Unit tests use no database. Integration tests run on SQLite by default and on PostgreSQL when `MEDITRACK_TEST_POSTGRES_URL` is set, with a fresh schema per test. AC-18 and the overlap race run on PostgreSQL only.

| AC / rule | Level | File :: test |
|---|---|---|
| AC-07 | Unit | `unit/domain/test_status.py::test_dose_before_scheduled_time_is_upcoming_ac07` |
| AC-08 | Unit | `test_status.py::test_dose_is_due_from_scheduled_time_to_end_of_grace_ac08`, `::test_dose_is_missed_one_second_after_grace_ac08` |
| §3.2 status rows, grace 0 and 240 | Unit | `test_status.py::test_status_boundary_table` (7 rows), `::test_grace_zero_is_missed_one_second_after_scheduled_time`, `::test_grace_240_is_due_until_four_hours_after` |
| AC-09 | Unit + Int | `unit/domain/test_planning.py::test_local_today_is_patient_date_not_utc_date_ac09`; `integration/test_doses_api.py::test_day_view_defaults_to_patient_local_date_ac09` |
| AC-10 | Unit | `test_planning.py::test_no_doses_outside_start_and_end_dates_ac10`, `::test_no_doses_on_excluded_weekdays_ac10`, `::test_deactivated_medication_plans_only_doses_before_deactivation_ac10` (incl. a dose exactly at `deactivated_at`) |
| AC-11 | Unit | `unit/domain/test_dst.py::test_london_gap_shifts_dose_forward_ac11`, `::test_london_gap_merges_two_times_into_one_dose_ac11` |
| AC-12 | Unit | `test_dst.py::test_london_overlap_plans_first_occurrence_once_ac12` |
| East/west of UTC (§3.3) | Unit | `test_dst.py::test_tokyo_dose_falls_on_previous_utc_day`, `::test_new_york_dose_uses_daylight_offset_in_summer` |
| Q1 | Unit | `test_dst.py::test_nuuk_saturday_2330_and_sunday_0030_are_one_dose_on_sunday` (also: Saturday's list doesn't show it), `::test_apia_skipped_day_plans_each_instant_once` (`08:00` on 30 and 31 Dec 2011 → one dose, on 31 Dec) |
| AC-39 | Unit | `unit/domain/test_dst_properties.py::test_no_schedule_plans_one_instant_twice_ac39`, `::test_existing_local_times_round_trip_ac39` (Hypothesis, all zones, 2000–2040, multi-day ranges, seed printed on failure) |
| AC-35 | Unit + CI | `unit/domain/test_planning.py::test_results_do_not_depend_on_process_timezone_ac35` (uses `time.tzset`; skipped with a reason on Windows), plus the CI matrix `TZ=UTC` / `TZ=America/Los_Angeles` (MT-031) |
| AC-15 | Unit + Int | `unit/domain/test_log_window.py::test_log_after_grace_is_late_ac15`, `::test_log_at_end_of_grace_is_not_late`; `test_doses_api.py::test_dose_logged_after_grace_is_marked_late_ac15` |
| AC-16 | Unit + Int | `test_log_window.py::test_log_more_than_an_hour_early_is_outside_window_ac16`, `::test_log_more_than_a_day_late_is_outside_window_ac16`, `::test_unplanned_instant_is_not_planned_ac16`; `test_doses_api.py::test_log_outside_window_returns_422_ac16`, `::test_log_for_unplanned_time_returns_422_ac16` |
| §3.2 log rows | Unit + Int | `test_log_window.py::test_log_window_boundary_table`; `test_doses_api.py::test_log_boundary_table` (7 rows through HTTP) |
| AC-25, AC-26, rounding | Unit + Int | `unit/domain/test_adherence.py::test_summary_counts_and_percent_ac25`, `::test_percent_is_null_with_only_upcoming_doses_ac26`, `::test_percent_rounds_half_up_not_half_even` (1 of 16 → 6.3; `round()` gives 6.2); `integration/test_reports_api.py::test_daily_adherence_endpoint_matches_summary_ac25` |
| AC-34 | Unit + Int + PG | `unit/domain/test_schedule_rules.py::test_open_ended_schedule_overlaps_later_start_ac34`, `::test_schedule_ending_day_before_does_not_overlap_ac34`, `::test_disjoint_weekdays_do_not_overlap_ac34`, `::test_mon_wed_and_tue_thu_schedules_do_not_overlap` (Q2), `::test_shared_weekday_without_common_date_does_not_overlap` (Q2), `::test_extended_end_date_overlaps_later_schedule` (Q3), `::test_cleared_end_date_overlaps_later_schedule` (Q3), `::test_schedule_does_not_overlap_itself`; `integration/test_schedules_api.py::test_overlap_rejected_then_allowed_after_ending_old_schedule_ac34` (incl. day views of 11-05 and 11-06), `::test_patch_into_overlap_rejected_ac34`, `::test_disjoint_weekday_schedules_accepted_ac34`, `::test_extending_end_date_with_logs_into_later_schedule_returns_overlap` (Q3), `::test_clearing_end_date_with_logs_before_later_schedule_returns_overlap` (Q3); `integration/test_concurrency_pg.py::test_concurrent_overlapping_schedules_one_created_ac34` |
| AC-01, AC-02, AC-13 | Unit + Int | `unit/test_schemas.py::test_unknown_or_wrong_case_timezone_rejected_ac02`; `integration/test_patients_api.py::test_created_patient_is_listed_ac01`, `::test_invalid_timezone_returns_field_error_ac02`, `::test_timezone_change_allowed_without_logs_ac13`, `::test_timezone_change_rejected_once_logged_ac13` |
| AC-03, AC-04 | Int | `integration/test_medications_api.py::test_empty_name_rejected_ac03`, `::test_new_medication_is_active_ac03`, `::test_deactivated_medication_only_listed_with_include_inactive_ac04`, `::test_reactivation_rejected` |
| AC-05 | Unit + Int | `unit/test_schemas.py::test_time_of_day_must_be_two_digit_24_hour_ac05`, `::test_duplicate_times_rejected_ac05`; `test_schedule_rules.py::test_end_before_start_rejected_ac05`; `test_schedules_api.py::test_invalid_schedule_rejected_ac05` |
| AC-06 | Unit + Int | `test_schedule_rules.py::test_only_end_date_may_change_with_logs_ac06`, `::test_end_date_not_before_today_or_last_log_ac06`; `test_schedules_api.py::test_time_or_grace_change_with_logs_rejected_ac06`, `::test_end_date_change_with_logs_ac06`, `::test_delete_with_logs_rejected_ac06`, `::test_delete_without_logs_ac06`, `::test_schedule_on_inactive_medication_rejected_ac06`, `::test_unchanged_fields_resent_with_new_end_date_accepted` (Q3) |
| AC-14, AC-17, AC-19, AC-20 | Int | `test_doses_api.py::test_logging_due_dose_shows_taken_ac14`, `::test_duplicate_log_rejected_and_original_unchanged_ac17`, `::test_logging_for_inactive_medication_rejected_ac19`, `::test_undo_restores_status_and_allows_relogging_ac20`, `::test_planned_dose_has_window_and_instructions` |
| AC-18 | Int (PG) | `test_concurrency_pg.py::test_ten_parallel_posts_create_exactly_one_log_ac18` (`asyncio.gather` over `httpx2.ASGITransport`; sync endpoints run in worker threads), `::test_constraint_blocks_second_uncommitted_insert_ac18` (two raw sessions, no app pre-check: proves the constraint does the work) |
| AC-22, AC-23, AC-24 | Unit + Int | `unit/domain/test_missed.py::test_default_range_is_today_and_six_days_before_ac22`, `::test_missed_list_is_unlogged_past_grace_newest_first_ac22`, `::test_range_over_31_days_rejected_ac23`, `::test_from_after_to_rejected_ac23`; `test_reports_api.py::test_missed_list_default_range_ac22`, `::test_invalid_range_rejected_ac23`, `::test_late_logged_dose_leaves_missed_list_ac24` |
| MT-013 schema | Int (both DBs) | `integration/test_migrations.py::test_upgrade_downgrade_upgrade`, `::test_migration_matches_models` (Alembic `compare_metadata` is empty), `::test_unique_constraint_exists`, `::test_datetimes_read_back_as_aware_utc` |
| `hide_parameters` | Int (both DBs) | `integration/test_db_privacy.py::test_database_error_log_contains_no_canary_value`: a failing INSERT with canary values, logged with its traceback; the canary is absent from the log output |
| Query counts | Int | `integration/test_query_counts.py::test_day_view_statement_count_is_constant`, `::test_reports_statement_count_is_constant`, `::test_medication_list_statement_count_is_constant` |
| Failure handling (§3.5), AC-31 | Int | `integration/test_errors.py` (existing) + `::test_malformed_id_is_not_found` (Q4), `::test_api_returns_503_when_database_is_down` |
| AC-31, AC-32 | Contract | `contract/test_contract.py::test_every_operation_conforms_to_contract_ac32`, `::test_every_error_is_problem_json_with_contract_code_ac31` (Schemathesis against the ASGI app; check its v4 API at MT-018) |
| AC-29 | Int | `integration/test_telemetry_privacy.py::test_no_canary_in_logs_spans_or_metrics_ac29` (in-memory exporters, every endpoint, success and error paths) |
| AC-37 | Int | `integration/test_trace_id.py::test_every_response_has_trace_id_header_ac37`, `::test_problem_trace_id_matches_header_and_log_records_ac37` (incl. 500 and 503) |
| AC-33, AC-41, probe | Int | `integration/test_seed.py::test_seed_counts_and_second_run_adds_nothing_ac33`, `::test_reset_replaces_every_row_ac41`, `::test_failed_reset_keeps_previous_data_ac41`, `::test_reset_twice_gives_same_counts_ac41`, `::test_probe_patient_always_has_a_dose_in_its_log_window` |
| MT-023 | Int | `integration/test_fault_injection.py::test_rate_zero_never_fails`, `::test_rate_one_always_returns_internal_error` (random source injected) |

AC-30 (data survives a restart) is the Platform agent's Compose smoke test. `tests/acceptance/**` belongs to the Test agent: I only remove its `xfail` markers.

## 8. Dependencies

| Package | Group | Task | Reason |
|---|---|---|---|
| fastapi, uvicorn[standard], pydantic-settings, sqlalchemy | runtime | MT-010 | Fixed stack; already in the scaffold |
| alembic | runtime | MT-013 | Migrations (fixed choice) |
| psycopg[binary] | runtime | MT-013 | PostgreSQL driver for `postgresql+psycopg://`; binary wheel, so the image needs no compiler or libpq headers |
| tzdata | runtime | MT-011 | IANA data as a wheel. Windows has no system zone database (verified: `ZoneInfoNotFoundError` in the current venv), and the image doesn't depend on OS timezone packages (ADR-004) |
| opentelemetry-api, -sdk, -exporter-otlp-proto-http, -instrumentation-fastapi, -instrumentation-sqlalchemy, -instrumentation-logging | runtime | MT-022 | Signals in operations §2. `-instrumentation-logging` provides the OTLP log handler, because the SDK's own `LoggingHandler` is deprecated in 1.45.1 (verified: it raises a `DeprecationWarning`) |
| pytest, ruff, mypy | dev | MT-010 | Fixed stack; already in the scaffold |
| httpx2 | dev | MT-010 | Required by `starlette.testclient` (verified: it imports `httpx2` in Starlette 1.10). Already in the scaffold |
| pytest-cov | dev | MT-011 | Coverage gate (85 % `app/domain` + `app/services`) |
| hypothesis | dev | MT-011 | AC-39 property test (required by test-strategy §3.3) |
| schemathesis | dev | MT-018 | Contract test (fixed choice) |

## 9. Changes needed in the MT-010 scaffold (PR #40)

PR #40 meets most of the bar. #40 merged without item 1, so a small follow-up PR makes it. This session makes the rest, in the task named for each:

1. Q5 rename: `APP_ENV` → `MEDITRACK_ENV`, `APP_VERSION` → `MEDITRACK_VERSION`, plus the README's explicit `--host 0.0.0.0 --port 8000`: follow-up PR `mt-010-env-prefix`.
2. MT-011: add `tzdata` (runtime), and `pytest-cov` and `hypothesis` (dev).
3. MT-013: `make_engine` gets `hide_parameters=True`. Otherwise SQLAlchemy puts bound values, such as names and notes, into exception text that can reach logs (security §2, rule 3). It also gets `PRAGMA foreign_keys=ON` for SQLite, and the canary test from §7. Add `psycopg[binary]` here too.
4. MT-014, the first task that touches `app/errors.py`: replace its two unexplained `Any`s, typing the problem body with a `TypedDict` and the location tuple as `tuple[int | str, ...]`. Same task: malformed path IDs → 404 (Q4).

## 10. Gotchas recorded for later tasks

- **MT-022, privacy.** Starlette's `ServerErrorMiddleware` re-raises after the 500 handler runs, and uvicorn then logs the traceback. Pydantic and SQLAlchemy messages can contain input fragments. So the log formatter writes only the exception type and `trace_id`, never the message. AC-29 exercises a forced 500 with canary values.
- **MT-022, X-Trace-Id on 500s.** The `Exception` handler runs in `ServerErrorMiddleware`, outside normal middleware. The header is set in the handler itself, and AC-37 tests the 500 path explicitly.
- **MT-022, database error text in spans.** When a statement fails, the SQLAlchemy instrumentation sets the span's status description to the database's message. PostgreSQL's duplicate-key message quotes the key values, which include a schedule ID. The exporter wrapper drops every status description and keeps only allowlisted attributes, on events too.
- **MT-022, semantic conventions.** The 0.66b1 instrumentations default to the old HTTP conventions: `http.server.duration` in ms, with the route template in `http.target` on metrics. Opting in to the stable ones (`OTEL_SEMCONV_STABILITY_OPT_IN=http`) renames both. The allowlists accept both sets of names, but dashboards would need the new names.
- **AC-35 on Windows.** Setting `TZ` doesn't affect Python's local time on Windows the way it does on Linux. The process-timezone test is skipped there with a reason. Linux CI is the authority.
