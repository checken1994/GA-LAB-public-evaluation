"""Learning result, JSONL ledger and SQLite telemetry must agree."""
from __future__ import annotations

import asyncio
import json

import pytest

from scp.core.learning_run_ledger import ledger_run, record_learning_run
from scp.core.subsystem_telemetry import (
    SubsystemTelemetry,
    telemetry_async_cycle,
    telemetry_sync_cycle,
)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"asked": 1, "verified": 1, "stored": 0}, "UNKNOWN"),
        ({"asked": 2, "verified": 0, "stored": 0, "provider_failed": 2}, "PROVIDER_FAILED"),
        ({"asked": 1, "verified": 1, "stored": 0, "db_write_failed": True}, "DB_WRITE_FAILED"),
        ({"asked": 1, "verified": 1, "stored": 1}, "SUCCESS"),
        ({"asked": 1, "verified": 0, "stored": 0}, "VERIFY_REJECTED"),
        ({"asked": 0, "verified": 0, "stored": 0, "skipped_known": 3}, "NO_NEW_FACTS"),
        ({}, "UNKNOWN"),
    ],
)
def test_async_cycle_agrees_with_durable_outcomes(tmp_path, monkeypatch, payload, expected):
    learning_path = tmp_path / "learning_runs.jsonl"
    monkeypatch.setenv("SCP_LEARNING_RUN_LEDGER_PATH", str(learning_path))

    class Workload:
        def __init__(self):
            self._telemetry = SubsystemTelemetry("outcome_contract", tmp_path)

        @ledger_run("fast")
        @telemetry_async_cycle
        async def cycle(self):
            return dict(payload)

    workload = Workload()
    result = asyncio.run(workload.cycle())
    learning_row = json.loads(learning_path.read_text(encoding="utf-8").splitlines()[-1])
    events = [json.loads(line) for line in workload._telemetry.ledger_path.read_text(encoding="utf-8").splitlines()]
    terminal = next(event for event in reversed(events) if event["event_type"] == "cycle_completed")
    observed = {"learning": learning_row["status"], "telemetry": terminal["status"], "snapshot": workload._telemetry.snapshot()["last_status"]}
    assert observed == {"learning": expected, "telemetry": expected, "snapshot": expected}
    assert result.get("run_id")


def test_sync_telemetry_surfaces_storage_gap(tmp_path):
    class Workload:
        def __init__(self):
            self._telemetry = SubsystemTelemetry("sync_outcome", tmp_path)

        @telemetry_sync_cycle
        def cycle(self):
            return {"bugs_found": 1, "bugs_fixed": 1, "lessons_stored": 0}

    result = Workload().cycle()
    assert result["status"] == "UNKNOWN"
    assert result["run_id"]


def test_learning_audit_write_failure_is_not_success(tmp_path):
    blocked_path = tmp_path / "blocked-ledger"
    blocked_path.mkdir()
    row = record_learning_run(
        mode="fast", started_at="start", ended_at="end",
        result={"asked": 1, "verified": 1, "stored": 1}, ledger_path=blocked_path,
    )
    assert row["ledger_write_error"]
    assert row["status"] == "DB_WRITE_FAILED"
