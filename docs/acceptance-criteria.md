# MediTrack — Acceptance Criteria

Every criterion is testable and maps to a requirement in [requirements.md](requirements.md). The **Test level** column says where the automated check lives (see [test-strategy.md](test-strategy.md)). A backlog task is done only when its listed criteria pass in CI.

Unless stated otherwise, examples use a patient in `Africa/Harare` (UTC+2, no DST), a schedule at `08:00` every day, a grace period of 60 minutes, and a fixed test clock.

## Patients, medications, schedules

| ID | Req | Given / When / Then | Test level |
|---|---|---|---|
| AC-01 | FR-01 | When I `POST /api/v1/patients` with a valid name and timezone, I get **201** and the patient appears in `GET /api/v1/patients`. | Integration |
| AC-02 | FR-01 | When the timezone is not a valid IANA name (e.g. `Mars/Base`), I get **422** with `code = VALIDATION_ERROR` and `errors[0].field = timezone`. | Unit + Integration |
| AC-03 | FR-02 | When I add a medication with an empty `name`, I get **422**. With valid data I get **201** and `active = true`. | Integration |
| AC-04 | FR-02 | Given an active medication, when I PATCH `active: false`, then `deactivated_at` is set, it disappears from the default list, and it appears with `include_inactive=true`. | Integration |
| AC-05 | FR-03 | Times must match `HH:MM` (24 h). `25:00`, `8:00` and duplicates are rejected with **422**. `end_date` before `start_date` is rejected with **422**. | Unit + Integration |
| AC-06 | FR-03 | Given a schedule with at least one dose log: PATCH of `times_of_day` or `grace_period_minutes` returns **409** `SCHEDULE_HAS_LOGS`; PATCH of `end_date` to a date on/after today and the last logged date returns **200**; an earlier `end_date` returns **422**; DELETE returns **409**. Without logs, DELETE returns **204**. Adding a schedule to an inactive medication returns **409** `MEDICATION_INACTIVE`. | Integration |
| AC-34 | FR-03 | **No overlap:** given schedule A (daily, `08:00`, from `2026-11-01`, no end), creating schedule B (daily, `09:00`, from `2026-11-05`) returns **409** `SCHEDULE_OVERLAP`. After PATCH A `end_date = 2026-11-05`, creating B from `2026-11-06` returns **201**; the day view for 2026-11-05 shows only A's 08:00 and for 2026-11-06 only B's 09:00. Schedules on disjoint weekdays (Mon–Fri `08:00`, Sat–Sun `10:00`) with the same dates are both accepted. In the UI, a 409 `SCHEDULE_OVERLAP` shows "This medication already has a schedule on those days. End the current schedule first; the new one can start the next day." next to the form, and the "change schedule" form defaults the new start date to the day after the old end date. | Unit + Integration + Frontend |

## Planned doses and status

| ID | Req | Given / When / Then | Test level |
|---|---|---|---|
| AC-07 | FR-04 | Given clock `2026-11-02T05:30:00Z` (07:30 local), the 08:00 dose for `2026-11-02` has `scheduled_for = 2026-11-02T06:00:00Z` and status **upcoming**. | Unit |
| AC-08 | FR-04 | At 08:00 and at 09:00 local exactly, status is **due**. At 09:00:01 local, status is **missed**. | Unit |
| AC-09 | FR-04 | `GET /patients/{id}/doses` with no `date` uses the **patient's** local date, not the server's. Test: server clock `2026-11-01T23:30:00Z` → patient date `2026-11-02`. | Unit + Integration |
| AC-10 | FR-04 | Schedules outside `start_date`/`end_date` or on excluded weekdays produce no planned doses. For a deactivated medication, only doses with `scheduled_for < deactivated_at` are planned. | Unit |
| AC-11 | FR-04 | **DST gap:** patient in `Europe/London`, schedule `01:30`, date `2027-03-28` (clocks go 01:00→02:00) → one dose at `2027-03-28T01:30:00Z`, `local_time = 02:30`. A schedule with `["01:30", "02:30"]` that day produces **one** dose, not two. | Unit |
| AC-12 | FR-04 | **DST overlap:** patient in `Europe/London`, schedule `01:30`, date `2026-10-25` → exactly one dose, at the first occurrence (`2026-10-25T00:30:00Z`). | Unit |
| AC-13 | FR-01 | Changing a patient's timezone succeeds (**200**) while the patient has no dose logs, and returns **409** `PATIENT_HAS_LOGS` once any dose log exists. | Integration |

## Recording doses

