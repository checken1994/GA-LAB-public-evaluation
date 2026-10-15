"""
SCP V103 — StorageManager cho 24/7 operation
=============================================
Giải quyết bài toán lưu trữ khi SCP chạy 24/7 liên tục.

Vấn đề:
  - SCP chạy 24/7 → data liên tục tăng
  - Nếu không rotate → disk full → crash
  - SQLite DB phình to (V63: 32.9MB sau 17K câu → 200MB sau 100K câu)
  - JSONL files grow unbounded (bypass_log, error_store, crawl_log, ...)

Giải pháp V103:
  1. LOG ROTATION — file > 100MB → compress + archive
  2. DB VACUUM — SQLite VACUUM mỗi 1h (reclaim space)  [OPT-5] was 24h
  3. DATA ARCHIVAL — data > 30 ngày → move to archive/ + compress
  4. DISK MONITOR — check disk space mỗi 1h, alert if < 10%
  5. AUTO-CLEANUP — expired records, old logs, stale cache

Storage layout:
  data/                          ← active data (fast access)
    ├── v13.db                   ← SQLite (main DB)
    ├── error_store.jsonl        ← errors (50K cap)
    ├── bypass_log.jsonl         ← bypass events
    ├── knowledge/               ← domain-separated KB
    ├── crawl_log.jsonl
    └── ...
  data/archive/                  ← archived data (compressed)
    ├── 2026-07/
    │   ├── error_store_2026-07-28.jsonl.gz
    │   ├── bypass_log_2026-07-28.jsonl.gz
    │   └── v13_backup_2026-07-28.db.gz
    └── 2026-08/
  data/backups/                  ← DB backups (3-tier: local + GitHub + HF)
"""
from __future__ import annotations

import gzip
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.runtime.storage_manager")


@dataclass
class StorageStats:
    """Storage statistics."""
    total_size_mb: float = 0.0
    active_size_mb: float = 0.0
    archive_size_mb: float = 0.0
    backup_size_mb: float = 0.0
    largest_files: list[dict[str, Any]] = field(default_factory=list)
    disk_free_mb: float = 0.0
    disk_free_percent: float = 0.0
    files_rotated: int = 0
    files_archived: int = 0
    last_vacuum: float = 0.0
    last_cleanup: float = 0.0


