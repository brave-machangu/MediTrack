# MediTrack — Development Workflow

## 1. Phases

| Phase | Goal | Exit check |
|---|---|---|
| 0. Spec | Requirements, acceptance criteria, contract, backlog, agent team | Lead merges spec PR; backlog board is public |
| 1. Build | Backend and frontend in parallel against the contract | All P0 feature tasks merged; contract test green |
| 2. Integrate & ship | Docker Compose, CI/CD, deployment, observability | App reachable at a public URL; dashboards show live data |
| 3. Operate | Alert, responder agent, incident simulation, rollback drill | Simulated incident is detected and rolled back automatically, with an incident issue |

## 2. Planned commands

These are the commands the project will expose. They **don't exist yet**. The `Makefile` is owned by the Platform agent and created in MT-030; it wraps commands that the Backend and Frontend agents create earlier. Until then, use the direct command.

| Command | Does | Direct command (created in) |
|---|---|---|
| `make up` | `docker compose up --build` — whole system incl. database and observability | MT-030 |
| `make down` | Stop the system (keeps data volume) | MT-030 |
| `make seed` | Load synthetic demo data (idempotent) | `cd backend && uv run python -m app.seed` (MT-019) |
| `make reset-demo` | Replace all data with the seed (what deploys and the nightly job do) | `cd backend && uv run python -m app.seed --reset` (MT-019) |
| `make test` | All backend and frontend tests | both lines below |
| `make test-backend` | Backend tests | `cd backend && uv run pytest` (MT-010) |
| `make test-frontend` | Frontend tests (single run) | `cd frontend && npm run test` (MT-020) |
| `make lint` | ruff + mypy, eslint + tsc, OpenAPI lint | per-agent prompts |
| `make contract` | Backend contract test against `api/openapi.yaml` | `cd backend && uv run pytest tests/contract` (MT-018) |
| `make gen-api` | Regenerate `frontend/src/api/schema.d.ts` | `cd frontend && npm run gen:api` (MT-020) |

OpenAPI lint works today: `npx @redocly/cli@1 lint api/openapi.yaml`.
Backlog rendering works today: `python3 scripts/render_backlog.py` after editing `backlog/backlog.json` (`--check` fails if `tasks.md` is stale). Sync issues with `python3 scripts/create_backlog.py --repo brave-machangu/MediTrack [--update]`.

## 3. Definition of Ready (before an agent starts)

A task is ready when it has: an owner role, the files it may touch, acceptance criteria (AC IDs or explicit bullets), verification commands, dependencies resolved, and a priority.

## 4. Definition of Done

- [ ] All acceptance criteria for the task pass, with automated tests where the criteria say so
- [ ] Verification commands run locally; output pasted in the PR
- [ ] CI green (lint, types, tests, contract test, build)
- [ ] No files changed outside the agent's ownership
- [ ] No secrets, real personal data, or real health data in the diff
- [ ] Telemetry added for new endpoints follows [security.md](security.md#2-telemetry-privacy-rules)
- [ ] Docs updated if behaviour or commands changed
- [ ] Reviewer agent report posted; Lead approved

## 5. Branches, commits, PRs

- `main` is protected: changes only via PR with passing checks and Lead approval.
- Branch: `mt-<id>-<short-name>`. Commit prefix: `MT-<id>: `.
- One task per PR; aim for under ~400 changed lines (excluding lockfiles and generated files).
- PR description uses [.github/pull_request_template.md](../.github/pull_request_template.md).

## 6. CI checks (target state)

MT-031 creates the workflow (`.github/workflows/ci.yml`) with the checks that exist at that point; each later task adds its job (contract test with MT-018, image builds with MT-021/MT-029, Compose smoke with MT-030). Every job runs on every PR, so each required check reports a status on every PR. A path filter would leave a required check waiting for a job that never ran.

| Check | Runs on | Blocks merge |
|---|---|---|
| OpenAPI lint | every PR | ✓ |
| Backend: ruff, mypy, pytest unit (SQLite) | every PR | ✓ |
| Backend: integration + contract tests (PostgreSQL service) | every PR | ✓ |
| Frontend: eslint, tsc, vitest | every PR | ✓ |
| Generated types up to date (`npm run gen:api` produces no diff; `make gen-api` once MT-030 adds the Makefile) | every PR | ✓ |
| Docker images build | every PR | ✓ |
| Compose smoke test (`/readyz`, create + log a dose) | every PR | ✓ |
| Backend tests under a second process timezone (`TZ=America/Los_Angeles`) | every PR | ✓ |
| Secrets and dependencies: gitleaks, `pip-audit`, `npm audit --audit-level=high` | every PR | ✓ |
| Migration safety: `scripts/check_migrations.py` (destructive change needs `contract-migration` label) | every PR | ✓ |
| Backlog page up to date: `scripts/render_backlog.py --check` | every PR | ✓ |

CD: merge to `main` → build images tagged with the Git SHA → deploy to **dev** → smoke test. Production deploy is a manual `workflow_dispatch` that needs approval on the `production` environment. Details in [operations.md](operations.md#5-deployment-and-rollback).

## 7. Contract changes

1. Agent opens an issue labelled `contract-change`: endpoint, proposed change, reason, which tasks are affected.
2. Spec agent drafts the PR to `api/openapi.yaml` (and acceptance criteria if needed).
3. Lead approves and merges.
4. Backend updates implementation and contract test; Frontend runs `make gen-api` and updates code. Both are separate PRs.

Breaking changes (removing fields, changing types) are avoided in v1; add fields instead.

## 8. Review of AI-generated work

AI-written code is reviewed as if written by an unknown contributor.

1. **Automated gate:** CI must be green. No "the tests pass on my machine".
2. **Independent reviewer:** A new AI session that did **not** write the code runs [prompts/reviewer-agent.md](../prompts/reviewer-agent.md) with only the PR diff, the task issue, and the docs. It checks each acceptance criterion, looks for untested paths, privacy leaks in telemetry, edits outside ownership, invented APIs, and hard-coded times.
3. **Lead review:** The Lead reads the reviewer report and the diff, runs the app for UI changes, and approves or requests changes.
4. **Spot checks on the riskiest logic:** for dose-status, DST and duplicate handling, the Lead reads the tests first and confirms they would fail if the rule were broken (e.g. temporarily change grace from 60 to 59 minutes and see a test fail).
5. **No self-approval:** the agent that wrote a PR never reviews or merges it.
6. **Tests written by someone else first:** for the riskiest rules, the Test agent ([prompt](../prompts/test-agent.md), task MT-008) commits acceptance tests as strict expected failures before implementation. The implementer can only remove the markers, so the tests can't drift to fit the code.
7. **Traceability:** the reviewer report is posted as a PR comment so the review is visible on GitHub.
