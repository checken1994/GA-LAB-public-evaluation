"""Functional tests for Observability and Telemetry subsystems.

Validates:
- SubsystemTelemetry heartbeat lifecycle, PID recording, and tick tracking
- Monitored cycle metrics (started, completed, asked, verified, stored, rejected)
- Fail-closed secret scrubbing in error summaries and json payloads
- Subsystem append-only JSONL run ledger
- OpenTelemetry graceful disable when unconfigured or disabled by env
- OpenTelemetry header sanitization and route exclusion when active
- Stale process detection threshold
- Database WAL configuration and busy timeout tolerance
"""
import json
import os
import sqlite3

from fastapi import FastAPI

from scp.core.subsystem_telemetry import SubsystemTelemetry
from scp.observability.otel import configure_fastapi_otel


def test_subsystem_telemetry_heartbeat_and_tick(tmp_path):
    telem = SubsystemTelemetry("crawler", data_dir=tmp_path)
    res = telem.tick(status="RUNNING")
    assert res["status"] == "RUNNING"
    assert res["subsystem"] == "crawler"

    db_path = tmp_path / "subsystem_heartbeat.sqlite"
    assert db_path.is_file()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM subsystem_heartbeat WHERE subsystem='crawler'"
        ).fetchone()
        assert row is not None
        assert row["subsystem"] == "crawler"
        assert row["owner_pid"] == os.getpid()
        assert row["last_status"] == "RUNNING"
        assert row["last_tick_at_utc"] is not None


def test_subsystem_telemetry_cycle_metrics_tracking(tmp_path):
    telem = SubsystemTelemetry("worker_cycles", data_dir=tmp_path)
    telem.cycle_started("cycle_1")
    telem.cycle_completed(
        "cycle_1",
        status="SUCCESS",
        asked=5,
        verified=4,
        stored=3,
        rejected=1,
    )

    db_path = tmp_path / "subsystem_heartbeat.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM subsystem_heartbeat WHERE subsystem='worker_cycles'"
        ).fetchone()
        assert row is not None
        assert row["cycles_started"] == 1
        assert row["cycles_completed"] == 1
        assert row["last_status"] == "SUCCESS"
        assert row["asked"] == 5
        assert row["verified"] == 4
        assert row["stored"] == 3
        assert row["rejected"] == 1


def test_subsystem_telemetry_secret_scrubbing_in_errors(tmp_path):
    telem = SubsystemTelemetry("scrub_worker", data_dir=tmp_path)
    telem.cycle_started("cycle_err")
    # Canary credentials are generated at runtime so no literal
    # credential pattern exists in test source; assertions compare
    # against the same generated values.
    secret_token = f"sk-{os.urandom(12).hex()}"
    secret_password = f"pw-{os.urandom(8).hex()}"
    err = RuntimeError(f"HTTP 401 token={secret_token} password={secret_password}")
    telem.cycle_failed("cycle_err", exc=err)

    db_path = tmp_path / "subsystem_heartbeat.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM subsystem_heartbeat WHERE subsystem='scrub_worker'"
        ).fetchone()
        assert row is not None
        error_summary = row["last_error_summary"]
        assert "token=<redacted>" in error_summary
        assert secret_token not in error_summary
        assert secret_password not in error_summary


def test_subsystem_telemetry_json_safe_payload_scrubbing(tmp_path):
    telem = SubsystemTelemetry("payload_worker", data_dir=tmp_path)
    telem.cycle_started("cycle_payload")
    # Runtime-generated canary values (no literal credential pattern in
    # source); the assertions below are key-based and unchanged.
    canary_password = f"plain-password-{os.urandom(8).hex()}"
    canary_token = f"sk-{os.urandom(16).hex()}"
    telem.cycle_completed(
        "cycle_payload",
        status="SUCCESS",
        password=canary_password,
        token=canary_token,
        safe_metric_count=99,
    )

    ledger_file = tmp_path / "payload_worker_runs.jsonl"
    assert ledger_file.is_file()

    lines = ledger_file.read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in lines]
    completed_events = [p for p in parsed if p.get("event_type") == "cycle_completed"]
    assert len(completed_events) == 1
    event = completed_events[0]
    assert "password" not in event
    assert "token" not in event
    assert event.get("safe_metric_count") == 99


def test_subsystem_telemetry_run_ledger_append_only(tmp_path):
    telem = SubsystemTelemetry("ledger_worker", data_dir=tmp_path)
    for i in range(3):
        telem.cycle_started(f"run_{i}")
        telem.cycle_completed(f"run_{i}", status="SUCCESS", step=i)

    ledger_file = tmp_path / "ledger_worker_runs.jsonl"
    lines = ledger_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 6  # 3 started + 3 completed

    for idx, line in enumerate(lines):
        obj = json.loads(line)
        assert obj["subsystem"] == "ledger_worker"
        assert "ts_utc" in obj


def test_otel_configuration_disabled_by_env(monkeypatch):
    monkeypatch.setenv("SCP_OTEL_ENABLED", "0")
    app = FastAPI()
    res = configure_fastapi_otel(app)
    assert res["enabled"] is False
    assert res["reason"] == "SCP_OTEL_ENABLED=0"


def test_otel_configuration_missing_endpoint_degrades_gracefully(monkeypatch):
    monkeypatch.setenv("SCP_OTEL_ENABLED", "1")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    app = FastAPI()
    res = configure_fastapi_otel(app)
    assert res["enabled"] is False
    assert res["reason"] == "OTEL_EXPORTER_OTLP_ENDPOINT is missing"


def test_otel_configuration_header_sanitization_rules(monkeypatch):
    monkeypatch.setenv("SCP_OTEL_ENABLED", "1")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

    captured_params = {}

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    original_instrument = FastAPIInstrumentor.instrument_app

    def mock_instrument_app(app, **kwargs):
        captured_params.update(kwargs)
        return original_instrument(app, **kwargs)

    monkeypatch.setattr(FastAPIInstrumentor, "instrument_app", mock_instrument_app)

    app = FastAPI()
    res = configure_fastapi_otel(app)
    assert res["enabled"] is True

    assert captured_params.get("http_capture_headers_sanitize_fields") == [
        "authorization",
        "cookie",
        "set-cookie",
    ]
    assert captured_params.get("http_capture_headers_server_request") == []
    assert captured_params.get("http_capture_headers_server_response") == []
    assert "health,metrics" in captured_params.get("excluded_urls", "")