class StorageManager:
    """Manage storage for 24/7 operation — rotation, archival, cleanup.

    Naming convention: <Purpose>Manager (world standard).

    Schedule:
      - Every 1h: check disk space, rotate large files
      - Every 1h: DB VACUUM, archive old data, cleanup expired  [OPT-5] was 24h
      - Every 7d: delete archives older than 90 days
    """

    # Thresholds
    ROTATE_SIZE_MB = 100       # file > 100MB → rotate
    ARCHIVE_AGE_DAYS = 30      # data > 30 days → archive
    DELETE_ARCHIVE_DAYS = 90   # archives > 90 days → delete
    DISK_ALERT_PERCENT = 10    # alert if disk < 10% free
    DB_VACUUM_INTERVAL_H = 1  # [OPT-5] was 24h — reduce data loss window (user request)

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.archive_dir = self.data_dir / "archive"
        self.backup_dir = self.data_dir / "backups"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._stats = StorageStats()
        self._last_vacuum = 0.0
        self._last_cleanup = 0.0

        # Files to monitor for rotation
        self._monitor_files = [
            "error_store.jsonl",
            "bypass_log.jsonl",
            "bypass_analysis.jsonl",
            "counter_audit.jsonl",
            "counter_forensic.jsonl",
            "human_alerts.jsonl",
            "human_review_queue.jsonl",
            "crawl_log.jsonl",
            "intel_updates.jsonl",
            "notifications.jsonl",
            "user_reports.jsonl",
            "phase3_audit.jsonl",
            "canary_tokens.jsonl",
            "canary_triggers.jsonl",
        ]

    def check_and_maintain(self) -> StorageStats:
        """Run full storage maintenance — should be called every 1h.

        Steps:
          1. Check disk space
          2. Rotate large files
          3. If 1h since last → VACUUM DB + archive old data  [OPT-5] was 24h
        """
        self._update_stats()
        now = time.time()

        # 1. Check disk space
        self._check_disk_space()

        # 2. Rotate large files
        rotated = self._rotate_large_files()
        self._stats.files_rotated += rotated

        # 3. DB VACUUM (every 1h)  [OPT-5] was 24h
        if now - self._last_vacuum > self.DB_VACUUM_INTERVAL_H * 3600:
            self._vacuum_db()
            self._last_vacuum = now
            self._stats.last_vacuum = now

        # 4. Archive old data (every 1h)  [OPT-5] was 24h
        if now - self._last_cleanup > self.DB_VACUUM_INTERVAL_H * 3600:
            archived = self._archive_old_data()
            self._stats.files_archived += archived
            self._cleanup_expired()
            self._last_cleanup = now
            self._stats.last_cleanup = now

        # 5. Delete old archives (every 7d — check inside)
        self._delete_old_archives()

        self._update_stats()
        return self._stats

    def _check_disk_space(self):
        """Check disk space — alert if low."""
        try:
            disk = os.statvfs(self.data_dir)
            free_bytes = disk.f_bavail * disk.f_frsize
            total_bytes = disk.f_blocks * disk.f_frsize
            self._stats.disk_free_mb = round(free_bytes / (1024 * 1024), 1)
            self._stats.disk_free_percent = round(free_bytes / total_bytes * 100, 1)

            if self._stats.disk_free_percent < self.DISK_ALERT_PERCENT:
                logger.warning(
                    f"[Storage] Disk space LOW: {self._stats.disk_free_percent}% free "
                    f"({self._stats.disk_free_mb}MB) — consider cleanup"
                )
        except Exception as e:
            logger.debug(f"[Storage] Disk check error: {e}", exc_info=True)

    def _rotate_large_files(self) -> int:
        """Rotate files larger than ROTATE_SIZE_MB.

        Rotation: rename to .1.gz, shift existing .1.gz → .2.gz, delete .3.gz

        [SCP-DNA-FIX R8-3] TẠI SAO: docstring nói "shift .1.gz → .2.gz, delete
        .3.gz" nhưng implementation cũ `gzip.open(gz_path, 'wb')` mở write+truncate
        → OVERWRITE .1.gz cũ mỗi lần rotate → chỉ giữ 1 generation, mất older
        rotations. Repro: rotate 2 lần → .1.gz = batch-2 (batch-1 bị ghi đè).
        Reality evidence: docstring lies convincingly (DNA #22). Fix matches
        docstring spec: shift .2.gz → .3.gz (delete .3.gz if exists first),
        shift .1.gz → .2.gz, THEN write new .1.gz. 3 generations kept.
        """
        MAX_GENERATIONS = 3  # .1.gz, .2.gz, .3.gz (cap, prevents unbounded growth)
        rotated = 0
        for filename in self._monitor_files:
            f = self.data_dir / filename
            if not f.is_file():
                continue
            try:
                size_mb = f.stat().st_size / (1024 * 1024)
                if size_mb > self.ROTATE_SIZE_MB:
                    #  Shift generations BEFORE writing new .1.gz.
                    # Build paths .1.gz .. .{MAX_GENERATIONS}.gz.
                    gz_paths = [
                        f.with_suffix(f.suffix + f".{gen}.gz")
                        for gen in range(1, MAX_GENERATIONS + 1)
                    ]
                    # Delete oldest (.3.gz) if exists — it's being pushed off.
                    if gz_paths[-1].is_file():
                        try:
                            gz_paths[-1].unlink()
                        except OSError as _e:
                            logger.debug(f"[Storage] R8-3 delete oldest gen: {_e}")
                    # Shift: .2.gz → .3.gz, then .1.gz → .2.gz (reverse order
                    # so we don't clobber before rename).
                    for gen in range(MAX_GENERATIONS - 1, 0, -1):
                        src_path = gz_paths[gen - 1]  # gen=2 → .1.gz index 0
                        dst_path = gz_paths[gen]      # gen=2 → .2.gz index 1
                        if src_path.is_file():
                            try:
                                src_path.rename(dst_path)
                            except OSError as _e:
                                logger.debug(f"[Storage] R8-3 shift gen {gen}: {_e}")
                    # Now write new .1.gz (gz_paths[0]) — no clobber risk.
                    gz_path = gz_paths[0]
                    with open(f, "rb") as src, gzip.open(gz_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    # Truncate original (keep last 1000 lines)
                    lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
                    f.write_text("\n".join(lines[-1000:]) + "\n", encoding="utf-8")
                    rotated += 1
                    logger.info(f"[Storage] Rotated {filename} ({size_mb:.1f}MB → compressed)")
            except Exception as e:
                logger.debug(f"[Storage] Rotate error for {filename}: {e}", exc_info=True)
        return rotated

    def _vacuum_db(self):
        """VACUUM SQLite database — reclaim space.

        [RUNTIME-FIX-4] Root cause (runtime log line 739):
          WARNING | scp.runtime.storage_manager | [Storage] VACUUM error:
            database disk image is malformed

        Bug: bare `conn.execute("VACUUM")` fails when DB is corrupted. The
        except clause just logs a warning and gives up — leaving the DB in a
        broken state where queries intermittently fail and ALTER TABLE
        migrations (like _migrate_reverify_schema) cannot add columns.

        Fix: attempt VACUUM first. If it fails with 'malformed', try recovery:
          1. VACUUM INTO '<db>.recovered' — creates a fresh DB from corrupted
             one, skipping bad pages (SQLite 3.27+, available since 2019).
          2. Swap: rename original to .broken.<ts>, rename .recovered to v13.db.
          3. If recovery also fails, log CRITICAL and signal for human
             intervention (DB needs restore from GitHub backup).
        """
        import os
        import sqlite3
        import time as _time
        db_path = self.data_dir / "v13.db"
        if not db_path.is_file():
            return
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("VACUUM")
            conn.close()
            size_mb = db_path.stat().st_size / (1024 * 1024)
            logger.info(f"[Storage] DB VACUUM complete — size: {size_mb:.1f}MB")
        except sqlite3.DatabaseError as e:
            err_msg = str(e).lower()
            if "malformed" in err_msg or "not a database" in err_msg:
                logger.error(
                    f"[Storage] DB corrupted ('{e}'). Attempting VACUUM INTO recovery..."
                )
                recovered_path = db_path.with_suffix(".db.recovered")
                try:
                    conn = sqlite3.connect(str(db_path))
                    # VACUUM INTO creates a new DB from the corrupted one,
                    # skipping bad pages. Available since SQLite 3.27.0 (2019).
                    # [SEC-S4] VACUUM INTO accepts a bound parameter for the
                    # filename — never interpolate the path into the SQL text.
                    # The char allowlist below stays as defense-in-depth so a
                    # corrupted config cannot smuggle exotic paths.
                    _rec_str = str(recovered_path)
                    if not _rec_str.replace("/", "").replace(".", "").replace("_", "").replace("-", "").isalnum():
                        raise ValueError(f"recovered_path contains unsafe characters: {_rec_str}")
                    conn.execute('VACUUM INTO ?', (_rec_str,))
                    conn.close()

                    # Swap: original -> .broken.<timestamp>, recovered -> original
                    backup_name = db_path.with_suffix(
                        f".db.broken.{int(_time.time())}"
                    )
                    os.rename(str(db_path), str(backup_name))
                    os.rename(str(recovered_path), str(db_path))

                    size_mb = db_path.stat().st_size / (1024 * 1024)
                    logger.info(
                        f"[Storage] DB recovered via VACUUM INTO — new size: "
                        f"{size_mb:.1f}MB. Old corrupted DB saved as {backup_name.name}"
                    )
                except Exception as recover_err:
                    # [ROOT-FIX-C] VACUUM INTO itself can fail when the DB is
                    # severely corrupted (runtime log: "CRITICAL: DB recovery
                    # FAILED: database disk image is malformed"). Final
                    # fallback: restore from local .db.gz backup (mirrored to
                    # GitHub by scp/core/github_backup.py). Without this the
                    # server enters a "limping" state where every query may
                    # fail unpredictably.
                    logger.critical(
                        f"[Storage] DB recovery FAILED: {recover_err}. "
                        f"Attempting GitHub backup restore..."
                    , exc_info=True)
                    backup_dir = self.data_dir / "backups"
                    if backup_dir.is_dir():
                        backups = sorted(
                            backup_dir.glob("v13_backup_*.db.gz"),
                            key=lambda f: f.stat().st_mtime,
                            reverse=True,
                        )
                        if backups:
                            latest = backups[0]
                            logger.warning(
                                f"[Storage] Restoring DB from local backup: {latest.name}"
                            )
                            try:
                                import gzip
                                import shutil
                                # [SEC-S4] Containment guard: the restored
                                # backup must live inside data_dir/backups and
                                # the target must stay inside data_dir — a
                                # crafted filename must never escape them.
                                if not latest.resolve().is_relative_to(backup_dir.resolve()):
                                    raise ValueError(
                                        f"backup path escapes backups dir: {latest}"
                                    )
                                if not db_path.resolve().is_relative_to(self.data_dir.resolve()):
                                    raise ValueError(
                                        f"db path escapes data dir: {db_path}"
                                    )
                                with gzip.open(latest, "rb") as src, \
                                        Path(db_path).open("wb") as dst:
                                    shutil.copyfileobj(src, dst)
                                size_mb = db_path.stat().st_size / (1024 * 1024)
                                logger.info(
                                    f"[Storage] DB restored from backup — "
                                    f"size: {size_mb:.1f}MB"
                                )
                            except Exception as restore_err:
                                logger.critical(
                                    f"[Storage] Restore from backup FAILED: "
                                    f"{restore_err}. Manual restore required: "
                                    f"download from GitHub backups repo. "
                                    f"Server will continue but DB queries "
                                    f"may fail unpredictably."
                                , exc_info=True)
                        else:
                            logger.critical(
                                f"[Storage] No local .db.gz backups found in "
                                f"{backup_dir}. Manual restore required: "
                                f"download from GitHub backups repo "
                                f"(scp/core/github_backup.py). Server will "
                                f"continue but DB queries may fail."
                            )
                    else:
                        logger.critical(
                            f"[Storage] Backup dir {backup_dir} does not exist. "
                            f"Manual restore required: download from GitHub "
                            f"backups repo (scp/core/github_backup.py). "
                            f"Server will continue but DB queries may fail."
                        )
            else:
                logger.warning(f"[Storage] VACUUM error: {e}")
        except Exception as e:
            logger.warning(f"[Storage] VACUUM error: {e}", exc_info=True)

    def _archive_old_data(self) -> int:
        """Move data older than ARCHIVE_AGE_DAYS to archive/.

        Returns: number of files archived.
        """
        archived = 0
        now = time.time()
        cutoff = now - (self.ARCHIVE_AGE_DAYS * 86400)

        # Archive month folder
        month_folder = self.archive_dir / time.strftime("%Y-%m", time.gmtime(now))
        month_folder.mkdir(parents=True, exist_ok=True)

        for filename in self._monitor_files:
            f = self.data_dir / filename
            if not f.is_file():
                continue
            try:
                mtime = f.stat().st_mtime
                if mtime < cutoff:
                    # Compress + move to archive
                    archive_name = f"{filename}_{time.strftime('%Y-%m-%d', time.gmtime(mtime))}.gz"
                    archive_path = month_folder / archive_name
                    with open(f, "rb") as src, gzip.open(archive_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    # Truncate original (keep last 100 lines)
                    lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
                    f.write_text("\n".join(lines[-100:]) + "\n", encoding="utf-8")
                    archived += 1
                    logger.info(f"[Storage] Archived {filename} → {archive_path}")
            except Exception as e:
                logger.debug(f"[Storage] Archive error for {filename}: {e}", exc_info=True)

        # Archive old knowledge files
        knowledge_dir = self.data_dir / "knowledge"
        if knowledge_dir.is_dir():
            for kf in knowledge_dir.glob("*.jsonl"):
                try:
                    if kf.stat().st_mtime < cutoff:
                        archive_name = f"knowledge_{kf.stem}_{time.strftime('%Y-%m-%d')}.gz"
                        archive_path = month_folder / archive_name
                        with open(kf, "rb") as src, gzip.open(archive_path, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        # Keep only recent records (last 500)
                        lines = kf.read_text(encoding="utf-8", errors="replace").splitlines()
                        kf.write_text("\n".join(lines[-500:]) + "\n", encoding="utf-8")
                        archived += 1
                except Exception as e:
                    logger.debug(f"[Storage] Knowledge archive error: {e}", exc_info=True)

        return archived

    def _cleanup_expired(self):
        """Cleanup expired records from DomainKnowledgeStore."""
        # This is handled by DomainKnowledgeStore.cleanup_expired()
        # Just trigger it via the judge instance if available
        pass

    def _delete_old_archives(self):
        """Delete archives older than DELETE_ARCHIVE_DAYS."""
        now = time.time()
        cutoff = now - (self.DELETE_ARCHIVE_DAYS * 86400)
        deleted = 0

        for month_dir in self.archive_dir.iterdir():
            if not month_dir.is_dir():
                continue
            try:
                # Check if month folder is old enough
                folder_time = month_dir.stat().st_mtime
                if folder_time < cutoff:
                    shutil.rmtree(month_dir)
                    deleted += 1
                    logger.info(f"[Storage] Deleted old archive: {month_dir.name}")
            except Exception as e:
                logger.debug(f"[Storage] Delete archive error: {e}", exc_info=True)

        if deleted > 0:
            logger.info(f"[Storage] Deleted {deleted} old archive folders (> {self.DELETE_ARCHIVE_DAYS} days)")

    def _update_stats(self):
        """Update storage statistics."""
        try:
            # Active data size
            active_size = 0
            for f in self.data_dir.rglob("*"):
                if f.is_file() and "archive" not in str(f) and "backups" not in str(f):
                    active_size += f.stat().st_size
            self._stats.active_size_mb = round(active_size / (1024 * 1024), 1)

            # Archive size
            archive_size = 0
            if self.archive_dir.is_dir():
                for f in self.archive_dir.rglob("*"):
                    if f.is_file():
                        archive_size += f.stat().st_size
            self._stats.archive_size_mb = round(archive_size / (1024 * 1024), 1)

            # Backup size
            backup_size = 0
            if self.backup_dir.is_dir():
                for f in self.backup_dir.rglob("*"):
                    if f.is_file():
                        backup_size += f.stat().st_size
            self._stats.backup_size_mb = round(backup_size / (1024 * 1024), 1)

            self._stats.total_size_mb = (
                self._stats.active_size_mb +
                self._stats.archive_size_mb +
                self._stats.backup_size_mb
            )

            # Largest files
            file_sizes = []
            for f in self.data_dir.rglob("*"):
                if f.is_file() and "archive" not in str(f) and "backups" not in str(f):
                    file_sizes.append({"file": str(f.relative_to(self.data_dir)), "size_mb": round(f.stat().st_size / (1024 * 1024), 1)})
            file_sizes.sort(key=lambda x: -x["size_mb"])
            self._stats.largest_files = file_sizes[:10]

        except Exception as e:
            logger.debug(f"[Storage] Stats update error: {e}", exc_info=True)

    def backup_db(self) -> bool:
        """Backup SQLite DB to backup_dir (compressed)."""
        db_path = self.data_dir / "v13.db"
        if not db_path.is_file():
            return False
        try:
            backup_name = f"v13_backup_{time.strftime('%Y-%m-%d_%H%M')}.db.gz"
            backup_path = self.backup_dir / backup_name
            with open(db_path, "rb") as src, gzip.open(backup_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            logger.info(f"[Storage] DB backup: {backup_path}")
            # Keep only last 7 backups
            backups = sorted(self.backup_dir.glob("v13_backup_*.db.gz"), key=lambda f: f.stat().st_mtime)
            for old in backups[:-7]:
                old.unlink()
            return True
        except Exception as e:
            logger.warning(f"[Storage] Backup error: {e}", exc_info=True)
            return False

    def stats(self) -> dict[str, Any]:
        self._update_stats()
        return {
            "total_size_mb": self._stats.total_size_mb,
            "active_size_mb": self._stats.active_size_mb,
            "archive_size_mb": self._stats.archive_size_mb,
            "backup_size_mb": self._stats.backup_size_mb,
            "disk_free_mb": self._stats.disk_free_mb,
            "disk_free_percent": self._stats.disk_free_percent,
            "files_rotated": self._stats.files_rotated,
            "files_archived": self._stats.files_archived,
            "last_vacuum": self._stats.last_vacuum,
            "last_cleanup": self._stats.last_cleanup,
            "largest_files": self._stats.largest_files[:5],
            "thresholds": {
                "rotate_mb": self.ROTATE_SIZE_MB,
                "archive_days": self.ARCHIVE_AGE_DAYS,
                "delete_archive_days": self.DELETE_ARCHIVE_DAYS,
                "disk_alert_percent": self.DISK_ALERT_PERCENT,
            },
        }


__all__ = ["StorageStats", "StorageManager"]
