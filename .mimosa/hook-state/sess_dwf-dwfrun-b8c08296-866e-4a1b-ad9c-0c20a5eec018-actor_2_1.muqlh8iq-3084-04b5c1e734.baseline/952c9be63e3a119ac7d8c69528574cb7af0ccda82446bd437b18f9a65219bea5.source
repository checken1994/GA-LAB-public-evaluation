# SCP CIRCUIT: M05 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M05-closure.json)
"""Durable request-level run ledger for SCP API boundaries.

This module records only bounded metadata: ids, hashes, status transitions,
verdict metadata, timings and redacted errors. It never stores raw prompts,
answers, tokens, passwords, or file contents.
"""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import logging
import os
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

from .runtime_paths import runtime_path
from .trace_contract import TraceSpanContract

logger = logging.getLogger(__name__)

try:
    from fastapi import HTTPException
except Exception as exc:  # pragma: no cover
    # silent-by-design: FastAPI is an optional dependency; the module must stay importable without it.
    logger.debug("fastapi unavailable; HTTPException disabled: %s", exc, exc_info=True)
    HTTPException = ()  # type: ignore[assignment]

P = ParamSpec("P")
R = TypeVar("R")

TERMINAL_STATUSES = {
    "SUCCESS",
    "UNKNOWN",
    "REJECTED",
    "PROVIDER_FAILED",
    "VERIFIER_FAILED",
    "DB_WRITE_FAILED",
    "TIMEOUT",
    "INTERNAL_FAILED",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_error(exc: BaseException | None) -> tuple[str | None, str | None]:
    if exc is None:
        return None, None
    text = str(exc).replace("\r", " ").replace("\n", " ")
    lowered = text.lower()
    for marker in ("token=", "password=", "api_key=", "authorization:", "bearer "):
        at = lowered.find(marker)
        if at >= 0:
            text = text[:at] + marker + "<redacted>"
            break
    return type(exc).__name__, text[:300]


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        blocked = {"prompt", "question", "answer", "token", "password", "secret", "api_key", "authorization", "body"}
        return {str(k): _json_safe(v) for k, v in value.items() if str(k).lower() not in blocked}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value[:50]]
    return str(value)[:300]


def _sha256_text(value: Any) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(str(value).encode("utf-8", "replace")).hexdigest()


