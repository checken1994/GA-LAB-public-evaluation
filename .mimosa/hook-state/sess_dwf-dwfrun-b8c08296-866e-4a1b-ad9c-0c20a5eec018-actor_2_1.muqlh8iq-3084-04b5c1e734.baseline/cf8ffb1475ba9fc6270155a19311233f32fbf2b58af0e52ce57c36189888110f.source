"""
V104.4.2 — 3-Tier Cache (HOT RAM + WARM SQLite + COLD pipeline).

  TIER 1 (HOT):   RAM dict          — TTL 1h  — hit trong 5ms
  TIER 2 (WARM):  SQLite verdict_cache — TTL 24h — hit trong 10-20ms
  TIER 3 (COLD):  RealityJudge pipeline  — full verify, hit trong 200-1000ms

Khi gặp cùng câu hỏi → kiểm tra HOT → WARM → COLD.

Extracted from `core/data_partitioner.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

from scp.core.partition.shard import (
    DB_PATH,
    TTL_VERDICT_CACHE,
    TTL_VERDICT_CACHE_DB,
    hash_question,
)

logger = logging.getLogger("scp.core.data_partitioner")

# [AUDIT-20260909 S6a] Migration copy statement as a pure SQL literal (13
# canonical columns + 13 bound-parameter placeholders). Column ORDER below
# MUST match scp.core.db_manager _VERDICT_CACHE_CANONICAL_DDL; a runtime
# PRAGMA comparison enforces it (fail-closed on drift). No SQL text is ever
# assembled from variables at runtime.
_VERDICT_CACHE_COPY_COLUMNS = (
    "cache_key", "question_hash", "question_text", "verdict", "confidence",
    "final_answer", "domain", "reasoning", "evidence_json", "timestamp",
    "cached_at", "expires_at", "times_used",
)
_VERDICT_CACHE_COPY_SQL = (
    "INSERT INTO verdict_cache "
    "(cache_key, question_hash, question_text, verdict, confidence, "
    "final_answer, domain, reasoning, evidence_json, timestamp, "
    "cached_at, expires_at, times_used) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


class ThreeTierCache:
    """
    3-Tier Cache cho verdict:
      TIER 1 (HOT):  RAM OrderedDict     — TTL 1h, max 1000 entries
      TIER 2 (WARM): SQLite verdict_cache — TTL 24h, max 10K entries
      TIER 3 (COLD): RealityJudge pipeline — full verify

    Khi gặp cùng câu hỏi → kiểm tra HOT → WARM → COLD.
    """

    def __init__(self, db_path: Path = DB_PATH, hot_max: int = 1000):
        self.db_path = Path(db_path)
        self.hot_max = hot_max
        self._hot: OrderedDict[str, dict] = OrderedDict()  # {hash: verdict_data}
        self._lock = threading.RLock()
        self._stats = {
            "hot_hits": 0, "warm_hits": 0, "cold_hits": 0,
            "misses": 0, "writes": 0,
            "hot_evictions": 0, "warm_expirations": 0,
        }
        self._init_warm_table()

    def _init_warm_table(self) -> None:
        """Initialize verdict_cache in self.db_path using the CANONICAL schema.

        [AUDIT-1 FIX] TẠI SAO: the previous "fix" (P2-18 test-fix) created a
        DIVERGENT 10-col schema (question_hash PK) that conflicts with db_manager's
        canonical 13-col schema (cache_key PK). This is the EXACT bug FIX-C tried
        to prevent — re-introduced as a regression. engine.py consumers
        (_set_sqlite_cache, _get_sqlite_cache) use cache_key/reasoning/timestamp
        columns that don't exist in the divergent schema → INSERT/SELECT silently
        fail → dead cache. Root-cause fix: import and use _VERDICT_CACHE_CANONICAL_DDL
        from db_manager (single source of truth). Also run a local migration check
        to add missing columns if the table already exists with old schema.
        """
        try:
            from scp.core.db_manager import _VERDICT_CACHE_CANONICAL_COLS, _VERDICT_CACHE_CANONICAL_DDL
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            # Create with canonical schema (idempotent — IF NOT EXISTS)
            conn.execute("CREATE TABLE IF NOT EXISTS verdict_cache " +
                        _VERDICT_CACHE_CANONICAL_DDL.split("verdict_cache", 1)[1])
            # Migration: check existing table has all canonical columns; add missing
            try:
                existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(verdict_cache)").fetchall()}
                missing = _VERDICT_CACHE_CANONICAL_COLS - existing_cols
                if missing:
                    logger.info(f"[AUDIT-1] verdict_cache missing cols {missing}; adding via ALTER")
                    # If any structural column is missing, rebuild via rename-copy
                    # (can't ALTER ADD PRIMARY KEY or UNIQUE). Simple approach: rename,
                    # recreate canonical, copy intersection, drop old.
                    conn.execute("ALTER TABLE verdict_cache RENAME TO verdict_cache_old")
                    conn.execute(_VERDICT_CACHE_CANONICAL_DDL)
                    common = existing_cols & _VERDICT_CACHE_CANONICAL_COLS
                    if common:
                        # [SEC-S4→S6a] Copy khối này từng là f-string ghép danh sách
                        # cột động — pattern-based scanner vẫn flag dù identifier đã
                        # regex-validate. Bây giờ: INSERT là SQL LITERAL tuyệt đối
                        # (13 cột hằng + 13 placeholder), thứ tự cột lấy từ PRAGMA
                        # của bảng canonical vừa tạo (nguồn sự thật), dữ liệu cũ được
                        # reorder trong Python và truyền qua bound parameter. Cột thiếu
                        # ở bảng cũ → dùng DEFAULT của cột đó (đúng ngữ nghĩa bỏ-cột
                        # trước đây). Lệch schema → fail-closed: bỏ copy, chỉ log.
                        new_info = conn.execute("PRAGMA table_info(verdict_cache)").fetchall()
                        new_defaults = [(row[1], row[4]) for row in new_info]
                        if [name for name, _dflt in new_defaults] != list(_VERDICT_CACHE_COPY_COLUMNS):
                            logger.warning(
                                "[AUDIT-1] verdict_cache canonical schema drifted; "
                                "skip row copy during migration"
                            )
                        else:
                            old_names = [row[1] for row in
                                         conn.execute("PRAGMA table_info(verdict_cache_old)").fetchall()]
                            old_idx = {name: i for i, name in enumerate(old_names)}
                            rows = conn.execute("SELECT * FROM verdict_cache_old").fetchall()
                            mapped = []
                            for r in rows:
                                vals = {name: r[i] for name, i in old_idx.items()}
                                mapped.append(tuple(
                                    vals[name] if name in vals else dflt
                                    for name, dflt in new_defaults
                                ))
                            conn.executemany(_VERDICT_CACHE_COPY_SQL, mapped)
                    conn.execute("DROP TABLE verdict_cache_old")
            except Exception as mig_e:
                logger.debug(f"[AUDIT-1] verdict_cache migration check: {mig_e}", exc_info=True)
            # Index for WARM-cache eviction queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_verdict_expires "
                        "ON verdict_cache(expires_at)")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Cache table init failed: {e}", exc_info=True)

    def get(self, question: str) -> dict | None:
        """Lookup 3-tier cache. Returns verdict_data or None."""
        qhash = hash_question(question)

        # TIER 1: HOT (RAM)
        with self._lock:
            if qhash in self._hot:
                # Move to end (LRU)
                self._hot.move_to_end(qhash)
                cached = self._hot[qhash]
                # Check TTL
                if time.time() < cached["expires_at"]:
                    self._stats["hot_hits"] += 1
                    cached["times_used"] = cached.get("times_used", 0) + 1
                    return cached
                else:
                    # Expired, remove from HOT
                    del self._hot[qhash]

        # TIER 2: WARM (SQLite)
        # [FIX-CRIT-135 BUG 2] TẠI SAO: every SQLite call used bare
        # sqlite3.connect(self.db_path) → bypassed db_manager._db_lock →
        # race with Brain (Invariant #7) under concurrent load (judge main
        # thread + healing bg thread + 3 learning engines all write to
        # v13.db). Fix: route through db_query_one/db_exec (single global
        # _db_lock, cached per-path connection).
        try:
            from scp.core.db_manager import db_query_one
            row = db_query_one(
                "SELECT verdict, confidence, final_answer, domain, "
                "evidence_json, cached_at, expires_at, times_used "
                "FROM verdict_cache WHERE question_hash = ?",
                (qhash,),
                db_path=str(self.db_path),
            )

            if row:
                verdict = row["verdict"]
                confidence = row["confidence"]
                final_answer = row["final_answer"]
                domain = row["domain"]
                evidence_json = row["evidence_json"]
                cached_at = row["cached_at"]
                expires_at = row["expires_at"]
                times_used = row["times_used"]
                # Check TTL
                expires_dt = datetime.fromisoformat(expires_at)
                if datetime.now() < expires_dt:
                    # Promote to HOT cache
                    data = {
                        "verdict": verdict,
                        "confidence": confidence,
                        "final_answer": final_answer,
                        "domain": domain,
                        "evidence": json.loads(evidence_json) if evidence_json else {},
                        "cached_at": cached_at,
                        "expires_at": time.time() + TTL_VERDICT_CACHE,
                        "times_used": times_used + 1,
                        "source": "warm",
                    }
                    with self._lock:
                        self._hot[qhash] = data
                        self._evict_hot_if_needed()
                    self._stats["warm_hits"] += 1

                    # Update times_used in DB
                    self._update_times_used(qhash, times_used + 1)
                    return data
                else:
                    # Expired — delete from WARM
                    self._delete_warm(qhash)
                    self._stats["warm_expirations"] += 1
        except Exception as e:
            logger.debug(f"WARM cache read failed: {e}", exc_info=True)

        # TIER 3: COLD — not in cache, return None (caller will run pipeline)
        self._stats["misses"] += 1
        return None

    def put(self, question: str, verdict_data: dict) -> None:
        """Store verdict vào HOT + WARM."""
        qhash = hash_question(question)
        now = time.time()
        now_dt = datetime.now()

        # TIER 1: HOT
        with self._lock:
            data = {
                "verdict": verdict_data.get("verdict"),
                "confidence": verdict_data.get("confidence"),
                "final_answer": verdict_data.get("final_answer", "")[:500],
                "domain": verdict_data.get("domain", "general"),
                "evidence": verdict_data.get("evidence", {}),
                "cached_at": now_dt.isoformat(),
                "expires_at": now + TTL_VERDICT_CACHE,
                "times_used": 1,
                "source": "fresh",
            }
            self._hot[qhash] = data
            self._evict_hot_if_needed()

        # TIER 2: WARM
        # [FIX-CRIT-135 BUG 2] route through db_exec (single _db_lock) — was bare sqlite3.connect.
        try:
            from scp.core.db_manager import db_exec
            expires_dt = now_dt + timedelta(seconds=TTL_VERDICT_CACHE_DB)
            # [AUDIT-1 FIX] Set cache_key = question_hash so engine.py consumers
            # (which query by cache_key) can ALSO find these rows. The canonical
            # schema has cache_key as PRIMARY KEY — without setting it, INSERT
            # would create NULL cache_key rows that engine.py can never read.
            db_exec("""
                INSERT OR REPLACE INTO verdict_cache
                (cache_key, question_hash, question_text, verdict, confidence,
                 final_answer, domain, evidence_json, cached_at,
                 expires_at, times_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                qhash,  # cache_key = question_hash (both unique, both = qhash)
                qhash,
                question[:500],
                verdict_data.get("verdict"),
                verdict_data.get("confidence"),
                verdict_data.get("final_answer", "")[:500],
                verdict_data.get("domain", "general"),
                json.dumps(verdict_data.get("evidence", {}),
                          ensure_ascii=False)[:5000],
                now_dt.isoformat(),
                expires_dt.isoformat(),
            ), db_path=str(self.db_path))
        except Exception as e:
            logger.debug(f"WARM cache write failed: {e}", exc_info=True)

        self._stats["writes"] += 1

    def _evict_hot_if_needed(self) -> None:
        """LRU eviction khi HOT cache > hot_max."""
        with self._lock:
            while len(self._hot) > self.hot_max:
                self._hot.popitem(last=False)
                self._stats["hot_evictions"] += 1

    def _update_times_used(self, qhash: str, times: int) -> None:
        # [FIX-CRIT-135 BUG 2] route through db_exec (single _db_lock) — was bare sqlite3.connect.
        try:
            from scp.core.db_manager import db_exec
            db_exec(
                "UPDATE verdict_cache SET times_used = ? WHERE question_hash = ?",
                (times, qhash),
                db_path=str(self.db_path),
            )
        except Exception:
            logger.exception("[data_partitioner.py:768] silenced exception")

    def _delete_warm(self, qhash: str) -> None:
        # [FIX-CRIT-135 BUG 2] route through db_exec (single _db_lock) — was bare sqlite3.connect.
        try:
            from scp.core.db_manager import db_exec
            db_exec(
                "DELETE FROM verdict_cache WHERE question_hash = ?",
                (qhash,),
                db_path=str(self.db_path),
            )
        except Exception:
            logger.exception("[data_partitioner.py:780] silenced exception")

    def expire_warm(self) -> int:
        """Xóa expired entries từ WARM cache. Returns count."""
        # [FIX-CRIT-135 BUG 2] route through db_exec (single _db_lock) — was bare sqlite3.connect.
        # db_exec returns rowcount for the DELETE statement.
        try:
            from scp.core.db_manager import db_exec
            now = datetime.now().isoformat()
            count = db_exec(
                "DELETE FROM verdict_cache WHERE expires_at < ?",
                (now,),
                db_path=str(self.db_path),
            )
            self._stats["warm_expirations"] += count or 0
            return count or 0
        except Exception as e:
            logger.warning(f"WARM expire failed: {e}", exc_info=True)
            return 0

    def clear_hot(self) -> int:
        """Clear HOT cache (restart-safe)."""
        with self._lock:
            n = len(self._hot)
            self._hot.clear()
            return n

    def stats(self) -> dict:
        """Cache stats."""
        with self._lock:
            return {
                **self._stats,
                "hot_size": len(self._hot),
                "hot_max": self.hot_max,
                "hit_rate": self._compute_hit_rate(),
            }

    def _compute_hit_rate(self) -> float:
        total = (self._stats["hot_hits"] + self._stats["warm_hits"]
                 + self._stats["misses"])
        if total == 0:
            return 0.0
        return round((self._stats["hot_hits"] + self._stats["warm_hits"]) / total, 3)
