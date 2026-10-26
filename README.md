# MediTrack

A medication reminder and adherence tracker for older adults and the people who care for them.

> **Status: Phase 1 — build starting.** The specification (requirements, API contract, agent team, backlog) was approved on 2026-10-26; the application isn't built yet. This is the final project for the [DataTalksClub AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp).

> MediTrack records what you report. It does not give medical advice. Contact your pharmacist or doctor about missed doses.

## The problem

Older adults who take several medications a day often forget a dose or take one twice. Caregivers (family members, home nurses) usually can't see what was taken until something goes wrong. Paper charts and phone alarms don't give a shared record that both people can check.

## Who it's for

- **Caregivers** who manage medications for one to five people and need to spot missed doses quickly.
- **Patients** who need one simple screen showing what to take today, with a big button to mark each dose taken.

## What it does

- Set up medications and schedules (times of day, days of the week, start and end dates, grace period).
- Show today's doses for a patient, in the **patient's** timezone, with a clear status: upcoming, due, missed, taken, taken late or skipped.
- Record a dose as taken or skipped with one tap, and undo a mistake.
- Prevent the same dose being recorded twice, even with a double tap or two devices at once.
- List missed doses for the last 7 days.
- Show a daily adherence summary: doses taken ÷ (taken + skipped + missed).

Full rules: [docs/requirements.md](docs/requirements.md). Testable criteria: [docs/acceptance-criteria.md](docs/acceptance-criteria.md).

## What it doesn't do

- It doesn't verify that a dose was actually swallowed. It records what users report.
- It doesn't prescribe, change dosages, check interactions, or say what to do after a missed dose.
- v1 has **no user accounts** (decision D1). The public demo holds synthetic data only and is reset on every deploy and every night. **Don't enter real health information.**
- No push or SMS notifications in v1.

## Architecture

React + TypeScript (Vite) frontend → FastAPI backend → PostgreSQL, all in Docker Compose. OpenTelemetry sends correlated traces, metrics and logs to Grafana. A user-impact alert on failed dose recordings wakes a bounded responder agent that can roll back a bad release.

Details and decisions: [docs/architecture.md](docs/architecture.md) · API contract: [api/openapi.yaml](api/openapi.yaml)

## How it's built: spec-first, with an AI agent team

| Role | Owns |
|---|---|
| Lead (human) | Requirements, contract, backlog, approvals, merges, production deploys |
| Spec agent | Docs, contract and backlog drafts (by PR) |
| Frontend agent | `frontend/` — [prompt](prompts/frontend-agent.md) + [Excellence edition](prompts/frontend-agent-excellence.md) from MT-020 |
| Backend agent | `backend/` — [prompt](prompts/backend-agent.md) + [Excellence edition](prompts/backend-agent-excellence.md) from MT-011 |
| Reviewer agent | Independent review of every PR — [prompt](prompts/reviewer-agent.md) |
| Test agent | Writes acceptance tests for the riskiest rules *before* they are implemented — [prompt](prompts/test-agent.md) |
| Platform agent (later) | Docker Compose, CI/CD, observability |
| Responder agent (runtime) | Reacts to the alert; one bounded action |

The frontend and backend agents work in parallel against the same OpenAPI contract. Rules for agents: [AGENTS.md](AGENTS.md) · Team and process: [docs/agent-team.md](docs/agent-team.md) · Workflow and review: [docs/development-workflow.md](docs/development-workflow.md)

## Project board

Backlog: [backlog/tasks.md](backlog/tasks.md) (source: [backlog/backlog.json](backlog/backlog.json)).

**Public project board: <https://github.com/users/brave-machangu/projects/1>**

