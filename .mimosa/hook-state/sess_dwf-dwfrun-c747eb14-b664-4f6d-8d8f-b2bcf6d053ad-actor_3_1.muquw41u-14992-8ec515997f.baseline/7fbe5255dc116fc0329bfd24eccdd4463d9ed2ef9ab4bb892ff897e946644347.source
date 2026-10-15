"""Small, dependency-free trace/span contract for SCP runtime boundaries.

The contract is intentionally additive: RequestRunLedger remains the source of
terminal request status, while this module records a bounded parent/child event
chain for debugging and external review. Raw prompts, answers, credentials and
file contents are never stored in span attributes.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_SENSITIVE_PARTS = (
    "secret",
    "token",
    "password",
    "cookie",
    "api_key",
    "authorization",
    "private_key",
    "credential",
    "key",
    "bearer",
    "auth",
    "dsn",
    "connection_string",
    "proxy",
    "cert",
)
_ALLOWED_STATUSES = {"RUNNING", "OK", "ERROR", "UNKNOWN", "CANCELLED"}

_MAX_SEQUENCE_ITEMS = 50
_MAX_STRING_LENGTH = 512

_BEARER_PATTERN = re.compile(r"(?i)\b(bearer\s+)([^\s\"'\,;]+)")
_SK_TOKEN_PATTERN = re.compile(r"\b(sk-[a-zA-Z0-9_\-]{8,})\b")
_KEY_PARAM_PATTERN = re.compile(r"(?i)(\b(?:api[_-]?key|key|token|secret|password|auth)=)([^&\"'\s]+)")
_DSN_PASSWORD_PATTERN = re.compile(r"(://[^\s:/?#]*:)([^\s/]+)(@(?=[a-zA-Z0-9_\-\.\[\]]+))")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: Any) -> str:
    """Return a deterministic digest without exposing the original value."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()


def _redact_string(s: str) -> str:
    """Inspect and mask credentials within string values."""
    if "-----BEGIN " in s and ("PRIVATE KEY" in s or "CERTIFICATE" in s):
        return "[REDACTED]"
    s = _BEARER_PATTERN.sub(r"\1[REDACTED]", s)
    s = _SK_TOKEN_PATTERN.sub("[REDACTED]", s)
    s = _KEY_PARAM_PATTERN.sub(r"\1[REDACTED]", s)
    s = _DSN_PASSWORD_PATTERN.sub(r"\1[REDACTED]\3", s)
    if len(s) > _MAX_STRING_LENGTH:
        s = s[:_MAX_STRING_LENGTH] + "...[truncated]"
    return s


def redact_attributes(value: Any, seen: set[int] | None = None, _depth: int = 0) -> Any:
    """Recursively redact sensitive keys, tuple headers, string secrets and bound sequences."""
    if _depth > 20:
        return "[MAX_DEPTH_EXCEEDED]"

    if seen is None:
        seen = set()

    obj_id = id(value)
    if isinstance(value, (Mapping, list, tuple, set)):
        if obj_id in seen:
            return "[CIRCULAR_REFERENCE]"
        seen = seen | {obj_id}

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(part in key_text.lower() for part in _SENSITIVE_PARTS):
                result[key_text] = "[REDACTED]"
            else:
                result[key_text] = redact_attributes(item, seen, _depth + 1)
        return result

    if isinstance(value, tuple):
        # Handle 2-tuple key-value header pairs like ("Authorization", "Bearer sk-...")
        if len(value) == 2 and isinstance(value[0], str):
            key_text = value[0].lower()
            if any(part in key_text for part in _SENSITIVE_PARTS):
                return (value[0], "[REDACTED]")
            return (value[0], redact_attributes(value[1], seen, _depth + 1))
        return tuple(redact_attributes(item, seen, _depth + 1) for item in list(value)[:_MAX_SEQUENCE_ITEMS])

    if isinstance(value, list):
        return [redact_attributes(item, seen, _depth + 1) for item in list(value)[:_MAX_SEQUENCE_ITEMS]]

    if isinstance(value, set):
        return {redact_attributes(item, seen, _depth + 1) for item in list(value)[:_MAX_SEQUENCE_ITEMS]}

    if isinstance(value, str):
        return _redact_string(value)

    if value is None or isinstance(value, (bool, int, float)):
        return value

    return _redact_string(str(value))


