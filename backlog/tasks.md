# MediTrack — Backlog

Source of truth: [backlog.json](backlog.json). This page is generated from it. Import to GitHub with `scripts/create_backlog.py` (see the [main README](../README.md#project-board)).

Priorities: **P0** needed to pass, **P1** strongly recommended, **P2** later. Task IDs are stable; GitHub issue numbers are assigned on import.

| ID | Title | Owner | Pri | Depends on |
|---|---|---|---|---|
| MT-001 | Approve spec, contract and decision D1 | Lead | P0 | — |
| MT-002 | Create public GitHub Project board and import backlog | Lead | P0 | MT-001 |
| MT-003 | Protect main and create GitHub environments | Lead | P0 | MT-001 |
| MT-004 | Repository guardrails: pre-commit with gitleaks, CODEOWNERS, Dependabot | Platform agent | P0 | MT-001 |
| MT-005 | Enforce agent roles: Claude Code agent definitions, deny rules, ownership check | Lead | P1 | MT-001 |
| MT-006 | Docs: adopt the Excellence agent prompts; record Lightsail (D2) and Sonnet 5.5 (D4) | Lead | P1 | MT-001 |
| MT-010 | Backend scaffold: FastAPI app, config, health endpoints, problem+json errors | Backend agent | P0 | MT-001 |
| MT-008 | Acceptance tests written first for the riskiest rules (Test agent) | Test agent | P1 | MT-010, MT-020 |
| MT-011 | Domain: planned doses, DST policy and dose status (pure functions) | Backend agent | P0 | MT-010 |
| MT-012 | Domain: daily adherence summary | Backend agent | P0 | MT-011 |
| MT-013 | Database models, Alembic migration, UTC handling | Backend agent | P0 | MT-010 |
| MT-014 | Patients API | Backend agent | P0 | MT-013 |
| MT-015 | Medications and schedules API | Backend agent | P0 | MT-014 |
| MT-016 | Planned doses day view and dose logging (create + undo) | Backend agent | P0 | MT-011, MT-015 |
| MT-017 | Missed doses and daily adherence endpoints | Backend agent | P0 | MT-012, MT-016 |
| MT-018 | Contract test against api/openapi.yaml | Backend agent | P0 | MT-017 |
| MT-019 | Synthetic demo seed | Backend agent | P1 | MT-016 |
| MT-021 | Backend Dockerfile | Backend agent | P0 | MT-013 |
| MT-022 | Backend telemetry: traces, metrics, logs with shared trace ID | Backend agent | P0 | MT-016 |
| MT-023 | Build-time fault injection for the incident drill | Backend agent | P1 | MT-022 |
| MT-020 | Frontend scaffold: Vite + React + TS, generated API types, client, layout, disclaimer | Frontend agent | P0 | MT-001 |
| MT-024 | Patients page | Frontend agent | P0 | MT-020 |
| MT-025 | Today page: dose list, Taken/Skipped, undo | Frontend agent | P0 | MT-020 |
| MT-026 | Medications and schedules pages | Frontend agent | P0 | MT-020 |
| MT-027 | Missed doses page | Frontend agent | P0 | MT-020 |
| MT-028 | Daily summary page | Frontend agent | P0 | MT-020 |
| MT-029 | Frontend Dockerfile with nginx (SPA + /api proxy) | Frontend agent | P0 | MT-020 |
| MT-030 | Docker Compose, Makefile and end-to-end smoke test | Platform agent | P0 | MT-016, MT-019, MT-021, MT-025, MT-029, MT-031 |
| MT-031 | CI workflow | Platform agent | P0 | MT-010, MT-020 |
| MT-033 | Choose and provision hosting (decision D2) | Lead | P0 | MT-001 |
| MT-032 | CD: build to GHCR, auto-deploy dev, manual production, rollback workflow | Platform agent | P0 | MT-031, MT-033 |
| MT-040 | Observability stack config and dashboard | Platform agent | P0 | MT-022, MT-030 |
| MT-041 | User-impact alert and probe | Platform agent | P0 | MT-040, MT-019, MT-023 |
| MT-050 | Responder agent service | Platform agent | P0 | MT-032, MT-041 |
| MT-053 | Responder investigation agent: evidence packet, investigate.yml, schema-checked analysis, fix PR | Platform agent | P0 | MT-050 |
| MT-054 | Security audit: scanners, model review, human disposition, capability table | Reviewer agent | P1 | MT-050, MT-053 |
| MT-051 | Incident drill and evidence | Lead | P0 | MT-023, MT-050, MT-053 |
| MT-052 | Final README, demo video and submission check | Lead | P0 | MT-051 |
| MT-060 | User accounts and sign-in (FR-12) — split into backend/frontend tasks when scheduled | Lead | P2 | MT-052 |

## MT-001 — Approve spec, contract and decision D1

- **Owner:** Lead  ·  **Priority:** P0  ·  **Phase:** 0-spec
- **Depends on:** none
- **Files:** `docs/**`, `api/openapi.yaml`, `README.md`, `AGENTS.md`

**Acceptance criteria**

- [ ] Lead has read requirements, acceptance criteria, architecture and the contract
- [ ] Decision D1 (no accounts in v1) is approved or changed, and requirements.md updated
- [ ] ADRs marked Proposed are accepted or changed
- [ ] Spec on main (first commit; later spec changes go through PRs)
- [ ] Decisions D4 (investigation agent) and D5 (schedule overlap rule) approved or changed

**Verification**

```bash
npx @redocly/cli@1 lint api/openapi.yaml
```

## MT-002 — Create public GitHub Project board and import backlog

- **Owner:** Lead  ·  **Priority:** P0  ·  **Phase:** 0-spec
- **Depends on:** MT-001
- **Files:** `backlog/**`, `README.md`

**Acceptance criteria**

- [ ] Running scripts/create_backlog.py creates one issue per task with labels
- [ ] A GitHub Project named 'MediTrack' exists, is PUBLIC, is linked to the repo, and contains every issue
- [ ] Board URL added to README.md

**Verification**

```bash
gh auth refresh -s project
python3 scripts/create_backlog.py --repo brave-machangu/MediTrack --dry-run
python3 scripts/create_backlog.py --repo brave-machangu/MediTrack
Open the board URL in a private browser window to confirm it is public
```

## MT-003 — Protect main and create GitHub environments

- **Owner:** Lead  ·  **Priority:** P0  ·  **Phase:** 0-spec
- **Depends on:** MT-001
- **Files:** `(GitHub settings only)`

**Acceptance criteria**

- [ ] main requires a PR, passing status checks and 1 approval; force pushes blocked
- [ ] Environments 'dev' and 'production' exist; 'production' requires Lead approval
- [ ] Secret scanning / push protection enabled if available for the repo

**Verification**

```bash
Try to push directly to main: it must be rejected
```

## MT-004 — Repository guardrails: pre-commit with gitleaks, CODEOWNERS, Dependabot

- **Owner:** Platform agent  ·  **Priority:** P0  ·  **Phase:** 0-spec
- **Depends on:** MT-001
- **Files:** `.pre-commit-config.yaml`, `.editorconfig`, `.github/CODEOWNERS`, `.github/dependabot.yml`

**Acceptance criteria**

- [ ] pre-commit run --all-files passes on a clean clone
- [ ] gitleaks blocks a commit that contains a fake secret (shown in the PR, not committed)
- [ ] CODEOWNERS makes the Lead a required reviewer for api/, AGENTS.md, backend/alembic/, .github/, responder/ and frontend/src/copy.ts
- [ ] Dependabot is configured for pip, npm, github-actions and docker

**Verification**

```bash
pre-commit run --all-files
```

**Notes:** Platform agent's first task; root tooling files only, Lead-approved PR.

## MT-005 — Enforce agent roles: Claude Code agent definitions, deny rules, ownership check

- **Owner:** Lead  ·  **Priority:** P1  ·  **Phase:** 0-spec
- **Depends on:** MT-001
- **Files:** `.claude/agents/*.md`, `.claude/settings.json`, `scripts/check_ownership.py`

**Acceptance criteria**

- [ ] One agent definition per role in docs/agent-team.md, with its tool list and owned paths
- [ ] .claude/settings.json contains the deny rules listed in docs/agent-team.md §7
- [ ] scripts/check_ownership.py --role backend --files frontend/src/App.tsx exits 1; with backend/app/main.py it exits 0
- [ ] An attempted git push origin main from an agent session is refused (noted in the PR)

**Verification**

```bash
python3 scripts/check_ownership.py --role backend --files frontend/src/App.tsx; test $? -eq 1
python3 scripts/check_ownership.py --role backend --files backend/app/main.py
```

**Notes:** Drafted by the Spec agent; the Lead reviews and merges.

## MT-006 — Docs: adopt the Excellence agent prompts; record Lightsail (D2) and Sonnet 5.5 (D4)

- **Owner:** Lead  ·  **Priority:** P1  ·  **Phase:** 0-spec
- **Depends on:** MT-001
- **Files:** `prompts/**`, `docs/**`, `README.md`, `AGENTS.md`, `backlog/**`

**Acceptance criteria**

- [ ] prompts/frontend-agent-excellence.md and prompts/backend-agent-excellence.md are in prompts/ and agree with docs/agent-team.md (file ownership) and AGENTS.md rule 11 (Test agent markers)
- [ ] Docs name the Excellence prompts as the ones to use for MT-020 and for MT-011 onwards, on top of the base prompts
- [ ] docs/architecture.md §6.1 lists source links; D2 records AWS Lightsail 4 GB with the credit terms and a billing-alarm step
- [ ] D4 records claude-sonnet-5-5 with a $20/month spend limit and the Opus upgrade path
- [ ] python3 scripts/check_docs.py and python3 scripts/render_backlog.py --check pass

**Verification**

```bash
python3 scripts/check_docs.py
python3 scripts/render_backlog.py --check
```

**Notes:** Spec agent drafts; the Lead reviews and merges.

## MT-010 — Backend scaffold: FastAPI app, config, health endpoints, problem+json errors

- **Owner:** Backend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-001
- **Files:** `backend/**`

**Acceptance criteria**

- [ ] uv project with pinned dependencies; ruff, mypy and pytest configured
- [ ] App factory in app/main.py; settings read from environment variables (names documented in backend/README.md)
- [ ] GET /healthz returns 200 {status: ok, version}
- [ ] GET /readyz returns 200 when DB reachable, 503 otherwise
- [ ] All errors (incl. FastAPI validation errors) return application/problem+json with a contract code (AC-31)
- [ ] Clock protocol with SystemClock and FixedClock in app/clock.py

**Verification**

```bash
(cd backend && uv run ruff check . && uv run mypy app && uv run pytest -q)
```

## MT-008 — Acceptance tests written first for the riskiest rules (Test agent)

- **Owner:** Test agent  ·  **Priority:** P1  ·  **Phase:** 1-build
- **Depends on:** MT-010, MT-020
- **Files:** `backend/tests/acceptance/**`, `frontend/src/test/acceptance/**`

**Acceptance criteria**

- [ ] Backend: AC-07, AC-08, AC-11, AC-12, AC-15, AC-16, AC-17, AC-25, AC-34 and the boundary table in test-strategy.md §3.2 written as strict-xfail tests
- [ ] Frontend: AC-21, AC-35 (frontend part) and AC-36 written as expected-failure tests
- [ ] Both suites are green on main (expected failures only); every test name contains its AC ID
- [ ] Written from the docs and contract only, in a session separate from the implementers (prompts/test-agent.md)

**Verification**

```bash
(cd backend && uv run pytest tests/acceptance -q)
(cd frontend && npm run test -- src/test/acceptance)
```

**Notes:** Implementers of MT-011, MT-012, MT-016 and MT-025 remove the markers as their code makes the tests pass. If this task is skipped, implementers still write tests first (see prompts).

## MT-011 — Domain: planned doses, DST policy and dose status (pure functions)

- **Owner:** Backend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-010
- **Files:** `backend/app/domain/scheduling.py`, `backend/tests/unit/**`

**Acceptance criteria**

- [ ] AC-07, AC-08, AC-10, AC-11, AC-12 covered by unit tests
- [ ] Boundary table in test-strategy.md §3.2 covered for status (log-window cases come in MT-016)
- [ ] No imports from FastAPI, SQLAlchemy or datetime.now in app/domain/
- [ ] AC-39 property-based DST test (Hypothesis); the suite passes under TZ=UTC and TZ=America/Los_Angeles (AC-35)
- [ ] Acceptance tests from MT-008, if merged, pass with only their xfail markers removed

**Verification**

```bash
(cd backend && uv run pytest tests/unit -q)
test -d backend/app/domain && ! grep -rnE 'datetime\.now|utcnow|date\.today|^(from|import) (fastapi|sqlalchemy)' backend/app/domain && echo 'domain purity ok'
```

## MT-012 — Domain: daily adherence summary

- **Owner:** Backend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-011
- **Files:** `backend/app/domain/adherence.py`, `backend/tests/unit/**`

**Acceptance criteria**

- [ ] AC-25 and the backend half of AC-26 covered by unit tests
- [ ] Rounding to 1 decimal; null when denominator is 0
- [ ] Acceptance tests from MT-008 for AC-25, if merged, pass with only their xfail markers removed

**Verification**

```bash
(cd backend && uv run pytest tests/unit -q)
```

## MT-013 — Database models, Alembic migration, UTC handling

- **Owner:** Backend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-010
- **Files:** `backend/app/db/**`, `backend/alembic/**`, `backend/tests/integration/**`

**Acceptance criteria**

- [ ] Models for Patient, Medication, Schedule, DoseLog per requirements §4.1; JSON columns for times/days
- [ ] Unique constraint uq_dose_log_schedule_time on (schedule_id, scheduled_for)
- [ ] alembic upgrade head / downgrade -1 / upgrade head works on SQLite and PostgreSQL
- [ ] Datetimes read back are timezone-aware UTC on both databases

**Verification**

```bash
(cd backend && uv run ruff check . && uv run mypy app && uv run pytest -q)
(cd backend && uv run pytest tests/integration -q)  # with the PostgreSQL test URL from backend/README.md set; must not skip AC-18
```

## MT-014 — Patients API

- **Owner:** Backend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-013
- **Files:** `backend/app/api/**`, `backend/app/services/**`, `backend/tests/**`

**Acceptance criteria**

- [ ] AC-01, AC-02, AC-13 pass
- [ ] Responses match the contract schemas

**Verification**

```bash
(cd backend && uv run ruff check . && uv run mypy app && uv run pytest -q)
```

## MT-015 — Medications and schedules API

- **Owner:** Backend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-014
- **Files:** `backend/app/api/**`, `backend/app/services/**`, `backend/tests/**`

**Acceptance criteria**

- [ ] AC-03, AC-04, AC-05, AC-06 pass
- [ ] has_dose_logs is returned on schedules
- [ ] AC-34: overlapping schedules of one medication return 409 SCHEDULE_OVERLAP on create and on PATCH

**Verification**

```bash
(cd backend && uv run ruff check . && uv run mypy app && uv run pytest -q)
```

## MT-016 — Planned doses day view and dose logging (create + undo)

- **Owner:** Backend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-011, MT-015
- **Files:** `backend/app/api/**`, `backend/app/services/**`, `backend/tests/**`

**Acceptance criteria**

- [ ] AC-09, AC-14, AC-15, AC-16, AC-17, AC-19, AC-20 pass
- [ ] AC-18 concurrency test passes on PostgreSQL
- [ ] Log-window rows of the boundary table in test-strategy.md §3.2 pass
- [ ] Planned doses include instructions, log_window_opens_at and log_window_closes_at
- [ ] Acceptance tests from MT-008, if merged, pass with only their xfail markers removed

**Verification**

```bash
(cd backend && uv run ruff check . && uv run mypy app && uv run pytest -q)
```

## MT-017 — Missed doses and daily adherence endpoints

- **Owner:** Backend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-012, MT-016
- **Files:** `backend/app/api/**`, `backend/app/services/**`, `backend/tests/**`

**Acceptance criteria**

- [ ] AC-22, AC-23, AC-24 pass; AC-25 via the API

**Verification**

```bash
(cd backend && uv run ruff check . && uv run mypy app && uv run pytest -q)
```

## MT-018 — Contract test against api/openapi.yaml

- **Owner:** Backend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-017
- **Files:** `backend/tests/contract/**`

**Acceptance criteria**

- [ ] AC-31 and AC-32 pass: every operation is exercised and responses validate against the contract
- [ ] Test fails if an endpoint returns a field or status not in the contract (prove by a temporary change, mention in PR)

**Verification**

```bash
(cd backend && uv run pytest tests/contract -q)
```

## MT-019 — Synthetic demo seed

- **Owner:** Backend agent  ·  **Priority:** P1  ·  **Phase:** 1-build
- **Depends on:** MT-016
- **Files:** `backend/app/seed.py`, `backend/tests/**`

**Acceptance criteria**

- [ ] AC-33 passes
- [ ] Only synthetic names (Demo Patient A/B, Demo Med Alpha…)
- [ ] Includes a dedicated 'Probe Patient' with a dose every 2 hours, used by the alert probe
- [ ] AC-41: `python -m app.seed --reset` replaces all application rows with the seed in one transaction (decision D1); without --reset seeding never deletes

**Verification**

```bash
(cd backend && uv run python -m app.seed && uv run python -m app.seed)  # second run adds nothing
```

## MT-021 — Backend Dockerfile

- **Owner:** Backend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-013
- **Files:** `backend/Dockerfile`, `backend/.dockerignore`

**Acceptance criteria**

- [ ] Runs as non-root; timezone data available (zoneinfo works for Europe/London)
- [ ] Separate command for migrations (alembic upgrade head) documented
- [ ] Image accepts build arg GIT_SHA exposed as /healthz version

**Verification**

```bash
docker build -t meditrack-backend:test --build-arg GIT_SHA=test backend
docker run --rm meditrack-backend:test python -c "from zoneinfo import ZoneInfo; ZoneInfo('Europe/London'); print('tz ok')"
```

## MT-022 — Backend telemetry: traces, metrics, logs with shared trace ID

- **Owner:** Backend agent  ·  **Priority:** P0  ·  **Phase:** 2-ship
- **Depends on:** MT-016
- **Files:** `backend/app/telemetry.py`, `backend/app/**`, `backend/tests/**`

**Acceptance criteria**

- [ ] Signals in operations.md §2 emitted via OTLP; endpoint from env var; disabled cleanly when unset
- [ ] meditrack.dose_log.attempts counter with outcome attribute only
- [ ] Problem responses include trace_id; logs include trace_id and span_id
- [ ] AC-29 privacy canary test passes using in-memory exporters
- [ ] AC-37: every response has X-Trace-Id equal to the problem trace_id and to the trace_id of the request's log records

**Verification**

```bash
(cd backend && uv run ruff check . && uv run mypy app && uv run pytest -q)
```

## MT-023 — Build-time fault injection for the incident drill

- **Owner:** Backend agent  ·  **Priority:** P1  ·  **Phase:** 3-operate
- **Depends on:** MT-022
- **Files:** `backend/app/**`, `backend/Dockerfile`, `backend/tests/**`

**Acceptance criteria**

- [ ] Build arg FAULT_DOSE_LOG_ERROR_RATE (default 0) makes that share of POST /dose-logs return 500 INTERNAL_ERROR
- [ ] Image gets label meditrack.fault=true when rate > 0
- [ ] Tests cover rate 0 (never fails) and 1 (always fails)

**Verification**

```bash
(cd backend && uv run ruff check . && uv run mypy app && uv run pytest -q)
```

## MT-020 — Frontend scaffold: Vite + React + TS, generated API types, client, layout, disclaimer

- **Owner:** Frontend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-001
- **Files:** `frontend/**`

**Acceptance criteria**

- [ ] npm scripts: dev, build, lint, typecheck, test (single run), gen:api
- [ ] src/api/schema.d.ts generated from ../api/openapi.yaml; client handles problem+json and network errors
- [ ] MSW handlers built from contract examples; tests use them
- [ ] React Router with routes for Patients, Today, Medications, Missed, Summary
- [ ] Disclaimer on every page (AC-27); base styles meet NFR-01 sizes
- [ ] Vite dev proxy sends /api, /healthz, /readyz to http://localhost:8000
- [ ] All UI text in src/copy.ts with the AC-38 safety copy test in place
- [ ] The test script runs with TZ=Asia/Tokyo (AC-35)
- [ ] AC-40: the FR-13 demo banner is on every page

**Verification**

```bash
(cd frontend && npm run lint && npm run typecheck && npm run test)
(cd frontend && npm run gen:api && git diff --exit-code src/api/schema.d.ts)
```

## MT-024 — Patients page

- **Owner:** Frontend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-020
- **Files:** `frontend/src/**`, `frontend/tests/**`

**Acceptance criteria**

- [ ] List, create and edit patients; timezone picker of IANA names
- [ ] 422 field errors shown next to fields (AC-02)
- [ ] Render + error-state tests

**Verification**

```bash
(cd frontend && npm run lint && npm run typecheck && npm run test)
```

## MT-025 — Today page: dose list, Taken/Skipped, undo

- **Owner:** Frontend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-020
- **Files:** `frontend/src/**`, `frontend/tests/**`

**Acceptance criteria**

- [ ] Shows planned doses for the patient's local today from the API
- [ ] AC-14, AC-20, AC-21 (double-tap guard, 409 → 'Already recorded')
- [ ] AC-28: status as text + icon, 44×44 px buttons, keyboard reachable, axe check has no serious/critical issues
- [ ] Network/5xx error shows Retry and never shows the dose as taken
- [ ] AC-35 (frontend part) and AC-36 pass
- [ ] Acceptance tests from MT-008, if merged, pass with only their expected-failure markers removed

**Verification**

```bash
(cd frontend && npm run lint && npm run typecheck && npm run test)
```

## MT-026 — Medications and schedules pages

- **Owner:** Frontend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-020
- **Files:** `frontend/src/**`, `frontend/tests/**`

**Acceptance criteria**

- [ ] Add/edit/deactivate medications; add/edit/delete schedules
- [ ] When has_dose_logs is true, only the end date is editable, with an explanation
- [ ] Validation errors from AC-03, AC-05, AC-06 shown clearly
- [ ] Changing a schedule that has logs sets its end_date (default today) and creates the new schedule from the next day; SCHEDULE_OVERLAP shows the message from prompts/frontend-agent.md
- [ ] AC-34 frontend part: SCHEDULE_OVERLAP message shown next to the form; new start date defaults to the old end date + 1

**Verification**

```bash
(cd frontend && npm run lint && npm run typecheck && npm run test)
```

## MT-027 — Missed doses page

- **Owner:** Frontend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-020
- **Files:** `frontend/src/**`, `frontend/tests/**`

**Acceptance criteria**

- [ ] Shows last 7 days by default, newest first; date range picker limited to 31 days
- [ ] Empty state; each item can be logged late if within the window

**Verification**

```bash
(cd frontend && npm run lint && npm run typecheck && npm run test)
```

## MT-028 — Daily summary page

- **Owner:** Frontend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-020
- **Files:** `frontend/src/**`, `frontend/tests/**`

**Acceptance criteria**

- [ ] Date picker; counts and adherence percent; 'No doses to score yet' when null (AC-26)

**Verification**

```bash
(cd frontend && npm run lint && npm run typecheck && npm run test)
```

## MT-029 — Frontend Dockerfile with nginx (SPA + /api proxy)

- **Owner:** Frontend agent  ·  **Priority:** P0  ·  **Phase:** 1-build
- **Depends on:** MT-020
- **Files:** `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/.dockerignore`

**Acceptance criteria**

- [ ] Multi-stage build; nginx serves SPA with history fallback and proxies /api, /healthz, /readyz to the backend service
- [ ] Sends a Content-Security-Policy header; runs as non-root if the base image supports it

**Verification**

```bash
docker build -t meditrack-frontend:test frontend
```

## MT-030 — Docker Compose, Makefile and end-to-end smoke test

- **Owner:** Platform agent  ·  **Priority:** P0  ·  **Phase:** 2-ship
- **Depends on:** MT-016, MT-019, MT-021, MT-025, MT-029, MT-031
- **Files:** `docker-compose.yml`, `Makefile`, `scripts/smoke.sh`, `.env.example`, `.github/workflows/ci.yml`

**Acceptance criteria**

- [ ] OPS-01: `make up` starts frontend, backend, PostgreSQL (named volume) and the observability stack; migrations run automatically
- [ ] AC-30 (data survives backend restart)
- [ ] make down / make seed / make test / make lint / make contract / make gen-api work
- [ ] Compose smoke job added to CI

**Verification**

```bash
make up
./scripts/smoke.sh http://localhost:8080
docker compose restart backend && ./scripts/smoke.sh http://localhost:8080
```

## MT-031 — CI workflow

- **Owner:** Platform agent  ·  **Priority:** P0  ·  **Phase:** 2-ship
- **Depends on:** MT-010, MT-020
- **Files:** `.github/workflows/ci.yml`, `Makefile`

**Acceptance criteria**

- [ ] OPS-02: CI runs on every PR and blocks merge; jobs for lint, unit and integration tests (PostgreSQL service container) for backend and frontend
- [ ] Later tasks add their jobs (contract test, image builds, Compose smoke) as listed in development-workflow.md §6
- [ ] Backend tests run under TZ=UTC and TZ=America/Los_Angeles (AC-35)
- [ ] gitleaks, pip-audit and npm audit --audit-level=high run; third-party actions pinned by commit SHA; workflow permissions default to contents: read
- [ ] scripts/check_migrations.py fails destructive migrations unless the PR has the contract-migration label
- [ ] python3 scripts/render_backlog.py --check passes
- [ ] python3 scripts/check_docs.py passes (links, anchors and requirement/AC/OPS/MT references)

**Verification**

```bash
Open a PR with a deliberately failing test: CI must fail; revert: CI passes
```

## MT-033 — Choose and provision hosting (decision D2)

- **Owner:** Lead  ·  **Priority:** P0  ·  **Phase:** 2-ship
- **Depends on:** MT-001
- **Files:** `docs/architecture.md`

**Acceptance criteria**

- [ ] D2 decided and recorded as an ADR; dev and production targets exist
- [ ] Required secrets created in GitHub Environments by the Lead (names documented, values never in Git)
- [ ] Provider chosen from the price check in docs/architecture.md §6.1 (VM with at least 2 vCPU, 4 GB RAM, 40 GB disk) and recorded in ADR-013
- [ ] Reverse proxy with automatic HTTPS for the dev and prod subdomains; only ports 80, 443 and SSH open
- [ ] D2 provider: AWS Lightsail 4 GB, created only after the billing alarm and credit check in docs/architecture.md §6.1 are done

**Verification**

```bash
Lead confirms both environments are reachable
```

## MT-032 — CD: build to GHCR, auto-deploy dev, manual production, rollback workflow

- **Owner:** Platform agent  ·  **Priority:** P0  ·  **Phase:** 2-ship
- **Depends on:** MT-031, MT-033
- **Files:** `.github/workflows/deploy.yml`, `.github/workflows/rollback.yml`, `deploy/**`, `.github/workflows/reset-demo.yml`

**Acceptance criteria**

- [ ] OPS-03, OPS-04, OPS-11
- [ ] Images tagged with git SHA; deployments recorded in GitHub Deployments
- [ ] Post-deploy smoke test; automatic redeploy of previous SHA if it fails
- [ ] Deploy workflow has an inject_fault input (dev only) that builds the MT-023 faulty image
- [ ] Production job refuses images labelled meditrack.fault=true
- [ ] FR-14: every deploy runs `python -m app.seed --reset` after migrations
- [ ] OPS-16: .github/workflows/reset-demo.yml resets dev and prod nightly at 03:00 UTC and can be run by hand

**Verification**

```bash
Merge a trivial change: dev updates automatically
gh workflow run rollback.yml -f environment=dev  # confirm previous SHA is live
```

## MT-040 — Observability stack config and dashboard

- **Owner:** Platform agent  ·  **Priority:** P0  ·  **Phase:** 2-ship
- **Depends on:** MT-022, MT-030
- **Files:** `deploy/otel/**`, `deploy/grafana/**`, `docker-compose.yml`

**Acceptance criteria**

- [ ] OPS-05: a request can be followed metric → trace → log
- [ ] Dashboard in operations.md §2.4 provisioned from files
- [ ] OPS-06 spot check documented
- [ ] The Collector removes url.*, request/response header, client.address and user_agent attributes (operations.md §2.3a)
- [ ] Deployed on the VM (decision D3): Grafana requires a login, anonymous access is off, and the OTLP and Prometheus ports are not reachable from outside the VM

**Verification**

```bash
make up && ./scripts/smoke.sh http://localhost:8080  # then follow the trace in Grafana
```

## MT-041 — User-impact alert and probe

- **Owner:** Platform agent  ·  **Priority:** P0  ·  **Phase:** 3-operate
- **Depends on:** MT-040, MT-019, MT-023
- **Files:** `deploy/grafana/alerts/**`, `probe/**`, `docker-compose.yml`

**Acceptance criteria**

- [ ] DoseRecordingFailing and ServiceNotReady rules provisioned as in operations.md §4
- [ ] Probe runs every 15 s: logs an open Probe Patient dose (expect 201) then undoes it (expect 204), as in operations.md §4
- [ ] OPS-07 demonstrated locally with a faulty image
- [ ] The probe looks up the Probe Patient by name on every run, so it keeps working after the nightly reset

**Verification**

```bash
Build a faulty image (MT-023) and run it: alert fires within 7 minutes
```

## MT-050 — Responder agent service

- **Owner:** Platform agent  ·  **Priority:** P0  ·  **Phase:** 3-operate
- **Depends on:** MT-032, MT-041
- **Files:** `responder/**`, `docker-compose.yml`

**Acceptance criteria**

- [ ] Runbook in operations.md §6.1 implemented; modes off / dry_run / active
- [ ] OPS-09 and OPS-10: unit tests for every decision rule; dry_run takes no action
- [ ] Uses only the permissions in operations.md §6.2; token from environment, never logged

**Verification**

```bash
(cd responder && uv run pytest -q)
```

## MT-053 — Responder investigation agent: evidence packet, investigate.yml, schema-checked analysis, fix PR

- **Owner:** Platform agent  ·  **Priority:** P0  ·  **Phase:** 3-operate
- **Depends on:** MT-050
- **Files:** `responder/**`, `.github/workflows/investigate.yml`

**Acceptance criteria**

- [ ] Decision D4 recorded: agent CLI, pinned model, API key as a 'responder' environment secret with a provider spend limit
- [ ] Responder step 7 posts the evidence packet (allowlisted query templates, operational data only, size-capped) and dispatches investigate.yml
- [ ] OPS-12: the agent runs on the live SHA with the tool allowlist in operations.md §6.3; its output is validated against responder/response.schema.json, otherwise the incident escalates
- [ ] OPS-13: for a code defect, a PR on incident/<n> with a failing-then-passing test, allowlisted paths only, at most 60 changed lines; never merged automatically
- [ ] Unit tests for the evidence allowlist, schema guard and path/size policy (test-strategy.md §3.8)
- [ ] Decision D4 limits: the model ID is pinned in investigate.yml; INVESTIGATION_MODE defaults to report; the model job has contents: read only and declares only the responder environment; a second job without a model posts findings and, in pr mode only, validates the patch and opens the PR
- [ ] Each run's measured cost is recorded on the incident issue and compared with the estimate in docs/operations.md §6.5
- [ ] Model pinned to claude-sonnet-5-5 with a $20/month spend limit (D4); switching to claude-opus-5-5 is a PR after the drill

**Verification**

```bash
(cd responder && uv run pytest -q)
gh workflow run investigate.yml -f issue=<incident issue number>   # during the drill on dev
```

**Notes:** The model never decides the rollback (that stays deterministic in MT-050) and never merges.

## MT-054 — Security audit: scanners, model review, human disposition, capability table

- **Owner:** Reviewer agent  ·  **Priority:** P1  ·  **Phase:** 3-operate
- **Depends on:** MT-050, MT-053
- **Files:** `security-audit/**`

**Acceptance criteria**

- [ ] Semgrep (Python, TypeScript and the local rules in security.md §7), gitleaks, pip-audit and npm audit run; outputs stored in security-audit/runs/<date>/
- [ ] The Reviewer agent's report uses the fixed findings format, and the Lead's disposition is recorded for every finding
- [ ] security-audit/capability-table.md lists every agent, MCP server, token and workflow permission with its scope and storage
- [ ] No unreviewed high-severity finding remains

**Verification**

```bash
semgrep scan --config auto --config security-audit/semgrep --error
(cd backend && uv run pip-audit) && (cd frontend && npm audit --audit-level=high)
```

## MT-051 — Incident drill and evidence

- **Owner:** Lead  ·  **Priority:** P0  ·  **Phase:** 3-operate
- **Depends on:** MT-023, MT-050, MT-053
- **Files:** `docs/incident-drill.md`

**Acceptance criteria**

- [ ] OPS-07 and OPS-08 demonstrated on dev
- [ ] Evidence (screenshots/recording, workflow run link, incident issue link) in docs/incident-drill.md
- [ ] OPS-14: drill B (database outage) causes no rollback and no PR, and escalates within 10 minutes
- [ ] OPS-15: the incident issue lets a reader reconstruct version, impact, alert, evidence, model and configuration, decision, actions and verification
- [ ] OPS-17: the drill first runs the investigation agent in report mode (findings only, no branch or PR); the Lead enables PR mode only afterwards

**Verification**

```bash
Follow operations.md §7 step by step
```

## MT-052 — Final README, demo video and submission check

- **Owner:** Lead  ·  **Priority:** P0  ·  **Phase:** 3-operate
- **Depends on:** MT-051
- **Files:** `README.md`

**Acceptance criteria**

- [ ] README has live URL, board URL, one-command setup, test command, screenshots, limitations
- [ ] Self-check against all 12 project criteria

**Verification**

```bash
Fresh clone on a clean machine: make up && make test both succeed
```

## MT-060 — User accounts and sign-in (FR-12) — split into backend/frontend tasks when scheduled

- **Owner:** Lead  ·  **Priority:** P2  ·  **Phase:** later
- **Depends on:** MT-052
- **Files:** `backend/**`, `frontend/**`, `api/openapi.yaml`

**Acceptance criteria**

- [ ] Spec and contract change approved first

**Verification**

```bash
(defined when scheduled)
```

**Notes:** Later option recorded under decision D1: a per-visitor private workspace (random cookie token, no email or password) instead of full accounts; it touches every endpoint.
