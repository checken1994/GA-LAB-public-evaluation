"""
[SCP-DNA-FIX R7-Full IMP-6 + IMP-9] Engine v2 extensions — rollback tokens + dry-run.

TẠI SAO file này tồn tại?
  R5/R6 audit log has: timestamp, file, line, fix, before_content. No
  after_hash, no reality_test_result, no rollback_token. Operator cannot
  revert a specific fix — only file-level restore from backup (loses ALL
  fixes in that file).

  R5/R6 Tier-2 fix applies DIRECTLY to source file. Operator cannot preview
  diff before apply. If fix wrong → rollback from backup (slow, loses other
  fixes in same file).

  This module adds 2 capabilities to AutoFixEngine (via monkey-patch at import):
    [IMP-6] Rollback tokens:
      - Each fix gets a rollback_token = sha256(patch + timestamp + file)[:16]
      - Stored in audit log alongside before_hash + after_hash + reality_result
      - rollback(token) reverts EXACTLY that fix (using stored before_content)
    [IMP-9] Dry-run mode:
      - dry_run=True writes patch to /tmp/scp-dryrun/{path} (snapshot)
      - NEVER touches the real file
      - Returns preview diff (unified format) for operator review
      - Operator approves → second call with dry_run=False applies for real

Inspired by:
  IMP-6: Git revert + Sentry release health (per-fix rollback, not file-level)
  IMP-9: terraform plan + git diff --staged (preview before apply)

DNA principles applied:
  IMP-6: #8 (KB accumulation) + #9 (No harm) + #17 (Operator oversight)
  IMP-9: #12 (Tăng tốc — diff first, apply after) + #17 + #11 (Reality check)

Usage (auto-injected at engine.py import time):
    engine = get_autofix_engine()
    result = engine.process_bug(bug)              # normal fix (auto-tokens)
    engine.rollback_fix_by_token("abc123def456")  # revert specific fix
    preview = engine.preview_fix_dry_run(bug)     # diff only, no apply
"""
from __future__ import annotations

import difflib
import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from scp.autofix.path_guard import sanitize_storage_path

logger = logging.getLogger("scp.autofix.engine_v2")


# ============================================================
# [IMP-6] RollbackTokenRegistry — per-fix rollback tokens.
# ============================================================

