"""Shared state-machine definitions, exceptions, and helpers for TaskKernel."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

STATES = {
    "CREATED", "PLANNING", "READY", "QUEUED", "LEASED", "RUNNING",
    "WAITING_TOOL", "VERIFYING", "CHECKPOINTED", "UNKNOWN", "RECOVERING",
    "RECONCILING", "HUMAN_REVIEW", "RETRY_SCHEDULED", "COMPLETED",
    "FAILED", "CANCELLED",
}
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}
ALLOWED_TRANSITIONS = {
    "CREATED": {"PLANNING", "CANCELLED"},
    "PLANNING": {"READY", "WAITING_APPROVAL", "FAILED", "CANCELLED"},
    "WAITING_APPROVAL": {"READY", "CANCELLED"},
    "READY": {"QUEUED", "CANCELLED"},
    "QUEUED": {"LEASED", "CANCELLED"},
    "LEASED": {"RUNNING", "RECOVERING", "CANCELLED"},
    # [Agent2 2026-09-29] RETRY_SCHEDULED added to execution states: the
    # retry branch of commit_failed() (pinned by b5/autonomous/gap13 tests)
    # commits it from RUNNING/WAITING_TOOL/VERIFYING; the map now agrees.
    "RUNNING": {"WAITING_TOOL", "VERIFYING", "CHECKPOINTED", "RECOVERING", "HUMAN_REVIEW", "RETRY_SCHEDULED", "FAILED", "CANCELLED"},
    "WAITING_TOOL": {"VERIFYING", "UNKNOWN", "RECOVERING", "RETRY_SCHEDULED", "FAILED", "CANCELLED"},
    "VERIFYING": {"RUNNING", "COMPLETED", "HUMAN_REVIEW", "RETRY_SCHEDULED", "FAILED"},
    "CHECKPOINTED": {"RUNNING", "QUEUED", "CANCELLED"},
    "UNKNOWN": {"RECONCILING", "HUMAN_REVIEW", "RECOVERING", "FAILED", "CANCELLED"},
    "HUMAN_REVIEW": {"READY", "CANCELLED", "FAILED"},
    "RECOVERING": {"RECONCILING", "CHECKPOINTED", "QUEUED", "HUMAN_REVIEW", "FAILED"},
    "RECONCILING": {"RECOVERING", "CHECKPOINTED", "QUEUED", "HUMAN_REVIEW", "FAILED", "CANCELLED"},
    "RETRY_SCHEDULED": {"QUEUED", "FAILED", "CANCELLED"},
    "COMPLETED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}


class KernelError(RuntimeError):
    pass


class InvalidTransition(KernelError):
    pass


class StaleLease(KernelError):
    pass


class OptimisticLockError(StaleLease):
    """Raised when an atomic OCC version check fails (0 rows updated due to version mismatch)."""

    def __init__(
        self,
        message: str = "",
        *,
        table: str | None = None,
        entity_id: str | None = None,
        expected_version: int | None = None,
    ) -> None:
        self.table = table
        self.entity_id = entity_id
        self.expected_version = expected_version
        if not message:
            message = (
                f"Optimistic lock conflict on table '{table}' for entity '{entity_id}'"
                f" (expected version {expected_version})"
            )
        elif entity_id and entity_id not in message:
            message = f"{message} (table={table}, entity_id={entity_id}, expected_version={expected_version})"
        super().__init__(message)


class KillSwitchActive(KernelError):
    pass


class CheckpointCorrupt(KernelError):
    pass


class NotFound(KernelError):
    pass


@dataclass(frozen=True)
class Lease:
    lease_id: str
    task_id: str
    attempt_id: str
    worker_id: str
    expires_at: float
    fencing_token: int
    global_kill_epoch: int


@dataclass(frozen=True)
class RecoveryDecision:
    decision: str
    reason: str
    safe_to_retry: bool
    required_evidence: tuple[str, ...]
    next_state: str
    escalation: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    else:
        raw = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


_SENSITIVE_KEY_MARKERS = (
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "authorization", "cookie", "private_key",
)
_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)=\S+"),
)


def _checkpoint_contains_secret(value: Any, path: str = "checkpoint") -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower().replace("-", "_")
            if any(marker in key_text for marker in _SENSITIVE_KEY_MARKERS):
                return True
            if _checkpoint_contains_secret(child, f"{path}.{key}"):
                return True
        return False
    if isinstance(value, (list, tuple, set)):
        return any(_checkpoint_contains_secret(child, f"{path}[]") for child in value)
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in _SENSITIVE_VALUE_PATTERNS)
    return False


def _assert_checkpoint_safe(value: Any) -> None:
    if _checkpoint_contains_secret(value):
        raise KernelError("checkpoint contains secret material")


def as_json(value: Any) -> str:
    payload = asdict(value) if hasattr(value, "__dataclass_fields__") else value
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
