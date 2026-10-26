# MediTrack — Product Requirements

Status: **v1.0 — approved by the Lead on 2026-10-26 (MT-001)**
Owner: Lead (Brave)

## 1. Problem

Older adults who take several medications a day often forget doses or take a dose twice. Caregivers (family members, home nurses) usually can't see what was taken until something goes wrong. Paper charts and phone alarms don't give a shared, reviewable record.

MediTrack gives the patient and the caregiver one shared record of the medication schedule, the doses reported as taken or skipped, and the doses that were missed.

## 2. Target users

| Persona | Description | Main needs |
|---|---|---|
| **Caregiver** (primary user) | Family member or home nurse who manages medications for 1–5 people | Set up schedules, see missed doses, review daily adherence |
| **Patient** (secondary user) | Older adult, possibly with low vision or limited tech experience | A simple "Today" screen, one tap to mark a dose taken or skipped, undo a mistake |

## 3. Product boundaries (what MediTrack does NOT do)

- It records **user-reported** activity only. It does not verify that a dose was physically swallowed.
- It does not prescribe, change dosages, check drug interactions, or recommend what to do after a missed dose.
- It is not a medical device. The UI shows a permanent notice: *"MediTrack records what you report. It does not give medical advice. Contact your pharmacist or doctor about missed doses."*
- Demonstrations use **synthetic data only**.

## 4. Domain model and rules

### 4.1 Entities

| Entity | Key fields |
|---|---|
| **Patient** | `id`, `display_name`, `timezone` (IANA name, e.g. `Africa/Harare`), `created_at` |
| **Medication** | `id`, `patient_id`, `name`, `dosage_label` (free text shown to the user, e.g. "500 mg, 1 tablet"), `instructions` (optional), `active`, `deactivated_at` (UTC, set when deactivated) |
| **Schedule** | `id`, `medication_id`, `times_of_day` (list of local `HH:MM`), `days_of_week` (ISO 1=Mon … 7=Sun), `start_date`, `end_date` (optional), `grace_period_minutes` |
| **DoseLog** | `id`, `schedule_id`, `scheduled_for` (UTC instant), `status` (`taken` or `skipped`), `recorded_at` (UTC), `late` (bool), `note` (optional) |
| **PlannedDose** (computed, not stored) | `schedule_id`, `medication_id`, `scheduled_for`, `local_time`, `status`, `dose_log_id` |

Dosage is stored as a display label only. MediTrack never calculates or changes amounts.

### 4.2 Dose status rules

All times are compared in UTC. `now` comes from an injectable clock so the rules are testable.

Constants (configurable, defaults shown):

| Name | Default | Meaning |
|---|---|---|
| `grace_period_minutes` | 60 (per schedule, allowed 0–240) | Time after the scheduled time before an unlogged dose counts as missed |
| `EARLY_LOG_WINDOW_MINUTES` | 60 | How early a dose can be logged before its scheduled time |
| `LATE_LOG_LIMIT_MINUTES` | 1440 (24 h) | How late a dose can still be logged |

Status of a planned dose:

| Status | Condition |
|---|---|
| `upcoming` | No log and `now < scheduled_for` |
| `due` | No log and `scheduled_for <= now <= scheduled_for + grace` |
| `missed` | No log and `now > scheduled_for + grace` |
| `taken` | A log with `status = taken` exists |
| `skipped` | A log with `status = skipped` exists |

- A log is `late = true` when `recorded_at > scheduled_for + grace`.
- A dose that was `missed` and is then logged (within the late limit) becomes `taken` or `skipped`. The missed-dose list only shows doses that are currently unlogged.
- **Duplicate prevention:** at most one DoseLog per (`schedule_id`, `scheduled_for`). A second attempt returns **409 Conflict** and leaves the first log unchanged. This is enforced by a database unique constraint, not only by application code.
- Logging is rejected with **422** when `scheduled_for` is not a real planned dose of that schedule, or when `now` is outside the **log window** `[scheduled_for − EARLY_LOG_WINDOW, scheduled_for + LATE_LOG_LIMIT]`. Each planned dose returns `log_window_opens_at` and `log_window_closes_at` so the UI can show or hide the buttons without computing rules itself.
- **Undo:** a DoseLog can be deleted (to fix a mis-tap). The dose returns to its time-based status.

