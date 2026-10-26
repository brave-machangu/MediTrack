# MediTrack backend

FastAPI service implementing [`api/openapi.yaml`](../api/openapi.yaml). Structure and rules: [docs/architecture.md §3](../docs/architecture.md#3-backend-structure).

## Run

Requires [uv](https://docs.astral.sh/uv/). It installs Python 3.12 (from `.python-version`) and the locked dependencies.

```bash
cd backend
uv sync
uv run uvicorn app.main:create_app --factory --reload   # http://localhost:8000/healthz
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

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./meditrack.db` | SQLAlchemy URL. PostgreSQL in Compose and deployments (MT-013, MT-030). |
| `APP_ENV` | `local` | One of `local`, `test`, `ci`, `dev`, `production`. |
| `APP_VERSION` | `dev` | Git SHA or release tag, reported by `/healthz` and `/readyz`; set at image build time. |

Telemetry and fault-injection settings are added by MT-022 and MT-023.
