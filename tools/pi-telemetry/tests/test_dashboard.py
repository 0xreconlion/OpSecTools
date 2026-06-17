from __future__ import annotations

import io
import json
import sqlite3
import sys
import time
from types import SimpleNamespace

from pi_telemetry import __author__, __license__, __version__
from pi_telemetry import dashboard
from pi_telemetry import updater


class RecordingHandler(dashboard.DashboardHandler):
    def send_response(self, code, message=None) -> None:  # type: ignore[no-untyped-def]
        self.status = code

    def send_header(self, keyword, value) -> None:  # type: ignore[no-untyped-def]
        self.headers[keyword] = value

    def end_headers(self) -> None:
        self.ended = True


class BrokenPipeWriter:
    def write(self, body: bytes) -> None:
        raise BrokenPipeError


def make_handler() -> RecordingHandler:
    handler = object.__new__(RecordingHandler)
    handler.status = None
    handler.headers = {}
    handler.ended = False
    handler.wfile = io.BytesIO()
    return handler


def make_codex_state(path) -> None:  # type: ignore[no-untyped-def]
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE threads (
                id TEXT,
                created_at REAL,
                updated_at REAL,
                created_at_ms INTEGER,
                updated_at_ms INTEGER,
                model_provider TEXT,
                model TEXT,
                tokens_used INTEGER,
                cwd TEXT,
                title TEXT,
                first_user_message TEXT,
                cli_version TEXT,
                source TEXT,
                thread_source TEXT
            )
            """
        )
        now_ms = int(time.time() * 1000)
        connection.executemany(
            """
            INSERT INTO threads (
                id,
                created_at,
                updated_at,
                created_at_ms,
                updated_at_ms,
                model_provider,
                model,
                tokens_used,
                cwd,
                title,
                first_user_message,
                cli_version,
                source,
                thread_source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "abcdef1234567890",
                    now_ms / 1000 - 120,
                    now_ms / 1000 - 30,
                    now_ms - 120_000,
                    now_ms - 30_000,
                    "openai",
                    "gpt-5-codex",
                    1200,
                    "/home/nsp/SecretProject",
                    "DO NOT LEAK: prompt title",
                    "DO NOT LEAK: user prompt text",
                    "0.99.0",
                    "codex-cli",
                    "cli",
                ),
                (
                    "bbbbbb1234567890",
                    now_ms / 1000 - 240,
                    now_ms / 1000 - 90,
                    now_ms - 240_000,
                    now_ms - 90_000,
                    "openai",
                    "gpt-5-codex",
                    800,
                    "/home/nsp/OpSecTools",
                    "also private",
                    "also private prompt",
                    "0.99.0",
                    "codex-cli",
                    "cli",
                ),
            ],
        )
        connection.commit()
    finally:
        connection.close()


def test_package_metadata() -> None:
    assert __version__ == "1.1.1"
    assert __author__ == "ReconLion"
    assert __license__ == "MIT"


def test_format_duration() -> None:
    assert dashboard.format_duration(59) == "0m"
    assert dashboard.format_duration(3600) == "1h 0m"
    assert dashboard.format_duration(90061) == "1d 1h 1m"


def test_parse_args_defaults(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["pi-telemetry"])
    monkeypatch.delenv("PI_TELEMETRY_BIND", raising=False)
    monkeypatch.delenv("PI_TELEMETRY_PORT", raising=False)
    monkeypatch.delenv("PI_TELEMETRY_LLM", raising=False)
    monkeypatch.delenv("PI_TELEMETRY_CODEX_STATE", raising=False)
    monkeypatch.delenv("PI_TELEMETRY_CODEX_PROCESS", raising=False)

    args = dashboard.parse_args()

    assert args.host == dashboard.DEFAULT_HOST
    assert args.port == dashboard.DEFAULT_PORT
    assert args.llm_telemetry is True
    assert args.codex_state_path == str(dashboard.CODEX_STATE_PATH)
    assert args.codex_process_marker == dashboard.DEFAULT_CODEX_PROCESS_MARKER


