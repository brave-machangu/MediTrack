"""Spans are scrubbed before export (security.md §2): only allowlisted attributes, and no text
from the database's error message, which can quote the values of a violated key."""

from __future__ import annotations

from opentelemetry.sdk.trace import Event, ReadableSpan
from opentelemetry.trace import SpanKind, Status, StatusCode

from app.telemetry import scrub

# The shape of a failed INSERT's span on PostgreSQL, as the SQLAlchemy instrumentation leaves it.
DUPLICATE_KEY = (
    "duplicate key value violates unique constraint "
    '"uq_dose_log_schedule_time" DETAIL: Key (schedule_id, scheduled_for)='
    "(PRIVACY-CANARY-ID, 2026-11-02 06:00:00+00) already exists."
)


def failed_insert_span() -> ReadableSpan:
    return ReadableSpan(
        name="INSERT meditrack",
        kind=SpanKind.CLIENT,
        attributes={
            "db.system": "postgresql",
            "db.statement": "INSERT INTO dose_logs (id, note) VALUES (%(id)s::UUID, %(note)s)",
            "db.user": "meditrack",
            "net.peer.name": "db",
            "net.peer.port": 5432,
        },
        events=[
            Event(
                "exception",
                {"exception.type": "UniqueViolation", "exception.message": DUPLICATE_KEY},
            )
        ],
        status=Status(StatusCode.ERROR, DUPLICATE_KEY),
    )


def test_scrub_keeps_only_allowlisted_attributes() -> None:
    clean = scrub(failed_insert_span())
    assert dict(clean.attributes or {}) == {
        "db.system": "postgresql",
        "db.statement": "INSERT INTO dose_logs (id, note) VALUES (%(id)s::UUID, %(note)s)",
    }
    assert [(event.name, dict(event.attributes or {})) for event in clean.events] == [
        ("exception", {"exception.type": "UniqueViolation"})
    ]


def test_scrub_keeps_the_error_status_but_not_its_text() -> None:
    clean = scrub(failed_insert_span())
    assert (clean.status.status_code, clean.status.description) == (StatusCode.ERROR, None)
    assert (clean.name, clean.kind) == ("INSERT meditrack", SpanKind.CLIENT)
