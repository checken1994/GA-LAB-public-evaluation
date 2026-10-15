"""
V104.4.3 + V104.4.4 + V104.4.5 — Bypass Lessons Store + TTL Expirer + Migration.

- BypassLessonsStore: học từ mỗi bypass → sinh rule phòng thủ.
- TTLExpirer: auto-expire data theo TTL (question_log, verdict_cache, etc.)
- migrate_old_to_new: chuyển data cũ (1 file) sang cấu trúc mới (theo domain + ngày).

Extracted from `core/data_partitioner.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

# Avoid hard dependency — ThreeTierCache used as forward type hint only.
from typing import TYPE_CHECKING

from scp.core.partition.shard import (
    DATA_DIR,
    DB_PATH,
    TTL_PENDING_RESOLUTIONS,
    TTL_QUESTION_LOG,
    DataPartitioner,
    hash_question,
)

if TYPE_CHECKING:
    from scp.core.partition.rotate import ThreeTierCache

logger = logging.getLogger("scp.core.data_partitioner")

# [SEC-S4] Partition date comes from external JSONL timestamps; it is used to
# build output filenames, so it must be a strict YYYY-MM-DD slug before it can
# ever reach a filesystem path (rejects traversal, separators, absolute paths).
_SAFE_PARTITION_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _safe_partition_date(date_str: str) -> str:
    """Validate a partition date slug; raise ValueError on anything unsafe."""
    if not _SAFE_PARTITION_DATE.fullmatch(date_str):
        raise ValueError(f"unsafe partition date: {date_str!r}")
    return date_str


class BypassLessonsStore:
    """Bypass lessons: học từ mỗi bypass → sinh rule phòng thủ.

    Schema:
      bypass_id TEXT PRIMARY KEY
      first_seen TEXT
      attack_type TEXT
      question TEXT
      root_cause TEXT
      missed_signatures TEXT (JSON)
      suggested_rule_pattern TEXT
      suggested_rule_type TEXT
      rule_activated INTEGER DEFAULT 0
      activated_at TEXT
      tested_against_normal INTEGER DEFAULT 0
      false_positive_rate REAL DEFAULT 0.0
      lesson TEXT  -- summary of what to learn
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self._init_table()

    def _init_table(self) -> None:
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bypass_lessons (
                    bypass_id TEXT PRIMARY KEY,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    times_seen INTEGER DEFAULT 1,
                    attack_type TEXT,
                    question TEXT,
                    root_cause TEXT,
                    missed_signatures TEXT,
                    suggested_rule_pattern TEXT,
                    suggested_rule_type TEXT,
                    rule_activated INTEGER DEFAULT 0,
                    rule_id TEXT,
                    activated_at TEXT,
                    tested_against_normal INTEGER DEFAULT 0,
                    false_positive_rate REAL DEFAULT 0.0,
                    lesson TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_attack "
                        "ON bypass_lessons(attack_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_activated "
                        "ON bypass_lessons(rule_activated)")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"BypassLessons init failed: {e}", exc_info=True)

    def record_lesson(self, bypass_record: dict) -> dict:
        """Record/update 1 bypass lesson. Returns: {new, updated, rule_suggested}."""
        bid = bypass_record.get("bypass_id", hash_question(
            bypass_record.get("question", "") + str(bypass_record.get("timestamp", ""))
        )[:16])
        now = datetime.now().isoformat()

        # Parse bypass analysis if available
        root_cause = bypass_record.get("root_cause", "unknown")
        missed = bypass_record.get("missed_signatures", [])
        suggested_pattern = bypass_record.get("suggested_rule_pattern", "")
        suggested_type = bypass_record.get("suggested_rule_type", "pattern")
        attack_type = (missed[0] if missed
                       else bypass_record.get("signatures", ["unknown"])[0]
                       if bypass_record.get("signatures") else "unknown")
        question = bypass_record.get("question", "")[:500]

        # Compose lesson summary
        lesson = (f"Khi attacker dùng '{attack_type}' "
                  f"(root_cause: {root_cause}) → "
                  f"thêm rule '{suggested_pattern}' "
                  f"để block tương lai") if suggested_pattern else \
                 f"Attacker bypass với '{attack_type}' — chưa có suggested rule"

        try:
            from scp.core.db_manager import db_exec, db_query_one
            # [FIX-CRIT-135 BUG 2] route through db_query_one/db_exec (single _db_lock) — was bare sqlite3.connect.
            # Check if exists
            row = db_query_one(
                "SELECT times_seen FROM bypass_lessons WHERE bypass_id = ?",
                (bid,),
                db_path=str(self.db_path),
            )

            if row:
                # Update
                db_exec("""
                    UPDATE bypass_lessons SET
                        last_seen = ?, times_seen = ?,
                        question = ?, root_cause = ?,
                        missed_signatures = ?,
                        suggested_rule_pattern = ?,
                        suggested_rule_type = ?
                    WHERE bypass_id = ?
                """, (
                    now, row["times_seen"] + 1, question,
                    root_cause, json.dumps(missed, ensure_ascii=False),
                    suggested_pattern, suggested_type, bid,
                ), db_path=str(self.db_path))
                return {"new": False, "updated": True, "bypass_id": bid}
            else:
                # Insert new
                db_exec("""
                    INSERT INTO bypass_lessons
                    (bypass_id, first_seen, last_seen, times_seen,
                     attack_type, question, root_cause, missed_signatures,
                     suggested_rule_pattern, suggested_rule_type,
                     rule_activated, lesson)
                    VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, 0, ?)
                """, (
                    bid, now, now,
                    attack_type, question, root_cause,
                    json.dumps(missed, ensure_ascii=False),
                    suggested_pattern, suggested_type,
                    lesson,
                ), db_path=str(self.db_path))
                return {"new": True, "updated": False,
                        "bypass_id": bid,
                        "rule_suggested": bool(suggested_pattern)}
        except Exception as e:
            logger.warning(f"Record lesson failed: {e}", exc_info=True)
            return {"new": False, "updated": False, "error": str(e)}

    def get_pending_rules(self, limit: int = 50) -> list[dict]:
        """Get lessons có suggested_rule nhưng chưa activate."""
        # [FIX-CRIT-135 BUG 2] route through db_query_all (single _db_lock) — was bare sqlite3.connect.
        try:
            from scp.core.db_manager import db_query_all
            rows = db_query_all("""
                SELECT bypass_id, attack_type, suggested_rule_pattern,
                       suggested_rule_type, times_seen, lesson
                FROM bypass_lessons
                WHERE rule_activated = 0
                  AND suggested_rule_pattern != ''
                ORDER BY times_seen DESC
                LIMIT ?
            """, (limit,), db_path=str(self.db_path))
            return [{
                "bypass_id": r["bypass_id"], "attack_type": r["attack_type"],
                "suggested_pattern": r["suggested_rule_pattern"],
                "suggested_type": r["suggested_rule_type"],
                "times_seen": r["times_seen"], "lesson": r["lesson"],
            } for r in rows]
        except Exception as e:
            logger.warning(f"Get pending rules failed: {e}", exc_info=True)
            return []

    def activate_rule(self, bypass_id: str, rule_id: str,
                      tested_against: int, fp_rate: float) -> bool:
        """Mark rule đã activate sau khi test FP."""
        # [FIX-CRIT-135 BUG 2] route through db_exec (single _db_lock) — was bare sqlite3.connect.
        try:
            from scp.core.db_manager import db_exec
            db_exec("""
                UPDATE bypass_lessons SET
                    rule_activated = 1,
                    rule_id = ?,
                    activated_at = ?,
                    tested_against_normal = ?,
                    false_positive_rate = ?
                WHERE bypass_id = ?
            """, (
                rule_id, datetime.now().isoformat(),
                tested_against, fp_rate, bypass_id,
            ), db_path=str(self.db_path))
            return True
        except Exception as e:
            logger.warning(f"Activate rule failed: {e}", exc_info=True)
            return False

    def get_stats(self) -> dict:
        # [FIX-CRIT-135 BUG 2] route through db_query_one/db_query_all (single _db_lock) — was bare sqlite3.connect.
        try:
            from scp.core.db_manager import db_query_all, db_query_one
            total_row = db_query_one(
                "SELECT COUNT(*) AS cnt FROM bypass_lessons",
                (),
                db_path=str(self.db_path),
            )
            total = total_row["cnt"] if total_row else 0
            activated_row = db_query_one(
                "SELECT COUNT(*) AS cnt FROM bypass_lessons WHERE rule_activated = 1",
                (),
                db_path=str(self.db_path),
            )
            activated = activated_row["cnt"] if activated_row else 0
            pending_row = db_query_one(
                "SELECT COUNT(*) AS cnt FROM bypass_lessons "
                "WHERE rule_activated = 0 AND suggested_rule_pattern != ''",
                (),
                db_path=str(self.db_path),
            )
            pending = pending_row["cnt"] if pending_row else 0
            by_attack = {}
            for r in db_query_all(
                "SELECT attack_type, COUNT(*) AS cnt FROM bypass_lessons "
                "GROUP BY attack_type ORDER BY cnt DESC",
                (),
                db_path=str(self.db_path),
            ):
                by_attack[r["attack_type"]] = r["cnt"]
            return {
                "total_lessons": total,
                "rules_activated": activated,
                "rules_pending": pending,
                "by_attack_type": by_attack,
            }
        except Exception as e:
            logger.debug(f"get_stats ignored: {e}", exc_info=True)
            return {"error": str(e)}


