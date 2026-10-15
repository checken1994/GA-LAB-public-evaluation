"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""
from __future__ import annotations

#!/usr/bin/env python3
"""
SCP V30 — Smart TTL Cache.

Cache per-source với TTL khác nhau tùy staleness của data:
    - PubChem MW:           24h   (hằng số không đổi)
    - Wikidata:             7d    (rarely change)
    - Wikipedia:            7d    (stable facts)
    - REST Countries:       7d    (rarely change)
    - CODATA constants:     ∞     (never change — permanent)
    - Frankfurter currency: 1h    (fiat rates change hourly)
    - Crypto (Binance etc): 5min  (volatile)
    - Open-Meteo weather:   30min (weather updates ~30min)
    - wttr.in:              15min (similar)
    - CoinGecko:            5min  (volatile)

LRU eviction: max 5000 entries (oldest accessed evicted first).
Thread-safe (Lock).
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Any

logger = logging.getLogger("scp.smart_cache")


# Per-source TTL (seconds)
SOURCE_TTL: dict[str, int] = {
    # Permanent / very stable
    "PubChem":              24 * 3600,    # 24h
    "PubChem(cached)":      24 * 3600,    # 24h
    "Wikidata":             7 * 24 * 3600,  # 7d
    "Wikipedia":            7 * 24 * 3600,  # 7d
    "REST Countries":       7 * 24 * 3600,  # 7d
    "REST Countries API":   7 * 24 * 3600,  # 7d
    "LocalDB":              365 * 24 * 3600,  # 1y (local, no staleness)
    "Local Geography Database": 365 * 24 * 3600,
    "Local History Database": 365 * 24 * 3600,
    "KnowledgeCache":       365 * 24 * 3600,  # 1y
    "InternalKB":           365 * 24 * 3600,  # 1y
    "PythonAST":            365 * 24 * 3600,  # 1y (deterministic)
    "PythonMath":           365 * 24 * 3600,  # 1y (deterministic)
    "CODATA":               365 * 24 * 3600,  # 1y

    # Hourly updates
    "Frankfurter":          3600,         # 1h
    "open.er-api.com":      3600,         # 1h

    # Real-time / volatile
    "Binance":              300,          # 5min
    "Coinbase":             300,          # 5min
    "Kraken":               300,          # 5min
    "Bitstamp":             300,          # 5min
    "KuCoin":               300,          # 5min
    "CoinGecko":            300,          # 5min
    "Binance(adversary)":   300,
    "Bitstamp(adversary)":  300,
    "KuCoin(adversary)":    300,
    "median(Coinbase,Kraken,Bitstamp)":   300,
    "weighted(Frankfurter,open.er-api.com)":  3600,

    # Weather
    "Open-Meteo":              1800,      # 30min
    "wttr.in":                 900,       # 15min
    "Open-Meteo-Archive":      3600,      # 1h
    "median(Open-Meteo,wttr.in,Open-Meteo-Archive)": 1800,
}


class SmartCache:
    """
    Smart TTL Cache — LRU + per-source TTL.

    Usage:
        cache = SmartCache()
        cache.set("bitcoin", {"value": 62113, "source": "Binance"})
        cached = cache.get("bitcoin")  # returns None if expired
    """

    _instance: SmartCache | None = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._cache: OrderedDict[str, tuple[float, Any, int]] = OrderedDict()
                    cls._instance._entry_lock = threading.RLock()
                    cls._instance._MAX_SIZE = 5000
                    cls._instance._stats = {
                        "hits": 0, "misses": 0, "expired": 0, "evicted": 0,
                    }
        return cls._instance

    def _key(self, namespace: str, identifier: str) -> str:
        """Generate cache key."""
        return f"{namespace}::{identifier}"

    def _get_ttl(self, source: str) -> int:
        """Get TTL for source. Default 300s (5min)."""
        # Try exact match
        if source in SOURCE_TTL:
            return SOURCE_TTL[source]
        # Try case-insensitive
        for k, v in SOURCE_TTL.items():
            if k.lower() == source.lower():
                return v
        # Try contains match (e.g., "weighted(Binance,Coinbase)" contains "Binance")
        for k, v in SOURCE_TTL.items():
            if k in source:
                return v
        # Default
        return 300

    def get(self, namespace: str, identifier: str) -> Any | None:
        """Get cached value if not expired."""
        key = self._key(namespace, identifier)
        with self._entry_lock:
            # Check in-memory cache first (fastest)
            if key in self._cache:
                ts, value, ttl = self._cache[key]
                now = time.time()
                if now - ts > ttl:
                    # Expired
                    del self._cache[key]
                    self._stats["expired"] += 1
                    self._stats["misses"] += 1
                    return None
                # Move to end (LRU)
                self._cache.move_to_end(key)
                self._stats["hits"] += 1
                return value

            #  Check disk cache (SQLite) — for cross-process persistence
            disk_value = self._disk_get(namespace, identifier)
            if disk_value is not None:
                # Promote to memory cache
                self._cache[key] = (time.time(), disk_value["value"], disk_value["ttl"])
                self._cache.move_to_end(key)
                self._stats["hits"] += 1
                return disk_value["value"]

            self._stats["misses"] += 1
            return None

    def _disk_get(self, namespace: str, identifier: str) -> dict | None:
        """[V89 OPT] Get from disk cache — use shared DB connection, no new conn.

        [V104.49 FIX-C] Now queries by `cache_key` (PRIMARY KEY) instead of
        (namespace, identifier) tuple — PK lookup is O(log n) on the SQLite
        index, faster than the previous table-scan-via-AND. Also reads
        `value_blob` (the BLOB column where _disk_set actually writes JSON
        bytes) instead of `value` (TEXT column, always NULL) — the previous
        mismatch caused _disk_get to always raise TypeError when a NULL blob
        hit the legacy binary deserializer and silently return None, so the
        disk cache was effectively dead.

        [SECURITY FIX] Replaced the legacy binary format with JSON — decoding
        attacker-writable blobs was RCE if the DB is compromised. JSON is safe
        (no code execution)."""
        try:
            import json

            from scp.core.db_manager import db_query_one
            cache_key = hashlib.sha256(
                f"{namespace}::{identifier}".encode()
            ).hexdigest()
            row = db_query_one(
                "SELECT value_blob, ttl, timestamp FROM smart_cache_disk WHERE cache_key = ?",
                (cache_key,)
            )
            if row:
                ts = float(row["timestamp"])
                ttl = int(row["ttl"])
                if time.time() - ts > ttl:
                    return None
                # value_blob is the BLOB column written by _disk_set (JSON bytes).
                blob = row["value_blob"] if "value_blob" in row.keys() else row["value"]
                if blob is None:
                    return None
                # [SECURITY FIX] JSON instead of pickle — no RCE risk
                if isinstance(blob, bytes):
                    value = json.loads(blob.decode("utf-8"))
                else:
                    value = json.loads(blob)
                return {"value": value, "ttl": ttl}
        except Exception as e:
            logger.debug(f"Disk cache get error: {e}", exc_info=True)
        return None

    def _disk_set(self, namespace: str, identifier: str, value: Any, ttl: int) -> None:
        """[V89 OPT] Set to disk cache — use shared db_exec, NO thread creation.

        [V104.49 FIX-C] Now computes `cache_key` = sha256(namespace + "::" +
        identifier) and includes it in the INSERT. Without cache_key (the
        PRIMARY KEY), SQLite accepted NULL for the PK column (NULLs are
        distinct in TEXT PRIMARY KEY), so every write created a NEW row
        instead of replacing the existing one — duplicate (namespace,
        identifier) rows accumulated and _disk_get could return any of them
        (stale data).

        [SECURITY FIX] Replaced the legacy binary format with JSON — serialized
        blobs must never become executable payloads if the DB is compromised.
        JSON is safe."""
        try:
            import json

            from scp.core.db_manager import db_exec
            # [DNA-FIX] Removed `default=str` — it silently converts non-serializable
            # objects (e.g. SLMResponse dataclass) to their str() repr, which
            # corrupts the cache (stores a string instead of a dict → confidence=0
            # on readback). Now we REJECT non-serializable values with TypeError.
            # Callers MUST convert dataclasses to dict before calling set().
            # See slm_cache_set() for the correct pattern (uses _slm_response_to_dict).
            try:
                value_blob = json.dumps(value, ensure_ascii=False).encode("utf-8")
            except TypeError as te:
                logger.error(
                    f"[SmartCache] REJECTED non-serializable value for {namespace}:{identifier} "
                    f"({type(value).__name__}). Convert to dict before caching. Error: {te}"
                )
                return False  # reject — do NOT silently corrupt with default=str
            cache_key = hashlib.sha256(
                f"{namespace}::{identifier}".encode()
            ).hexdigest()
            db_exec(
                "INSERT OR REPLACE INTO smart_cache_disk "
                "(cache_key, namespace, identifier, value, value_blob, ttl, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cache_key, namespace, identifier, None, value_blob, ttl, time.time())
            )
        except Exception as e:
            logger.debug(f"Disk cache set error: {e}", exc_info=True)

    def set(self, namespace: str, identifier: str, value: Any, source: str = "") -> None:
        if hasattr(value, "confidence") and (value.confidence < 0.3 or not getattr(value, "answer", "")):
            logger.debug("skip caching low-conf response")
            return
        """Set cache value with TTL based on source."""
        key = self._key(namespace, identifier)
        ttl = self._get_ttl(source)
        with self._entry_lock:
            # Evict if at capacity
            while len(self._cache) >= self._MAX_SIZE:
                # Remove oldest (FIFO from front of OrderedDict)
                self._cache.popitem(last=False)
                self._stats["evicted"] += 1
            self._cache[key] = (time.time(), value, ttl)
            self._cache.move_to_end(key)

        # [V33.1] Disk cache strategy:
        # - Cache ALL non-deterministic sources (API-based)
        # - Skip only pure deterministic (PythonAST, PythonMath, CODATA, InternalKB, LocalDB)
        # - This includes "median(...)", "weighted(...)", "Binance", "Open-Meteo", etc.
        deterministic_sources = {
            "PythonAST", "PythonMath", "CODATA", "InternalKB", "LocalDB",
            "KnowledgeCache", "Local Geography Database", "Local History Database",
        }
        # Check if source is deterministic (skip disk for those — they're instant)
        is_deterministic = source in deterministic_sources
        if not is_deterministic and source and source != "none":
            try:
                self._disk_set(namespace, identifier, value, ttl)
            except Exception as e:
                logger.debug(f"[V104.37] core/smart_cache.py: e={e}", exc_info=True)

    def invalidate(self, namespace: str, identifier: str) -> None:
        """Remove specific entry."""
        key = self._key(namespace, identifier)
        with self._entry_lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        """Clear all cache."""
        with self._entry_lock:
            self._cache.clear()

    def stats(self) -> dict[str, Any]:
        """Get cache stats."""
        with self._entry_lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / max(1, total)
            return {
                "size": len(self._cache),
                "max_size": self._MAX_SIZE,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "expired": self._stats["expired"],
                "evicted": self._stats["evicted"],
                "hit_rate": round(hit_rate, 3),
                "ttl_sources": len(SOURCE_TTL),
            }

    def get_entries_by_namespace(self, namespace: str) -> list[dict]:
        """Get all entries in a namespace (for debugging)."""
        with self._entry_lock:
            result = []
            for key, (ts, value, ttl) in self._cache.items():
                if key.startswith(f"{namespace}::"):
                    result.append({
                        "key": key,
                        "age_sec": time.time() - ts,
                        "ttl_sec": ttl,
                        "expires_in_sec": max(0, ttl - (time.time() - ts)),
                        "value_preview": str(value)[:80],
                    })
            return result


# Singleton accessor
def get_smart_cache() -> SmartCache:
    """Get the singleton SmartCache instance."""
    return SmartCache()


# ============================================================
#  SLM Cache Helper — tích hợp SmartCache vào SLM.predict()
# ============================================================
# [Task 35-A ROOT-FIX] TẠI SAO: slm_cache_set previously passed the raw
# SLMResponse dataclass to SmartCache.set() → _disk_set() called
# `json.dumps(value, default=str)` → SLMResponse (not natively JSON-serializable)
# was converted to its str() repr → stored as a JSON-encoded STRING like
# "SLMResponse(question='...', answer='...', confidence=0.7, ...)".
# On subsequent reads (after process restart, when in-memory cache is empty),
# slm_cache_get returned this STRING instead of an SLMResponse object.
# SLM.predict() then returned the string to _call_slm in judgecore_mixin.py,
# which tried `resp.answer` → AttributeError → caught by `except Exception`
# → returned `{"error": ..., "confidence": 0.0}` → filtered out as garbage
# → primary=None → confidence=0 → UNKNOWN verdict with
# "SLM returned no useful answer (confidence ~0)".
# This affected ALL cached SLM responses (~9 entries in disk cache at audit,
# 100% stored as broken string repr, 0 stored as proper JSON dict).
# Fix: convert SLMResponse ↔ dict at the helper boundary, so the underlying
# SmartCache only ever sees JSON-serializable dicts for SLM entries.
import dataclasses as _dataclasses


def _slm_response_to_dict(response):
    """Convert SLMResponse (or any dataclass instance) to a JSON-safe dict."""
    try:
        if _dataclasses.is_dataclass(response) and not isinstance(response, type):
            return _dataclasses.asdict(response)
    except Exception as e:
        logger.warning(f"Silent except: {e}", exc_info=True)
    return response


def _dict_to_slm_response(value):
    """Convert a dict back to an SLMResponse, or return value as-is if not a dict.

    Returns None for legacy broken string-repr entries (so caller treats as miss).
    """
    if isinstance(value, dict) and "question" in value and "answer" in value and "slm_name" in value:
        # Looks like a serialized SLMResponse — reconstruct it.
        try:
            # Lazy import to avoid circular dependency at module load time.
            from scp.runtime.slm_base import SLMResponse
            return SLMResponse(**value)
        except Exception as exc:
            # silent-by-design: invalid cached payload degrades to a cache miss by design.
            logger.debug("smart_cache: cached SLMResponse reconstruction failed, cache miss: %s", exc, exc_info=True)
            return None
    # If it's already a real SLMResponse (in-memory cache hit), return as-is.
    if hasattr(value, "answer") and hasattr(value, "confidence") and hasattr(value, "slm_name"):
        return value
    # Legacy broken string repr — treat as cache miss (will be re-cached properly).
    return None


def slm_cache_get(slm_name: str, question: str):
    """Check SmartCache cho SLM. Return cached SLMResponse or None."""
    try:
        cached = get_smart_cache().get(f"slm:{slm_name}", question)
        if cached is None:
            return None
        return _dict_to_slm_response(cached)
    except Exception as exc:
        # silent-by-design: cache read failure degrades to a cache miss, never to a wrong answer.
        logger.debug("smart_cache: cache read failed, treating as miss: %s", exc, exc_info=True)
        return None


def slm_cache_set(slm_name: str, question: str, response, source: str = ""):
    """Save SLMResponse to SmartCache với per-source TTL."""
    try:
        # [Task 35-A ROOT-FIX] Convert SLMResponse → dict so json.dumps produces
        # a real JSON object (not a str repr via default=str fallback).
        response = _slm_response_to_dict(response)
        get_smart_cache().set(f"slm:{slm_name}", question, response, source)
    except Exception as e:
        logger.debug(f"[V104.37] core/smart_cache.py: e={e}", exc_info=True)


def cleanup_legacy_cache_entries() -> dict:
    """[OPT-32] Remove legacy broken cache entries (string repr of SLMResponse).

    DNA SCP #7 safe: cleanup only broken entries, don't touch valid ones.

    TẠI SAO: Pre-Task-35-A, `slm_cache_set` passed the raw SLMResponse dataclass
    to `SmartCache.set()` → `_disk_set` did `json.dumps(value, default=str)`
    which converted the dataclass to its `str()` repr → stored as a JSON-encoded
    string like `"SLMResponse(question='...', answer='...', confidence=0.7, ...)"`.
    Task 35-A fixed forward serialization (now writes a proper JSON dict via
    `_slm_response_to_dict`), but legacy rows still exist in
    `smart_cache_disk.value_blob`. Task 35-A also made `slm_cache_get` return
    `None` for these (treated as cache miss), so they're functionally harmless
    — this function reclaims the disk space + keeps the table clean.

    Safety: we only match rows whose `value_blob` decodes to a JSON STRING
    starting with `"SLMResponse("`. Valid dict entries start with `{` so they
    can NEVER match. We also fetch-then-delete (verify in Python before each
    DELETE) instead of a blind `DELETE ... WHERE ... LIKE` — this avoids any
    ambiguity in SQLite's BLOB LIKE semantics.

    Returns:
        {
          "deleted": int,         # rows actually deleted
          "scanned": int,         # rows examined
          "matched": int,         # rows identified as broken
          "reason": str,          # human-readable explanation
          "error": str (optional) # only present if scan failed entirely
        }
    """
    from scp.core.db_manager import db_exec, db_query_all

    # Valid SLMResponse dict entry → value_blob decodes to JSON object → starts with b'{'
    # Legacy broken entry → value_blob decodes to JSON string → starts with b'"SLMResponse('
    BROKEN_PREFIX = b'"SLMResponse('

    # Step 1: scan all rows with non-null value_blob. The smart_cache_disk
    # table is bounded (~5000 rows max via LRU + only non-deterministic
    # sources write to disk), so a full scan is cheap.
    try:
        rows = db_query_all(
            "SELECT cache_key, value_blob FROM smart_cache_disk "
            "WHERE value_blob IS NOT NULL"
        )
    except Exception as e:
        logger.warning(f"[OPT-32] cleanup: failed to scan smart_cache_disk: {e}", exc_info=True)
        return {"deleted": 0, "error": f"scan_failed: {e}"}

    broken_keys: list[str] = []
    for row in rows:
        blob = row.get("value_blob")
        if blob is None:
            continue
        # value_blob may be returned as bytes (default) or str depending on
        # the sqlite3 connection's text_factory setting. Normalize to bytes.
        if isinstance(blob, str):
            blob_bytes = blob.encode("utf-8", errors="ignore")
        elif isinstance(blob, (bytes, bytearray, memoryview)):
            blob_bytes = bytes(blob)
        else:
            # Unexpected type — skip (don't delete what we don't understand).
            continue
        if blob_bytes.startswith(BROKEN_PREFIX):
            broken_keys.append(row["cache_key"])

    if not broken_keys:
        logger.info(
            f"[OPT-32] cleanup: scanned {len(rows)} rows, 0 legacy broken entries found"
        )
        return {
            "deleted": 0,
            "scanned": len(rows),
            "matched": 0,
            "reason": "no legacy broken entries found",
        }

    # Step 2: delete by cache_key (PRIMARY KEY) — atomic per row, safe.
    deleted = 0
    for ck in broken_keys:
        try:
            n = db_exec(
                "DELETE FROM smart_cache_disk WHERE cache_key = ?",
                (ck,)
            )
            # db_exec returns cur.rowcount; for DELETE that's the # of rows removed.
            deleted += max(0, int(n))
        except Exception as e:
            logger.debug(f"cleanup_legacy_cache_entries ignored: {e}", exc_info=True)
            logger.warning(
                f"[OPT-32] cleanup: failed to delete cache_key={ck[:12]}...: {e}"
            )

    logger.info(
        f"[OPT-32] cleanup: removed {deleted}/{len(broken_keys)} legacy broken "
        f"SLMResponse entries from smart_cache_disk (scanned {len(rows)} rows)"
    )
    return {
        "deleted": deleted,
        "scanned": len(rows),
        "matched": len(broken_keys),
        "reason": "legacy broken SLMResponse string repr",
    }


# ============================================================
# DECORATOR — auto-cache SLM predict results
# ============================================================
def cached_predict(slm_name: str, source_field: str = "source"):
    """
    Decorator cho SLM.predict() — auto cache result.
    Cache key = question. TTL = based on source from evidence.
    """
    def decorator(predict_func):
        def wrapper(self, question: str, *args, **kwargs):
            cache = get_smart_cache()
            # Try cache first
            cached = cache.get(f"slm:{slm_name}", question)
            if cached is not None:
                # [Fix 4-a-004 / DNA #2, #22, #25, #26] Task 35-A root-fixed the
                # SLMResponse ↔ dict conversion in slm_cache_get/slm_cache_set, but
                # missed this decorator path. cache.get() returns the raw stored
                # value — which after a disk hit is a JSON-decoded dict, NOT an
                # SLMResponse. Callers (e.g. runtime/judge.py) expect .answer /
                # .confidence / .evidence attributes → AttributeError → silent
                # except → confidence=0 → UNKNOWN verdict with "SLM returned no
                # useful answer". Route through the SAME _dict_to_slm_response
                # helper that slm_cache_get uses.
                converted = _dict_to_slm_response(cached)
                if converted is not None:
                    return converted
                # cached was a legacy broken string-repr entry (or unrecognized
                # shape) → fall through and recompute, then re-cache the proper
                # dict form below (Task 35-A / OPT-32 cleanup will reap the bad
                # entry on its next sweep).
            # Call original
            result = predict_func(self, question, *args, **kwargs)
            # Cache result (extract source from evidence if available)
            source = ""
            if hasattr(result, "evidence") and isinstance(result.evidence, dict):
                source = result.evidence.get(source_field, "")
            # [Fix 4-a-004] Convert SLMResponse → dict BEFORE cache.set so the
            # underlying _disk_set serializes a real JSON object (not the
            # dataclass str() repr via default=str fallback). Mirrors slm_cache_set.
            cached_value = _slm_response_to_dict(result)
            cache.set(f"slm:{slm_name}", question, cached_value, source)
            return result
        return wrapper
    return decorator


# ============================================================
# MAIN — test
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCP V30 Smart Cache")
    parser.add_argument("--stats", action="store_true", help="Show cache stats")
    parser.add_argument("--test", action="store_true", help="Run test")
    parser.add_argument("--clear", action="store_true", help="Clear cache")
    args = parser.parse_args()

    cache = get_smart_cache()

    if args.clear:
        cache.clear()
        print("  Cache cleared.")
        return

    if args.stats:
        s = cache.stats()
        print("\n  Smart Cache Stats:")
        for k, v in s.items():
            print(f"    {k:15s} {v}")
        return

    if args.test:
        print("\n  Testing Smart Cache...")
        # Test 1: Set + get
        cache.set("test", "key1", {"value": 100}, "PubChem")
        r = cache.get("test", "key1")
        print(f"    [OK] Set + Get: {r}")

        # Test 2: TTL expiration (mock)
        cache.set("test", "key2", {"value": 200}, "Binance")  # TTL=300s
        r = cache.get("test", "key2")
        print(f"    [OK] Get fresh: {r}")

        # Test 3: Different TTLs
        print("\n  TTL by source:")
        for src in ["PubChem", "Binance", "Frankfurter", "Open-Meteo", "Wikipedia", "CODATA"]:
            ttl = cache._get_ttl(src)
            print(f"    {src:20s} {ttl:>8}s ({ttl/3600:.1f}h)")

        s = cache.stats()
        print(f"\n  Final stats: {s}")
        return

    print("Use --stats, --test, or --clear")


if __name__ == "__main__":
    main()
