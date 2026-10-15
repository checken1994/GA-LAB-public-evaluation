"""Bounded process wrapper for SCP evolution runs.

The evolution engine can call provider/analysis code that is not reliably
cancellable from a thread. This wrapper makes the run externally bounded and
fail-closed: a timed-out child is terminated, no partial result is reported as
success, and the parent records a sanitized TIMEOUT ledger row.
"""
from __future__ import annotations

import json
import logging
import multiprocessing as mp
import os
import queue
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scp.core.learning_outcome import classify_learning_outcome
from scp.core.learning_run_ledger import record_learning_run
from scp.core.subsystem_telemetry import SubsystemTelemetry

logger = logging.getLogger("scp.autofix.bounded_evolution")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_checkpoint(stage_file: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(stage_file).read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("bounded_evolution: stage file read failed for %s: %s", stage_file, exc, exc_info=True)
        return {}


def _evolution_child(
    result_queue: Any,
    max_bugs: int,
    data_dir: str,
    stage_file: str,
    provider_timeout_seconds: float,
) -> None:
    """Run evolution in a spawn-safe child process."""
    try:
        os.environ["SCP_EVOLUTION_STAGE_FILE"] = stage_file
        # [R38] Child evolution must write its ledger under the requested
        # data_dir; tests and isolated runs must not contaminate production data.
        ledger_path = (Path(data_dir) / "learning_runs.jsonl").resolve()
        os.environ["SCP_LEARNING_RUN_LEDGER_PATH"] = str(ledger_path)
        os.environ["SCP_LLM_REQUEST_TIMEOUT_SECONDS"] = str(provider_timeout_seconds)
        from scp.autofix.evolution import get_evolution_engine

        engine = get_evolution_engine(data_dir=data_dir)
        result = engine.evolve_cycle(max_bugs=max_bugs)
        result_queue.put({"ok": True, "result": result})
    except BaseException as exc:  # silent-by-design: sanitized failure is propagated to the parent via the queue.
        logger.debug("bounded_evolution: child cycle failed (%s), propagated via queue", type(exc).__name__, exc_info=True)
        result_queue.put(
            {
                "ok": False,
                "error_class": type(exc).__name__,
                "error_summary": str(exc)[:300],
            }
        )


def _terminate_child(process: mp.Process) -> None:
    if not process.is_alive():
        process.join(timeout=1)
        return
    process.terminate()
    process.join(timeout=5)
    if process.is_alive():
        process.kill()
        process.join(timeout=5)


def run_bounded_evolution(
    *,
    max_bugs: int = 20,
    timeout_seconds: float = 300.0,
    data_dir: str = "data",
) -> dict[str, Any]:
    """Run one evolution cycle with a hard parent-owned deadline."""
    timeout_seconds = float(timeout_seconds)
    if timeout_seconds <= 0 or timeout_seconds != timeout_seconds:
        raise ValueError("timeout_seconds must be a positive finite number")
    started_at = _utc_iso()
    stage_file = str(Path(data_dir) / "evolution_stage.json")
    run_id = f"bounded-evolution-{time.time_ns()}"
    telemetry: SubsystemTelemetry | None = None
    try:
        telemetry = SubsystemTelemetry("evolution", data_dir)
        telemetry.cycle_started(
            run_id,
            trigger="bounded_parent",
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:  # Telemetry must not hide the true bounded outcome.
        logger.warning("bounded evolution telemetry start failed: %s", type(exc).__name__, exc_info=True)

    def finalize(payload: dict[str, Any]) -> dict[str, Any]:
        """Write one parent-owned terminal event for every returned outcome."""
        if telemetry is None:
            return payload
        status = classify_learning_outcome(payload, mode="evolution")
        payload = dict(payload)
        payload["status"] = status
        details = {
            "execution_owner": "bounded_parent",
            "child_pid": payload.get("child_pid"),
            "stage": payload.get("stage"),
            "timeout_seconds": payload.get("timeout_seconds"),
            "error_class": payload.get("error_class"),
            "error_summary": payload.get("error_summary"),
            "bugs_found": payload.get("bugs_found"),
            "bugs_fixed": payload.get("bugs_fixed"),
            "verified": payload.get("verified"),
            "stored": payload.get("stored"),
        }
        try:
            telemetry.cycle_completed(run_id, status, **details)
        except Exception as exc:  # Do not convert the real outcome into success.
            logger.warning("bounded evolution telemetry completion failed: %s", type(exc).__name__, exc_info=True)
            payload = dict(payload)
            payload["telemetry_degraded"] = True
        return payload
    try:
        configured_provider_timeout = float(
            os.environ.get("SCP_EVOLUTION_PROVIDER_TIMEOUT_SECONDS", "30")
        )
    except ValueError as exc:
        # silent-by-design: malformed env value falls back to the documented 30s default.
        logger.debug("bounded_evolution: SCP_EVOLUTION_PROVIDER_TIMEOUT_SECONDS unparseable, using 30.0: %s", exc, exc_info=True)
        configured_provider_timeout = 30.0
    provider_timeout_seconds = min(timeout_seconds, max(1.0, configured_provider_timeout))
    context = mp.get_context("spawn")

    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_evolution_child,
        args=(
            result_queue,
            int(max_bugs),
            str(data_dir),
            stage_file,
            provider_timeout_seconds,
        ),
        name="scp-evolution-child",
    )
    process.start()
    child_pid = process.pid
    process.join(timeout=timeout_seconds)

    if process.is_alive():
        checkpoint = _read_checkpoint(stage_file)
        _terminate_child(process)
        last_stage = str(checkpoint.get("stage", "unknown"))
        error = TimeoutError(
            f"stage={last_stage}; child_pid={child_pid}; "
            f"timeout_seconds={timeout_seconds:g}"
        )
        record_learning_run(
            mode="evolution",
            started_at=started_at,
            ended_at=_utc_iso(),
            result={"stage": last_stage},
            error=error,
            ledger_path=str((Path(data_dir) / "learning_runs.jsonl").resolve()),
        )
        return finalize({
            "action": "timed_out",
            "status": "TIMEOUT",
            "stage": last_stage,
            "timeout_seconds": timeout_seconds,
            "child_pid": child_pid,
            "stage_file": stage_file,
        })

    try:
        message = result_queue.get(timeout=1)
    except queue.Empty:
        return finalize({
            "action": "failed",
            "status": "PROVIDER_FAILED",
            "stage": "child_result_collection",
            "child_pid": child_pid,
            "error_class": "ChildResultMissing",
            "error_summary": "child exited without a result message",
        })
    finally:
        result_queue.close()
        result_queue.join_thread()

    if message.get("ok"):
        result = message.get("result")
        if isinstance(result, dict):
            # Derive status from verified/stored/provider evidence. A nonzero
            # bugs_fixed counter alone cannot prove durable storage.
            result = dict(result)
            result["status"] = classify_learning_outcome(result, mode="evolution")
        payload = result if isinstance(result, dict) else {"action": "evolved", "status": "SUCCESS", "result": result}
        return finalize(payload)

    return finalize({
        "action": "failed",
        "status": "PROVIDER_FAILED",
        "stage": "child_evolve_cycle",
        "child_pid": child_pid,
        "error_class": message.get("error_class", "ChildEvolutionError"),
        "error_summary": message.get("error_summary", "child evolution failed"),
    })


if __name__ == "__main__":
    print(json.dumps(run_bounded_evolution(), sort_keys=True, default=str))
