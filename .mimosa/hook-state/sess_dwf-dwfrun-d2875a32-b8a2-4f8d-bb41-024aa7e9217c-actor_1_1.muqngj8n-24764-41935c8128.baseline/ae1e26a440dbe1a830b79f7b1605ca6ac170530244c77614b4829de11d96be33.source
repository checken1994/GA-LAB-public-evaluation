"""
[SCP-DNA-FIX 4-b-013] RollbackTokenRegistry — refuses on hash mismatch.

This module is the public API for rollback. The implementation lives in
`engine_extensions.py` (RollbackTokenRegistry class). This module:
  1. Re-exports RollbackTokenRegistry + helpers so callers have a stable
     import path (`scp.autofix.rollback_registry`).
  2. Adds a `rollback_or_raise()` helper that RAISES RuntimeError on hash
     mismatch (instead of returning ok=False) — for callers that prefer
     exceptions over dict inspection.

TẠI SAO file này tồn tại?
  Pre-fix: `RollbackTokenRegistry.rollback(token)` (in engine_extensions.py)
  checked if the current file hash matches the recorded `after_hash`. If
  MISMATCH (file was modified by another fix after ours), it only
  `logger.warning(...)` and PROCEEDED to restore `before_content` —
  clobbering any newer fixes applied between our fix and the rollback
  call. Operator saw a warning but the damage was done (DNA #9 No harm
  violation; DNA #4 Con người quyết định violation — silent override).

  Post-fix:
    - `RollbackTokenRegistry.rollback(token, force=False)` now REFUSES the
      rollback on hash mismatch (returns ok=False + reason + current_hash +
      expected_after_hash + force_required=True). Restore only happens if
      either:
        (a) current_hash == entry.after_hash (safe — no newer changes lost), OR
        (b) caller explicitly passes force=True (operator override).

    - `rollback_or_raise(token, force=False)` — same as rollback(), but
      RAISES `RuntimeError` on hash mismatch (when force=False) for
      callers that prefer exception-based control flow. This is the
      explicit "refuse" path mandated by DNA #9.

DNA principles applied:
  #9 (No harm — refuse rollback that would destroy newer changes)
  #4 (Con người quyết định — force flag is the explicit operator override)
  #8 (KB accumulation — refusal carries current_hash + expected_after_hash
      so operator can decide based on evidence, not guesswork)
  #22 (PASS ≠ TRUE — pre-fix code claimed "operator request" but never
      asked operator; post-fix code requires explicit force=True)
"""
from __future__ import annotations

import logging
from typing import Any

# Re-export everything from engine_extensions so this module is a drop-in
# replacement for `from scp.autofix.engine_extensions import RollbackTokenRegistry`.
from scp.autofix.engine_extensions import (  # noqa: F401
    RollbackTokenRegistry,
    _token_registries,
    get_rollback_registry,
)

logger = logging.getLogger("scp.autofix.rollback_registry")


def rollback_or_raise(
    token: str,
    data_dir: str = "data",
    force: bool = False,
) -> dict[str, Any]:
    """Roll back a fix by token; RAISE on hash mismatch (DNA #9 refuse).

    Wrapper around `RollbackTokenRegistry.rollback(token, force=force)`.
    If the registry returns `{"ok": False, "force_required": True}` (hash
    mismatch + force=False), this function RAISES `RuntimeError` with the
    mismatch details so the caller's exception handler can decide.

    Use this when your control flow is exception-based (e.g. CLI scripts,
    API endpoints that map exceptions to HTTP 409). Use
    `RollbackTokenRegistry.rollback(token, force=force)` directly when
    you prefer dict-return inspection.

    Args:
        token: 16-char rollback token from audit log.
        data_dir: data directory (default "data").
        force: if True, override hash mismatch check (will clobber newer
               changes). Operator must explicitly opt in.

    Returns:
        The rollback result dict on success.

    Raises:
        RuntimeError: on hash mismatch when force=False. Message includes
            current_hash + expected_after_hash so operator can decide.
        ValueError: on token-not-found or file-not-found (when caller
            prefers exception over dict inspection).
    """
    registry = get_rollback_registry(data_dir)
    result = registry.rollback(token, force=force)
    if result.get("ok"):
        return result

    reason = result.get("reason", "unknown")
    if result.get("force_required"):
        # DNA #9 No harm: refuse — raise RuntimeError on hash mismatch.
        current = result.get("current_hash", "?")
        expected = result.get("expected_after_hash", "?")
        raise RuntimeError(
            f"[4-b-013] rollback REFUSED for token {token!r}: hash mismatch "
            f"(current_hash={current} != expected_after_hash={expected}). "
            f"File was modified after the original fix — restoring would "
            f"clobber newer changes (DNA #9 No harm). "
            f"Reason: {reason}. "
            f"To override, pass force=True (operator explicitly accepts "
            f"clobber risk)."
        )
    # Other failures (token not found, file missing, etc.) — raise ValueError.
    raise ValueError(f"[4-b-013] rollback failed for token {token!r}: {reason}")


__all__ = [
    "RollbackTokenRegistry",
    "get_rollback_registry",
    "rollback_or_raise",
]