def test_parse_args_uses_environment_defaults(monkeypatch, tmp_path) -> None:
    codex_state = tmp_path / "state.sqlite"
    monkeypatch.setattr(sys, "argv", ["pi-telemetry"])
    monkeypatch.setenv("PI_TELEMETRY_BIND", "0.0.0.0")
    monkeypatch.setenv("PI_TELEMETRY_PORT", "9191")
    monkeypatch.setenv("PI_TELEMETRY_LLM", "off")
    monkeypatch.setenv("PI_TELEMETRY_CODEX_STATE", str(codex_state))
    monkeypatch.setenv("PI_TELEMETRY_CODEX_PROCESS", "ollama")

    args = dashboard.parse_args()

    assert args.host == "0.0.0.0"
    assert args.port == 9191
    assert args.llm_telemetry is False
    assert args.codex_state_path == str(codex_state)
    assert args.codex_process_marker == "ollama"


def test_parse_args_cli_overrides_environment(monkeypatch, tmp_path) -> None:
    codex_state = tmp_path / "state.sqlite"
    monkeypatch.setenv("PI_TELEMETRY_BIND", "0.0.0.0")
    monkeypatch.setenv("PI_TELEMETRY_PORT", "9191")
    monkeypatch.setenv("PI_TELEMETRY_LLM", "off")
    monkeypatch.setenv("PI_TELEMETRY_CODEX_STATE", "/ignored.sqlite")
    monkeypatch.setenv("PI_TELEMETRY_CODEX_PROCESS", "ollama")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pi-telemetry",
            "--host",
            "127.0.0.2",
            "--port",
            "9292",
            "--llm-telemetry",
            "--codex-state-path",
            str(codex_state),
            "--codex-process-marker",
            "codex",
        ],
    )

    args = dashboard.parse_args()

    assert args.host == "127.0.0.2"
    assert args.port == 9292
    assert args.llm_telemetry is True
    assert args.codex_state_path == str(codex_state)
    assert args.codex_process_marker == "codex"


def test_load_update_notice_from_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        updater.UPDATE_NOTICE_ENV,
        json.dumps({"available": True, "latest_version": "1.1.0"}),
    )

    notice = dashboard.load_update_notice()

    assert notice["available"] is True
    assert notice["latest_version"] == "1.1.0"


def test_throttle_cache_reuses_recent_result(monkeypatch) -> None:
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout="throttled=0x0\n", stderr="", returncode=0)

    monkeypatch.setattr(dashboard.subprocess, "run", fake_run)
    cache = dashboard.ThrottleCache(vcgencmd_path="/usr/bin/vcgencmd")

    assert cache.get_throttle_status() == "throttled=0x0 (clear)"
    assert cache.get_throttle_status() == "throttled=0x0 (clear)"
    assert len(calls) == 1
    assert calls[0][0][0] == ["/usr/bin/vcgencmd", "get_throttled"]


def test_throttle_cache_unavailable_when_vcgencmd_missing(monkeypatch) -> None:
    def fail_run(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called without vcgencmd")

    monkeypatch.setattr(dashboard.shutil, "which", lambda command: None)
    monkeypatch.setattr(dashboard.subprocess, "run", fail_run)
    cache = dashboard.ThrottleCache()

    assert cache.get_throttle_status() == "unavailable"


def test_codex_telemetry_missing_state_fails_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        dashboard,
        "codex_process_snapshot",
        lambda marker=dashboard.DEFAULT_CODEX_PROCESS_MARKER: {
            "count": 0,
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_bytes": 0,
            "top": [],
        },
    )
    state = dashboard.CodexTelemetryState(tmp_path / "missing.sqlite")

    snapshot = state.snapshot()

    assert snapshot["available"] is False
    assert snapshot["privacy"] == "metadata-only"
    assert snapshot["summary"]["total_tokens"] == 0  # type: ignore[index]
    assert "not found" in snapshot["warnings"][0]  # type: ignore[index]


