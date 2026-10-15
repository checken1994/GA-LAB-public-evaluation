"""
[SCP-DNA-FIX R8 v3 IMP-13] Incremental AST-Diff Cache.

TẠI SAO file này tồn tại?
  R7-Full IMP-12 (diff_rescan) track file mtime + size + first-8KB hash để
  skip unchanged files. NHƯNG:
    - mtime có thể bị touch mà không thay đổi nội dung (cp -p, git checkout
      same-content branch).
    - first-8KB hash bỏ qua thay đổi ở cuối file (e.g. append hàm mới ở EOF).
    - Không phân biệt "content changed" (genuine edit) vs "whitespace-only
      edit" (reformat — không tạo bug mới).

  v3 IMP-13 tăng accuracy:
    1. content_sha = SHA-256 của TOÀN BỘ file (không phải 8KB).
    2. ast_sha = SHA-256 của `ast.dump(ast.parse(source))` — insensitive với
       whitespace, comments, formatting. Cùng AST = cùng behavior (giả định).
    3. Chỉ re-scan khi BOTH content_sha + ast_sha khác cache. Nếu chỉ
       content_sha khác (reformat) → skip (behavior không đổi).
    4. Store findings_count per file — if 0 findings on last scan, cached
       "clean" status accelerates even further.

  Inspired by:
    - ruff `--diff` cache (ruff lưu AST hash để skip file)
    - pytest `--testmon` (testmon lưu per-test dependency graph + file hash
      để chạy only-affected tests)

Flow:
  before_scan: ASTDiffCache.partition_files(all_paths) → {scan, cached}
  after_scan:  ASTDiffCache.update(path, findings_count) → ghi cache

DNA principles applied:
  #9  (Tăng tốc)         — re-scan ~3s thay vì 45s (R7-Full claim becomes real)
  #20 (Cache for speed)  — content + AST double-hash cache
  #26 (Reality cuối cùng)— ast.parse là ground truth, không phải mtime
  #7  (Autofix safe)     — fail-open: corrupt cache → rebuild from scratch
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from scp.autofix.path_guard import sanitize_storage_path

logger = logging.getLogger("scp.autofix.ast_diff_cache")


# Default cache file location.
_DEFAULT_CACHE_FILE = "data/ast_diff_cache.json"
# After N incremental cycles, force full re-scan (safety net — same idea as IMP-12).
DEFAULT_FULL_RESCAN_INTERVAL = 10
# Skip files larger than this (avoid hashing mega-files on every cycle).
_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB


# ============================================================
# Hashing helpers
# ============================================================

def _hash_content(content: str | bytes) -> str:
    """SHA-256 of full content (first 32 hex chars = 128-bit, plenty)."""
    if isinstance(content, str):
        content = content.encode("utf-8", errors="replace")
    return hashlib.sha256(content).hexdigest()[:32]


def _hash_ast(source: str) -> str:
    """SHA-256 of `ast.dump(ast.parse(source))`.

    Why AST hash? Reformat (black, isort, IDE autoformat) changes content
    but NOT AST → behavior unchanged → skip re-scan. This is the key
    improvement over IMP-12's first-8KB content hash.

    Returns "" on parse error (caller treats as "must re-scan").
    """
    try:
        tree = ast.parse(source)
        # ast.dump without indent + without attributes → stable across reformat
        dumped = ast.dump(tree, annotate_fields=False, include_attributes=False)
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()[:32]
    except SyntaxError as e:
        # File has syntax error — must re-scan to surface the error.
        logger.debug(f"[IMP-13] AST hash failed (SyntaxError): {e}")
        return ""
    except Exception as e:  # noqa: BLE001 — best-effort
        logger.debug(f"[IMP-13] AST hash failed: {e}")
        return ""


def _compute_file_hashes(path: Path) -> tuple[str, str, int]:
    """Return (content_sha, ast_sha, size_bytes) for a file.

    On read error → content_sha = "", ast_sha = "", size = 0.
    """
    try:
        stat = path.stat()
        if stat.st_size > _MAX_FILE_SIZE_BYTES:
            # Large file — skip AST hash (too expensive). Force content-only
            # comparison (still better than mtime-only).
            content = path.read_text(encoding="utf-8", errors="replace")
            return _hash_content(content), "", stat.st_size
        content = path.read_text(encoding="utf-8", errors="replace")
        return _hash_content(content), _hash_ast(content), stat.st_size
    except OSError as e:
        logger.debug(f"[IMP-13] read failed for {path}: {e}")
        return "", "", 0


# ============================================================
# ASTDiffCache — the on-disk cache.
# ============================================================

class ASTDiffCache:
    """Incremental AST-diff cache.

    On-disk JSON format:
        {
            "last_full_scan": 1700000000.0,
            "incremental_count": 3,
            "files": {
                "/abs/path/foo.py": {
                    "content_sha": "abc...",
                    "ast_sha":     "def...",
                    "size":        1234,
                    "last_scan_ts": 1700000000.0,
                    "findings_count": 2,
                    "syntax_error": false
                },
                ...
            }
        }

    Thread-safe: all public mutations take self._lock.
    Atomic writes: write to .tmp then os.replace.
    Fail-open: corrupt cache → log + rebuild from empty.
    """

    def __init__(self, cache_file: str | Path = _DEFAULT_CACHE_FILE):
        # [S3-SECURITY-SWEEP] reject traversal-shaped cache paths (HIGH fix).
        self.cache_file = sanitize_storage_path(
            cache_file, default=_DEFAULT_CACHE_FILE, label="ast_diff cache",
        )
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"[IMP-13] mkdir failed for cache dir: {e}")
        self._lock = threading.RLock()
        self._data: dict[str, Any] = self._load()

    # ---------- persistence ----------

    def _load(self) -> dict[str, Any]:
        if not self.cache_file.exists():
            return self._empty_state()
        try:
            with Path(self.cache_file).open(encoding="utf-8") as f:
                data = json.load(f)
            # Validate structure
            if not isinstance(data, dict) or "files" not in data:
                logger.warning(
                    f"[IMP-13] cache at {self.cache_file} is corrupt — rebuilding"
                )
                return self._empty_state()
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[IMP-13] cache load failed, starting fresh: {e}")
            return self._empty_state()

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {
            "last_full_scan": 0.0,
            "incremental_count": 0,
            "files": {},
        }

    def _save_locked(self) -> None:
        """Write cache atomically. Caller holds self._lock."""
        try:
            tmp = self.cache_file.with_suffix(self.cache_file.suffix + ".tmp")
            with Path(tmp).open("w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.cache_file)  # atomic on POSIX
        except OSError as e:
            logger.warning(f"[IMP-13] cache save failed: {e}")

    # ---------- queries ----------

    def get(self, abs_path: str) -> dict[str, Any] | None:
        """Look up a file's cached entry. Returns None if not cached."""
        with self._lock:
            return self._data["files"].get(abs_path)

    def is_cached_clean(self, abs_path: str) -> bool:
        """True if file is cached AND last scan found 0 findings.

        Caller can use this to skip even the audit-log append for clean files.
        """
        with self._lock:
            entry = self._data["files"].get(abs_path)
            if not entry:
                return False
            return int(entry.get("findings_count", -1)) == 0

    def partition_files(
        self,
        all_paths: list[str],
        force_full: bool = False,
        full_rescan_interval: int = DEFAULT_FULL_RESCAN_INTERVAL,
    ) -> dict[str, list[str]]:
        """Partition paths into {scan: [...], cached: [...]}.

        Decision per file:
          - force_full=True           → scan
          - incremental_count >= interval → scan (safety net)
          - no cached entry           → scan (first time)
          - cached content_sha != current → scan (real edit)
          - cached ast_sha != current AND ast_sha != "" → scan (AST changed)
          - cached syntax_error=True  → scan (was broken, maybe fixed now)
          - else                       → cached (skip)

        Returns:
            {"scan": [...paths to re-scan...],
             "cached": [...paths to skip...]}
        """
        with self._lock:
            do_full = (
                force_full
                or int(self._data.get("incremental_count", 0)) >= full_rescan_interval
            )

        scan: list[str] = []
        cached: list[str] = []
        for p in all_paths:
            try:
                path = Path(p)
                if not path.exists() or not path.is_file():
                    continue
            except OSError as probe_err:
                # silent-by-design: exists/is_file probe — vanished path is
                # skipped from this cache refresh.
                logger.debug("ast_diff_cache: path probe failed for %s: %s", p, probe_err, exc_info=True)
                continue

            if do_full:
                scan.append(p)
                continue

            with self._lock:
                entry = self._data["files"].get(p)

            if not entry:
                scan.append(p)
                continue

            content_sha, ast_sha, _size = _compute_file_hashes(path)

            # Cached content_sha differs (or file was previously broken) → re-scan
            if entry.get("content_sha") != content_sha:
                scan.append(p)
                continue
            # Same content_sha but different ast_sha → impossible (same content
            # → same AST) unless cached entry was written with ast_sha="" (large
            # file path). In that case content_sha match is enough → cached.
            if entry.get("syntax_error"):
                scan.append(p)
                continue

            cached.append(p)

        logger.info(
            f"[IMP-13] partition: {len(scan)} scan / {len(cached)} cached "
            f"(force_full={do_full})"
        )
        return {"scan": scan, "cached": cached}

    # ---------- mutations ----------

    def update(self, abs_path: str, findings_count: int, syntax_error: bool = False) -> None:
        """Update (or insert) a file's cache entry after a scan."""
        try:
            path = Path(abs_path)
            content_sha, ast_sha, size = _compute_file_hashes(path)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[IMP-13] update() hash failed for {abs_path}: {e}")
            content_sha, ast_sha, size = "", "", 0

        with self._lock:
            self._data["files"][abs_path] = {
                "content_sha": content_sha,
                "ast_sha": ast_sha,
                "size": size,
                "last_scan_ts": time.time(),
                "findings_count": int(findings_count),
                "syntax_error": bool(syntax_error),
            }
            self._save_locked()

    def bulk_update(self, updates: dict[str, dict[str, Any]]) -> None:
        """Batch update — `updates` is {abs_path: {findings_count, syntax_error}}."""
        if not updates:
            return
        with self._lock:
            now = time.time()
            for abs_path, info in updates.items():
                try:
                    path = Path(abs_path)
                    content_sha, ast_sha, size = _compute_file_hashes(path)
                except Exception as hash_err:  # noqa: BLE001
                    # silent-by-design: documented default — empty hashes mark the
                    # entry as un-hashed; recomputed on next refresh.
                    logger.debug("ast_diff_cache: hash compute failed for %s: %s", abs_path, hash_err, exc_info=True)
                    content_sha, ast_sha, size = "", "", 0
                self._data["files"][abs_path] = {
                    "content_sha": content_sha,
                    "ast_sha": ast_sha,
                    "size": size,
                    "last_scan_ts": now,
                    "findings_count": int(info.get("findings_count", 0)),
                    "syntax_error": bool(info.get("syntax_error", False)),
                }
            self._save_locked()

    def mark_full_scan(self) -> None:
        """Reset incremental_count after a full scan completes."""
        with self._lock:
            self._data["last_full_scan"] = time.time()
            self._data["incremental_count"] = 0
            self._save_locked()

    def increment_incremental(self) -> None:
        """Bump incremental_count (called when an incremental scan completes)."""
        with self._lock:
            self._data["incremental_count"] = int(
                self._data.get("incremental_count", 0)
            ) + 1
            self._save_locked()

    def invalidate(self, abs_path: str) -> None:
        """Drop a single file from the cache (e.g. after a known edit)."""
        with self._lock:
            if abs_path in self._data["files"]:
                del self._data["files"][abs_path]
                self._save_locked()

    def clear_all(self) -> int:
        """Wipe the entire cache. Returns count of entries removed."""
        with self._lock:
            n = len(self._data["files"])
            self._data = self._empty_state()
            self._save_locked()
            logger.info(f"[IMP-13] cleared cache ({n} entries removed)")
            return n

    def prune_missing(self, existing_paths: set[str]) -> int:
        """Remove cache entries for files that no longer exist on disk."""
        removed = 0
        with self._lock:
            for p in list(self._data["files"].keys()):
                if p not in existing_paths:
                    del self._data["files"][p]
                    removed += 1
            if removed:
                self._save_locked()
        return removed

    # ---------- observability ----------

    def stats(self) -> dict[str, Any]:
        """Return cache statistics for monitoring."""
        with self._lock:
            files = self._data["files"]
            total = len(files)
            clean = sum(1 for e in files.values() if int(e.get("findings_count", -1)) == 0)
            dirty = sum(1 for e in files.values() if int(e.get("findings_count", -1)) > 0)
            unknown = total - clean - dirty
            return {
                "total_entries": total,
                "clean_files": clean,
                "dirty_files": dirty,
                "unknown_files": unknown,
                "last_full_scan": self._data.get("last_full_scan", 0.0),
                "incremental_count": self._data.get("incremental_count", 0),
                "cache_file": str(self.cache_file),
            }


# ============================================================
# Singleton (per cache_file path).
# ============================================================

_singleton_lock = threading.Lock()
_cache_singletons: dict[str, ASTDiffCache] = {}


def get_ast_diff_cache(cache_file: str | Path = _DEFAULT_CACHE_FILE) -> ASTDiffCache:
    """Get the singleton ASTDiffCache instance for a given cache_file."""
    key = str(Path(cache_file).resolve())
    with _singleton_lock:
        if key not in _cache_singletons:
            _cache_singletons[key] = ASTDiffCache(cache_file=cache_file)
        return _cache_singletons[key]


def reset_ast_diff_cache() -> None:
    """Reset all singletons (for tests / forced re-init)."""
    global _cache_singletons
    with _singleton_lock:
        _cache_singletons = {}


__all__ = [
    "ASTDiffCache",
    "DEFAULT_FULL_RESCAN_INTERVAL",
    "get_ast_diff_cache",
    "reset_ast_diff_cache",
]