@dataclass
class TraceSpan:
    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    kind: str
    started_at: str
    started_monotonic: float
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "RUNNING"
    ended_at: str | None = None
    duration_ms: float | None = None
    input_sha256: str | None = None
    output_sha256: str | None = None
    error_class: str | None = None
    closed: bool = False


class TraceSpanContract:
    """Emit bounded span events through a RequestRunLedger-like object."""

    def __init__(self, event_writer: Any) -> None:
        self._event_writer = event_writer
        self._active: dict[str, TraceSpan] = {}

    def start(
        self,
        *,
        trace_id: str,
        name: str,
        kind: str = "internal",
        parent_id: str | None = None,
        attributes: Mapping[str, Any] | None = None,
        input_value: Any = None,
    ) -> TraceSpan:
        span = TraceSpan(
            trace_id=str(trace_id),
            span_id="span-" + uuid.uuid4().hex,
            parent_id=parent_id,
            name=str(name)[:120],
            kind=str(kind)[:80],
            started_at=utc_now(),
            started_monotonic=time.monotonic(),
            attributes=redact_attributes(dict(attributes or {})),
            input_sha256=stable_hash(input_value) if input_value is not None else None,
        )
        self._active[span.span_id] = span
        self._write(
            "span_started",
            span,
            status="RUNNING",
            started_at=span.started_at,
        )
        return span

    def finish(
        self,
        span: TraceSpan,
        *,
        status: str = "OK",
        output_value: Any = None,
        error: BaseException | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if span.closed or span.span_id not in self._active:
            raise RuntimeError(f"span is not active: {span.span_id}")
        final_status = str(status).upper()
        if final_status not in _ALLOWED_STATUSES or final_status == "RUNNING":
            final_status = "ERROR"
        span.status = final_status
        span.ended_at = utc_now()
        span.duration_ms = round(max(0.0, time.monotonic() - span.started_monotonic) * 1000.0, 3)
        span.output_sha256 = stable_hash(output_value) if output_value is not None else None
        span.error_class = type(error).__name__ if error is not None else None
        if attributes:
            span.attributes.update(redact_attributes(dict(attributes)))
        event = self._write(
            "span_finished",
            span,
            status=span.status,
            started_at=span.started_at,
            ended_at=span.ended_at,
            duration_ms=span.duration_ms,
            output_sha256=span.output_sha256,
            error_class=span.error_class,
        )
        span.closed = True
        del self._active[span.span_id]
        return event

    def _write(self, event: str, span: TraceSpan, **fields: Any) -> dict[str, Any]:
        payload = {
            "span_id": span.span_id,
            "parent_id": span.parent_id,
            "span_name": span.name,
            "span_kind": span.kind,
            "attributes": span.attributes,
            "input_sha256": span.input_sha256,
            **fields,
        }
        # RequestRunLedger._event supplies request identity and fsync semantics.
        ok = self._event_writer._event_by_identity(span.trace_id, event, payload)
        if not ok:
            raise OSError("trace span event could not be persisted")
        return payload

    def active_parent_id(self, trace_id: str) -> str | None:
        """Return the newest active span for a trace as a safe child parent."""
        active = [span for span in self._active.values() if span.trace_id == str(trace_id)]
        if not active:
            return None
        return max(active, key=lambda span: span.started_monotonic).span_id

    def active_span_ids(self) -> list[str]:
        return sorted(self._active)


__all__ = ["TraceSpan", "TraceSpanContract", "redact_attributes", "stable_hash", "utc_now"]
