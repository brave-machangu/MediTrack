# MediTrack backend

FastAPI service implementing [`api/openapi.yaml`](../api/openapi.yaml). Structure and rules: [docs/architecture.md §3](../docs/architecture.md#3-backend-structure).

## Run

Requires [uv](https://docs.astral.sh/uv/). It installs Python 3.12 (from `.python-version`) and the locked dependencies.

```bash
cd backend
uv sync
uv run alembic upgrade head   # create or update the schema; the app never migrates on start
uv run python -m app.seed      # synthetic demo data + the alert probe's "Probe Patient"; running it again adds nothing
uv run python -m app.seed --reset   # replace ALL data with the seed in one transaction (deploys and the nightly reset)
uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log --reload   # http://localhost:8000/healthz
```

Logs are JSON lines on stdout, each with `trace_id` and `span_id`; every response carries the same ID in `X-Trace-Id`. With `OTEL_EXPORTER_OTLP_ENDPOINT` set, traces, metrics and the same log records also go to that collector over OTLP/HTTP (see [Telemetry](#telemetry)). Unset, nothing is exported. Run uvicorn with `--no-access-log`: its access log prints raw paths, which contain IDs (docs/security.md §2), while the app logs failed requests with the route template.

Migrations live in `alembic/versions/` and read the database from `DATABASE_URL`. Run them as their own step, before the new version starts (operations.md §5.1).

## Check

```bash
uv run ruff check .        # lint, incl. the ban on datetime.now()/utcnow()/date.today() outside app/clock.py
uv run ruff format --check .
uv run mypy app            # strict
uv run pytest              # unit + integration; database tests run on SQLite, and on PostgreSQL if configured
uv run pytest tests/contract   # the app against ../api/openapi.yaml (Schemathesis + a walk through every operation)
```

### PostgreSQL tests

Every database test runs on SQLite and on PostgreSQL. The PostgreSQL half needs a **throwaway** server. Each test session creates its own database on it (`meditrack_test_<random>`) and drops it afterwards; nothing else on the server is touched.

```bash
docker run --rm -d --name meditrack-test-db -p 5433:5432 -e POSTGRES_PASSWORD=<password> postgres:16
export MEDITRACK_TEST_POSTGRES_URL='postgresql+psycopg://postgres:<password>@localhost:5433/postgres'
uv run pytest tests/integration
docker stop meditrack-test-db
```

| Variable | Meaning | Default | Example |
|---|---|---|---|
| `MEDITRACK_TEST_POSTGRES_URL` | Tests only: a PostgreSQL server the tests may create and drop databases on. Unset → PostgreSQL tests are **skipped, with that reason** in the report. | unset | `postgresql+psycopg://postgres:<password>@localhost:5433/postgres` |
| `MEDITRACK_REQUIRE_POSTGRES` | Tests only: `1` turns those skips into failures. CI sets it, so PostgreSQL tests can never be skipped there. | unset | `1` |

## Configuration

Settings are read from environment variables (`app/config.py`). No variable is required for local development.

Every variable uses the `MEDITRACK_` prefix, except `DATABASE_URL`, which keeps its conventional name because hosted platforms inject it (Lead decision Q5 in [DESIGN.md](DESIGN.md)), and the standard OpenTelemetry variables. No variable has a secret as its default.

| Variable | Meaning | Default | Example |
|---|---|---|---|
| `DATABASE_URL` | SQLAlchemy URL. PostgreSQL in Compose and deployments (MT-013, MT-030). | `sqlite:///./meditrack.db` | `postgresql+psycopg://meditrack:<password>@db:5432/meditrack` |
| `MEDITRACK_ENV` | One of `local`, `test`, `ci`, `dev`, `production`. | `local` | `production` |
| `MEDITRACK_VERSION` | Git SHA or release tag, reported by `/healthz` and `/readyz`. The Dockerfile sets it from the `GIT_SHA` build arg (MT-021). | `dev` | `3f2c1a9` |
| `MEDITRACK_EARLY_LOG_WINDOW_MINUTES` | How long before its scheduled time a dose can be recorded (requirements §4.2). | `60` | `60` |
| `MEDITRACK_LATE_LOG_LIMIT_MINUTES` | How long after its scheduled time a dose can still be recorded (requirements §4.2). | `1440` | `1440` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP/HTTP base URL of the collector. Traces, metrics and logs go to `/v1/traces`, `/v1/metrics` and `/v1/logs` under it. Unset: nothing is exported, and trace IDs still work. | unset | `http://otel-collector:4318` |
| `OTEL_EXPORTER_OTLP_HEADERS` | Read by the OTLP exporters, not by `app/config.py`: headers sent to the collector, such as an auth token. When set it's a secret, so it comes from the deployment's secret store. | unset | `authorization=Basic <token>` |

The fault-injection setting is added by MT-023.

## Telemetry

Signal names from operations.md §2, as the backend emits them. Every span attribute, metric attribute and log field is on an allowlist in `app/telemetry.py`; anything else an instrumentation adds is dropped before export.

- **Traces:** one server span per request, named `METHOD /route/template`; database spans whose statements hold placeholders, never values; and `dose_log.create` with `meditrack.outcome`, `meditrack.late` and `meditrack.error_code`.
- **Metrics:**
  - `meditrack.dose_log.attempts{outcome}`: the alert's SLI. `outcome` is `created`, `duplicate`, `rejected` or `error`, and only `error` (a 5xx) counts against it.
  - `meditrack.db.errors{operation}`: `read` for GET and HEAD requests, `write` otherwise.
  - `meditrack.build.info{version, environment}`: always 1.
  - `http.server.duration`: in ms, with `http.method`, `http.status_code` and `http.target`. These are the instrumentation's default semantic conventions, which put the route template in `http.target`, never the raw path.
  - Also `http.server.active_requests`, `http.server.request.size`, `http.server.response.size` and `db.client.connections.usage`.
- **Logs:** `dose_log.created`, `dose_log.duplicate`, `dose_log.rejected`, `dose_log.error` and `request.failed`, each with its trace and span IDs.
