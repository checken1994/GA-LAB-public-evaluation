"""Small local telemetry primitives for long-lived SCP subsystems.

This module never stores prompts, answers, credentials, or raw file contents.
It records only bounded counters, hashes, lifecycle states, and redacted error
metadata so that a live process cannot be mistaken for a completed cycle.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
import uuid

logger = logging.getLogger(__name__)
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any

from scp.core.learning_outcome import LEARNING_OUTCOME_STATUSES, classify_learning_outcome

TERMINAL_STATUSES = LEARNING_OUTCOME_STATUSES | {
    "STALE",
    "TELEMETRY_DEGRADED",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_error(exc: BaseException | None) -> tuple[str | None, str | None]:
    if exc is None:
        return None, None
    text = str(exc).replace("\r", " ").replace("\n", " ")
    # Do not persist obvious secret-bearing command fragments.
    lowered = text.lower()
    for marker in ("token=", "password=", "api_key=", "authorization:"):
        if marker in lowered:
            text = text[: lowered.index(marker)] + marker + "<redacted>"
            break
    return type(exc).__name__, text[:300]


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items() if str(k).lower() not in {"prompt", "answer", "token", "password", "secret", "api_key"}}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value[:100]]
    return str(value)[:300]


class SubsystemTelemetry:
    """Heartbeat + append-only run ledger for one named subsystem."""

    def __init__(self, subsystem: str, data_dir: str | Path = "data", stale_after_seconds: int = 45):
        self.subsystem = str(subsystem)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.heartbeat_db = self.data_dir / "subsystem_heartbeat.sqlite"
        self.ledger_path = self.data_dir / f"{self.subsystem}_runs.jsonl"
        self.stale_after_seconds = max(15, int(stale_after_seconds))
        self.instance_id = f"{self.subsystem}-{uuid.uuid4().hex}"
        self.pid = os.getpid()
        self.parent_pid = os.getppid()
        self._lock = threading.RLock()
        self._seq = 0
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        # Telemetry must tolerate a busy runtime DB without killing the
        # monitored worker. WAL + a bounded 15s wait gives writers room while
        # the caller-side ticker still retries instead of dying.
        conn = sqlite3.connect(self.heartbeat_db, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=15000")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS subsystem_heartbeat (
                    subsystem TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL,
                    owner_pid INTEGER NOT NULL,
                    parent_pid INTEGER NOT NULL,
                    started_at_utc TEXT NOT NULL,
                    last_tick_at_utc TEXT NOT NULL,
                    last_cycle_started_at_utc TEXT,
                    last_cycle_completed_at_utc TEXT,
                    last_status TEXT NOT NULL,
                    last_error_class TEXT,
                    last_error_summary TEXT,
                    next_due_at_utc TEXT,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    cycles_started INTEGER NOT NULL DEFAULT 0,
                    cycles_completed INTEGER NOT NULL DEFAULT 0,
                    provider_calls INTEGER NOT NULL DEFAULT 0,
                    asked INTEGER NOT NULL DEFAULT 0,
                    verified INTEGER NOT NULL DEFAULT 0,
                    stored INTEGER NOT NULL DEFAULT 0,
                    rejected INTEGER NOT NULL DEFAULT 0,
                    config_hash TEXT,
                    ledger_seq INTEGER NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS subsystem_heartbeat_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    subsystem TEXT NOT NULL,
                    instance_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    run_id TEXT,
                    ts_utc TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )

    def _append_ledger(self, payload: dict[str, Any]) -> bool:
        try:
            with self.ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(_json_safe(payload), ensure_ascii=False, sort_keys=True) + "\n")
            return True
        except OSError as exc:
            logger.warning("subsystem_telemetry: ledger append failed for %s: %s", self.ledger_path, exc, exc_info=True)
            return False

    def _write(self, event_type: str, status: str, run_id: str | None = None, **payload: Any) -> dict[str, Any]:
        now = _utc_now()
        event = {
            "event_type": event_type,
            "subsystem": self.subsystem,
            "instance_id": self.instance_id,
            "owner_pid": self.pid,
            "parent_pid": self.parent_pid,
            "run_id": run_id,
            "status": status,
            "ts_utc": now,
            **_json_safe(payload),
        }
        # Heartbeats belong in SQLite current-state/events; only lifecycle and
        # cycle records go to the append-only JSONL run ledger.
        ledger_ok = True if event_type == "heartbeat" else self._append_ledger(event)
        if not ledger_ok:
            event["operation_status"] = status
            status = "DB_WRITE_FAILED"
            event["status"] = status
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute(
                "SELECT * FROM subsystem_heartbeat WHERE subsystem=?", (self.subsystem,)
            ).fetchone()
            current_data = dict(current) if current else {}
            defaults = {
                "started_at_utc": now,
                "last_cycle_started_at_utc": None,
                "last_cycle_completed_at_utc": None,
                "next_due_at_utc": None,
                "consecutive_failures": 0,
                "cycles_started": 0,
                "cycles_completed": 0,
                "provider_calls": 0,
                "asked": 0,
                "verified": 0,
                "stored": 0,
                "rejected": 0,
                "config_hash": None,
                "ledger_seq": 0,
            }
            for key, value in defaults.items():
                current_data.setdefault(key, value)
            if event_type == "cycle_started":
                current_data["cycles_started"] = int(current_data.get("cycles_started", 0)) + 1
                current_data["last_cycle_started_at_utc"] = now
            if event_type == "cycle_completed":
                current_data["cycles_completed"] = int(current_data.get("cycles_completed", 0)) + 1
                current_data["last_cycle_completed_at_utc"] = now
            if status in {"SUCCESS", "NO_NEW_FACTS"}:
                current_data["consecutive_failures"] = 0
            elif status in TERMINAL_STATUSES - {"DISABLED"}:
                current_data["consecutive_failures"] = int(current_data.get("consecutive_failures", 0)) + 1
            current_data.update({
                "subsystem": self.subsystem,
                "instance_id": self.instance_id,
                "owner_pid": self.pid,
                "parent_pid": self.parent_pid,
                "started_at_utc": current_data.get("started_at_utc") or now,
                "last_tick_at_utc": now,
                "last_status": status,
                "last_error_class": payload.get("error_class"),
                "last_error_summary": payload.get("error_summary"),
                "next_due_at_utc": payload.get("next_due_at_utc", current_data.get("next_due_at_utc")),
                "provider_calls": int(payload.get("provider_calls", current_data.get("provider_calls", 0)) or 0),
                "asked": int(payload.get("asked", current_data.get("asked", 0)) or 0),
                "verified": int(payload.get("verified", current_data.get("verified", 0)) or 0),
                "stored": int(payload.get("stored", current_data.get("stored", 0)) or 0),
                "rejected": int(payload.get("rejected", current_data.get("rejected", 0)) or 0),
                "config_hash": payload.get("config_hash", current_data.get("config_hash")),
                "updated_at_utc": now,
            })
            columns = [
                "subsystem", "instance_id", "owner_pid", "parent_pid", "started_at_utc",
                "last_tick_at_utc", "last_cycle_started_at_utc", "last_cycle_completed_at_utc",
                "last_status", "last_error_class", "last_error_summary", "next_due_at_utc",
                "consecutive_failures", "cycles_started", "cycles_completed", "provider_calls",
                "asked", "verified", "stored", "rejected", "config_hash", "ledger_seq", "updated_at_utc",
            ]
            values = [current_data.get(c) for c in columns]
            conn.execute(
                f"INSERT OR REPLACE INTO subsystem_heartbeat ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                values,
            )
            if event_type != "heartbeat":
                conn.execute(
                    "INSERT INTO subsystem_heartbeat_events(subsystem,instance_id,event_type,status,run_id,ts_utc,payload_json) VALUES(?,?,?,?,?,?,?)",
                    (self.subsystem, self.instance_id, event_type, status, run_id, now, json.dumps(_json_safe(payload), ensure_ascii=False, sort_keys=True)),
                )
            conn.commit()
        self._seq += 1
        if not ledger_ok:
            event["ledger_write_error"] = True
        return event

    def start(self, *, mode: str = "background", config: dict[str, Any] | None = None) -> dict[str, Any]:
        config_json = json.dumps(_json_safe(config or {}), sort_keys=True).encode("utf-8")
        config_hash = hashlib.sha256(config_json).hexdigest()
        with self._lock:
            # A subsystem intentionally disabled by policy is already in a
            # terminal state. Recording it as STARTING left durable ledgers
            # full of false unfinished runs after every safe startup.
            initial_status = "DISABLED" if mode == "disabled" else "STARTING"
            return self._write("started", initial_status, config_hash=config_hash, policy_mode=mode)

    def tick(self, *, status: str = "IDLE", next_due_at_utc: str | None = None, **counters: Any) -> dict[str, Any]:
        with self._lock:
            return self._write("heartbeat", status, next_due_at_utc=next_due_at_utc, **counters)

    def cycle_started(self, run_id: str, **payload: Any) -> dict[str, Any]:
        with self._lock:
            return self._write("cycle_started", "RUNNING", run_id=run_id, **payload)

    def cycle_completed(self, run_id: str, status: str, **payload: Any) -> dict[str, Any]:
        status = status if status in TERMINAL_STATUSES else "TELEMETRY_DEGRADED"
        with self._lock:
            return self._write("cycle_completed", status, run_id=run_id, **payload)

    def cycle_failed(self, run_id: str, exc: BaseException, status: str = "PROVIDER_FAILED", **payload: Any) -> dict[str, Any]:
        error_class, error_summary = _safe_error(exc)
        with self._lock:
            return self._write("cycle_completed", status, run_id=run_id, error_class=error_class, error_summary=error_summary, **payload)

    def audit_failed(self, run_id: str, **payload: Any) -> dict[str, Any]:
        """Record missing companion audit evidence without counting work twice."""
        with self._lock:
            return self._write("audit_failed", "DB_WRITE_FAILED", run_id=run_id, **payload)

    def snapshot(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM subsystem_heartbeat WHERE subsystem=?", (self.subsystem,)).fetchone()
        if not row:
            return {"subsystem": self.subsystem, "status": "NEVER_STARTED", "fresh": False}
        out = dict(row)
        try:
            last = datetime.fromisoformat(str(out["last_tick_at_utc"]))
            age = max(0.0, (datetime.now(timezone.utc) - last).total_seconds())
        except (TypeError, ValueError) as exc:
            # silent-by-design: unparseable tick timestamp reports infinite age (never a fake fresh age).
            logger.debug("subsystem_telemetry: last_tick timestamp unparseable, age=inf: %s", exc, exc_info=True)
            age = float("inf")
        out["age_seconds"] = round(age, 3)
        # Disabled-by-policy is a deliberate terminal state, not a dead worker.
        out["fresh"] = age <= self.stale_after_seconds or out.get("last_status") == "DISABLED"
        if not out["fresh"] and out.get("last_status") not in {"DISABLED", "NEVER_STARTED"}:
            out["last_status"] = "STALE"
        return out




def classify_cycle_status(result: Any, error: BaseException | None = None) -> str:
    return classify_learning_outcome(result, error)


def heartbeat_sleep(
    telemetry: SubsystemTelemetry | None,
    seconds: float,
    *,
    status: str = "IDLE",
    stop_event: threading.Event | None = None,
) -> None:
    """Sleep without making a healthy idle subsystem look dead.

    [L-03 fix 2026-09-28] When ``stop_event`` is set, wake immediately so
    shutdown (registry.stop_all) does not wait out the full sleep window
    (previously up to 86400s in 15s chunks while is_alive() stayed True).
    """
    deadline = time.time() + max(0.0, float(seconds))
    while time.time() < deadline:
        if stop_event is not None and stop_event.is_set():
            return
        remaining = max(0.0, deadline - time.time())
        if telemetry is not None:
            telemetry.tick(status=status, next_due_at_utc=str(deadline))
        chunk = min(15.0, remaining)
        if stop_event is not None:
            if stop_event.wait(chunk):
                return
        else:
            time.sleep(chunk)


def telemetry_async_cycle(func):
    """Decorate an async subsystem cycle with a separate evidence ledger."""
    @wraps(func)
    async def wrapped(self, *args, **kwargs):
        telemetry = getattr(self, "_telemetry", None)
        run_id = f"{getattr(telemetry, 'subsystem', 'subsystem')}-{time.time_ns()}"
        if telemetry is None:
            return await func(self, *args, **kwargs)
        telemetry.cycle_started(run_id, trigger=kwargs.get("trigger", "interval"))
        self._active_telemetry_run_id = run_id
        ticker = asyncio.create_task(_async_heartbeat_ticker(telemetry))
        try:
            result = await func(self, *args, **kwargs)
            status = classify_cycle_status(result)
            if isinstance(result, dict):
                result = dict(result)
                result.setdefault("status", status)
                result.setdefault("run_id", run_id)
            terminal = telemetry.cycle_completed(
                run_id,
                status,
                asked=(result or {}).get("asked", 0) if isinstance(result, dict) else 0,
                verified=(result or {}).get("verified", 0) if isinstance(result, dict) else 0,
                stored=(result or {}).get("stored", 0) if isinstance(result, dict) else 0,
                rejected=(result or {}).get("rejected", 0) if isinstance(result, dict) else 0,
                provider_calls=(result or {}).get("provider_calls", 0) if isinstance(result, dict) else 0,
            )
            if isinstance(result, dict) and terminal.get("ledger_write_error"):
                result.update(ledger_status="DB_WRITE_FAILED", ledger_write_error=True)
            return result
        except asyncio.CancelledError as exc:
            status = "TIMEOUT" if getattr(self, "_telemetry_timeout_requested", False) else "TELEMETRY_DEGRADED"
            telemetry.cycle_failed(run_id, exc, status=status)
            raise
        except BaseException as exc:
            telemetry.cycle_failed(run_id, exc, status=classify_cycle_status(None, exc))
            raise
        finally:
            self._active_telemetry_run_id = None
            ticker.cancel()
            try:
                await ticker
            except asyncio.CancelledError as exc:
                # silent-by-design: awaiting an already-cancelled ticker is the expected shutdown path.
                logger.debug("subsystem_telemetry: ticker cancellation observed: %s", exc, exc_info=True)
    return wrapped


async def _async_heartbeat_ticker(telemetry: SubsystemTelemetry) -> None:
    while True:
        await asyncio.sleep(15)
        telemetry.tick(status="RUNNING")


def telemetry_sync_cycle(func):
    """Synchronous equivalent used by Evolution's bounded cycle."""
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        telemetry = getattr(self, "_telemetry", None)
        run_id = f"{getattr(telemetry, 'subsystem', 'subsystem')}-{time.time_ns()}"
        if telemetry is None:
            return func(self, *args, **kwargs)
        telemetry.cycle_started(run_id, trigger=kwargs.get("trigger", "admin"))
        stop = threading.Event()
        def _tick_loop():
            while not stop.wait(15):
                telemetry.tick(status="RUNNING")
        ticker = threading.Thread(target=_tick_loop, name=f"{telemetry.subsystem}-heartbeat", daemon=True)
        ticker.start()
        try:
            result = func(self, *args, **kwargs)
            status = classify_cycle_status(result)
            terminal = telemetry.cycle_completed(
                run_id,
                status,
                bugs_found=(result or {}).get("bugs_found", 0) if isinstance(result, dict) else 0,
                bugs_fixed=(result or {}).get("bugs_fixed", 0) if isinstance(result, dict) else 0,
                verified=(result or {}).get("verified", 0) if isinstance(result, dict) else 0,
                stored=(result or {}).get("stored", 0) if isinstance(result, dict) else 0,
                promotion_status=(result or {}).get("promotion_status", "none") if isinstance(result, dict) else "none",
            )
            if isinstance(result, dict):
                result = dict(result)
                result.setdefault("status", status)
                result.setdefault("run_id", run_id)
                if terminal.get("ledger_write_error"):
                    result.update(ledger_status="DB_WRITE_FAILED", ledger_write_error=True)
            return result
        except BaseException as exc:
            telemetry.cycle_failed(run_id, exc, status="PROVIDER_FAILED")
            raise
        finally:
            stop.set()
            ticker.join(timeout=1)
    return wrapped


__all__ = ["SubsystemTelemetry", "TERMINAL_STATUSES", "classify_cycle_status", "heartbeat_sleep", "telemetry_async_cycle", "telemetry_sync_cycle"]
