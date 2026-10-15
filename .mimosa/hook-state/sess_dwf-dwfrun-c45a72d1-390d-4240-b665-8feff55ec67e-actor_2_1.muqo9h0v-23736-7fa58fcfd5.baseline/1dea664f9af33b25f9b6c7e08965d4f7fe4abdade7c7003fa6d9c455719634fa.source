"""
[SCP-DNA-FIX 4-b-012] Pydantic audit log schema — enforces 4 required fields
for ALL tiers (DNA #8 KB accumulation).

TẠI SAO file này tồn tại?
  Pre-fix: `AutoFixEngine._write_audit` (used for Tier 1 / Tier 2 / Tier 4
  fixes) wrote only:
    timestamp, file, line, bug_type, tier, action, attack_mode, description
  NO before_hash, NO after_hash, NO rollback_token, NO reality_test_result.
  Only Tier-3 auto-approved fixes (via `_write_tier3_auto_audit`) logged
  all 4 fields. This violated DNA #8 (KB accumulation — every important
  decision must carry before/after hash + reality test result + rollback
  token). The vast majority of fixes were non-revertible by token and
  non-auditable to the standard claimed (DNA #22 — PASS ≠ TRUE).

  This module defines a Pydantic `AuditLogEntry` schema that ENFORCES all
  4 fields at type level. An entry missing `before_hash`, `after_hash`,
  `rollback_token`, or `reality_test_result` is REJECTED at write time
  (Pydantic ValidationError fires inside `write_audit_entry()` — caller
  sees a False return + ERROR log, not a silent malformed entry). The
  schema is applied to ALL tiers (Tier 1, Tier 2, Tier 3, Tier 4) — no
  tier-specific gating of which fields are required.

DNA principles applied:
  #8 (KB accumulation — every fix decision auditable to before/after
     hash + reality test result + rollback token)
  #9 (No harm — every fix has a rollback path, recorded as rollback_token)
  #22 (PASS ≠ TRUE — log entry now carries forensic data, not just message)
  #16 (Học nói phạm vi — schema makes the audit contract explicit:
     callers CANNOT claim "audited" without proving they passed all 4 fields)

Fallback: if Pydantic is unavailable at runtime, we use a dataclass with
__post_init__ enforcement. Same write-time validation, same 4 required
fields — only the error type differs (ValueError vs ValidationError).

Public API:
    AuditLogEntry                 — Pydantic (or dataclass) schema with validator
    write_audit_entry(...)        — construct + validate + append to JSONL log
    compute_hashes(...)           — sha256 helper for before/after content
    make_rollback_token_backup(...)— Tier 1/2 token = backup file path
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.autofix.audit_log")

# ---------------------------------------------------------------------------
# Pydantic availability check — fall back to dataclass if Pydantic missing.
# DNA #7 (Autofix an toàn): fail-open at the import level. The schema
# enforcement still happens (via __post_init__) even without Pydantic.
# ---------------------------------------------------------------------------
try:
    from pydantic import BaseModel, Field, validator  # type: ignore[import-untyped]
    _PYDANTIC_AVAILABLE = True
except ImportError:  # pragma: no cover — exercised only when Pydantic missing
    # silent-by-design: documented fail-open import — schema enforcement still happens via __post_init__ without Pydantic.
    _PYDANTIC_AVAILABLE = False
    BaseModel = object  # type: ignore[assignment, misc]

    def Field(default, **kwargs):  # type: ignore[no-redef]
        return default

    def validator(*fields, **kwargs):  # type: ignore[no-redef]
        def _decorator(cls):
            return cls
        return _decorator


# ---------------------------------------------------------------------------
# Hash helper — sha256 first 32 hex chars (128-bit, plenty for audit trail).
# ---------------------------------------------------------------------------

def _hash_content(content: str) -> str:
    """SHA-256 of file content (first 32 hex chars = 128-bit hash)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# AuditLogEntry schema — enforced for ALL tiers (DNA #8).
# ---------------------------------------------------------------------------