### 4.3 Timezone rules

- Schedule times are **local times in the patient's timezone**. Planned doses are stored and returned as UTC instants plus the local time for display.
- "Today" and daily summaries use the **patient's** local calendar day, not the server's or the browser's.
- Local times are converted to UTC using the UTC offset in effect **before** any DST transition (Python `zoneinfo` with `fold=0`). This gives one rule for both cases:
  - **DST gap** (local time doesn't exist): the dose shifts forward by the length of the gap. Example: `Europe/London`, 2027-03-28, `01:30` → `01:30Z`, shown as local `02:30`.
  - **DST overlap** (local time happens twice): the dose is planned once, at the first occurrence.
- If two times of the **same schedule** convert to the same UTC instant (possible in a DST gap), only one planned dose is produced.
- **Timezone changes:** because planned doses are computed on read (ADR-002), a patient's timezone can only be changed while the patient has **no dose logs**. Otherwise the request returns **409** `PATIENT_HAS_LOGS`. Known v1 limitation; a timezone history is a later improvement.

### 4.4 Changing schedules and medications

- A schedule with **no** dose logs can be edited freely or deleted.
- A schedule **with** dose logs can only change `end_date`. Changing any other field, or deleting it, returns **409** (`SCHEDULE_HAS_LOGS`). To change times or the grace period, set the old schedule's `end_date` and create a new one starting the next day. This keeps past statuses and stored `late` flags consistent.
- **No overlapping schedules for one medication.** Two schedules of the same medication may not have overlapping date ranges (open `end_date` = no end) on a shared weekday; creating or editing a schedule that would overlap returns **409** `SCHEDULE_OVERLAP`. Without this rule, ending a schedule today and starting its replacement today would put both on today's list (for example 08:00, already taken, plus a new 09:00), inviting a double dose. Consequences: a schedule change always takes effect from the next day (the UI defaults the new start date to the old end date + 1); different times on the same days belong in **one** schedule; disjoint weekday schedules (e.g. Mon–Fri 08:00 and Sat–Sun 10:00) are allowed.
- The new `end_date` of a schedule with logs must be on or after both the patient's local today and the local date of its latest dose log; otherwise **422** `VALIDATION_ERROR`. This prevents hiding recorded doses.
- Deactivating a medication sets `deactivated_at`. Only doses with `scheduled_for < deactivated_at` are planned, so nothing after deactivation can turn into a missed dose. Deactivation is one-way in v1 (to restart a medication, add it again). Past logs and past days stay visible. Doses can't be logged for an inactive medication, and schedules can't be added to it (**409** `MEDICATION_INACTIVE`).
- Nothing is hard-deleted except schedules without logs and dose logs (undo).

### 4.5 Daily adherence summary

For a patient and a local date:

- Counts: `planned`, `taken`, `taken_late`, `skipped`, `missed`, `pending` (`upcoming` + `due`).
- `adherence_percent = taken / (taken + skipped + missed) × 100`, rounded **half-up** to 1 decimal place (computed with `decimal.Decimal`; Python's `round()` rounds half to even). Example: 1 taken of 16 → 6.25 → **6.3**. Late doses count as taken.
- If `taken + skipped + missed = 0`, `adherence_percent` is `null` (the UI shows "No doses to score yet").

## 5. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Create, view, and edit patients (name, timezone) | P0 |
| FR-02 | Add, edit, and deactivate medications for a patient | P0 |
| FR-03 | Add, edit, end and remove schedules (times, days, start/end date, grace period), following §4.4 | P0 |
| FR-04 | Show a patient's planned doses for a local date with their status | P0 |
| FR-05 | Record a dose as taken or skipped, with an optional note | P0 |
| FR-06 | Prevent duplicate dose records | P0 |
| FR-07 | Undo a dose record | P1 |
| FR-08 | List missed doses for a date range (default: last 7 days) | P0 |
| FR-09 | Show the daily adherence summary for a local date | P0 |
| FR-10 | Load a synthetic demo data set with one command | P1 |
| FR-11 | Show the medical-advice disclaimer on every page | P0 |
| FR-12 | User accounts and sign-in | P2 (not in v1, decision D1) |
| FR-13 | Show a demo banner on every page: "Demo with synthetic data. Don't enter real health information. Data resets every night." | P0 |
| FR-14 | Reset the dev and prod demo data to the synthetic seed on every deploy and every night | P0 |

## 6. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 Accessibility | WCAG 2.1 AA target: body text ≥ 18 px, touch targets ≥ 44×44 px, full keyboard use, status never shown by colour alone |
| NFR-02 Performance | p95 latency < 300 ms for `POST /dose-logs` and `GET /patients/{id}/doses` at demo load |
| NFR-03 Reliability | Dose-recording success rate ≥ 99% (non-5xx) over 1 hour; this is the SLI the alert is based on |
| NFR-04 Privacy | No medication names, patient names, notes, or credentials in logs, metrics, traces, or alert payloads |
| NFR-05 Persistence | Data survives container restarts (named volume locally, managed PostgreSQL when deployed) |
| NFR-06 Portability | Runs locally with one command; the same images run in deployment |
| NFR-07 Testability | All time-based logic takes an injectable clock; no test depends on the real current time |
| NFR-08 Truthful recording UI | The UI never shows a dose as taken or skipped unless the server confirmed it (201, or 409 for the same dose). No optimistic success state for dose recording |
| NFR-09 Timezone independence | Results do not depend on the server's or the browser's timezone; backend tests run under two process `TZ` values and frontend tests under a non-UTC `TZ` |
| NFR-10 Correlation | Every API response carries `X-Trace-Id`; logs, spans and metric exemplars for that request share the same trace ID |

## 7. Out of scope for v1

Push/SMS notifications, multiple caregivers sharing a patient, pharmacy integration, refill tracking, native mobile apps, AI features in the product itself.

## 8. Decisions

Recorded by the Lead in MT-001 on 2026-10-26.

| # | Decision | Outcome | Status |
|---|---|---|---|
| D1 | Authentication in v1 | **No accounts in v1.** The public demo holds synthetic data only and is **reset to the synthetic seed on every deploy and nightly** (FR-14). Every page warns not to enter real health information (FR-13). *Later option, not v1:* a private demo workspace per visitor (random token in an `HttpOnly` cookie, no email or password), or full accounts (FR-12). Deferred because it touches every endpoint. | **Decided** |
| D2 | Hosting | **One small Linux VM running Docker Compose**, with dev and prod as two Compose projects. Provider: **AWS Lightsail, 4 GB bundle** (2 vCPU, 4 GB RAM, 80 GB SSD, $24/month with IPv4), paid from the new-account credit during the course. Credit terms and the billing-alarm step: [architecture.md §6.1](architecture.md#61-price-check-2026-10-26). Fallback: hosted platform + managed PostgreSQL. | **Decided** |
| D3 | Telemetry backend when deployed | Follows D2: **the same Grafana stack on the VM**, with Grafana behind a login and not publicly writable ([operations.md §3](operations.md#3-telemetry-backend)) | **Decided** |
| D4 | Investigation agent | **Approved with limits:** headless Claude Code with the **pinned model `claude-sonnet-5-5`**. The API key lives in a dedicated workspace with a **hard spend limit of $20/month** and is stored only as a `responder` environment secret. It starts in **report-only mode** (findings on the incident issue, no branch or PR); PR mode is switched on by the Lead only after the drill works. It never merges, deploys or sees production secrets. If the drill shows weak investigations, the Lead switches the pin to `claude-opus-5-5` by PR. Expected cost per run: [operations.md §6.5](operations.md#65-cost-per-investigation-run) | **Decided** |
| D5 | Schedule overlap rule (§4.4) | **Adopted.** AC-34; `SCHEDULE_OVERLAP` in the contract (with example) and in the frontend error messages | **Decided** |
