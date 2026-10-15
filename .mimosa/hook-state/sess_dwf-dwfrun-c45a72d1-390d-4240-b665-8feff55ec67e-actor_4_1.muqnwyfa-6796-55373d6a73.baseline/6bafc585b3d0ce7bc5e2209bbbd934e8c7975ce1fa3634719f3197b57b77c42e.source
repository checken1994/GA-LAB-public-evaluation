"""
[SCP-DNA-FIX R7-Full IMP-8] LLM Fix Caching — avoid re-querying for same pattern.

TẠI SAO file này tồn tại?
  R5/R6 LLM fixer queries LLM for EACH bug, even if same pattern (e.g. 8
  None>0 sites → 8 LLM calls). Slow (3-15s/call × 8 = 24-120s) + expensive
  ($0.005 × 8 = $0.04 per audit cycle) + inconsistent (LLM may suggest
  slightly different fix each time → 8 sites get 8 slightly-different patches).

  Cache key = sha256(bug_signature + context_hash). Same pattern → reuse
  cached fix (apply to all sites). TTL 24h. Invalidated if file content
  changes (context_hash differs).

Inspired by: GitHub Copilot Autofix — caches fix suggestions by pattern hash

Flow:
  generate_fix_for_bug(bug)
    → cache_key = compute_cache_key(bug)
    → if cache.get(cache_key): return cached fix (skip LLM call)
    → else: llm_response = call_llm(prompt)
            fix_block = extract_search_replace(llm_response)
            cache.set(cache_key, fix_block, ttl=86400)
            return fix_block

DNA principles applied:
  #9 (No harm)   — same-pattern bugs get CONSISTENT fixes (no LLM variance)
  #8 (KB accumulation) — fix cache = learned patterns across audit cycles
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from scp.autofix.path_guard import sanitize_storage_path

logger = logging.getLogger("scp.autofix.llm_fix_cache")


# Default cache file location.
_DEFAULT_CACHE_FILE = "data/llm_fix_cache.json"
# Default TTL = 24 hours (86400 seconds).
_DEFAULT_TTL_SECONDS = 86400
# Max cache entries (LRU eviction when exceeded).
_DEFAULT_MAX_ENTRIES = 500


def _hash(text: str) -> str:
    """SHA-256 of text (first 32 hex chars = 128-bit)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def _compute_bug_signature(bug: Any) -> str:
    """Compute a stable signature for a bug (used as part of cache key).

    Signature = bug_type + normalized description (lowercased, stripped).
    File path + line are intentionally EXCLUDED — we WANT same-pattern bugs
    in different files/lines to share the cache.
    """
    bug_type = str(getattr(bug, "bug_type", "")).strip().lower()
    desc = str(getattr(bug, "description", "")).strip().lower()
    # Normalize whitespace in description (collapse runs of whitespace)
    desc = " ".join(desc.split())
    # Truncate to 500 chars (avoid mega-keys for mega-descriptions)
    desc = desc[:500]
    return f"{bug_type}::{desc}"


