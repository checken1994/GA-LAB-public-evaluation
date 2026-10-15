"""Durable TaskKernel public contract and shared state-machine definitions."""
from __future__ import annotations

# [hygiene-keep] restored re-export: StorageIntegrityError bị xoá nhầm trong đợt
# dọn F401 (name nằm giữa import nhiều tên) trong khi scp/ask_kernel_adapter.py
# vẫn dùng `from .task_kernel import StorageIntegrityError` — khôi phục surface.
from scp.kernel_storage import StorageIntegrityError  # noqa: F401

from .task_kernel_parts.definitions import (
    ALLOWED_TRANSITIONS,
    STATES,
    TERMINAL,
    CheckpointCorrupt,
    InvalidTransition,
    KernelError,
    KillSwitchActive,
    Lease,
    NotFound,
    OptimisticLockError,
    RecoveryDecision,
    StaleLease,
    as_json,
    now_iso,
    stable_hash,
)
from .task_kernel_parts.taskkernel import TaskKernel, verify_approval_authority


def _idempotency_claim_fenced(self, *args, **kwargs):
    return self.idempotency_claim(*args, **kwargs)

def _idempotency_complete_fenced(self, *args, **kwargs):
    return self.idempotency_complete(*args, **kwargs)

def _idempotency_status(self, *args, **kwargs):
    return self.idempotency_status(*args, **kwargs)

# The implementation may live in a part module, but the public class lived at
# ``scp.task_kernel.TaskKernel`` before the split. Preserve that identity for
# introspection and pickle/import compatibility.
TaskKernel.__module__ = __name__

__all__ = [
    "TaskKernel", "Lease", "RecoveryDecision", "KernelError",
    "InvalidTransition", "StaleLease", "OptimisticLockError", "KillSwitchActive",
    "CheckpointCorrupt", "NotFound", "STATES", "TERMINAL",
    "ALLOWED_TRANSITIONS", "now_iso", "stable_hash", "as_json",
    "verify_approval_authority",
    "_idempotency_claim_fenced", "_idempotency_complete_fenced", "_idempotency_status",
]
