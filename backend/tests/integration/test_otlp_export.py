"""With OTEL_EXPORTER_OTLP_ENDPOINT set, traces, metrics and logs reach a collector over
OTLP/HTTP at the standard signal paths, without the private values that went into the API."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.clock import FixedClock
from app.config import Settings
from app.main import create_app


class Collector(ThreadingHTTPServer):
    """Accepts every OTLP/HTTP export and keeps (path, body)."""

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _ExportHandler)
        self.received: list[tuple[str, bytes]] = []

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"


class _ExportHandler(BaseHTTPRequestHandler):
    server: Collector

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.received.append((self.path, body))
        self.send_response(200)
        self.send_header("Content-Type", "application/x-protobuf")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass  # keep the test output clean


@pytest.fixture
def collector() -> Iterator[Collector]:
    server = Collector()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


def test_signals_are_exported_over_otlp_when_an_endpoint_is_set(
    engine: Engine, database_url: str, clock: FixedClock, collector: Collector
) -> None:
    # A trailing slash on the base URL is allowed, as the exporters allow it.
    settings = Settings(database_url=database_url, otlp_endpoint=collector.url + "/")
    with TestClient(create_app(settings, clock)) as client:
        patient = client.post(
            "/api/v1/patients",
            json={"display_name": "PRIVACY-CANARY-PATIENT", "timezone": "Africa/Harare"},
        ).json()
        client.get(f"/api/v1/patients/{patient['id']}/medications?q=PRIVACY-CANARY-QUERY")
        client.get("/api/v1/patients/PRIVACY-CANARY-PATH")  # 404, logged as request.failed
    # Leaving the client shuts the app down, which flushes every signal.

    assert {path for path, _ in collector.received} == {"/v1/traces", "/v1/metrics", "/v1/logs"}
    for _, body in collector.received:
        assert b"PRIVACY-CANARY" not in body
        assert patient["id"].encode() not in body