class TTLExpirer:
    """Auto-expire data theo TTL."""

    def __init__(self, db_path: Path = DB_PATH,
                 partitioner: DataPartitioner = None,
                 cache: ThreeTierCache = None):
        self.db_path = Path(db_path)
        self.partitioner = partitioner or DataPartitioner()
        self.cache = cache

    def expire_question_log(self) -> int:
        """Xóa question_log > 1 ngày. Returns count."""
        # [FIX-CRIT-135 BUG 2] route through db_exec (single _db_lock) — was bare sqlite3.connect.
        try:
            from scp.core.db_manager import db_exec
            cutoff = (datetime.now() - timedelta(seconds=TTL_QUESTION_LOG)
                      ).isoformat()
            count = db_exec(
                "DELETE FROM question_log WHERE last_seen_ts < ?",
                (cutoff,),
                db_path=str(self.db_path),
            )
            return count or 0
        except Exception as e:
            logger.warning(f"Expire question_log failed: {e}", exc_info=True)
            return 0

    def expire_verdict_cache_warm(self) -> int:
        """Xóa verdict_cache expired."""
        if self.cache:
            return self.cache.expire_warm()
        return 0

    def expire_pending_resolutions(self) -> int:
        """Xóa pending_reverification đã done > 1 ngày."""
        # [FIX-CRIT-135 BUG 2] route through db_exec (single _db_lock) — was bare sqlite3.connect.
        # [EXEC-1 B6] TẠI SAO: was `WHERE ... created_at < ?` but the
        # pending_reverification schema (db_manager.py:657-665) has NO
        # `created_at` column — only `timestamp`. SQLite is permissive on
        # unknown columns in WHERE clauses only when the column doesn't
        # exist as an identifier (actually it raises OperationalError).
        # Either way, no rows ever matched → 0 rows expired →
        # pending_reverification table grew unbounded. Fix: use `timestamp`
        # (the actual column name from the canonical schema).
        try:
            from scp.core.db_manager import db_exec
            cutoff = (datetime.now() - timedelta(seconds=TTL_PENDING_RESOLUTIONS)
                      ).isoformat()
            count = db_exec(
                "DELETE FROM pending_reverification WHERE status = 'done' "
                "AND timestamp < ?",
                (cutoff,),
                db_path=str(self.db_path),
            )
            return count or 0
        except Exception as exc:
            # silent-by-design: TTL cleanup is best-effort maintenance; stale rows are harmless.
            logger.debug("archive: pending_reverification TTL cleanup failed (non-fatal): %s", exc, exc_info=True)
            return 0

    def archive_old_bypasses(self, max_age_days: int = 7) -> dict:
        """Archive bypasses > 7 ngày → gzip."""
        return self.partitioner.archive_old_files("bypasses", max_age_days)

    def archive_old_errors(self, max_age_days: int = 7) -> dict:
        """Archive errors > 7 ngày → gzip."""
        return self.partitioner.archive_old_files("errors", max_age_days)

    def run_all_expirations(self) -> dict:
        """Run all TTL expirations. Returns summary."""
        return {
            "question_log_expired": self.expire_question_log(),
            "verdict_cache_warm_expired": self.expire_verdict_cache_warm(),
            "pending_resolutions_expired": self.expire_pending_resolutions(),
            "bypasses_archived": self.archive_old_bypasses(),
            "errors_archived": self.archive_old_errors(),
        }


