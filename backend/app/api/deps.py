"""Request-scoped dependencies: the app context, a database session, the clock and telemetry."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.clock import Clock
from app.config import Settings
from app.domain.types import DoseRules
from app.fault import DoseLogFault
from app.telemetry import Telemetry


@dataclass(frozen=True, slots=True)
class AppContext:
    """Everything create_app() wires up, stored once on app.state."""

    settings: Settings
    clock: Clock
    engine: Engine
    session_factory: sessionmaker[Session]
    dose_rules: DoseRules
    telemetry: Telemetry
    dose_log_fault: DoseLogFault


def get_context(request: Request) -> AppContext:
    context = request.app.state.context
    if not isinstance(context, AppContext):
        raise RuntimeError("create_app() must set app.state.context")
    return context


ContextDep = Annotated[AppContext, Depends(get_context)]


def get_session(context: ContextDep) -> Iterator[Session]:
    with context.session_factory() as session:
        yield session


def get_clock(context: ContextDep) -> Clock:
    return context.clock


def get_dose_rules(context: ContextDep) -> DoseRules:
    return context.dose_rules


def get_telemetry(context: ContextDep) -> Telemetry:
    return context.telemetry


def get_dose_log_fault(context: ContextDep) -> DoseLogFault:
    return context.dose_log_fault


SessionDep = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]
DoseRulesDep = Annotated[DoseRules, Depends(get_dose_rules)]
TelemetryDep = Annotated[Telemetry, Depends(get_telemetry)]
DoseLogFaultDep = Annotated[DoseLogFault, Depends(get_dose_log_fault)]