@dataclass(frozen=True)
class RequestRun:
    run_id: str
    trace_id: str
    started_at: float
    source: str
    domain: str
    question_sha256: str | None
    ledger_path: str
    ledger_write_ok: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class RequestRunLedger:
    """Append-only request ledger with explicit terminal statuses."""

    def __init__(self, path: str | Path | None = None) -> None:
        raw = str(path or runtime_path("SCP_REQUEST_RUN_LEDGER_PATH", "request_runs.jsonl")).strip()

        ledger_path = Path(raw)
        if not ledger_path.is_absolute():
            ledger_path = Path.cwd() / ledger_path
        self.path = ledger_path
        self._lock = threading.RLock()
        self.trace_contract = TraceSpanContract(self)

    def _append(self, row: dict[str, Any]) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(_json_safe(row), ensure_ascii=False, sort_keys=True) + "\n"
            with self._lock, self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            return True
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("request_run_ledger: ledger append failed for %s: %s", self.path, exc, exc_info=True)
            return False

    def _event(self, run: RequestRun, event: str, status: str, **fields: Any) -> bool:
        row = {
            "event": event,
            "run_id": run.run_id,
            "trace_id": run.trace_id,
            "started_at_utc": datetime.fromtimestamp(run.started_at, timezone.utc).isoformat(),
            "ts_utc": _utc_now(),
            "source": run.source[:80],
            "domain": run.domain[:80],
            "question_sha256": run.question_sha256,
            "metadata": run.metadata,
            "status": status,
            **fields,
        }
        return self._append(row)

    def _event_by_identity(self, trace_id: str, event: str, payload: dict[str, Any]) -> bool:
        """Persist a bounded span event when only trace identity is available."""
        row = {
            "event": event,
            "trace_id": str(trace_id)[:120],
            "ts_utc": _utc_now(),
            **payload,
        }
        return self._append(row)

    def begin(self, request: Any, **metadata: Any) -> RequestRun:
        req = request if request is not None else object()
        safe_metadata = {
            key: str(value)[:80]
            for key, value in metadata.items()
            if key in {"action", "risk_class", "policy_version", "decision_source"}
            and value is not None
        }
        safe_metadata.setdefault("action", "request")
        safe_metadata.setdefault("risk_class", "unknown")
        safe_metadata.setdefault("policy_version", str(os.environ.get("SCP_POLICY_VERSION", "runtime-v1"))[:80])
        safe_metadata.setdefault("decision_source", "scp")
        source = str(getattr(req, "source", "api") or "api")[:80]
        domain = str(getattr(req, "domain", "general") or "general")[:80]
        question = next((getattr(req, name, None) for name in ("question", "prompt", "message", "command", "content") if getattr(req, name, None) is not None), None)
        run = RequestRun(
            run_id=f"run-{uuid.uuid4().hex}",
            trace_id=f"trace-{uuid.uuid4().hex}",
            started_at=time.time(),
            source=source,
            domain=domain,
            question_sha256=_sha256_text(question),
            ledger_path=str(self.path),
            ledger_write_ok=True,
            metadata=safe_metadata,
        )
        received_ok = self._event(run, "request_received", "RECEIVED")
        running_ok = self._event(run, "request_started", "RUNNING")
        return RequestRun(**{**run.__dict__, "ledger_write_ok": received_ok and running_ok})

    def stage(self, run: RequestRun, stage: str, status: str = "RUNNING", **fields: Any) -> bool:
        ok = self._event(run, "stage", status, stage=stage, **fields)
        try:
            span = self.trace_contract.start(
                trace_id=run.trace_id,
                name=str(stage),
                kind="request.stage",
                parent_id=self.trace_contract.active_parent_id(run.trace_id),
                attributes={"run_id": run.run_id, "status": status, **fields},
            )
            span_status = "OK" if status in {"RUNNING", "RECEIVED", "AUDIT_READY", "SUCCESS"} else ("UNKNOWN" if status == "UNKNOWN" else "ERROR")
            self.trace_contract.finish(span, status=span_status, attributes={"terminal_status": status})
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            # silent-by-design: the request ledger remains authoritative; tracing is observability only.
            logger.debug("trace span finish failed (non-fatal): %s", exc, exc_info=True)
        return ok

    def finish(self, run: RequestRun, status: str, *, result: Any = None, error: BaseException | None = None, **fields: Any) -> tuple[str, bool]:
        if status not in TERMINAL_STATUSES:
            status = "INTERNAL_FAILED"
        error_class, error_summary = _redact_error(error)
        verdict = getattr(result, "verdict", None)
        governance = getattr(result, "governance_decision", None)
        if isinstance(result, dict):
            verdict = result.get("verdict", verdict)
            governance = result.get("governance_decision", result.get("governance", governance))
        elapsed_ms = round(max(0.0, time.time() - run.started_at) * 1000.0, 2)
        ok = run.ledger_write_ok and self._event(
            run,
            "request_finished",
            status,
            elapsed_ms=elapsed_ms,
            verdict=str(verdict)[:40] if verdict is not None else None,
            governance_decision=str(governance)[:40] if governance is not None else None,
            error_class=error_class,
            error_summary=error_summary,
            **fields,
        )
        return (status if ok else "DB_WRITE_FAILED"), ok

    @staticmethod
    def classify_result(result: Any) -> str:
        """Map model and ordinary JSON API responses to terminal run status.

        Not every API route returns a verdict. A normal HTTP handler may return a
        health, capability, model-list or policy-preview payload, so absence of
        ``verdict`` must not be treated as an internal failure. Explicit errors
        and policy denials still fail closed.
        """
        if isinstance(result, dict):
            status_code = result.get("status_code")
            verdict = str(result.get("verdict", "")).upper()
            governance = str(result.get("governance_decision", result.get("governance", ""))).upper()
            explicit_status = str(result.get("run_status", result.get("status", ""))).upper()
            explicit_success = result.get("success", result.get("ok"))
        else:
            status_code = getattr(result, "status_code", None)
            verdict = str(getattr(result, "verdict", "")).upper()
            governance = str(getattr(result, "governance_decision", "")).upper()
            explicit_status = str(getattr(result, "run_status", getattr(result, "status", ""))).upper()
            explicit_success = getattr(result, "success", getattr(result, "ok", None))
        if isinstance(status_code, int) and status_code >= 400:
            return "REJECTED" if status_code < 500 else "INTERNAL_FAILED"
        if explicit_status in TERMINAL_STATUSES:
            return explicit_status
        if explicit_status in {"ERROR", "FAILED", "FAIL"}:
            return "INTERNAL_FAILED"
        if governance in {"KILL", "REJECT", "DENY"} or verdict in {"FAIL", "FLAGGED"}:
            return "REJECTED"
        if verdict == "UNKNOWN":
            return "UNKNOWN"
        if verdict == "PASS":
            return "SUCCESS"
        if explicit_success is False:
            return "REJECTED" if isinstance(result, dict) and result.get("allowed") is False else "INTERNAL_FAILED"
        if explicit_success is True:
            return "SUCCESS"
        if isinstance(result, dict) and "error" not in result:
            return "SUCCESS"
        return "INTERNAL_FAILED"

    @staticmethod
    def classify_error(exc: BaseException) -> str:
        if isinstance(exc, asyncio.TimeoutError) or isinstance(exc, TimeoutError) or "timeout" in str(exc).lower():
            return "TIMEOUT"
        name = type(exc).__name__.lower()
        text = str(exc).lower()
        if isinstance(exc, HTTPException):  # type: ignore[arg-type]
            return "REJECTED" if int(getattr(exc, "status_code", 500)) < 500 else "INTERNAL_FAILED"
        if "verif" in name or "verif" in text or "judge" in name:
            return "VERIFIER_FAILED"
        if any(word in name or word in text for word in ("ollama", "provider", "llm", "model", "gateway")):
            return "PROVIDER_FAILED"
        return "INTERNAL_FAILED"

    @staticmethod
    def attach(result: Any, run: RequestRun, status: str, ledger_ok: bool) -> Any:
        fields = {
            "run_id": run.run_id,
            "trace_id": run.trace_id,
            "run_status": status,
            "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED",
        }
        if hasattr(result, "model_copy"):
            return result.model_copy(update=fields)
        if hasattr(result, "headers"):
            try:
                result.headers["X-SCP-Run-ID"] = run.run_id
                result.headers["X-SCP-Trace-ID"] = run.trace_id
                result.headers["X-SCP-Run-Status"] = status
                result.headers["X-SCP-Ledger-Status"] = fields["ledger_status"]
            except Exception as exc:
                # silent-by-design: header enrichment is best-effort; response identity stays in the ledger.
                logger.debug("ledger response-header attach failed (non-fatal): %s", exc, exc_info=True)
            return result
        if isinstance(result, dict):
            out = dict(result)
            out.update(fields)
            return out
        return result


