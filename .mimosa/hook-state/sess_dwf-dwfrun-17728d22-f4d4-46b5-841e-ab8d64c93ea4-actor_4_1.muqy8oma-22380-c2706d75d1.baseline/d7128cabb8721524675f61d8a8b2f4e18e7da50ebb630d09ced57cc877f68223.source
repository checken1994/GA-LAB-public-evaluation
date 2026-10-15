"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

#!/usr/bin/env python3
"""
SCP V14 — Hypothesis Zone (DB2)
================================
DB riêng cho PARTIAL (chưa xác nhận) + conflicts.

Tables:
  1. partial_entries  — lưu PARTIAL verdicts, chờ xác nhận
  2. conflicts         — ghi xung đột khi PASS khác PARTIAL

Quy trình:
  - PARTIAL → ghi vào hypothesis_zone.db (status='pending')
  - PASS sau này → kiểm tra hypothesis_zone.db:
    - PASS giống PARTIAL → confirmed
    - PASS khác PARTIAL → rejected + ghi conflicts
  - recall: ưu tiên main_kb, fallback hypothesis (confirmed only)
"""
import logging
import os
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)
from typing import Any

# ============================================================
# CONFIG — DB2 riêng (không đụng main_kb.db)
# ============================================================
# Go up 3 levels: scp/core/hypothesis_zone.py -> scp_v14_final/
_RUNTIME_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HZ_DB_PATH = os.path.join(_RUNTIME_DIR, "data", "hypothesis_zone.db")


