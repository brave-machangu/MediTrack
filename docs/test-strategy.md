# MediTrack — Test Strategy

Goal: every acceptance criterion in [acceptance-criteria.md](acceptance-criteria.md) has an automated test, the riskiest rules (time, duplicates, persistence) are tested at more than one level, and **no test depends on the real current time**.

## 1. Test levels

| Level | Tool (verify current APIs in docs) | Scope | Runs in CI |
|---|---|---|---|
| **Backend unit** | pytest | Pure functions in `app/domain/` (planned doses, status, DST, adherence) and validators. No DB, no HTTP. `FixedClock` for time. | Every backend PR |
| **Backend integration** | pytest + FastAPI `TestClient` + real database | Endpoints end to end through the service and database. SQLite for speed locally; **PostgreSQL in CI** (service container). | Every backend PR |
| **Contract** | Schema-based testing against `api/openapi.yaml` (e.g. Schemathesis — confirm its current Python API) plus targeted response-schema assertions | Backend responses and errors match the contract | Every backend or contract PR |
| **Frontend unit/component** | Vitest + React Testing Library + MSW | Components and pages with mocked API responses from contract examples; accessibility with an axe-based matcher | Every frontend PR |
| **End-to-end smoke** | Script or Playwright against Docker Compose | `/readyz`, create patient → medication → schedule → log dose → see it taken; restart backend → data still there | Every PR (Compose job) and after each deploy |
| **Operational** | Probe and drill scripts (Platform agent) | Alert fires on injected faults; responder rolls back | Manual drill + recorded evidence (phase 3) |

## 2. Time control

- Backend: `Clock` protocol with `SystemClock` and `FixedClock`. Injected through FastAPI dependency overrides in tests. Domain functions take `now` as a parameter.
- Frontend: the backend's `generated_at` and statuses are the source of truth; the UI does not compute dose status. Where the UI shows relative time, tests use Vitest fake timers.
- Lint rule / review check: no `datetime.now()`, `datetime.utcnow()` or `date.today()` outside `clock.py`.
- **Process timezone must not matter (AC-35):** CI runs the backend suite twice, with `TZ=UTC` and `TZ=America/Los_Angeles`; the frontend test script sets `TZ=Asia/Tokyo` so any accidental use of the browser timezone fails a test.

## 3. Focus areas

### 3.1 Duplicate-dose prevention (AC-17, AC-18, AC-21)

| Test | Level |
|---|---|
| Second POST for same dose → 409, original row unchanged | Integration |
| 10 concurrent POSTs → exactly one 201, nine 409, one row | Integration on **PostgreSQL** (threads or async client) |
| Unique constraint exists in the Alembic migration (inspect schema) | Integration |
| Double tap on **Taken** sends one request; 409 shows "Already recorded" | Frontend |
| Undo then re-log succeeds | Integration + Frontend |
| Overlapping schedules for one medication → 409 `SCHEDULE_OVERLAP` (create and PATCH); end-today + start-tomorrow accepted; disjoint weekdays accepted (AC-34) | Unit (overlap function) + Integration |

### 3.2 Missed-dose timing (AC-07, AC-08, AC-15, AC-16, AC-22, AC-24)

Boundary table, schedule 08:00 local, grace 60, `Africa/Harare`:

| Clock (local) | No log → status | Log now → result |
|---|---|---|
| 06:59:59 | upcoming | 422 OUTSIDE_LOG_WINDOW |
| 07:00:00 | upcoming | 201, late=false |
| 08:00:00 | due | 201, late=false |
| 09:00:00 | due | 201, late=false |
| 09:00:01 | missed | 201, late=true |
| next day 08:00:00 | missed | 201, late=true |
| next day 08:00:01 | missed | 422 OUTSIDE_LOG_WINDOW |

Also: grace 0 (missed one second after scheduled time) and grace 240.

### 3.3 Timezone handling (AC-09, AC-11, AC-12, AC-13)

