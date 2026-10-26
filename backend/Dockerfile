# MediTrack backend image (MT-021). Build from the repository root:
#   docker build --build-arg GIT_SHA=$(git rev-parse --short HEAD) -t meditrack-backend backend
# The same image runs every backend command; set DATABASE_URL (the app directory is read-only):
#   API:         docker run -p 8000:8000 -e DATABASE_URL=... meditrack-backend
#   Migrations:  docker run --rm -e DATABASE_URL=... meditrack-backend alembic upgrade head
#   Demo reset:  docker run --rm -e DATABASE_URL=... meditrack-backend python -m app.seed --reset

# Both stages use python:3.12-slim-trixie pinned by digest (security.md §4). The FROM lines are
# written out in full so Dependabot can propose updates.
FROM python:3.12-slim-trixie@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS build
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv==0.12.10
WORKDIR /app
# Dependencies first, so a code change doesn't reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

FROM python:3.12-slim-trixie@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS runtime
RUN groupadd --system --gid 10001 meditrack \
    && useradd --system --uid 10001 --gid meditrack --no-create-home \
        --home-dir /nonexistent --shell /usr/sbin/nologin meditrack
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Late, so a new commit only rebuilds these cheap layers.
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="meditrack-backend" \
      org.opencontainers.image.revision="${GIT_SHA}"
# PYTHONTZPATH empty: zoneinfo reads only the locked tzdata wheel, the same data the tests use,
# never the OS's zone files (ADR-004).
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONTZPATH="" \
    MEDITRACK_VERSION="${GIT_SHA}"

USER 10001:10001
EXPOSE 8000
# --no-access-log: uvicorn's access log prints raw paths, which contain IDs (security.md §2).
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
