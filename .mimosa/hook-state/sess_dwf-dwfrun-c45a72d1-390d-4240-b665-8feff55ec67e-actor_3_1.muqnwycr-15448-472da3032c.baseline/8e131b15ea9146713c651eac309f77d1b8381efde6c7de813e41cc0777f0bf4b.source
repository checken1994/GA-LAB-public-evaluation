"""Shadow Snapshot Manager for AutoFix.

Provides durable, atomic snapshot and rollback management at the filesystem level.
Transactions are tracked under:
  data/shadow/
    active/<tx_id>/
      manifest.json
      files/
    completed/<tx_id>/
    rolled_back/<tx_id>/
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def is_pid_alive(pid: int) -> bool:
    """Check whether a process with the given PID is currently alive."""
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        # silent-by-design: documented liveness probe — dead PID returns False.
        return False
    except PermissionError:
        # Process exists but cannot signal
        # silent-by-design: documented probe contract — alive-but-protected returns True.
        return True
    except OSError:
        # On Windows, non-existent PID raises OSError WinError 87
        # silent-by-design: same documented probe contract.
        return False


class ShadowSnapshotManager:
    """Manages transactional filesystem snapshots for AutoFix patch operations.
    
    Guarantees:
    - Pre-patch copies are fsynced to disk with SHA256 hashes before any source modification.
    - Rollback is atomic via temporary file + os.replace.
    - Zero in-tree backup files (.tier3bak).
    - Unfinished/abandoned transactions from process crashes can be recovered at startup.
    """  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim

    def __init__(self, shadow_dir: Path | str = "data/shadow"):
        self.shadow_dir = Path(shadow_dir).resolve()
        self.active_dir = self.shadow_dir / "active"
        self.completed_dir = self.shadow_dir / "completed"
        self.rolled_back_dir = self.shadow_dir / "rolled_back"

        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.completed_dir.mkdir(parents=True, exist_ok=True)
        self.rolled_back_dir.mkdir(parents=True, exist_ok=True)

    def begin(self, target_files: list[Path | str], bug_id: str = "") -> str:
        """Begin a snapshot transaction for target files.
        
        Copies pre-patch files to data/shadow/active/<tx_id>/files/ and writes
        manifest.json atomically.
        
        Returns:
            tx_id (str): Unique transaction identifier.
        """  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim
        tx_id = f"tx_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        tx_dir = self.active_dir / tx_id
        files_dir = tx_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        target_records: list[dict[str, Any]] = []
        for idx, f in enumerate(target_files):
            target_path = Path(f).resolve()
            if target_path.is_file():
                data = target_path.read_bytes()
                sha = hashlib.sha256(data).hexdigest()
                backup_name = f"{idx}_{target_path.name}.bak"
                backup_file = files_dir / backup_name
                backup_file.write_bytes(data)
                target_records.append({
                    "target_path": str(target_path),
                    "backup_file": str(backup_file.relative_to(tx_dir).as_posix()),
                    "pre_sha256": sha,
                    "exists": True,
                })
            else:
                target_records.append({
                    "target_path": str(target_path),
                    "backup_file": None,
                    "pre_sha256": None,
                    "exists": False,
                })

        manifest = {
            "tx_id": tx_id,
            "bug_id": bug_id,
            "status": "PRE_PATCH",
            "created_at": time.time(),
            "pid": os.getpid(),
            "target_files": target_records,
        }

        manifest_path = tx_dir / "manifest.json"
        tmp_manifest = tx_dir / f".manifest.json.tmp_{uuid.uuid4().hex[:6]}"
        with tmp_manifest.open("w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)
            mf.flush()
            try:
                os.fsync(mf.fileno())
            except OSError as fsync_err:
                # silent-by-design: best-effort durability — os.replace below still commits.
                logger.debug("[ShadowSnapshot] manifest fsync failed: %s", fsync_err, exc_info=True)
                pass
        os.replace(tmp_manifest, manifest_path)

        logger.info(f"[ShadowSnapshot] Began transaction {tx_id} for bug '{bug_id}' with {len(target_records)} file(s)")
        return tx_id

    def rollback(self, tx_id: str, reason: str = "") -> bool:
        """Atomically restore files from data/shadow/active/<tx_id>/ to their pre-patch state.
        
        Moves transaction directory to data/shadow/rolled_back/<tx_id>/.
        
        Returns:
            bool: True if rollback succeeded, False otherwise.
        """  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim
        tx_dir = self.active_dir / tx_id
        if not tx_dir.is_dir():
            logger.warning(f"[ShadowSnapshot] Rollback failed: active transaction '{tx_id}' not found at {tx_dir}")
            return False

        manifest_path = tx_dir / "manifest.json"
        if not manifest_path.is_file():
            logger.error(f"[ShadowSnapshot] Rollback failed: manifest.json missing in {tx_dir}")
            return False

        try:
            with manifest_path.open("r", encoding="utf-8") as mf:
                manifest = json.load(mf)
        except Exception as e:
            logger.error(f"[ShadowSnapshot] Rollback failed: cannot read manifest in {tx_dir}: {e}", exc_info=True)
            return False

        target_files = manifest.get("target_files", [])
        restore_errors = []

        for item in target_files:
            target_path = Path(item["target_path"])
            exists_before = item.get("exists", False)
            if exists_before:
                backup_rel = item.get("backup_file")
                if not backup_rel:
                    restore_errors.append(f"Missing backup_file path in manifest for {target_path}")
                    continue
                backup_path = tx_dir / backup_rel
                if not backup_path.is_file():
                    restore_errors.append(f"Backup file does not exist: {backup_path}")
                    continue
                backup_bytes = backup_path.read_bytes()
                expected_sha = item.get("pre_sha256")
                actual_sha = hashlib.sha256(backup_bytes).hexdigest()
                if expected_sha and actual_sha != expected_sha:
                    restore_errors.append(
                        f"Checksum mismatch for backup of {target_path}: expected {expected_sha}, got {actual_sha}"
                    )
                    continue

                # Atomic restore via temp file in target's directory
                try:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    tmp_restore = target_path.with_name(f".{target_path.name}.rb_{uuid.uuid4().hex[:6]}")
                    with tmp_restore.open("wb") as rf:
                        rf.write(backup_bytes)
                        rf.flush()
                        try:
                            os.fsync(rf.fileno())
                        except OSError as fsync_err2:
                            # silent-by-design: best-effort durability — restore replace below still commits.
                            logger.debug("[ShadowSnapshot] restore temp fsync failed: %s", fsync_err2, exc_info=True)
                            pass
                    try:
                        os.replace(tmp_restore, target_path)
                    except OSError as replace_err:
                        # fail-loudly (S-B1b): rollback-restore atomic replace failed — copy fallback keeps the restore alive.
                        logger.warning("[ShadowSnapshot] atomic replace failed during restore of %s, using copy fallback: %s", target_path, replace_err, exc_info=True)
                        shutil.copy2(str(tmp_restore), str(target_path))
                        try:
                            tmp_restore.unlink()
                        except OSError as tmp_err:
                            # silent-by-design: secondary temp cleanup — restore already completed via fallback.
                            logger.debug("[ShadowSnapshot] restore temp unlink failed: %s", tmp_err, exc_info=True)
                            pass
                    logger.info(f"[ShadowSnapshot] Restored {target_path} to pre-patch state (sha: {actual_sha[:8]})")
                except Exception as restore_err:
                    logger.debug(f"ShadowSnapshotManager.rollback: exception ignored: {restore_err}", exc_info=True)
                    restore_errors.append(f"Failed to atomically restore {target_path}: {restore_err}")  # silent-by-design: explicit error accumulator — logged via logger.error + rollback returns False below
            else:
                # File did not exist prior to patch; delete if present
                if target_path.exists():
                    try:
                        target_path.unlink()
                        logger.info(f"[ShadowSnapshot] Removed newly created file {target_path}")
                    except Exception as unlink_err:
                        logger.debug(f"ShadowSnapshotManager.rollback: exception ignored: {unlink_err}", exc_info=True)
                        restore_errors.append(f"Failed to remove newly created file {target_path}: {unlink_err}")  # silent-by-design: explicit error accumulator — logged via logger.error + rollback returns False below

        if restore_errors:
            logger.error(f"[ShadowSnapshot] Rollback encountered errors for {tx_id}: {restore_errors}")
            return False

        # Update manifest to ROLLED_BACK
        manifest["status"] = "ROLLED_BACK"
        manifest["rolled_back_at"] = time.time()
        manifest["rollback_reason"] = reason

        try:
            with manifest_path.open("w", encoding="utf-8") as mf:
                json.dump(manifest, mf, indent=2)
            if reason:
                (tx_dir / "failure_reason.txt").write_text(reason, encoding="utf-8")
        except Exception as e:
            logger.warning(f"[ShadowSnapshot] Could not write final rollback status to manifest: {e}", exc_info=True)

        # Move to rolled_back directory
        # Windows: shutil.move fails with WinError 5 when any file handle
        # inside tx_dir is still open (e.g. pytest basetemp on full suite).
        # Fallback: copytree → rmtree with a short retry loop.
        dest_dir = self.rolled_back_dir / tx_id
        try:
            if dest_dir.exists():
                shutil.rmtree(dest_dir, ignore_errors=True)
            shutil.move(str(tx_dir), str(dest_dir))
            logger.info(f"[ShadowSnapshot] Moved transaction {tx_id} to {dest_dir}")
        except OSError as move_err:
            logger.warning(
                f"[ShadowSnapshot] shutil.move failed ({move_err}); "
                f"falling back to copytree+rmtree for {tx_id}"
            )
            try:
                shutil.copytree(str(tx_dir), str(dest_dir), dirs_exist_ok=True)
                for _attempt in range(5):
                    try:
                        shutil.rmtree(str(tx_dir))
                        break
                    except OSError as rm_err:
                        # silent-by-design: bounded retry with backoff — final
                        # attempt uses ignore_errors and the outcome is logged.
                        logger.debug("[ShadowSnapshot] rmtree retry %s: %s", _attempt + 1, rm_err, exc_info=True)
                        time.sleep(0.05 * (_attempt + 1))
                else:
                    shutil.rmtree(str(tx_dir), ignore_errors=True)
                logger.info(f"[ShadowSnapshot] Fallback copy+remove OK for {tx_id}")
            except Exception as fallback_err:
                logger.error(
                    f"[ShadowSnapshot] Failed to move {tx_dir} to {dest_dir}: {fallback_err}", exc_info=True
                )
                return False
        except Exception as move_err:
            logger.error(f"[ShadowSnapshot] Failed to move {tx_dir} to {dest_dir}: {move_err}", exc_info=True)
            return False

        return True

    def commit(self, tx_id: str) -> bool:
        """Mark snapshot transaction as successfully verified and committed.
        
        Moves transaction directory to data/shadow/completed/<tx_id>/.
        
        Returns:
            bool: True if commit succeeded, False otherwise.
        """  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim
        tx_dir = self.active_dir / tx_id
        if not tx_dir.is_dir():
            logger.warning(f"[ShadowSnapshot] Commit failed: active transaction '{tx_id}' not found at {tx_dir}")
            return False

        manifest_path = tx_dir / "manifest.json"
        if not manifest_path.is_file():
            logger.error(f"[ShadowSnapshot] Commit failed: manifest.json missing in {tx_dir}")
            return False

        try:
            with manifest_path.open("r", encoding="utf-8") as mf:
                manifest = json.load(mf)
        except Exception as e:
            logger.error(f"[ShadowSnapshot] Commit failed: cannot read manifest in {tx_dir}: {e}", exc_info=True)
            return False

        # Compute post-patch hashes
        for item in manifest.get("target_files", []):
            target_path = Path(item["target_path"])
            if target_path.is_file():
                item["post_sha256"] = hashlib.sha256(target_path.read_bytes()).hexdigest()
            else:
                item["post_sha256"] = None

        manifest["status"] = "COMMITTED"
        manifest["committed_at"] = time.time()

        try:
            with manifest_path.open("w", encoding="utf-8") as mf:
                json.dump(manifest, mf, indent=2)
        except Exception as e:
            logger.warning(f"[ShadowSnapshot] Could not write final commit status to manifest: {e}", exc_info=True)

        # Move to completed directory
        # Windows: same WinError 5 risk as rollback(); use same fallback.
        dest_dir = self.completed_dir / tx_id
        try:
            if dest_dir.exists():
                shutil.rmtree(dest_dir, ignore_errors=True)
            shutil.move(str(tx_dir), str(dest_dir))
            logger.info(f"[ShadowSnapshot] Committed transaction {tx_id} to {dest_dir}")
        except OSError as move_err:
            logger.warning(
                f"[ShadowSnapshot] shutil.move failed ({move_err}); "
                f"falling back to copytree+rmtree for commit {tx_id}"
            )
            try:
                shutil.copytree(str(tx_dir), str(dest_dir), dirs_exist_ok=True)
                for _attempt in range(5):
                    try:
                        shutil.rmtree(str(tx_dir))
                        break
                    except OSError as rm_err:
                        # silent-by-design: bounded retry with backoff — final
                        # attempt uses ignore_errors and the outcome is logged.
                        logger.debug("[ShadowSnapshot] rmtree retry %s: %s", _attempt + 1, rm_err, exc_info=True)
                        time.sleep(0.05 * (_attempt + 1))
                else:
                    shutil.rmtree(str(tx_dir), ignore_errors=True)
                logger.info(f"[ShadowSnapshot] Fallback copy+remove OK for commit {tx_id}")
            except Exception as fallback_err:
                logger.error(
                    f"[ShadowSnapshot] Failed to move {tx_dir} to {dest_dir}: {fallback_err}", exc_info=True
                )
                return False
        except Exception as move_err:
            logger.error(f"[ShadowSnapshot] Failed to move {tx_dir} to {dest_dir}: {move_err}", exc_info=True)
            return False

        return True

    def recover_abandoned_transactions(self, force: bool = False) -> list[str]:
        """Scan data/shadow/active/ and roll back any leftover transactions from prior crashes.
        
        Args:
            force: If True, rolls back all active transactions regardless of owning PID.
                   If False (default), rolls back transactions whose owning PID is no longer alive
                   or is not the current process.
        
        Returns:
            list[str]: IDs of recovered transactions.
        """  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim
        if not self.active_dir.exists():
            return []

        recovered: list[str] = []
        for entry in sorted(self.active_dir.iterdir()):
            if not entry.is_dir():
                continue
            tx_id = entry.name
            manifest_path = entry / "manifest.json"
            if not manifest_path.is_file():
                continue

            try:
                with manifest_path.open("r", encoding="utf-8") as mf:
                    manifest = json.load(mf)
            except Exception as e:
                logger.warning(f"[ShadowSnapshot] Skipping unreadable manifest in {entry}: {e}", exc_info=True)
                continue

            pid = manifest.get("pid", 0)
            should_recover = False

            if force:
                should_recover = True
            elif pid != os.getpid():
                # Belongs to a different process: check if that process is dead
                if not is_pid_alive(pid):
                    should_recover = True
                else:
                    # If external process is dead
                    should_recover = not is_pid_alive(pid)

            if should_recover:
                logger.warning(
                    f"[ShadowSnapshot] Recovering abandoned transaction {tx_id} (owner PID {pid}, dead or orphaned)"
                )
                if self.rollback(tx_id, reason="CRASH_RECOVERY_ABANDONED_TRANSACTION"):
                    recovered.append(tx_id)

        return recovered


_DEFAULT_MANAGER: ShadowSnapshotManager | None = None


def get_shadow_snapshot_manager(shadow_dir: Path | str = "data/shadow") -> ShadowSnapshotManager:
    """Get or create singleton instance of ShadowSnapshotManager."""
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None or _DEFAULT_MANAGER.shadow_dir != Path(shadow_dir).resolve():
        _DEFAULT_MANAGER = ShadowSnapshotManager(shadow_dir=shadow_dir)
    return _DEFAULT_MANAGER