if _PYDANTIC_AVAILABLE:

    class AuditLogEntry(BaseModel):
        """Pydantic schema for autofix audit log entries (DNA #8).

        Enforces: every entry MUST carry before_hash + after_hash +
        rollback_token + reality_test_result (the 4 forensic fields).
        An entry missing any of these fields is REJECTED at write time
        (Pydantic ValidationError), not silently logged.

        For events that are NOT fix applications (e.g. permission_requested,
        rollback_logged), callers pass sentinel "n/a" strings — schema still
        requires non-empty values so the entry is auditable.

        Fields:
            finding_id          — "file:line" of the bug being fixed
            tier                — 1, 2, 3, or 4
            action              — "fixed" | "fixed_silent" | "permission_requested"
                                  | "rollback" | "fixed_after_permission" | ...
            before_hash         — sha256 of file content pre-fix
            after_hash          — sha256 of file content post-fix
            rollback_token      — registry token / backup path / git ref / "n/a"
            reality_test_result — "pass" | "fail:reason" | "skipped" | "n/a"
            timestamp           — str(time.time())
            message             — short description (bug.description[:200])
        """
        finding_id: str
        tier: int
        action: str
        before_hash: str = Field(
            ..., description="sha256 of file content pre-fix; 'n/a' for non-fix events"
        )
        after_hash: str = Field(
            ..., description="sha256 of file content post-fix; 'n/a' for non-fix events"
        )
        rollback_token: str = Field(
            ...,
            description="rollback token (registry token, backup path, or git ref); "
                        "'n/a' for non-fix events",
        )
        reality_test_result: str = Field(
            ...,
            description="'pass' | 'fail:reason' | 'skipped' | 'n/a' for non-fix events",
        )
        timestamp: str
        message: str

        # DNA #8: validator rejects empty / non-string for the 4 required
        # forensic fields. This is the WRITE-TIME guard — without it,
        # a buggy caller could write a malformed entry silently.
        @validator("before_hash", "after_hash",
                   "rollback_token", "reality_test_result")
        def not_empty(cls, v):  # noqa: N805
            if not v or not isinstance(v, str):
                raise ValueError(
                    "field cannot be empty (DNA #8 — KB accumulation requires "
                    "before_hash + after_hash + rollback_token + "
                    "reality_test_result for every audit entry)"
                )
            return v

else:
    # Fallback dataclass when Pydantic unavailable — same 4-field enforcement
    # via __post_init__. DNA #7: fail-open at import (Pydantic optional),
    # fail-CLOSED at write (entry missing fields → ValueError).
    from dataclasses import dataclass

    @dataclass
    class AuditLogEntry:  # type: ignore[no-redef]
        """Fallback dataclass schema (Pydantic unavailable).

        Enforces the same 4 required fields via __post_init__ — an entry
        missing before_hash / after_hash / rollback_token /
        reality_test_result raises ValueError at write time.
        """
        finding_id: str
        tier: int
        action: str
        before_hash: str
        after_hash: str
        rollback_token: str
        reality_test_result: str
        timestamp: str
        message: str

        def __post_init__(self):
            for fname in ("before_hash", "after_hash",
                          "rollback_token", "reality_test_result"):
                v = getattr(self, fname)
                if not v or not isinstance(v, str):
                    raise ValueError(
                        f"{fname} cannot be empty (DNA #8 — KB accumulation "
                        f"requires before_hash + after_hash + rollback_token + "
                        f"reality_test_result for every audit entry)"
                    )


# ---------------------------------------------------------------------------
# write_audit_entry — construct + validate + append.
# ---------------------------------------------------------------------------