- Patient-local "today" differs from UTC date (late evening UTC, early morning local).
- `Europe/London` spring-forward gap and autumn overlap (dates in acceptance criteria).
- A patient east of UTC (`Asia/Tokyo`) and west (`America/New_York`) produce correct UTC instants.
- Timezone change is accepted with no logs and rejected with 409 `PATIENT_HAS_LOGS` once logs exist.
- Invalid timezone rejected.
- **Property-based test (required, AC-39):** Hypothesis over random IANA zones, dates 2000–2040 and times; no duplicate `scheduled_for` per schedule, and existing local times round-trip. Print the seed on failure.
- **TZ matrix (AC-35):** same suite under two process timezones (see §2).

### 3.4 Database persistence (AC-30, AC-33)

- Alembic: `upgrade head` on an empty database, then `downgrade -1` and `upgrade head` again, on SQLite and PostgreSQL.
- Datetimes read back from both databases are timezone-aware UTC.
- Compose smoke: create data → `docker compose restart backend` → data still returned.
- Seed script is idempotent (run twice, same row counts).

### 3.5 Failure handling

| Failure | Expected behaviour | Test |
|---|---|---|
| Database unreachable | `/readyz` → 503; API → 503 `SERVICE_UNAVAILABLE` problem+json with `trace_id`; no stack trace in body | Integration (stop DB or inject failing session) |
| Unhandled exception | 500 `INTERNAL_ERROR` + `trace_id`; error logged with the same trace ID | Integration |
| Invalid input | 422 `VALIDATION_ERROR` with field errors | Integration |
| Unknown IDs | 404 `NOT_FOUND` | Integration |
| Network error / 5xx in UI | Clear message with **Retry**; dose not shown as taken | Frontend |
| 409 / 422 in UI | Friendly message mapped from `code` | Frontend |
| Build-time fault injection (`FAULT_DOSE_LOG_ERROR_RATE`, MT-023) | Configured share of `POST /dose-logs` return 500 `INTERNAL_ERROR`; default 0; faulty images are labelled and refused by the production deploy; the drill runs on dev | Integration |

Also: the UI never shows a dose as taken without server confirmation (AC-36), and every response carries `X-Trace-Id` matching the problem body and the log records of that request (AC-37).

### 3.6 Telemetry privacy (AC-29)

In-memory OTel exporters capture spans, metrics and log records during an integration run that uses canary strings; the test fails if any canary appears.

### 3.7 Safety copy check

All user-facing strings live in `frontend/src/copy.ts`. A test (AC-38) fails if any string matches, case-insensitively: `take (it|them|the dose|your dose)? ?(now|as soon as)`, `double`, `extra dose`, `make up for`, `catch up`, `skip the next`, `wait until`, `should take`, `you need to take`. "Skipped"/"Skip" is allowed only as the label for recording a skipped dose. Changes to `copy.ts` need Lead review.

### 3.8 Responder agent (OPS-10, OPS-12 – OPS-15)

| Test | Level |
|---|---|
| Every decision rule in operations.md §6.1 step 3, as a table test (each condition true/false) | Unit |
| `dry_run` performs no dispatch, no PR and no issue writes beyond the report | Unit |
| Evidence collector issues only allowlisted query templates (snapshot of rendered queries) and caps the packet size | Unit |
| Agent output that is not valid JSON or fails `response.schema.json` → escalate, nothing executed | Unit |
| Proposals outside the policy (prod deploy, migration or workflow edits, secret access) are always denied | Unit |
| Full drill: faulty release → alert → rollback → incident issue (OPS-07, OPS-08) | Manual drill, recorded |

## 4. Coverage and quality gates

- Backend: line coverage ≥ 85% for `app/domain/` and `app/services/`; reported, not gamed. Branch coverage ≥ 95% for `app/domain/` (time and status rules are where boundary bugs hide).
- Frontend: every page has at least one render test and one error-state test.
- Mutation-style spot check (manual, see workflow §8): break a rule on purpose and confirm a test fails.

## 5. Test data

- Synthetic only. Names like "Demo Patient A", medications like "Demo Med Alpha".
- Fixtures build objects through factory helpers; no shared mutable state between tests.
- Each integration test runs in a transaction that is rolled back, or on a fresh database.

## 6. Flaky tests

No `sleep`-based waits (poll with a deadline instead) and no automatic CI retries that hide flakes. A flaky test gets an issue within a day; it may be marked `quarantine` only with Lead approval, and quarantined tests still run and report.