def test_codex_telemetry_disabled_skips_collectors(tmp_path, monkeypatch) -> None:
    def fail_snapshot(marker=dashboard.DEFAULT_CODEX_PROCESS_MARKER):  # type: ignore[no-untyped-def]
        raise AssertionError("process scanning should be skipped when LLM telemetry is disabled")

    monkeypatch.setattr(dashboard, "codex_process_snapshot", fail_snapshot)
    state = dashboard.CodexTelemetryState(tmp_path / "state_5.sqlite", enabled=False)

    snapshot = state.snapshot()

    assert snapshot["available"] is False
    assert snapshot["summary"]["pressure"] == "idle"  # type: ignore[index]
    assert "disabled" in snapshot["warnings"][0]  # type: ignore[index]


def test_codex_telemetry_reads_metadata_without_prompt_content(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "state_5.sqlite"
    make_codex_state(db_path)
    monkeypatch.setattr(
        dashboard,
        "codex_process_snapshot",
        lambda marker=dashboard.DEFAULT_CODEX_PROCESS_MARKER: {
            "count": 1,
            "cpu_percent": 12.5,
            "memory_percent": 3.0,
            "memory_bytes": 128 * 1024 * 1024,
            "top": [
                {
                    "pid": 123,
                    "name": "codex",
                    "cpu_percent": 12.5,
                    "memory_percent": 3.0,
                    "memory_bytes": 128 * 1024 * 1024,
                }
            ],
        },
    )
    state = dashboard.CodexTelemetryState(db_path)

    snapshot = state.snapshot()
    encoded = json.dumps(snapshot)

    assert snapshot["available"] is True
    assert snapshot["summary"]["thread_count"] == 2  # type: ignore[index]
    assert snapshot["summary"]["total_tokens"] == 2000  # type: ignore[index]
    assert snapshot["summary"]["dominant_model"] == "openai/gpt-5-codex"  # type: ignore[index]
    assert snapshot["summary"]["pressure"] == "active"  # type: ignore[index]
    assert snapshot["models"][0]["tokens_used"] == 2000  # type: ignore[index]
    assert snapshot["recent_threads"][0]["thread_id"] == "abcdef1234"  # type: ignore[index]
    assert snapshot["recent_threads"][0]["cwd"] == "SecretProject"  # type: ignore[index]
    assert "/home/nsp/" not in encoded
    assert "DO NOT LEAK" not in encoded
    assert "first_user_message" not in encoded
    assert "title" not in encoded


def test_codex_telemetry_reports_token_delta(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "state_5.sqlite"
    make_codex_state(db_path)
    monkeypatch.setattr(
        dashboard,
        "codex_process_snapshot",
        lambda marker=dashboard.DEFAULT_CODEX_PROCESS_MARKER: {
            "count": 0,
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_bytes": 0,
            "top": [],
        },
    )
    state = dashboard.CodexTelemetryState(db_path)
    state.previous_total_tokens = 1500
    state.previous_sample_time = time.time() - 60

    snapshot = state.snapshot()

    assert snapshot["summary"]["token_delta"] == 500  # type: ignore[index]
    assert 490 <= snapshot["summary"]["tokens_per_minute"] <= 510  # type: ignore[index]


def test_process_marker_is_configurable() -> None:
    assert dashboard.matches_codex_process("python", ["ollama", "serve"], marker="ollama")
    assert not dashboard.matches_codex_process("python", ["ollama", "serve"], marker="codex")


def test_health_endpoint_security_headers() -> None:
    handler = make_handler()

    handler.send_json({"ok": True})

    assert handler.status == 200
    assert handler.headers["Content-Type"] == "application/json; charset=utf-8"
    assert handler.headers["Cache-Control"] == "no-store"
    assert handler.headers["X-Content-Type-Options"] == "nosniff"
    assert handler.wfile.getvalue() == b'{"ok": true}'


def test_response_body_write_ignores_client_abort() -> None:
    handler = make_handler()
    handler.wfile = BrokenPipeWriter()

    handler.send_json({"ok": True})

    assert handler.status == 200
    assert handler.ended is True


def test_html_endpoint_frame_and_csp_headers() -> None:
    handler = make_handler()

    handler.send_html()

    csp = handler.headers["Content-Security-Policy"]

    assert handler.status == 200
    assert handler.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in csp
    assert "script-src 'nonce-" in csp
    assert "style-src 'nonce-" in csp
    assert "connect-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert b"__CSP_NONCE__" not in handler.wfile.getvalue()


def test_embedded_client_uses_resize_safe_polling() -> None:
    assert "ResizeObserver" in dashboard.HTML
    assert "AbortController" in dashboard.HTML
    assert "visibilitychange" in dashboard.HTML
    assert "requestAnimationFrame" in dashboard.HTML
    assert "window.__piTelemetryStatus" in dashboard.HTML
    assert 'data-view="llm"' in dashboard.HTML
    assert 'id="llm-view"' in dashboard.HTML
    assert "function renderLlm" in dashboard.HTML
    assert "activeView" in dashboard.HTML
    assert "update-banner" in dashboard.HTML
    assert "Copy command" in dashboard.HTML


def test_embedded_client_avoids_inline_style_attributes() -> None:
    assert " style=" not in dashboard.HTML


def test_head_health_endpoint_has_headers_without_body() -> None:
    handler = make_handler()
    handler.path = "/health"

    handler.do_HEAD()

    assert handler.status == 200
    assert handler.headers["Content-Type"] == "application/json; charset=utf-8"
    assert handler.headers["Content-Length"] == str(len(b'{"ok": true}'))
    assert handler.wfile.getvalue() == b""


def test_head_unknown_endpoint_has_not_found_without_body() -> None:
    handler = make_handler()
    handler.path = "/missing"

    handler.do_HEAD()

    assert handler.status == 404
    assert handler.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert handler.wfile.getvalue() == b""


def test_version_comparison_prefers_newer_release() -> None:
    assert updater.is_newer_version("1.2.0", "1.1.9")
    assert not updater.is_newer_version("1.0.0", "1.0.0")


def test_build_update_notice_prefers_git_root(monkeypatch, tmp_path) -> None:
    install_root = tmp_path / "pi-telemetry"
    (install_root / ".git").mkdir(parents=True)
    monkeypatch.setattr(updater, "latest_git_version", lambda repo_root, timeout=1.5: "1.1.0")

    notice = updater.build_update_notice("1.0.0", install_root=install_root)

    assert notice["available"] is True
    assert notice["channel"] == "git"
    assert notice["latest_version"] == "1.1.0"
    assert "git -C" in notice["update_command"]  # type: ignore[index]
    assert notice["auto_update_ready"] is False


def test_build_update_notice_falls_back_to_pypi(monkeypatch) -> None:
    monkeypatch.setattr(updater, "latest_pypi_version", lambda timeout=1.5: "1.0.1")

    notice = updater.build_update_notice("1.0.0")

    assert notice["available"] is True
    assert notice["channel"] == "pypi"
    assert "pip install --upgrade" in notice["update_command"]  # type: ignore[index]
    assert notice["auto_update_ready"] is False


def test_build_update_notice_when_current_version_matches(monkeypatch, tmp_path) -> None:
    install_root = tmp_path / "pi-telemetry"
    (install_root / ".git").mkdir(parents=True)
    monkeypatch.setattr(updater, "latest_git_version", lambda repo_root, timeout=1.5: "1.1.0")

    notice = updater.build_update_notice("1.1.0", install_root=install_root)

    assert notice["available"] is False
    assert notice["channel"] == "git"
    assert notice["summary"] == "No newer git tag is available."
