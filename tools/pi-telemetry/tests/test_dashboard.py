from __future__ import annotations

import io
import sys
from types import SimpleNamespace

from pi_telemetry import __author__, __license__, __version__
from pi_telemetry import dashboard


class RecordingHandler(dashboard.DashboardHandler):
    def send_response(self, code, message=None) -> None:  # type: ignore[no-untyped-def]
        self.status = code

    def send_header(self, keyword, value) -> None:  # type: ignore[no-untyped-def]
        self.headers[keyword] = value

    def end_headers(self) -> None:
        self.ended = True


def make_handler() -> RecordingHandler:
    handler = object.__new__(RecordingHandler)
    handler.status = None
    handler.headers = {}
    handler.ended = False
    handler.wfile = io.BytesIO()
    return handler


def test_package_metadata() -> None:
    assert __version__ == "1.0.0"
    assert __author__ == "ReconLion"
    assert __license__ == "MIT"


def test_format_duration() -> None:
    assert dashboard.format_duration(59) == "0m"
    assert dashboard.format_duration(3600) == "1h 0m"
    assert dashboard.format_duration(90061) == "1d 1h 1m"


def test_parse_args_defaults(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["pi-telemetry"])

    args = dashboard.parse_args()

    assert args.host == dashboard.DEFAULT_HOST
    assert args.port == dashboard.DEFAULT_PORT


def test_throttle_cache_reuses_recent_result(monkeypatch) -> None:
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout="throttled=0x0\n", stderr="", returncode=0)

    monkeypatch.setattr(dashboard.subprocess, "run", fake_run)
    cache = dashboard.ThrottleCache()

    assert cache.get_throttle_status() == "throttled=0x0 (clear)"
    assert cache.get_throttle_status() == "throttled=0x0 (clear)"
    assert len(calls) == 1


def test_health_endpoint_security_headers() -> None:
    handler = make_handler()

    handler.send_json({"ok": True})

    assert handler.status == 200
    assert handler.headers["Content-Type"] == "application/json; charset=utf-8"
    assert handler.headers["Cache-Control"] == "no-store"
    assert handler.headers["X-Content-Type-Options"] == "nosniff"
    assert handler.wfile.getvalue() == b'{"ok": true}'


def test_html_endpoint_frame_and_csp_headers() -> None:
    handler = make_handler()

    handler.send_html()

    assert handler.status == 200
    assert handler.headers["X-Frame-Options"] == "DENY"
    assert handler.headers["Content-Security-Policy"] == "default-src 'self'"
