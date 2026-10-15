"""Append-only run ledger for SCP learning/evolution cycles.

The ledger is deliberately fail-open: inability to write an audit record must
never make a learning/evolution operation appear successful or crash the main
pipeline. Records contain counters and exception metadata only; no prompts,
answers, or credentials are persisted here.
"""
from __future__ import annotations

import inspect
import json
import logging
import os
import re
import time
from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

from scp.core.learning_outcome import LEARNING_OUTCOME_STATUSES, classify_learning_outcome
from scp.core.runtime_paths import runtime_path

logger = logging.getLogger("scp.learning_run_ledger")

P = ParamSpec("P")
R = TypeVar("R")

_ALLOWED_STATUSES = LEARNING_OUTCOME_STATUSES


def _utc_iso(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts or time.time(), tz=timezone.utc).isoformat()


def _ledger_path() -> Path:
    raw = os.environ.get("SCP_LEARNING_RUN_LEDGER_PATH", "").strip()
    path = Path(raw) if raw else runtime_path("SCP_LEARNING_RUN_LEDGER_PATH", "learning_runs.jsonl")
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError) as exc:
        # silent-by-design: coerce probe; None means "not an int" by contract.
        logger.debug("learning_run_ledger: int coercion failed: %s", exc, exc_info=True)
        return None


def _metrics(result: Any) -> dict[str, int | None]:
    payload = result if isinstance(result, dict) else {}
    asked = _int_or_none(payload.get("asked", payload.get("questions")))
    verified = _int_or_none(payload.get("verified"))
    stored = _int_or_none(payload.get("stored"))
    answered = _int_or_none(payload.get("answered"))
    if answered is None and asked is not None:
        provider_failed = _int_or_none(
            payload.get("provider_failed", payload.get("provider_errors"))
        ) or 0
        answered = max(asked - provider_failed, 0)
    rejected = _int_or_none(payload.get("rejected"))
    if rejected is None and answered is not None and verified is not None:
        rejected = max(answered - verified, 0)
    return {
        "asked": asked,
        "answered": answered,
        "verified": verified,
        "rejected": rejected,
        "stored": stored,
        "rows_before": _int_or_none(payload.get("rows_before")),
        "rows_after": _int_or_none(payload.get("rows_after")),
    }


def _status(mode: str, result: Any, error: BaseException | None) -> str:
    return classify_learning_outcome(result, error, mode=mode)


_RUN_ID_SEEN: set[str] = set()


def _seen_run_ids() -> set[str]:
    """Best-effort in-process set of run ids already written this session."""
    return _RUN_ID_SEEN


def record_learning_run(
    *,
    mode: str,
    started_at: str,
    ended_at: str,
    result: Any = None,
    error: BaseException | None = None,
    ledger_path: str | Path | None = None,
) -> dict[str, Any]:
    """Append one sanitized run record and return it.

    This function never raises because telemetry must not alter the guarded
    learning/evolution result. A write failure is logged to stderr and the
    returned record carries ``ledger_write_error`` for callers/tests.
    """
    metrics = _metrics(result)
    status = _status(mode, result, error)
    if status not in _ALLOWED_STATUSES:
        # [LEARNING-OUTCOME] Unrecognized classification must stay visible:
        # audit 2026-09-28 flagged silent coercion as a downgrade of the
        # outcome taxonomy (K-01).
        logger.warning(
            "[LEARNING-OUTCOME] unrecognized status %r coerced to UNKNOWN "
            "(mode=%s)", status, mode
        )
        status = "UNKNOWN"
    existing_run_id = result.get("run_id") if isinstance(result, dict) else None
    if isinstance(existing_run_id, str):
        # [LEDGER-RUNID-VALIDATION] (K-02) run_id is audit-trail identity:
        # only accept caller-supplied values with a bounded, safe format;
        # anything else falls back to the ledger-generated id.
        if not re.fullmatch(r"[\w][\w\-.]{0,127}", existing_run_id):
            logger.warning(
                "[LEDGER-RUNID-VALIDATION] caller run_id %r failed format "
                "check; regenerating ledger id (mode=%s)", existing_run_id, mode
            )
            existing_run_id = None
        elif existing_run_id in _seen_run_ids():
            logger.warning(
                "[LEDGER-RUNID-VALIDATION] duplicate caller run_id %r; "
                "regenerating ledger id (mode=%s)", existing_run_id, mode
            )
            existing_run_id = None
    else:
        existing_run_id = None
    row: dict[str, Any] = {
        "run_id": existing_run_id or f"{mode}-{time.time_ns()}",
        "mode": mode,
        "started_at": started_at,
        "ended_at": ended_at,
        "status": status,
        **metrics,
        "error_class": type(error).__name__ if error else None,
        "error_summary": str(error)[:300] if error else None,
    }
    _seen_run_ids().add(str(row["run_id"]))
    try:
        path = Path(ledger_path) if ledger_path is not None else _ledger_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception as ledger_error:  # pragma: no cover - OS-specific failure
        row["operation_status"] = status
        row["status"] = "DB_WRITE_FAILED"
        row["ledger_write_error"] = type(ledger_error).__name__
        logger.warning("learning run ledger write failed: %s", ledger_error, exc_info=True)
    return row


def _finish_run(mode: str, started: str, result: Any, error: BaseException | None, owner: Any) -> None:
    row = record_learning_run(mode=mode, started_at=started, ended_at=_utc_iso(), result=result, error=error)
    if isinstance(result, dict):
        result["run_id"] = row["run_id"]
        result["run_status"] = row["status"]
        audit_failed = bool(row.get("ledger_write_error") or result.get("ledger_write_error"))
        result["ledger_status"] = "DB_WRITE_FAILED" if audit_failed else result.get("ledger_status", "OK")
        if row.get("ledger_write_error"):
            result["ledger_write_error"] = row["ledger_write_error"]
    if row.get("ledger_write_error"):
        telemetry = getattr(owner, "_telemetry", None)
        if telemetry is not None:
            try:
                telemetry.audit_failed(row["run_id"], error_class=row["ledger_write_error"])
            except Exception as exc:
                logger.warning("learning audit failure could not update telemetry: %s", type(exc).__name__)


def ledger_run(mode: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorate one sync or async learning/evolution boundary."""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
                started = _utc_iso()
                error: BaseException | None = None
                result: Any = None
                try:
                    result = await func(*args, **kwargs)  # type: ignore[misc]
                    return result
                except BaseException as exc:
                    error = exc
                    raise
                finally:
                    _finish_run(mode, started, result, error, args[0] if args else None)
            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs):
            started = _utc_iso()
            error: BaseException | None = None
            result: Any = None
            try:
                result = func(*args, **kwargs)
                return result
            except BaseException as exc:
                error = exc
                raise
            finally:
                _finish_run(mode, started, result, error, args[0] if args else None)
        return sync_wrapper  # type: ignore[return-value]

    return decorator