def get_hz_db():
    """Get hypothesis zone DB connection"""
    os.makedirs(os.path.dirname(HZ_DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(HZ_DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hz_exec(sql, params=()):
    conn = get_hz_db()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        # [V104.35 #35] TẠI SAO: return lastrowid so callers don't need
        # last_insert_rowid() on a NEW connection (which returns 0)
        return cur.lastrowid if cur.lastrowid else cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hz_query_one(sql, params=()):
    conn = get_hz_db()
    try:
        r = conn.execute(sql, params).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def hz_query_all(sql, params=()):
    conn = get_hz_db()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def init_hz_schema():
    """Create hypothesis zone tables"""
    conn = get_hz_db()

    # Table 1: partial_entries — lưu PARTIAL verdicts
    conn.execute("""
        CREATE TABLE IF NOT EXISTS partial_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            entity TEXT,
            attribute TEXT,
            value TEXT,
            confidence REAL NOT NULL,
            source TEXT,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_partial_status ON partial_entries(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_partial_entity ON partial_entries(entity, attribute)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_partial_question ON partial_entries(question)")

    # Table 2: conflicts — ghi xung đột khi PASS khác PARTIAL
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conflicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            pass_answer TEXT NOT NULL,
            pass_value TEXT,
            partial_answer TEXT NOT NULL,
            partial_value TEXT,
            resolved_at TEXT NOT NULL,
            resolution TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_question ON conflicts(question)")

    conn.commit()
    conn.close()
    logger.info("Hypothesis Zone schema created (hypothesis_zone.db)")


# ============================================================
# HYPOTHESIS STORE — quản lý PARTIAL entries
# ============================================================
class HypothesisStore:
    """Quản lý PARTIAL entries trong hypothesis_zone.db"""

    @staticmethod
    def add_partial(question: str, answer: str, entity: str, attribute: str,
                    value: str, confidence: float, source: str = "") -> int:
        """Thêm PARTIAL entry (status='pending') with dedup"""
        # [EXEC-1 B5] TẠI SAO: entity was stored as-is (e.g. "Hà Nội"),
        # but find_pending() / find_confirmed() query `WHERE entity = ?`
        # with `entity.lower()` (e.g. "hà nội"). The case mismatch meant
        # PARTIAL entries stored via add_partial were INVISIBLE to
        # find_pending → resolve_partial() never saw them → they stayed
        # pending forever (memory leak + dead hypothesis zone).
        # Fix: lowercase entity here so storage + lookup agree. Matches
        # the canonical form used everywhere else in the codebase
        # (RealityAnchor, knowledge table, FastLearning._store_kb, etc.).
        # NOTE: only entity is lowercased — find_pending lowercases entity
        # but NOT attribute, so attribute stays as-is to stay consistent.
        entity = (entity or "").lower()

        # [FIXED] Check for existing entry with same question to prevent duplicate
        existing = hz_query_one("SELECT id FROM partial_entries WHERE question = ?", (question,))
        if existing:
            hz_exec("""
                UPDATE partial_entries
                SET answer = ?, value = ?, confidence = ?, source = ?, timestamp = ?
                WHERE question = ?
            """, (answer, str(value), confidence, source, datetime.now().isoformat(), question))
            return existing["id"]

        ts = datetime.now().isoformat()
        try:
            # [V104.35 #35] TẠI SAO: hz_exec now returns lastrowid (was: last_insert_rowid()
            # on NEW connection returned 0 → confirm(id)/reject(id) targeted non-existent row)
            new_id = hz_exec("""
                INSERT INTO partial_entries
                (question, answer, entity, attribute, value, confidence, source, timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (question, answer, entity, attribute, str(value), confidence, source, ts))
            return new_id if new_id and new_id > 0 else -1
        except Exception as e:
            logger.warning("HypothesisStore add_partial failed: %s", e, exc_info=True)
            logger.error(f"HypothesisStore add_partial error: {e}")
            return -1

    @staticmethod
    def find_pending(entity: str, attribute: str) -> list[dict]:
        """Tìm PARTIAL entries pending cho entity+attribute"""
        return hz_query_all("""
            SELECT * FROM partial_entries
            WHERE entity = ? AND attribute = ? AND status = 'pending'
            ORDER BY timestamp ASC
        """, (entity.lower(), attribute))

    @staticmethod
    def find_confirmed(entity: str, attribute: str) -> dict | None:
        """Tìm PARTIAL entry đã confirmed cho entity+attribute"""
        return hz_query_one("""
            SELECT * FROM partial_entries
            WHERE entity = ? AND attribute = ? AND status = 'confirmed'
            ORDER BY timestamp DESC LIMIT 1
        """, (entity.lower(), attribute))

    @staticmethod
    def confirm(entry_id: int):
        """Đánh dấu PARTIAL entry là confirmed"""
        hz_exec("UPDATE partial_entries SET status = 'confirmed' WHERE id = ?", (entry_id,))

    @staticmethod
    def reject(entry_id: int):
        """Đánh dấu PARTIAL entry là rejected"""
        hz_exec("UPDATE partial_entries SET status = 'rejected' WHERE id = ?", (entry_id,))

    @staticmethod
    def add_conflict(question: str, pass_answer: str, pass_value: str,
                     partial_answer: str, partial_value: str, resolution: str):
        """Ghi xung đột vào conflicts table"""
        ts = datetime.now().isoformat()
        hz_exec("""
            INSERT INTO conflicts
            (question, pass_answer, pass_value, partial_answer, partial_value, resolved_at, resolution)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (question, pass_answer, str(pass_value), partial_answer, str(partial_value), ts, resolution))

    @staticmethod
    def get_stats() -> dict:
        """Thống kê hypothesis zone"""
        pending = hz_query_one("SELECT COUNT(*) as cnt FROM partial_entries WHERE status = 'pending'")
        confirmed = hz_query_one("SELECT COUNT(*) as cnt FROM partial_entries WHERE status = 'confirmed'")
        rejected = hz_query_one("SELECT COUNT(*) as cnt FROM partial_entries WHERE status = 'rejected'")
        conflicts = hz_query_one("SELECT COUNT(*) as cnt FROM conflicts")
        return {
            "pending": pending["cnt"] if pending else 0,
            "confirmed": confirmed["cnt"] if confirmed else 0,
            "rejected": rejected["cnt"] if rejected else 0,
            "conflicts": conflicts["cnt"] if conflicts else 0,
        }

    @staticmethod
    def resolve_partial(entity: str, attribute: str, pass_value: Any,
                        pass_answer: str, question: str) -> dict:
        """
        Đối chiếu PASS mới với PARTIAL pending.

        Returns: {confirmed: int, rejected: int, conflicts: int}
        """
        result = {"confirmed": 0, "rejected": 0, "conflicts": 0}
        pending_entries = HypothesisStore.find_pending(entity, attribute)

        for entry in pending_entries:
            try:
                partial_val = float(entry["value"])
                pass_val = float(pass_value)
                # So sánh với tolerance (5% hoặc epsilon)
                rel_diff = abs(partial_val - pass_val) / max(abs(pass_val), 1e-300)
                abs_diff = abs(partial_val - pass_val)
                epsilon = 0.001 if abs(pass_val) < 100 else abs(pass_val) * 0.001
                is_match = rel_diff < 0.05 or abs_diff < epsilon
            except (ValueError, TypeError) as exc:
                # silent-by-design: non-numeric entries fall back to documented string comparison.
                logger.debug("hypothesis_zone: numeric compare failed, using string compare: %s", exc, exc_info=True)
                is_match = str(entry["value"]).strip().lower() == str(pass_value).strip().lower()

            if is_match:
                # PASS giống PARTIAL → confirmed
                HypothesisStore.confirm(entry["id"])
                result["confirmed"] += 1
            else:
                # PASS khác PARTIAL → rejected + ghi conflict
                HypothesisStore.reject(entry["id"])
                HypothesisStore.add_conflict(
                    question=question,
                    pass_answer=pass_answer,
                    pass_value=str(pass_value),
                    partial_answer=entry["answer"],
                    partial_value=entry["value"],
                    resolution="rejected"
                )
                result["rejected"] += 1
                result["conflicts"] += 1

        return result

    @staticmethod
    def cleanup_old(days: int = 30) -> int:
        """Xóa PARTIAL entries cũ hơn N ngày (pending + rejected)"""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        try:
            # [EXEC-1 B4] TẠI SAO: was `hz_query_one("SELECT changes() as cnt")`
            # on a NEW connection. SQLite `changes()` is PER-CONNECTION — it
            # returns the rowcount of the LAST statement executed ON THAT
            # CONNECTION. Since hz_query_one opens its OWN connection (separate
            # from the one that ran the DELETE), `changes()` always returned 0
            # → caller always thought 0 rows were cleaned up, even when the
            # DELETE actually removed rows. The cleanup stats were a lie.
            # Fix: hz_exec already returns rowcount for the DELETE statement
            # (cur.rowcount). Use that directly — no second query needed.
            return hz_exec(
                "DELETE FROM partial_entries WHERE timestamp < ? AND status IN ('pending', 'rejected')",
                (cutoff,)
            ) or 0
        except Exception as exc:
            # silent-by-design: cleanup is best-effort maintenance; stale pending entries are harmless.
            logger.debug("hypothesis_zone: partial_entries cleanup failed (non-fatal): %s", exc, exc_info=True)
            return 0


# ============================================================
# AUTO-INIT ON IMPORT
# ============================================================
try:
    init_hz_schema()
except Exception as e:
    logger.warning("Hypothesis Zone init failed: %s", e, exc_info=True)
    logger.debug(f"[WARN] Hypothesis Zone init failed: {e}")