| ID | Req | Given / When / Then | Test level |
|---|---|---|---|
| AC-14 | FR-05 | Given a **due** dose, when I POST a dose log with `status = taken`, I get **201**, `late = false`, and the dose shows **taken** in the day view. | Integration + Frontend |
| AC-15 | FR-05 | Logging at 09:30 local (after grace) gives `late = true` and the dose shows **taken** with a "late" label. | Unit + Integration |
| AC-16 | FR-05 | Logging more than 60 min early or more than 24 h late returns **422** `OUTSIDE_LOG_WINDOW`. Logging a `scheduled_for` that is not a planned time returns **422** `DOSE_NOT_PLANNED`. | Unit + Integration |
| AC-17 | FR-06 | **Duplicate:** a second POST for the same `schedule_id` + `scheduled_for` returns **409** `DUPLICATE_DOSE_LOG`, and the first log is unchanged (same id, status, recorded_at). | Integration |
| AC-18 | FR-06 | **Concurrent duplicate:** 10 parallel POSTs for the same dose produce exactly one **201** and nine **409**, and exactly one row in the database. Runs against PostgreSQL. | Integration (Postgres) |
| AC-19 | FR-05 | Logging a dose for an inactive medication returns **409** `MEDICATION_INACTIVE`. | Integration |
| AC-20 | FR-07 | Deleting a dose log returns **204**; the dose goes back to its time-based status; the same dose can be logged again. | Integration + Frontend |
| AC-21 | FR-05 | In the UI, tapping **Taken** disables both buttons until the request finishes, so a double tap sends one request. A 409 response shows "Already recorded" and refreshes the list instead of an error. | Frontend |

## Missed doses and adherence

| ID | Req | Given / When / Then | Test level |
|---|---|---|---|
| AC-22 | FR-08 | Missed-dose list with no dates covers today and the previous 6 local days, newest first, and contains only unlogged doses past grace. | Unit + Integration |
| AC-23 | FR-08 | A range covering more than 31 days (`to − from > 30` days, both inclusive), or `from` after `to`, returns **422**. | Integration |
| AC-24 | FR-08 | After a missed dose is logged late, it no longer appears in the missed list. | Integration |
| AC-25 | FR-09 | Given 4 planned (2 taken incl. 1 late, 1 skipped, 1 missed), the summary is `planned 4, taken 2, taken_late 1, skipped 1, missed 1, pending 0, adherence_percent 50.0`. | Unit |
| AC-26 | FR-09 | Given only upcoming doses, `adherence_percent` is `null` and the UI shows "No doses to score yet". | Unit + Frontend |

## Cross-cutting

| ID | Req | Given / When / Then | Test level |
|---|---|---|---|
| AC-27 | FR-11 | Every page shows the disclaimer text from requirements §3. | Frontend |
| AC-28 | NFR-01 | Dose status is shown with text and an icon, not colour only. Taken/Skipped buttons are at least 44×44 px and reachable by keyboard. Automated axe check reports no serious or critical violations on the Today page. | Frontend |
| AC-29 | NFR-04 | Telemetry privacy test: after exercising every endpoint with known synthetic values (e.g. medication name `PRIVACY-CANARY-MED`, note `PRIVACY-CANARY-NOTE`), none of these strings appear in captured log records, span attributes or metric labels. | Integration |
| AC-30 | NFR-05 | Data created through the API is still there after `docker compose restart backend`. | Integration (Compose smoke) |
| AC-31 | All | Every error response has `Content-Type: application/problem+json` and a `code` from the contract. | Contract |
| AC-32 | All | The running backend conforms to `api/openapi.yaml` (contract test passes with no schema violations). | Contract |
| AC-33 | FR-10 | `make seed` (or the documented equivalent) loads 2 synthetic patients, 4 medications and 7 days of mixed history; running it twice does not create duplicates. | Integration |
| AC-35 | NFR-09 | The backend test suite gives identical results under process `TZ=UTC` and `TZ=America/Los_Angeles` (CI matrix). Frontend tests run with `TZ=Asia/Tokyo` and, for a patient in `America/New_York`, show New York local dates and times. | Unit + Frontend |
| AC-36 | NFR-08 | When **Taken** gets a 5xx, a network error or a timeout, the dose is **not** shown as taken; the card shows a **Retry** button and the support reference (`X-Trace-Id`). If the retry gets 409 `DUPLICATE_DOSE_LOG` for the same dose, the list refreshes and shows the dose as recorded, not an error. | Frontend |
| AC-37 | NFR-10 | Every API response (success and error) has an `X-Trace-Id` header of 32 lowercase hex characters; for errors it equals the body's `trace_id`, and every log record written while handling the request carries the same `trace_id`. | Integration |
| AC-38 | FR-11 | An automated scan of all UI copy (`frontend/src/copy.ts`) finds none of the banned phrases listed in [test-strategy.md §3.7](test-strategy.md#37-safety-copy-check); missed-dose screens say only that no dose was recorded, plus the disclaimer. | Frontend |
| AC-39 | FR-04 | Property-based test over random IANA timezones, dates from 2000 to 2040 and schedule times: no schedule ever produces two planned doses with the same `scheduled_for`, and every local time that exists on that date converts back to itself. | Unit |
| AC-40 | FR-13 | Every page shows the demo banner text from FR-13, and it is reachable by screen readers (landmark or `role="note"`). | Frontend |
| AC-41 | FR-14 | `python -m app.seed --reset` replaces all patients, medications, schedules and dose logs with the synthetic seed in one transaction: after it runs, row counts equal the seed's, no earlier row remains, and a failure part-way leaves the previous data intact. Running it twice gives the same result. | Integration |
| AC-42 | FR-09 | `adherence_percent` rounds half-up: 1 taken + 15 missed → `6.3` (not `6.2`); 2 taken + 1 skipped → `66.7`. | Unit |

Operational criteria (deployment, CI/CD, alerting, responder agent) are in [operations.md](operations.md#8-operational-acceptance-criteria).
