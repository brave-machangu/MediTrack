# MediTrack backend

FastAPI service implementing [`api/openapi.yaml`](../api/openapi.yaml). Structure and rules: [docs/architecture.md §3](../docs/architecture.md#3-backend-structure).

## Run

Requires [uv](https://docs.astral.sh/uv/). It installs Python 3.12 (from `.python-version`) and the locked dependencies.

```bash
cd backend
uv sync
uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload   # http://localhost:8000/healthz
```

## Check

```bash
uv run ruff check .        # lint, incl. the ban on datetime.now()/utcnow()/date.today() outside app/clock.py
uv run ruff format --check .
uv run mypy app            # strict
uv run pytest              # unit + integration (SQLite)
```

## Configuration

Settings are read from environment variables (`app/config.py`). No variable is required for local development.

Every variable uses the `MEDITRACK_` prefix, except `DATABASE_URL`, which keeps its conventional name because hosted platforms inject it (Lead decision Q5 in [DESIGN.md](DESIGN.md)). No variable has a secret as its default.

| Variable | Meaning | Default | Example |
|---|---|---|---|
| `DATABASE_URL` | SQLAlchemy URL. PostgreSQL in Compose and deployments (MT-013, MT-030). | `sqlite:///./meditrack.db` | `postgresql+psycopg://meditrack:<password>@db:5432/meditrack` |
| `MEDITRACK_ENV` | One of `local`, `test`, `ci`, `dev`, `production`. | `local` | `production` |
| `MEDITRACK_VERSION` | Git SHA or release tag, reported by `/healthz` and `/readyz`. The Dockerfile sets it from the `GIT_SHA` build arg (MT-021). | `dev` | `3f2c1a9` |

Telemetry and fault-injection settings are added by MT-022 and MT-023.
