"""App factory. Run locally with:

uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log --reload

--no-access-log: uvicorn's access log prints raw paths, which contain IDs (security.md §2);
failed requests are logged by app.telemetry with the route template instead.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI
from starlette.routing import Route

from app.api import doses, health, medications, patients, reports, schedules
from app.api.deps import AppContext
from app.clock import Clock, SystemClock
from app.config import Settings
from app.db.session import make_engine, make_session_factory
from app.domain.types import DoseRules
from app.errors import install_error_handlers, internal_error_response
from app.telemetry import Telemetry, instrument, setup_telemetry


def create_app(
    settings: Settings | None = None,
    clock: Clock | None = None,
    telemetry: Telemetry | None = None,
) -> FastAPI:
    settings = settings or Settings()
    telemetry = telemetry or setup_telemetry(settings)
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        telemetry.start()
        yield
        telemetry.stop()
        engine.dispose()

    app = FastAPI(
        title="MediTrack API",
        version=settings.version,
        # api/openapi.yaml is the contract; don't serve a second, generated one.
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.context = AppContext(
        settings=settings,
        clock=clock or SystemClock(),
        engine=engine,
        session_factory=make_session_factory(engine),
        dose_rules=DoseRules(
            early_log_window=timedelta(minutes=settings.early_log_window_minutes),
            late_log_limit=timedelta(minutes=settings.late_log_limit_minutes),
        ),
    )

    routers = (
        health.router,
        patients.router,
        medications.router,
        schedules.router,
        doses.router,
        reports.router,
    )
    for router in routers:
        app.include_router(router)
    install_error_handlers(
        app, [route for router in routers for route in router.routes if isinstance(route, Route)]
    )
    instrument(app, telemetry, internal_error_response)
    return app
