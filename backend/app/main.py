"""App factory. Run locally with:

uv run uvicorn app.main:create_app --factory --reload
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api import health
from app.clock import Clock, SystemClock
from app.config import Settings
from app.db.session import make_engine
from app.errors import install_error_handlers


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="MediTrack API",
        version=settings.version,
        # api/openapi.yaml is the contract; don't serve a second, generated one.
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.clock = clock or SystemClock()
    app.state.engine = make_engine(settings.database_url)

    install_error_handlers(app)
    app.include_router(health.router)
    return app