class RollbackTokenRegistry:
    """Registry of per-fix rollback tokens.

    Stores: {token: {file, before_hash, after_hash, before_content, timestamp, bug_id}}
    On-disk JSON format at data/rollback_tokens.json (single JSON file, atomic write).
    Lookup by token is O(1).
    """

    def __init__(self, data_dir: str | Path = "data"):
        # [S3-SECURITY-SWEEP] reject traversal-shaped data dirs (HIGH fix).
        self.data_dir = sanitize_storage_path(
            data_dir, default="data", label="rollback registry data dir",
        )
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"[IMP-6] mkdir failed for data dir: {e}")
        self.registry_file = self.data_dir / "rollback_tokens.json"
        self._registry: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.registry_file.exists():
            return {}
        try:
            with Path(self.registry_file).open(encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[IMP-6] rollback registry load failed: {e}")
            return {}

    def _save(self) -> None:
        try:
            tmp = self.registry_file.with_suffix(".tmp")
            with Path(tmp).open("w", encoding="utf-8") as f:
                json.dump(self._registry, f, ensure_ascii=False, indent=2)
            tmp.replace(self.registry_file)  # atomic on POSIX
        except OSError as e:
            logger.warning(f"[IMP-6] rollback registry save failed: {e}")

    @staticmethod
    def _hash_content(content: str) -> str:
        """SHA-256 of file content (first 32 hex chars = 128-bit hash, plenty)."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _make_token(patch: str, file_path: str, timestamp: float) -> str:
        """Generate a 16-char rollback token from patch + file + timestamp.

        SHA-256 of (patch + file_path + timestamp_ns), first 16 hex chars.
        Collision probability: 2^-64 (negligible for any realistic fleet).
        """
        raw = f"{patch}|{file_path}|{timestamp:.9f}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def register(
        self,
        file_path: str,
        before_content: str,
        after_content: str,
        patch: str,
        bug_id: str,
        bug_type: str,
        tier: int,
        reality_test_result: dict | None = None,
    ) -> str:
        """Register a fix → return its rollback token.

        Stores before_content so rollback can restore exactly. The token
        is also written to the audit log by the caller.
        """
        timestamp = time.time()
        token = self._make_token(patch, file_path, timestamp)
        self._registry[token] = {
            "token": token,
            "file": file_path,
            "bug_id": bug_id,
            "bug_type": bug_type,
            "tier": tier,
            "timestamp": timestamp,
            "before_hash": self._hash_content(before_content),
            "after_hash": self._hash_content(after_content),
            "before_content": before_content,
            "patch": patch,
            "reality_test_result": reality_test_result or {},
        }
        self._save()
        logger.info(
            f"[IMP-6] registered rollback token {token} for fix "
            f"{file_path} (bug_id={bug_id}, tier={tier})"
        )
        return token

    def lookup(self, token: str) -> dict[str, Any] | None:
        """Look up a fix by rollback token. Returns None if not found."""
        return self._registry.get(token)

    def rollback(self, token: str, force: bool = False) -> dict[str, Any]:
        """Rollback a specific fix by restoring its before_content.

        [SCP-DNA-FIX 4-b-013] DNA #9 (No harm) + DNA #4 (Con người quyết định):
        Pre-fix, when current file hash != recorded after_hash (newer fixes
        applied on top), this method only `logger.warning(...)` and proceeded
        to restore `before_content` — clobbering any newer fixes applied
        between our fix and the rollback call. Operator saw a warning but
        the damage was done (silent override without explicit --force).

        Post-fix: on hash mismatch, REFUSE the rollback (return ok=False
        with reason="file modified after fix — require force=True") UNLESS
        caller passes `force=True`. The force flag is the explicit operator
        override (DNA #4 — surface to human, don't silently decide).

        Args:
            token: 16-char rollback token from audit log.
            force: if True, proceed with restore EVEN IF current file hash
                != entry after_hash (will destroy newer changes). Use only
                when operator explicitly confirms clobber is acceptable.

        Returns:
            {
                "ok": bool,
                "token": str,
                "file": str,
                "reason": str,
                "current_hash": str (when refused — operator can compare
                                    against entry["after_hash"] to decide),
                "expected_after_hash": str (when refused),
            }
        """
        entry = self._registry.get(token)
        if entry is None:
            return {"ok": False, "token": token, "file": "",
                    "reason": f"token {token} not found in registry"}

        file_path = entry["file"]
        try:
            target = Path(file_path)
            if not target.exists():
                return {"ok": False, "token": token, "file": file_path,
                        "reason": f"file {file_path} no longer exists"}

            # Verify current file matches the AFTER hash (else someone else
            # modified it after our fix — rollback would lose their changes).
            current = target.read_text(encoding="utf-8")
            current_hash = self._hash_content(current)
            if current_hash != entry["after_hash"]:
                # DNA #9 No harm: REFUSE the rollback by default. Do NOT
                # proceed to restore before_content — that would clobber any
                # newer fixes applied between our fix and the rollback call.
                # Operator must explicitly pass force=True to override.
                logger.warning(
                    f"[IMP-6/4-b-013] file {file_path} was modified after fix "
                    f"{token} (current_hash={current_hash} != "
                    f"after_hash={entry['after_hash']}) — REFUSING rollback "
                    f"(DNA #9 No harm). Pass force=True to override and "
                    f"clobber newer changes."
                )
                if not force:
                    return {
                        "ok": False,
                        "token": token,
                        "file": file_path,
                        "reason": (
                            "hash mismatch: file modified after fix — "
                            "require force=True to overwrite (will destroy "
                            "newer changes), or snapshot current state first "
                            "via register() before reverting"
                        ),
                        "current_hash": current_hash,
                        "expected_after_hash": entry["after_hash"],
                        "force_required": True,
                    }
                # force=True: operator explicitly accepted clobber risk.
                logger.warning(
                    f"[IMP-6/4-b-013] force=True — proceeding to restore "
                    f"before_content (will CLOBBER newer changes on "
                    f"{file_path}). Operator explicitly accepted risk."
                )

            # Restore before_content atomically. A direct write_text() can
            # leave a truncated source file if the process/disk fails midway.
            # The worker and rollback API share this durability contract.
            tmp_name = None
            try:
                fd, tmp_name = tempfile.mkstemp(
                    prefix=f".{target.name}.rollback-",
                    suffix=".tmp",
                    dir=str(target.parent),
                    text=True,
                )
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                    handle.write(entry["before_content"])
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_name, target)
                tmp_name = None
            finally:
                if tmp_name:
                    try:
                        Path(tmp_name).unlink(missing_ok=True)
                    except OSError as unlink_err:
                        # silent-by-design: secondary temp-file cleanup after a
                        # rollback failure — outer handler reports rollback failed.
                        logger.debug(" rollback temp-file cleanup failed: %s", unlink_err, exc_info=True)
            logger.info(
                f"[IMP-6] rolled back fix {token} — restored {file_path} "
                f"to before_hash={entry['before_hash']}"
            )
            return {
                "ok": True,
                "token": token,
                "file": file_path,
                "reason": (
                    f"rollback OK — restored {file_path} to pre-fix state "
                    f"(token={token}, before_hash={entry['before_hash']}, "
                    f"forced={force})"
                ),
                "forced": force,
            }
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "token": token, "file": file_path,
                    "reason": f"rollback failed: {e}"}

    def list_tokens(self, file_path: str | None = None) -> list[dict[str, Any]]:
        """List all registered tokens (optionally filtered by file).

        Returns list of token metadata (without before_content — too large).
        """
        out = []
        for token, entry in self._registry.items():
            if file_path and entry["file"] != file_path:
                continue
            out.append({
                "token": token,
                "file": entry["file"],
                "bug_id": entry["bug_id"],
                "bug_type": entry["bug_type"],
                "tier": entry["tier"],
                "timestamp": entry["timestamp"],
                "before_hash": entry["before_hash"],
                "after_hash": entry["after_hash"],
            })
        # Sort by timestamp descending (most recent first)
        out.sort(key=lambda e: e["timestamp"], reverse=True)
        return out

    def stats(self) -> dict[str, Any]:
        return {
            "total_tokens": len(self._registry),
            "registry_file": str(self.registry_file),
        }


# Singleton registry (per data_dir). Keyed by data_dir for multi-tenant scenarios.
_token_registries: dict[str, RollbackTokenRegistry] = {}


def get_rollback_registry(data_dir: str | Path = "data") -> RollbackTokenRegistry:
    """Get the singleton RollbackTokenRegistry for a given data_dir."""
    key = str(Path(data_dir).resolve())
    if key not in _token_registries:
        _token_registries[key] = RollbackTokenRegistry(data_dir=data_dir)
    return _token_registries[key]


# ============================================================
# [IMP-9] DryRunManager — preview fixes without touching real files.
# ============================================================

class DryRunManager:
    """Manages dry-run snapshots for fix previews.

    When dry_run=True:
      1. The real file is NOT modified.
      2. A snapshot is written to /tmp/scp-dryrun/{sanitized_path}.
      3. The fix is applied to the snapshot.
      4. A unified diff (real → snapshot) is returned for operator review.
      5. If operator approves → call apply_dry_run_result() to copy snapshot
         to the real file.
    """

    def __init__(self, snapshot_root: str | Path | None = None):
        if snapshot_root is None:
            snapshot_root = Path(tempfile.gettempdir()) / "scp-dryrun"
        self.snapshot_root = Path(snapshot_root)
        self.snapshot_root.mkdir(parents=True, exist_ok=True)

    def _sanitize_path(self, file_path: str) -> Path:
        """Convert an absolute file path to a snapshot path under snapshot_root.

        /repo/scp/foo.py → /tmp/scp-dryrun/repo/scp/foo.py
        """
        # Strip leading slash + drive letter (Windows) to make a relative path.
        p = Path(file_path)
        parts = p.parts
        # Remove drive (Windows) and leading separator
        if parts and (parts[0].endswith(":\\") or parts[0].endswith(":/")):
            parts = parts[1:]
        elif parts and parts[0] in ("/", "\\"):
            parts = parts[1:]
        rel = Path(*parts) if parts else Path(p.name)
        return self.snapshot_root / rel

    def preview(
        self,
        file_path: str,
        patched_content: str,
    ) -> dict[str, Any]:
        """Generate a dry-run preview without touching the real file.

        Args:
            file_path: Real file path (will be READ but NOT written).
            patched_content: The proposed patched content.

        Returns:
            {
                "ok": bool,
                "diff": str,           — unified diff (real → patched)
                "snapshot_path": str,  — where the patched content was written
                "real_path": str,
                "stats": {additions, deletions, changes},
                "reason": str,
            }
        """
        try:
            real_path = Path(file_path)
            if not real_path.exists():
                return {"ok": False, "diff": "", "snapshot_path": "",
                        "real_path": file_path,
                        "stats": {},
                        "reason": f"real file not found: {file_path}"}

            original = real_path.read_text(encoding="utf-8")
            snapshot_path = self._sanitize_path(file_path)
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(patched_content, encoding="utf-8")

            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                original.splitlines(keepends=True),
                patched_content.splitlines(keepends=True),
                fromfile=f"a/{real_path.name}",  # git-style a/ b/
                tofile=f"b/{real_path.name}",
                n=3,  # context lines
            ))
            diff = "".join(diff_lines)

            # Stats
            additions = sum(1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++"))
            deletions = sum(1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---"))

            return {
                "ok": True,
                "diff": diff,
                "snapshot_path": str(snapshot_path),
                "real_path": str(real_path),
                "stats": {
                    "additions": additions,
                    "deletions": deletions,
                    "changes": additions + deletions,
                },
                "reason": (
                    f"dry-run OK — snapshot at {snapshot_path}, "
                    f"+{additions}/-{deletions} lines"
                ),
            }
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "diff": "", "snapshot_path": "",
                    "real_path": file_path, "stats": {},
                    "reason": f"dry-run error: {e}"}

    def apply_preview(self, snapshot_path: str, real_path: str) -> dict[str, Any]:
        """Apply a dry-run snapshot to the real file (after operator approval).

        Args:
            snapshot_path: Path returned by preview()["snapshot_path"].
            real_path: Real file path to overwrite.

        Returns:
            {"ok": bool, "reason": str}
        """
        try:
            snap = Path(snapshot_path)
            real = Path(real_path)
            if not snap.exists():
                return {"ok": False, "reason": f"snapshot not found: {snapshot_path}"}
            # Backup real file before overwrite (for safety).
            backup = real.with_suffix(real.suffix + ".dryrunbak")
            if real.exists():
                shutil.copy2(real, backup)
            shutil.copy2(snap, real)
            logger.info(
                f"[IMP-9] applied dry-run snapshot {snap} → {real} "
                f"(backup at {backup})"
            )
            return {
                "ok": True,
                "reason": (
                    f"applied dry-run snapshot to {real} "
                    f"(backup at {backup})"
                ),
                "backup_path": str(backup),
            }
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "reason": f"apply_preview error: {e}"}

    def cleanup(self, max_age_seconds: int = 86400) -> int:
        """Remove snapshots older than max_age_seconds. Returns count removed."""
        removed = 0
        now = time.time()
        for path in self.snapshot_root.rglob("*"):
            if path.is_file():
                try:
                    if now - path.stat().st_mtime > max_age_seconds:
                        path.unlink()
                        removed += 1
                except OSError as gc_err:
                    # silent-by-design: best-effort snapshot GC — leftover files
                    # are retried on the next cleanup cycle.
                    logger.debug(" snapshot GC unlink failed for %s: %s", path, gc_err, exc_info=True)
        return removed


# Singleton DryRunManager.
_dry_run_manager: DryRunManager | None = None


def get_dry_run_manager() -> DryRunManager:
    """Get the singleton DryRunManager instance."""
    global _dry_run_manager
    if _dry_run_manager is None:
        _dry_run_manager = DryRunManager()
    return _dry_run_manager


# ============================================================
# [IMP-6 + IMP-9] Engine extension methods — injected into AutoFixEngine.
# ============================================================

def _engine_rollback_fix_by_token(self, token: str) -> dict[str, Any]:
    """[IMP-6] Rollback a specific fix by its rollback token.

    Added to AutoFixEngine at import time.

    Args:
        token: 16-char rollback token from audit log.

    Returns:
        {"ok": bool, "token": str, "file": str, "reason": str}
    """
    registry = get_rollback_registry(self.data_dir)
    return registry.rollback(token)


def _engine_list_rollback_tokens(self, file_path: str | None = None) -> list[dict[str, Any]]:
    """[IMP-6] List rollback tokens (optionally filtered by file)."""
    registry = get_rollback_registry(self.data_dir)
    return registry.list_tokens(file_path=file_path)


def _engine_register_fix_for_rollback(
    self,
    file_path: str,
    before_content: str,
    after_content: str,
    patch: str,
    bug_id: str,
    bug_type: str,
    tier: int,
    reality_test_result: dict | None = None,
) -> str:
    """[IMP-6] Register a completed fix → return rollback token.

    Called by AutoFixEngine._auto_fix() after a successful patch.
    """
    registry = get_rollback_registry(self.data_dir)
    return registry.register(
        file_path=file_path,
        before_content=before_content,
        after_content=after_content,
        patch=patch,
        bug_id=bug_id,
        bug_type=bug_type,
        tier=tier,
        reality_test_result=reality_test_result,
    )


def _engine_preview_fix_dry_run(
    self,
    file_path: str,
    patched_content: str,
) -> dict[str, Any]:
    """[IMP-9] Generate a dry-run preview without touching the real file.

    Args:
        file_path: Real file path (read but NOT written).
        patched_content: Proposed patched content.

    Returns:
        {
            "ok": bool,
            "diff": str,            — unified diff
            "snapshot_path": str,
            "stats": {additions, deletions, changes},
            "reason": str,
        }
    """
    mgr = get_dry_run_manager()
    return mgr.preview(file_path, patched_content)


def _engine_apply_dry_run(self, snapshot_path: str, real_path: str) -> dict[str, Any]:
    """[IMP-9] Apply a dry-run snapshot to the real file (post-approval)."""
    mgr = get_dry_run_manager()
    return mgr.apply_preview(snapshot_path, real_path)


def _engine_rollback_registry_stats(self) -> dict[str, Any]:
    """[IMP-6] Return rollback registry stats for monitoring."""
    registry = get_rollback_registry(self.data_dir)
    return registry.stats()


def inject_v2_extensions(engine_cls) -> None:
    """Inject IMP-6 + IMP-9 methods into an AutoFixEngine class.

    Called once at engine.py import time. Idempotent (safe to call multiple
    times — checks if methods already present).
    """
    methods = {
        "rollback_fix_by_token":          _engine_rollback_fix_by_token,
        "list_rollback_tokens":           _engine_list_rollback_tokens,
        "register_fix_for_rollback":      _engine_register_fix_for_rollback,
        "preview_fix_dry_run":            _engine_preview_fix_dry_run,
        "apply_dry_run":                  _engine_apply_dry_run,
        "rollback_registry_stats":        _engine_rollback_registry_stats,
    }
    for name, method in methods.items():
        if not hasattr(engine_cls, name):
            setattr(engine_cls, name, method)
            logger.debug(f"[IMP-6/9] injected {name} into {engine_cls.__name__}")


__all__ = [
    "RollbackTokenRegistry",
    "DryRunManager",
    "get_rollback_registry",
    "get_dry_run_manager",
    "inject_v2_extensions",
]