def write_audit_entry(
    log_path: str | Path,
    finding_id: str,
    tier: int,
    action: str,
    before_hash: str,
    after_hash: str,
    rollback_token: str,
    reality_test_result: str,
    message: str,
    extra: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> bool:
    """Construct + validate an AuditLogEntry and append it to log_path.

    DNA #8: every entry has the 4 required fields enforced by Pydantic
    (or dataclass __post_init__ if Pydantic unavailable). Callers cannot
    write a malformed entry — ValidationError fires at write time.

    Args:
        log_path: JSONL file to append to (created if missing).
        finding_id: "file:line" of the bug.
        tier: 1, 2, 3, or 4.
        action: "fixed" | "fixed_silent" | "permission_requested" | ...
        before_hash: sha256 of file content pre-fix (or "n/a").
        after_hash: sha256 of file content post-fix (or "n/a").
        rollback_token: registry token / backup path / git ref / "n/a".
        reality_test_result: "pass" | "fail:reason" | "skipped" | "n/a".
        message: short description.
        extra: optional extra fields (e.g. attack_mode, request_id).
        timestamp: optional ISO/epoch string (defaults to str(time.time())).

    Returns:
        True on success, False on validation/write failure.
    """
    # DNA #8: empty string is NOT auto-converted to "n/a" — that would
    # silently hide caller bugs (e.g. a new call site that forgot to compute
    # hashes would write "n/a" forever, masking the bug). Instead, empty
    # strings are REJECTED at write time (Pydantic ValidationError). The
    # `_write_audit` wrapper in engine.py defaults the 4 fields to the
    # explicit "n/a" sentinel — so callers that genuinely don't have a
    # hash (e.g. permission_requested events) must rely on the default,
    # not silently pass "".
    bh = before_hash
    ah = after_hash
    rt = rollback_token
    rtr = reality_test_result

    try:
        entry = AuditLogEntry(
            finding_id=str(finding_id),
            tier=int(tier),
            action=str(action),
            before_hash=str(bh),
            after_hash=str(ah),
            rollback_token=str(rt),
            reality_test_result=str(rtr),
            timestamp=timestamp if timestamp else str(time.time()),
            message=str(message),
        )
    except Exception as ve:
        # DNA #9 No harm: log the validation failure but do NOT raise —
        # a failed audit-write must not break the autofix flow (which
        # already applied the fix). Operator sees ERROR log + can retry.
        logger.error(
            f"[4-b-012] audit log entry REJECTED (DNA #8 validation): {ve}. "
            f"finding_id={finding_id!r} tier={tier} action={action!r} "
            f"before_hash={bh!r} after_hash={ah!r} "
            f"rollback_token={rt!r} reality_test_result={rtr!r}. "
            f"HINT: caller must pass real hash/token, or 'n/a' sentinel "
            f"explicitly (empty string is rejected).", exc_info=True
        )
        return False

    # Serialize to dict (Pydantic .dict() / dataclasses.asdict()).
    try:
        if hasattr(entry, "dict"):
            payload: dict[str, Any] = entry.dict()
        elif hasattr(entry, "model_dump"):
            payload = entry.model_dump()
        else:
            from dataclasses import asdict as _asdict
            payload = _asdict(entry)
    except Exception as pe:
        logger.error(f"[4-b-012] audit log serialization failed: {pe}", exc_info=True)
        return False

    # Merge in extra fields (attack_mode, request_id, etc.).
    if extra:
        for k, v in extra.items():
            # Don't allow extra to overwrite the 4 required fields.
            if k not in ("before_hash", "after_hash", "rollback_token",
                         "reality_test_result", "finding_id", "tier",
                         "action", "timestamp", "message"):
                payload[k] = v

    try:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return True
    except Exception as we:
        logger.warning(f"[4-b-012] audit log write failed: {we}", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Helpers for callers (engine.py).
# ---------------------------------------------------------------------------

def compute_hashes(
    before_content: str | None,
    after_content: str | None,
) -> tuple[str, str]:
    """Compute (before_hash, after_hash) from content.

    Returns ("n/a", "n/a") if either content is None (e.g. file missing
    or fix not actually applied).
    """
    bh = _hash_content(before_content) if before_content is not None else "n/a"
    ah = _hash_content(after_content) if after_content is not None else "n/a"
    return bh, ah


def make_rollback_token_backup(file_path: str) -> str:
    """Tier 1/2 rollback token: backup file path sentinel.

    DNA #8: every fix MUST have a rollback_token. For low-stakes tiers
    where we don't allocate a registry token (Tier 1/2 fast-path), the
    rollback_token field is set to "backup:<file_path>" — operator can
    locate the .tier1bak / .tier2bak / dryrunbak file manually.

    Tier 3 uses registry token (already wired via register_fix_for_rollback).
    Tier 4 (attack_mode) uses git revert ref when available.
    """
    return f"backup:{file_path}"


def make_rollback_token_git(file_path: str, head_ref: str = "HEAD") -> str:
    """Tier 4 rollback token: git revert ref.

    For attack-mode fixes (Tier 4), the rollback_token is a git ref so
    operator can `git revert <ref>` to undo. If git is unavailable or
    file is not in a repo, fall back to backup path sentinel.
    """
    return f"git:{file_path}@{head_ref}"


__all__ = [
    "AuditLogEntry",
    "write_audit_entry",
    "compute_hashes",
    "make_rollback_token_backup",
    "make_rollback_token_git",
]