Every backlog task is a [GitHub issue](https://github.com/brave-machangu/MediTrack/issues) on the board, labelled by role, priority and phase, with its dependencies linked. Spec questions and contract-change issues go on the board too.

Keeping it in sync:

```bash
python3 scripts/render_backlog.py                                   # after editing backlog/backlog.json
python3 scripts/create_backlog.py --repo brave-machangu/MediTrack   # creates issues for new tasks and adds them to the board
python3 scripts/create_backlog.py --repo brave-machangu/MediTrack --update   # also refreshes existing issue bodies
```

The board steps need a `gh` token with the `project` scope (`gh auth refresh -s project`).

## Running locally

*Not available yet.* When phase 2 is done (task MT-030), the whole system — frontend, backend, database and observability — will start with:

```bash
make up          # docker compose up --build
make seed        # load synthetic demo data
make test        # run all tests
```

Requirements will be Docker with Docker Compose, plus `uv` (Python) and Node.js for running tests outside containers.

## Testing

Unit, integration (PostgreSQL), contract, frontend component and end-to-end smoke tests. Focus areas: duplicate-dose prevention, missed-dose timing, timezones and DST, persistence, and failure handling. See [docs/test-strategy.md](docs/test-strategy.md).

## Deployment, monitoring and on-call

- CI on every PR; merge to `main` auto-deploys to **dev**; **production** needs manual approval.
- Rollback = redeploy the previous image (tagged by Git SHA), automatically or by the responder agent.
- Alert: dose recording error rate > 5% over 5 minutes.
- On-call: the responder restores service with a rule-based rollback (no model involved). Then an investigation agent (a headless coding agent with read-only evidence) finds the cause and, for a code defect, opens a fix PR with a failing-then-passing test. A person always merges.

Details: [docs/operations.md](docs/operations.md) · Security and privacy: [docs/security.md](docs/security.md)

Hosting is one small VM running Docker Compose for dev and prod, with the Grafana stack on the same VM. Provider: AWS Lightsail 4 GB (US$24/month); credit terms and the billing alarm are in [docs/architecture.md §6.1](docs/architecture.md#61-price-check-2026-10-26). MT-033 creates it.

## Decisions

Recorded in MT-001 (2026-10-26):

| # | Decision | Outcome |
|---|---|---|
| D1 | Accounts in v1 | No accounts. Demo data resets to the synthetic seed on every deploy and nightly, and every page warns not to enter real health data. A per-visitor private workspace is a later option. |
| D2 | Hosting | One small Linux VM running Docker Compose (dev and prod as two projects); hosted platform + managed PostgreSQL as fallback. Provider: AWS Lightsail 4 GB (US$24/month); credit terms and billing alarm in [§6.1](docs/architecture.md#61-price-check-2026-10-26). |
| D3 | Deployed telemetry | The same Grafana stack on the VM, behind a login |
| D4 | Investigation agent | Approved with limits: model pinned to `claude-sonnet-5-5` (Opus 5.5 if its investigations are weak), key with a US$20/month spend limit stored only as a secret, report-only mode until the drill works, never merges, deploys or sees production secrets. Cost per run in [operations §6.5](docs/operations.md#65-cost-per-investigation-run). |
| D5 | Schedule overlap rule | Adopted: no two schedules of one medication on the same weekday and dates (`SCHEDULE_OVERLAP`) |

Details: [docs/requirements.md §8](docs/requirements.md#8-decisions).

## Demonstration plan

1. Open the live app (URL added once deployed) with synthetic demo data.
2. As a caregiver: add a medication with two daily times.
3. Open **Today**: mark one dose taken; double-tap another to show duplicate protection; undo.
4. Show a missed dose and the daily adherence summary.
5. In Grafana: follow one dose recording from metric to trace to log using its trace ID.
6. Incident drill: deploy a faulty release → alert fires → responder agent rolls back → incident issue appears.
7. Show CI on a PR, the dev auto-deploy, and the production approval step.

Evidence from the drill will be in `docs/incident-drill.md` (task MT-051).

## Limitations and known risks

- Synthetic data only; no accounts in v1. Anyone can see and change the public demo data until the next reset (every deploy and every night).
- Statuses depend on the server clock being correct.
- One VM hosts dev and prod: if the VM is down, both are down. The hosted-platform fallback is documented in [architecture.md §6](docs/architecture.md#6-deployment-options).

## Course criteria map

| Criterion | Where |
|---|---|
| Problem description | This README |
| Product specification + tracker | [docs/requirements.md](docs/requirements.md), [docs/acceptance-criteria.md](docs/acceptance-criteria.md), [backlog](backlog/tasks.md), [public GitHub Project board](https://github.com/users/brave-machangu/projects/1) |
| Agent team | [docs/agent-team.md](docs/agent-team.md), [prompts/](prompts/) |
| Context management | [AGENTS.md](AGENTS.md) → `docs/` |
| Application, tests, containers, deployment | Phases 1–2 (see backlog) |
| CI/CD | CI on every PR; auto-deploy to dev; manual, approved production deploy, the top level of this criterion ([operations.md §5](docs/operations.md#5-deployment-and-rollback)) |
| Observability, alerting | [docs/operations.md](docs/operations.md) §2–4, phase 3 |
| On-call agent | Wakes on the alert, rolls back, investigates and proposes the fix ([operations.md §6](docs/operations.md#6-responder-agent)), phase 3 |
