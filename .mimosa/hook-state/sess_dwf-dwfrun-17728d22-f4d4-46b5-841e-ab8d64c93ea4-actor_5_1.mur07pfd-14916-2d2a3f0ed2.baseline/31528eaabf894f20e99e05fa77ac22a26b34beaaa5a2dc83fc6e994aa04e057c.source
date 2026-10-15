"""
[SCP-DNA-FIX R7-Full IMP-12] Diff-Aware Re-scan — NEW autofix pipeline phase.

TẠI SAO file này tồn tại?
  R5/R6 re-runs ALL 18 scanners on ALL 353 files every cycle. ~45s per cycle,
  mostly wasted on unchanged files. STARTUP-GATE blocks server boot waiting
  for full scan. DNA #9 (Tăng tốc): xử lý nhanh hơn con người → full scan
  every cycle is anti-pattern.

  Phase này tracks file mtimes (mtime + size + hash). On subsequent runs:
    - Files unchanged since last scan → SKIP (use cached bug list).
    - Files changed → re-scan only those.
    - Every Nth cycle (default 10): full re-scan as safety net (catches bugs
      introduced by subtle cross-file refactors that mtime alone misses).

  Inspired by: pytest --testmon + ruff --diff

Flow:
  Before scan: diff_rescan.compute_changed_files(all_files) → {changed: [...], cached: [...]}
  Scan ONLY changed files.
  After scan: diff_rescan.update_cache(scanned_files) — store mtime + hash.

DNA principles applied:
  #9  (Tăng tốc)       — incremental scan = 3s instead of 45s
  #20 (Cache for speed) — mtime + hash cache avoids re-work
  #22 (PASS ≠ TRUE)    — periodic full re-scan as safety net
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from scp.autofix.path_guard import sanitize_storage_path

logger = logging.getLogger("scp.autofix.diff_rescan")


# Default cache file location.
_DEFAULT_CACHE_FILE = "data/diff_rescan_cache.json"
# After N incremental cycles, force a full re-scan (safety net).
DEFAULT_FULL_RESCAN_INTERVAL = 10
# Hash algorithm (sha256 — fast enough, no collisions in practice).
_HASH_ALGO = "sha256"


def _file_signature(path: Path) -> dict[str, Any]:
    """Compute a file signature: mtime, size, sha256 (first 8KB to be fast)."""
    try:
        stat = path.stat()
        # Hash only first 8KB — large files would be slow to fully hash.
        # 8KB is enough to detect most edits; combined with mtime+size, very robust.
        h = hashlib.new(_HASH_ALGO)
        with Path(path).open("rb") as f:
            h.update(f.read(8192))
        return {
            "mtime": stat.st_mtime,
            "size": stat.st_size,
            "hash": h.hexdigest(),
        }
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-12] signature failed for {path}: {e}")
        return {"mtime": 0, "size": 0, "hash": ""}


class DiffRescanCache:
    """On-disk cache of file signatures, used to skip unchanged files.

    JSON format:
        {
            "last_full_scan": 1700000000.0,
            "incremental_count": 3,
            "files": {
                "/abs/path/foo.py": {"mtime": ..., "size": ..., "hash": ...},
                ...
            }
        }
    """

    def __init__(self, cache_file: str | Path = _DEFAULT_CACHE_FILE):
        # [S3-SECURITY-SWEEP] reject traversal-shaped cache paths (HIGH fix).
        self.cache_file = sanitize_storage_path(
            cache_file, default=_DEFAULT_CACHE_FILE, label="diff_rescan cache",
        )
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.cache_file.exists():
            return {"last_full_scan": 0.0, "incremental_count": 0, "files": {}}
        try:
            with Path(self.cache_file).open(encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[IMP-12] cache load failed, starting fresh: {e}")
            return {"last_full_scan": 0.0, "incremental_count": 0, "files": {}}

    def _save(self) -> None:
        try:
            with Path(self.cache_file).open("w", encoding="utf-8") as f:
                json.dump(self._data, f)
        except OSError as e:
            logger.warning(f"[IMP-12] cache save failed: {e}")

    def get(self, abs_path: str) -> dict[str, Any] | None:
        return self._data["files"].get(abs_path)

    def update(self, abs_path: str, signature: dict[str, Any]) -> None:
        self._data["files"][abs_path] = signature

    def mark_full_scan(self) -> None:
        self._data["last_full_scan"] = time.time()
        self._data["incremental_count"] = 0
        self._save()

    def increment_incremental(self) -> int:
        self._data["incremental_count"] = (
            self._data.get("incremental_count", 0) + 1
        )
        return self._data["incremental_count"]

    def save(self) -> None:
        self._save()


def compute_changed_files(
    all_files: list[Path],
    cache: DiffRescanCache,
    force_full: bool = False,
    full_rescan_interval: int = DEFAULT_FULL_RESCAN_INTERVAL,
) -> dict[str, Any]:
    """Determine which files need re-scanning (mtime/size/hash changed).

    Args:
        all_files: List of absolute file paths to consider.
        cache: DiffRescanCache instance.
        force_full: If True, return ALL files (caller does full scan).
        full_rescan_interval: Force full scan after N incremental cycles.

    Returns:
        {
            "scan_files": list[Path],      — files to scan this cycle
            "cached_files": list[Path],    — files skipped (use cached bugs)
            "mode": "full" | "incremental",
            "reason": str,
        }
    """
    if force_full:
        cache.mark_full_scan()
        return {
            "scan_files": list(all_files),
            "cached_files": [],
            "mode": "full",
            "reason": "force_full=True",
        }

    # Periodic full re-scan (safety net)
    incr_count = cache._data.get("incremental_count", 0)
    if incr_count >= full_rescan_interval:
        cache.mark_full_scan()
        return {
            "scan_files": list(all_files),
            "cached_files": [],
            "mode": "full",
            "reason": f"safety net: incremental_count={incr_count} >= {full_rescan_interval}",
        }

    # Incremental: partition files into changed vs cached
    scan_files: list[Path] = []
    cached_files: list[Path] = []
    for path in all_files:
        abs_path = str(path.resolve())
        cached_sig = cache.get(abs_path)
        current_sig = _file_signature(path)
        if cached_sig is None:
            scan_files.append(path)
            continue
        # Compare mtime + size + hash (any change → rescan)
        if (
            cached_sig.get("mtime") != current_sig.get("mtime")
            or cached_sig.get("size") != current_sig.get("size")
            or cached_sig.get("hash") != current_sig.get("hash")
        ):
            scan_files.append(path)
        else:
            cached_files.append(path)

    cache.increment_incremental()
    reason = (
        f"[IMP-12] diff_rescan: incremental cycle "
        f"({len(scan_files)} changed / {len(cached_files)} cached / {len(all_files)} total)"
    )
    logger.info(reason)

    return {
        "scan_files": scan_files,
        "cached_files": cached_files,
        "mode": "incremental",
        "reason": reason,
    }


def update_cache_after_scan(
    scanned_files: list[Path],
    cache: DiffRescanCache,
) -> int:
    """Update the cache with fresh signatures for just-scanned files.

    Call this AFTER a scan completes (success or partial failure).
    Returns number of cache entries updated.
    """
    updated = 0
    for path in scanned_files:
        abs_path = str(path.resolve())
        sig = _file_signature(path)
        if sig.get("hash"):  # don't cache empty/failed signatures
            cache.update(abs_path, sig)
            updated += 1
    cache.save()
    return updated


def get_cache_stats(cache: DiffRescanCache) -> dict[str, Any]:
    """Return cache statistics for observability."""
    return {
        "cached_file_count": len(cache._data.get("files", {})),
        "last_full_scan": cache._data.get("last_full_scan", 0.0),
        "incremental_count": cache._data.get("incremental_count", 0),
        "cache_file": str(cache.cache_file),
    }


# Singleton cache instance (lazy-initialized).
_cache_singleton: DiffRescanCache | None = None


def get_diff_rescan_cache(
    cache_file: str | Path = _DEFAULT_CACHE_FILE,
) -> DiffRescanCache:
    """Get the singleton DiffRescanCache instance."""
    global _cache_singleton
    if _cache_singleton is None:
        _cache_singleton = DiffRescanCache(cache_file=cache_file)
    return _cache_singleton


def reset_diff_rescan_cache() -> None:
    """Reset the singleton (for tests / forced re-init)."""
    global _cache_singleton
    _cache_singleton = None


__all__ = [
    "DEFAULT_FULL_RESCAN_INTERVAL",
    "DiffRescanCache",
    "compute_changed_files",
    "update_cache_after_scan",
    "get_cache_stats",
    "get_diff_rescan_cache",
    "reset_diff_rescan_cache",
]