def stage_request(request: Any, stage: str, status: str = "RUNNING", **fields: Any) -> bool:
    run = getattr(getattr(request, "state", None), "scp_run", None)
    ledger = getattr(getattr(request, "state", None), "scp_request_ledger", None)
    if run is None or ledger is None:
        return False
    return ledger.stage(run, stage, status, **fields)


def require_audit(request: Any, action: str = "high_risk_action") -> RequestRun:
    """Fail closed when a high-risk route cannot persist its audit start event."""
    run = getattr(getattr(request, "state", None), "scp_run", None)
    ledger = getattr(getattr(request, "state", None), "scp_request_ledger", None)
    if run is None or ledger is None or not run.ledger_write_ok:
        raise HTTPException(status_code=503, detail="Audit ledger unavailable; high-risk action blocked")
    ledger.stage(run, "high_risk_guard", "AUDIT_READY", action=str(action)[:100], risk_class="high", decision_source="audit_guard")
    return run


def traced_request(ledger: RequestRunLedger, require_write: bool = False, action: str = "request", risk_class: str = "unknown", policy_version: str = "runtime-v1", decision_source: str = "scp"):
    """Wrap an async API boundary and guarantee one terminal ledger event."""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if not inspect.iscoroutinefunction(func):
            raise TypeError("traced_request requires an async function")

        @wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs):
            req = kwargs.get("req")
            if req is None and args:
                req = args[0]
            effective_risk = risk_class if risk_class != "unknown" else ("high" if require_write else "normal")
            run = ledger.begin(req, action=action, risk_class=effective_risk, policy_version=policy_version, decision_source=decision_source)
            root_span = None
            try:
                root_span = ledger.trace_contract.start(
                    trace_id=run.trace_id,
                    name=getattr(func, "__name__", "request"),
                    kind="http.request",
                    attributes={"run_id": run.run_id, "source": run.source, "domain": run.domain, "action": action},
                    input_value=next((getattr(req, name, None) for name in ("question", "prompt", "message", "command", "content") if getattr(req, name, None) is not None), None),
                )
            except (OSError, TypeError, ValueError) as exc:
                # silent-by-design: observability must not turn a normal API request into a failure.
                logger.debug("root span start failed (non-fatal): %s", exc, exc_info=True)
                root_span = None
            http_request = kwargs.get("request")
            if http_request is None and len(args) > 1:
                http_request = args[1]
            try:
                if http_request is not None and hasattr(http_request, "state"):
                    http_request.state.scp_run = run
                    http_request.state.scp_request_ledger = ledger
            except Exception as exc:
                # silent-by-design: state attach is observability only; request must proceed.
                logger.debug("request.state ledger attach failed (non-fatal): %s", exc, exc_info=True)
            if require_write and not run.ledger_write_ok:
                exc = HTTPException(status_code=503, detail="Audit ledger unavailable; high-risk action blocked")
                ledger.finish(run, "DB_WRITE_FAILED", error=exc, action=str(action)[:100])
                if root_span is not None:
                    try:
                        ledger.trace_contract.finish(root_span, status="ERROR", error=exc)
                    except (OSError, RuntimeError, TypeError, ValueError) as exc:
                        # silent-by-design: tracing is observability only; the ledger stays authoritative.
                        logger.debug("trace span finish failed (non-fatal): %s", exc, exc_info=True)
                raise exc
            if require_write:
                ledger.stage(run, "high_risk_guard", "AUDIT_READY", action=str(action)[:100])
            try:
                result = await func(*args, **kwargs)
                status = ledger.classify_result(result)
                terminal_status, write_ok = ledger.finish(run, status, result=result)
                # A successful terminal append is the only basis for SUCCESS.
                if status == "SUCCESS" and terminal_status == "DB_WRITE_FAILED":
                    status = "DB_WRITE_FAILED"
                if root_span is not None:
                    try:
                        span_status = "OK" if status == "SUCCESS" else ("UNKNOWN" if status == "UNKNOWN" else "ERROR")
                        ledger.trace_contract.finish(root_span, status=span_status, output_value=result)
                    except (OSError, RuntimeError, TypeError, ValueError) as exc:
                        # silent-by-design: tracing is observability only; the ledger stays authoritative.
                        logger.debug("trace span finish failed (non-fatal): %s", exc, exc_info=True)
                return ledger.attach(result, run, status, write_ok)
            except BaseException as exc:
                status = ledger.classify_error(exc)
                terminal_status, write_ok = ledger.finish(run, status, error=exc)
                # Do not hide the original API exception; ledger exposes the failure.
                if root_span is not None:
                    try:
                        ledger.trace_contract.finish(root_span, status="ERROR", error=exc)
                    except (OSError, RuntimeError, TypeError, ValueError) as exc:
                        # silent-by-design: tracing is observability only; the ledger stays authoritative.
                        logger.debug("trace span finish failed (non-fatal): %s", exc, exc_info=True)
                _ = terminal_status
                _ = write_ok
                raise

        return wrapped
    return decorator


__all__ = ["RequestRun", "RequestRunLedger", "TERMINAL_STATUSES", "require_audit", "stage_request", "traced_request"]