def _compute_context_hash(file_path: str, bug_line: int, context_lines: int = 5) -> str:
    """Hash the surrounding code context (5 lines around bug line).

    Why context hash? Same bug_type + description in DIFFERENT code context
    may need different fixes. Cache key includes context hash so a cached fix
    is only reused when the surrounding code is identical.

    If file cannot be read, hash is empty string (cache key degrades to
    bug_signature only — still useful for very generic patterns).
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return ""
        source = path.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
        # Hash ±context_lines around bug line (NOT whole file — too sensitive)
        start = max(0, bug_line - 1 - context_lines)
        end = min(len(lines), bug_line + context_lines)
        context = "\n".join(lines[start:end])
        return _hash(context)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-8] context hash failed for {file_path}: {e}")
        return ""


def compute_cache_key(bug: Any) -> str:
    """Compute the cache key for a bug.

    Cache key = sha256(bug_signature + context_hash).
    Same key → same fix can be reused (skip LLM call).
    """
    sig = _compute_bug_signature(bug)
    ctx = _compute_context_hash(getattr(bug, "file", ""), int(getattr(bug, "line", 0) or 0))
    raw = f"{sig}|{ctx}"
    return _hash(raw)


class LLMFixCache:
    """On-disk LLM fix cache (JSON file, atomic writes).

    Format:
        {
            "entries": {
                "<cache_key>": {
                    "fix_block": "<<<<<<< SEARCH\\n...\\n>>>>>>> REPLACE",
                    "bug_signature": "...",
                    "context_hash": "...",
                    "bug_type": "...",
                    "created_at": 1700000000.0,
                    "last_used_at": 1700000000.0,
                    "use_count": 1,
                },
                ...
            },
            "stats": {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
            }
        }
    """

    def __init__(
        self,
        cache_file: str | Path = _DEFAULT_CACHE_FILE,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        max_entries: int = _DEFAULT_MAX_ENTRIES,
    ):
        # [S3-SECURITY-SWEEP] reject traversal-shaped cache paths (HIGH fix).
        self.cache_file = sanitize_storage_path(
            cache_file, default=_DEFAULT_CACHE_FILE, label="llm_fix cache",
        )
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.cache_file.exists():
            return {"entries": {}, "stats": {"hits": 0, "misses": 0, "evictions": 0}}
        try:
            with Path(self.cache_file).open(encoding="utf-8") as f:
                loaded = json.load(f)
            # Fail-closed shape normalization: legacy/corrupt cache files must
            # never make invalidation/stats crash with KeyError('entries').
            if not isinstance(loaded, dict):
                raise ValueError("cache root must be an object")
            entries = loaded.get("entries")
            stats = loaded.get("stats")
            if not isinstance(entries, dict):
                logger.warning("[IMP-8] cache shape missing/invalid entries; resetting entries")
                entries = {}
            if not isinstance(stats, dict):
                stats = {}
            normalized_stats = {
                "hits": int(stats.get("hits", 0) or 0),
                "misses": int(stats.get("misses", 0) or 0),
                "evictions": int(stats.get("evictions", 0) or 0),
            }
            return {"entries": entries, "stats": normalized_stats}
        except (json.JSONDecodeError, OSError, ValueError, TypeError) as e:
            logger.warning(f"[IMP-8] cache load failed, starting fresh: {e}")
            return {"entries": {}, "stats": {"hits": 0, "misses": 0, "evictions": 0}}

    def _save(self) -> None:
        try:
            tmp = self.cache_file.with_suffix(".tmp")
            with Path(tmp).open("w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False)
            tmp.replace(self.cache_file)  # atomic
        except OSError as e:
            logger.warning(f"[IMP-8] cache save failed: {e}")

    def _evict_if_needed(self) -> None:
        """LRU eviction: if entries > max, evict oldest by last_used_at."""
        entries = self._data["entries"]
        if len(entries) <= self.max_entries:
            return
        # Sort by last_used_at ascending (oldest first)
        sorted_keys = sorted(entries.keys(), key=lambda k: entries[k].get("last_used_at", 0))
        evict_count = len(entries) - self.max_entries
        for k in sorted_keys[:evict_count]:
            del entries[k]
            self._data["stats"]["evictions"] += 1
        logger.info(f"[IMP-8] evicted {evict_count} LRU entries (max={self.max_entries})")

    def get(self, cache_key: str) -> str | None:
        """Look up a cached fix. Returns None if not found or expired."""
        entry = self._data["entries"].get(cache_key)
        if entry is None:
            self._data["stats"]["misses"] += 1
            return None
        # Check TTL
        age = time.time() - entry.get("created_at", 0)
        if age > self.ttl_seconds:
            logger.debug(
                f"[IMP-8] cache entry {cache_key[:8]} expired (age={age:.0f}s > ttl={self.ttl_seconds}s)"
            )
            del self._data["entries"][cache_key]
            self._data["stats"]["misses"] += 1
            self._save()
            return None
        # Hit — update last_used_at + use_count
        entry["last_used_at"] = time.time()
        entry["use_count"] = entry.get("use_count", 0) + 1
        self._data["stats"]["hits"] += 1
        self._save()
        logger.info(
            f"[IMP-8] cache HIT for key {cache_key[:8]} "
            f"(use_count={entry['use_count']}, age={age:.0f}s) — skipping LLM call"
        )
        return entry.get("fix_block")

    def set(self, cache_key: str, fix_block: str, bug: Any | None = None) -> None:
        """Store a fix in the cache."""
        now = time.time()
        self._data["entries"][cache_key] = {
            "fix_block": fix_block,
            "bug_signature": _compute_bug_signature(bug) if bug else "",
            "context_hash": _compute_context_hash(
                getattr(bug, "file", ""), int(getattr(bug, "line", 0) or 0)
            ) if bug else "",
            "bug_type": str(getattr(bug, "bug_type", "")) if bug else "",
            # [SCP-DNA-FIX R12-2] Store source file path so invalidate_for_file()
            # can actually match entries. Previously this field was omitted
            # ("for privacy" per old comment) which made invalidate_for_file()
            # a no-op -> stale fixes could be re-served after a file changed.
            # The context_hash already changes when the file content changes
            # (so cache keys diverge naturally), but invalidate_for_file() is
            # a belt-and-suspenders eviction — it must actually work.
            "file_path": str(getattr(bug, "file", "")) if bug else "",
            "created_at": now,
            "last_used_at": now,
            "use_count": 0,
        }
        self._evict_if_needed()
        self._save()
        logger.debug(f"[IMP-8] cache SET for key {cache_key[:8]} (entries={len(self._data['entries'])})")

    def invalidate_for_file(self, file_path: str) -> int:
        """Invalidate all cache entries sourced from `file_path`.

        Called when a file changes (post-fix) to avoid serving stale fixes.
        Returns count of entries invalidated.

        [SCP-DNA-FIX R12-2] Previous implementation was a no-op (`pass` in the
        loop body, always returned 0). Caller believed the cache was invalidated
        → stale LLM fix suggestions could be re-applied to a file whose content
        had already changed. PASS != TRUE (DNA #22).

        Fix: entries now store `file_path` (added in set()). This method matches
        on it. Entries written by older versions (without `file_path`) are left
        alone — they expire via TTL (24h default). Path matching is exact
        (normalized via os.path.normpath) so 'scp/foo.py' and 'scp/./foo.py'
        are treated the same.
        """
        if not file_path:
            return 0
        import os as _os
        target = _os.path.normpath(file_path)
        removed = 0
        for key in list(self._data["entries"].keys()):
            entry = self._data["entries"].get(key)
            if not entry:
                continue
            entry_path = entry.get("file_path", "")
            if not entry_path:
                # Legacy entry (pre-R12-2) — skip, TTL handles it.
                continue
            if _os.path.normpath(entry_path) == target:
                del self._data["entries"][key]
                removed += 1
        if removed > 0:
            self._save()
            logger.info(
                f"[IMP-8] invalidated {removed} cache entr(y/ies) for {target} "
                f"(file changed post-fix)"
            )
        return removed

    def clear_all(self) -> int:
        """Clear the entire cache. Returns count of entries removed."""
        n = len(self._data["entries"])
        self._data["entries"] = {}
        self._save()
        logger.info(f"[IMP-8] cleared cache ({n} entries removed)")
        return n

    # [SCP-DNA-FIX R13-3] Bug #6: invalidate_for_file() had its internal
    # storage + matching logic fixed in R12-2, but NO CALLER ever invokes
    # it. Result: stale LLM fixes silently re-applied after a file is
    # modified by an autofix. The public wrapper below logs the
    # invalidation count so callers (engine.py after a successful fix
    # application) can verify the eviction actually happened. The module-
    # level helper `invalidate_cache_for_file(file_path)` (defined below
    # near the singleton accessor) is the canonical entry point for
    # engine.py — it lazily gets the singleton and calls this method.
    def invalidate_for_file_safe(self, file_path: str) -> int:
        """Public wrapper around invalidate_for_file() with logging.

        Returns the number of cache entries invalidated. Always returns
        an int (0 on error or empty path) — fail-open, never raises.

        Caller contract:
            - engine.py should call `invalidate_cache_for_file(path)`
              after EVERY successful fix application to prevent stale
              cached fixes from being re-served for the same file.
            - This wrapper is safe to call even if the cache is disabled
              or the singleton isn't initialized — it lazily initializes
              the cache via __init__ state and returns 0 if there's
              nothing to invalidate.
        """
        try:
            if not file_path:
                return 0
            removed = self.invalidate_for_file(file_path)
            if removed > 0:
                logger.info(
                    f"[IMP-8] invalidate_for_file_safe: {removed} entr(y/ies) "
                    f"invalidated for {file_path} (post-fix cache eviction)"
                )
            else:
                logger.debug(
                    f"[IMP-8] invalidate_for_file_safe: 0 entries for "
                    f"{file_path} (nothing to evict)"
                )
            return removed
        except Exception as e:  # noqa: BLE001 — fail-open per DNA #7
            logger.warning(
                f"[IMP-8] invalidate_for_file_safe crashed for {file_path}: {e} "
                f"(fail-open — stale cache may persist)"
            )
            return 0

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        total = self._data["stats"]["hits"] + self._data["stats"]["misses"]
        hit_rate = (self._data["stats"]["hits"] / total) if total > 0 else 0.0
        return {
            "entries": len(self._data["entries"]),
            "hits": self._data["stats"]["hits"],
            "misses": self._data["stats"]["misses"],
            "evictions": self._data["stats"]["evictions"],
            "hit_rate": round(hit_rate, 3),
            "ttl_seconds": self.ttl_seconds,
            "max_entries": self.max_entries,
            "cache_file": str(self.cache_file),
        }


# Singleton cache instance (lazy).
_cache_singleton: LLMFixCache | None = None


def get_llm_fix_cache(
    cache_file: str | Path = _DEFAULT_CACHE_FILE,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> LLMFixCache:
    """Get the singleton LLMFixCache instance.

    Env var SCP_LLM_FIX_CACHE_FILE can override cache_file location.
    Env var SCP_LLM_FIX_CACHE_TTL can override TTL (seconds).
    Env var SCP_LLM_FIX_CACHE_DISABLED=1 disables caching entirely
    (cache.get() always returns None).
    """
    global _cache_singleton
    if _cache_singleton is None:
        _cache_override = os.environ.get("SCP_LLM_FIX_CACHE_FILE", "").strip()
        if _cache_override:
            cache_file = _cache_override
        ttl_env = os.environ.get("SCP_LLM_FIX_CACHE_TTL")
        if ttl_env:
            try:
                ttl_seconds = int(ttl_env)
            except ValueError as ttl_err:
                # silent-by-design: documented default — invalid TTL env keeps the built-in TTL.
                logger.debug("llm_fix_cache: invalid SCP_LLM_FIX_CACHE_TTL %r, keeping default: %s", ttl_env, ttl_err, exc_info=True)
                pass
        _cache_singleton = LLMFixCache(
            cache_file=cache_file, ttl_seconds=ttl_seconds
        )
    return _cache_singleton


def is_cache_enabled() -> bool:
    """Check if LLM fix caching is enabled (default: True)."""
    return os.environ.get("SCP_LLM_FIX_CACHE_DISABLED", "0") != "1"


def reset_llm_fix_cache() -> None:
    """Reset the singleton (for tests / forced re-init)."""
    global _cache_singleton
    _cache_singleton = None


# [SCP-DNA-FIX R13-3] Bug #6: module-level helper for engine.py to call
# after every successful fix application. This is the canonical entry
# point — engine.py should NOT call invalidate_for_file() directly
# (bypasses the safe wrapper + logging). Group A owns engine.py and is
# responsible for wiring this call.
#
# Contract for engine.py (Group A TODO — DO NOT EDIT engine.py from
# Group C):
#   After a successful `agent._apply_fix(filepath, fix_block)` call
#   in engine.py (around lines 739-752 / 1589 / 1645 / 1717 where
#   `filepath.write_text(...)` happens), insert:
#       from scp.autofix.llm_fix_cache import invalidate_cache_for_file
#       invalidate_cache_for_file(str(filepath))
#   This evicts any cached LLM fix suggestions sourced from that file
#   so subsequent runs don't re-apply the stale cached version.
def invalidate_cache_for_file(file_path: str) -> int:
    """Module-level helper: invalidate cached LLM fixes for `file_path`.

    Lazily initializes the singleton cache (if not already created) and
    delegates to LLMFixCache.invalidate_for_file_safe(). Fail-open:
    returns 0 on any error, never raises.

    Args:
        file_path: Path of the file that was just modified by an autofix.

    Returns:
        Number of cache entries invalidated (0 if none or on error).

    Wire-in (Group A TODO — engine.py):
        After every successful fix application that writes to disk:
            from scp.autofix.llm_fix_cache import invalidate_cache_for_file
            invalidate_cache_for_file(str(filepath))
    """
    try:
        if not file_path:
            return 0
        if not is_cache_enabled():
            # Cache disabled — nothing to invalidate. Still return 0
            # (not an error condition).
            logger.debug(
                f"[IMP-8] invalidate_cache_for_file: cache disabled, "
                f"skipping eviction for {file_path}"
            )
            return 0
        cache = get_llm_fix_cache()
        return cache.invalidate_for_file_safe(file_path)
    except Exception as e:  # noqa: BLE001 — fail-open per DNA #7
        logger.warning(
            f"[IMP-8] invalidate_cache_for_file crashed for {file_path}: {e} "
            f"(fail-open — stale cache may persist)"
        )
        return 0


def cached_or_compute(
    bug: Any,
    llm_compute_fn,
) -> str | None:
    """High-level helper: check cache → if miss, call llm_compute_fn → store.

    Args:
        bug: BugReport-like object.
        llm_compute_fn: Callable[[], str | None] that calls the LLM and returns
                        a fix block (or None on failure).

    Returns: fix_block (cached or fresh), or None if LLM call failed.

    If cache is disabled (SCP_LLM_FIX_CACHE_DISABLED=1), always calls LLM.
    """
    if not is_cache_enabled():
        return llm_compute_fn()

    cache = get_llm_fix_cache()
    cache_key = compute_cache_key(bug)

    # Try cache first
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info(
            f"[IMP-8] using cached fix for {getattr(bug, 'bug_type', '?')} "
            f"at {getattr(bug, 'file', '?')}:{getattr(bug, 'line', '?')} "
            f"(cache_key={cache_key[:8]})"
        )
        return cached

    # Cache miss — call LLM
    fresh = llm_compute_fn()
    if fresh is not None:
        cache.set(cache_key, fresh, bug=bug)
    return fresh


__all__ = [
    "LLMFixCache",
    "compute_cache_key",
    "get_llm_fix_cache",
    "is_cache_enabled",
    "reset_llm_fix_cache",
    "cached_or_compute",
    # [SCP-DNA-FIX R13-3] Bug #6: exposed for engine.py post-fix eviction.
    "invalidate_cache_for_file",
]