def migrate_old_to_new(data_dir: Path = DATA_DIR,
                       db_path: Path = DB_PATH,
                       dry_run: bool = True) -> dict:
    """Migrate data từ cấu trúc cũ (1 file) sang mới (theo domain + ngày).

    - bypass_log.jsonl → bypasses/{date}.jsonl (split by timestamp)
    - error_store.jsonl → errors/{date}.jsonl (split by timestamp)
    - knowledge table → keep in SQLite (sẽ route theo domain khi query)
    """
    data_dir = Path(data_dir)
    result = {"migrated": [], "skipped": [], "errors": []}

    # Migrate bypass_log.jsonl
    old_bypass_log = data_dir / "bypass_log.jsonl"
    if old_bypass_log.exists():
        try:
            partitioner = DataPartitioner(data_dir)
            with open(old_bypass_log, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            grouped = {}
            for line in lines:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    ts = record.get("timestamp", time.time())
                    if isinstance(ts, (int, float)):
                        dt = datetime.fromtimestamp(ts)
                    else:
                        dt = datetime.fromisoformat(str(ts))
                    date_str = dt.strftime("%Y-%m-%d")
                    grouped.setdefault(date_str, []).append(record)
                except Exception as e:
                    logger.debug(f"migrate_old_to_new ignored: {e}", exc_info=True)
                    result["errors"].append(f"parse line: {e}")

            if not dry_run:
                for date_str, records in grouped.items():
                    _safe_partition_date(date_str)  # [SEC-S4] slug guard before path build
                    path = partitioner.bypasses_path(date_str)
                    # [SEC-S4] Containment: partition output must stay under data_dir.
                    if not path.resolve().is_relative_to(data_dir.resolve()):
                        raise ValueError(f"partition path escapes data dir: {path}")
                    with path.open("w", encoding="utf-8") as f:
                        for r in records:
                            f.write(json.dumps(r, ensure_ascii=False) + "\n")

            result["migrated"].append({
                "from": str(old_bypass_log),
                "lines": len(lines),
                "by_date": {d: len(rs) for d, rs in grouped.items()},
                "dry_run": dry_run,
            })
        except Exception as e:
            logger.debug(f"migrate_old_to_new ignored: {e}", exc_info=True)
            result["errors"].append(f"bypass_log: {e}")
    else:
        result["skipped"].append("bypass_log.jsonl not exists")

    # Migrate error_store.jsonl
    old_error_store = data_dir / "error_store.jsonl"
    if old_error_store.exists():
        try:
            partitioner = DataPartitioner(data_dir)
            with open(old_error_store, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            grouped = {}
            for line in lines:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    ts = record.get("ts", record.get("timestamp", time.time()))
                    if isinstance(ts, (int, float)):
                        dt = datetime.fromtimestamp(ts)
                    else:
                        dt = datetime.fromisoformat(str(ts))
                    date_str = dt.strftime("%Y-%m-%d")
                    grouped.setdefault(date_str, []).append(record)
                except Exception as e:
                    logger.debug(f"migrate_old_to_new ignored: {e}", exc_info=True)
                    result["errors"].append(f"parse error line: {e}")

            if not dry_run:
                for date_str, records in grouped.items():
                    _safe_partition_date(date_str)  # [SEC-S4] slug guard before path build
                    path = partitioner.errors_path(date_str)
                    # [SEC-S4] Containment: partition output must stay under data_dir.
                    if not path.resolve().is_relative_to(data_dir.resolve()):
                        raise ValueError(f"partition path escapes data dir: {path}")
                    with path.open("w", encoding="utf-8") as f:
                        for r in records:
                            f.write(json.dumps(r, ensure_ascii=False) + "\n")

            result["migrated"].append({
                "from": str(old_error_store),
                "lines": len(lines),
                "by_date": {d: len(rs) for d, rs in grouped.items()},
                "dry_run": dry_run,
            })
        except Exception as e:
            logger.debug(f"migrate_old_to_new ignored: {e}", exc_info=True)
            result["errors"].append(f"error_store: {e}")
    else:
        result["skipped"].append("error_store.jsonl not exists")

    return result
