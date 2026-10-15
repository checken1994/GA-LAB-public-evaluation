"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

#!/usr/bin/env python3
"""
SCP V14 EXPERIENCE ENGINE — Tầng "Bài học" thống nhất.

Vấn đề audit phát hiện:
    SCP có 3 loại trí nhớ nhưng không có tầng tổng hợp:
        Memory       -> ghi nhớ câu hỏi từng sai
        Knowledge    -> ghi nhớ sự thật đã xác minh
        ErrorHistory -> ghi nhớ pattern lỗi

    Thiếu: Experience -> Lesson -> Policy Update

Giải pháp:
    ExperienceEngine tổng hợp cả 3 -> tạo "bài học" -> thay đổi hành vi engine.

    Question + Knowledge + Error + Outcome
                    ?
                Experience
                    ?
                  Lesson
                    ?
               Policy Update
                    ?
           Engine xử lý khác lần sau

Chạy:
    python v14_experience.py                    # Học + báo cáo
    python v14_experience.py --lien-tuc          # 24/7
    python v14_experience.py --chinh-sach        # Xem policies hiện tại
"""

import argparse
import hashlib
import json
import os
import signal
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import logging

from scp.core.db_manager import _KNOWLEDGE_CANONICAL_DDL, db_exec, db_query_all, db_query_one, init_db
from scp.core.scp_v14 import SCPV14 as SCPV13

logger = logging.getLogger("scp.experience")


# ============================================================
# EXPERIENCES TABLE
# ============================================================
def init_experience_db():
    """Tạo bảng experiences — nơi lưu bài học.

    [V104.38] TẠI SAO: V104.37 #77 added INSERT OR IGNORE but without UNIQUE
    constraint, it's a no-op (INSERT OR IGNORE only ignores on constraint
    violation). This migration adds UNIQUE(sha256) so dedup actually works.
    """
    db_exec("""
        CREATE TABLE IF NOT EXISTS experiences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            question TEXT NOT NULL,
            entity TEXT,
            domain TEXT,
            source TEXT,
            ai_answer TEXT,
            real_value TEXT,
            verdict TEXT,
            error_type TEXT,
            error_reason TEXT,
            lesson_type TEXT NOT NULL,
            lesson_description TEXT NOT NULL,
            policy_action TEXT NOT NULL,
            policy_target TEXT,
            policy_value TEXT,
            applied BOOLEAN DEFAULT 0,
            applied_at TEXT,
            sha256 TEXT
        )
    """)
    db_exec("CREATE INDEX IF NOT EXISTS idx_exp_lesson ON experiences(lesson_type)")
    db_exec("CREATE INDEX IF NOT EXISTS idx_exp_domain ON experiences(domain)")
    db_exec("CREATE INDEX IF NOT EXISTS idx_exp_applied ON experiences(applied)")

    # [V104.38] Migration: add UNIQUE(sha256) constraint
    # TẠI SAO: SQLite doesn't support ALTER TABLE ADD CONSTRAINT, so we
    # recreate the table. Dedup existing rows first (keep latest id per sha256).
    _migrate_experiences_unique_sha256()


def _migrate_experiences_unique_sha256():
    """[V104.38] Add UNIQUE(sha256) to experiences table via table recreation.

    TẠI SAO: Without UNIQUE constraint, INSERT OR IGNORE is a no-op.
    This migration:
      1. Checks if constraint already exists (idempotent)
      2. Deduplicates existing rows (keeps max(id) per sha256)
      3. Creates new table with UNIQUE(sha256)
      4. Copies deduped data
      5. Drops old, renames new
    """
    import logging
    _logger = logging.getLogger("scp.experience")

    try:
        # Check if UNIQUE constraint already exists
        # SQLite stores index info in sqlite_master
        existing = db_query_all(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='experiences'"
        )
        if not existing:
            return  # table doesn't exist yet

        schema_sql = existing[0].get("sql", "") if existing else ""
        if "UNIQUE(sha256)" in schema_sql or "sha256 TEXT UNIQUE" in schema_sql:
            return  # already migrated

        _logger.info("[V104.38] Migrating experiences table: adding UNIQUE(sha256)")

        # Step 1: Deduplicate existing rows (keep max(id) per sha256)
        # TẠI SAO: If we try to add UNIQUE with dupes present, the copy will fail.
        db_exec("""
            DELETE FROM experiences WHERE id NOT IN (
                SELECT MAX(id) FROM experiences
                WHERE sha256 IS NOT NULL
                GROUP BY sha256
            ) AND sha256 IS NOT NULL
        """)

        # Step 2: Create new table with UNIQUE constraint + all columns from old schema
        # [G4-phase3 FIX] Restore `applied_at TEXT` column — was accidentally
        # dropped from the migration's experiences_new schema (Task 9-D RE-13
        # finding). mark_applied() at line ~658 references this column via
        # `UPDATE experiences SET applied = 1, applied_at = ? WHERE id = ?`.
        # Without the column, post-migration SQLite raises
        # `OperationalError: no such column: applied_at` and the entire
        # mark_applied() call fails (lessons are read but never marked
        # applied → re-read every cycle → wasted DB I/O).
        db_exec("""
            CREATE TABLE IF NOT EXISTS experiences_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                question TEXT NOT NULL,
                entity TEXT,
                domain TEXT,
                source TEXT,
                ai_answer TEXT,
                real_value TEXT,
                verdict TEXT,
                error_type TEXT,
                error_reason TEXT,
                lesson_type TEXT NOT NULL,
                lesson_description TEXT NOT NULL,
                policy_action TEXT NOT NULL,
                policy_target TEXT,
                policy_value REAL,
                applied INTEGER DEFAULT 0,
                applied_at TEXT,
                sha256 TEXT UNIQUE,
                frame TEXT,
                final_verdict TEXT,
                verdict_detail TEXT,
                confidence REAL,
                cycle INTEGER
            )
        """)

        # Step 3: Copy deduped data — list COMMON columns explicitly.
        # [FIX-CRIT-135 BUG 6] TẠI SAO: the previous `INSERT OR IGNORE INTO
        # experiences_new SELECT * FROM experiences` FAILED because the column
        # counts differ:
        #   - old experiences (experience.py:82, 19 cols) has applied_at, no
        #     frame/final_verdict/verdict_detail/confidence/cycle, sha256 is
        #     non-UNIQUE.
        #   - new experiences_new (experience.py:157, 24 cols — was 23 cols
        #     before Task G4-phase3 restored `applied_at TEXT` to fix the
        #     mark_applied() crash, Task 9-D RE-13) adds
        #     frame/final_verdict/verdict_detail/confidence/cycle, and
        #     makes sha256 UNIQUE.
        #   - db_manager.py:376 may have ALREADY created experiences with the
        #     23-col schema (no UNIQUE) before this migration runs.
        # `SELECT *` returns N values from the source, but `INSERT` expects 24
        # (was 23 before Task G4-phase3 restored `applied_at`)
        # → "table experiences_new has X columns but Y values were supplied"
        # → INSERT fails → DROP TABLE experiences succeeds → DATA LOSS +
        # UNIQUE(sha256) never added → duplicates unbounded on next learn().
        # Fix: compute the column INTERSECTION dynamically via PRAGMA
        # table_info — robust against ALL source schema variants (19-col old,
        # 23-col db_manager, or any future variant). Only insert columns that
        # exist in BOTH tables. The new table's NOT NULL columns (timestamp,
        # question, lesson_type, lesson_description, policy_action) all exist
        # in the old schema too, so the intersection is non-empty and
        # satisfies NOT NULL constraints.
        src_cols = {
            row["name"]
            for row in db_query_all("PRAGMA table_info(experiences)")
        }
        dst_cols = {
            row["name"]
            for row in db_query_all("PRAGMA table_info(experiences_new)")
        }
        common = sorted(src_cols & dst_cols)
        if common:
            col_list = ", ".join(common)
            db_exec(
                f"INSERT OR IGNORE INTO experiences_new ({col_list}) "  # nosec B608 — input validated by SCP whitelist  # noqa: S608
                f"SELECT {col_list} FROM experiences"
            )
        # If common is empty (shouldn't happen — both schemas share id,
        # timestamp, question, etc.), fall through to DROP — old data is
        # lost but the migration still completes and UNIQUE(sha256) is added.

        # Step 4: Drop old, rename new
        db_exec("DROP TABLE experiences")
        db_exec("ALTER TABLE experiences_new RENAME TO experiences")

        # Step 5: Recreate indexes
        db_exec("CREATE INDEX IF NOT EXISTS idx_exp_lesson ON experiences(lesson_type)")
        db_exec("CREATE INDEX IF NOT EXISTS idx_exp_domain ON experiences(domain)")
        db_exec("CREATE INDEX IF NOT EXISTS idx_exp_applied ON experiences(applied)")

        _logger.info("[V104.38] Migration complete: UNIQUE(sha256) added to experiences")
    except Exception as e:
        logger.warning('_migrate_experiences_unique_sha256: Exception not handled: %s', e, exc_info=True)
        _logger.warning(f"[V104.38] experiences migration failed (non-fatal): {e}")


# ============================================================
# EXPERIENCE ENGINE — Tầng tổng hợp 3 trí nhớ -> Bài học -> Policy
# ============================================================
class ExperienceEngine:
    """
    Experience Engine — Tổng hợp Memory + Knowledge + ErrorHistory.

    3 khả năng:
      1. REFLECT  — Đọc 3 nguồn trí nhớ -> rút bài học
      2. LEARN    — Lưu bài học vào experiences table
      3. ENFORCE  — Áp dụng policy lên engine (thay đổi hành vi)

    5 loại bài học:
      1. SOURCE_RELIABILITY  — Source nào đáng tin? (dựa trên Knowledge times_verified)
      2. DOMAIN_BIAS         — Domain nào thường over/under-predict?
      3. ERROR_FREQUENCY     — Pattern lỗi lặp lại -> cảnh giác
      4. CONFIDENCE_TUNING   — Điều chỉnh confidence theo lịch sử
      5. ROUTE_OPTIMIZATION  — Ưu tiên route qua KB thay vì API
    """

    def __init__(self):
        init_db()
        init_experience_db()
        # Ensure knowledge table exists — [ROOT-FIX 1] uses canonical DDL imported
        # from db_manager (single source of truth). Previously experience.py
        # declared its own schema with `id INTEGER PK AUTOINCREMENT + UNIQUE`,
        # which conflicted with db_manager.py's `PRIMARY KEY (entity, attribute)`.
        # The migration guard in `_init_all_module_tables` rebuilds any legacy
        # table to canonical on `init_db()` call above; this CREATE is now a
        # no-op on already-migrated DBs and a safe canonical create on fresh DBs.
        try:
            db_exec(_KNOWLEDGE_CANONICAL_DDL)
        except Exception as e:
            logger.debug(f"[ROOT-FIX 1] experience.py knowledge create failed: {e}", exc_info=True)
        self.engine = SCPV13()

    # ============================================================
    # REFLECT — Đọc 3 nguồn -> rút bài học
    # ============================================================
    def reflect(self) -> list[dict]:
        """
        Phản tỉnh — đọc Memory + Knowledge + ErrorHistory -> tạo bài học.

        Returns: list of lessons, mỗi lesson có:
            lesson_type, lesson_description, policy_action, policy_target, policy_value
        """
        lessons = []

        # === Lesson 1: SOURCE_RELIABILITY ===
        # Đọc knowledge -> tính độ tin cậy mỗi source
        lessons.extend(self._reflect_source_reliability())

        # === Lesson 2: DOMAIN_BIAS ===
        # Đọc error_history -> tính bias mỗi domain
        lessons.extend(self._reflect_domain_bias())

        # === Lesson 3: ERROR_FREQUENCY ===
        # Đọc error_history -> tìm pattern lỗi lặp
        lessons.extend(self._reflect_error_frequency())

        # === Lesson 4: CONFIDENCE_TUNING ===
        # Đọc memory -> câu nào sai nhiều -> giảm confidence
        lessons.extend(self._reflect_confidence_tuning())

        # === Lesson 5: ROUTE_OPTIMIZATION ===
        # Đọc knowledge -> entity nào verified nhiều -> ưu tiên KB
        lessons.extend(self._reflect_route_optimization())

        return lessons

    def _reflect_source_reliability(self) -> list[dict]:
        """Phân tích độ tin cậy mỗi source từ knowledge."""
        lessons = []
        try:
            # [V65 FIX] Ensure times_wrong column exists (some legacy DBs missing it)
            try:
                db_exec("ALTER TABLE knowledge ADD COLUMN times_wrong INTEGER DEFAULT 0")
            except Exception as e:
                # Expected on legacy DBs that already have the column.
                logger.debug(f"knowledge.times_wrong column add skipped (likely already exists): {e}", exc_info=True)

            # Đọc từ knowledge (V14 Brain table)
            rows = db_query_all("""
                SELECT source, COUNT(*) as cnt,
                       AVG(confidence) as avg_conf,
                       SUM(times_verified) as total_verified,
                       SUM(times_wrong) as total_wrong
                FROM knowledge
                GROUP BY source
            """)
            for row in rows:
                src = row["source"]
                total_v = row["total_verified"] or 0
                total_w = row["total_wrong"] or 0
                avg_conf = row["avg_conf"] or 0

                if total_v + total_w > 0:
                    reliability = total_v / (total_v + total_w)
                else:
                    reliability = avg_conf

                if reliability > 0.9:
                    action = "PRIORITY_HIGH"
                    desc = f"Source '{src}' rất đáng tin (reliability={reliability:.0%}, verified={total_v}x)"
                elif reliability > 0.7:
                    action = "PRIORITY_NORMAL"
                    desc = f"Source '{src}' khá tin cậy (reliability={reliability:.0%})"
                elif reliability > 0.4:
                    action = "PRIORITY_LOW"
                    desc = f"Source '{src}' cần cẩn thận (reliability={reliability:.0%}, wrong={total_w}x)"
                else:
                    action = "DISABLE"
                    desc = f"Source '{src}' không đáng tin (reliability={reliability:.0%}, wrong={total_w}x) -> nên vô hiệu hóa"

                lessons.append({
                    "lesson_type": "SOURCE_RELIABILITY",
                    "lesson_description": desc,
                    "policy_action": action,
                    "policy_target": src,
                    "policy_value": str(round(reliability, 2)),
                    "entity": "", "domain": "", "source": src,
                    "ai_answer": "", "real_value": "", "verdict": "",
                    "error_type": "", "error_reason": "",
                })
        except Exception as e:
            logger.error(f"reflect_source_reliability error: {e}", exc_info=True)

        return lessons

    def _reflect_domain_bias(self) -> list[dict]:
        """Phân tích bias mỗi domain từ error_history."""
        lessons = []
        try:
            rows = db_query_all("""
                SELECT frame, COUNT(*) as total,
                       SUM(CASE WHEN final_verdict = 'FAIL' THEN 1 ELSE 0 END) as fails
                FROM error_history
                GROUP BY frame
                HAVING total >= 3
            """)
            for row in rows:
                domain = row["frame"]
                total = row["total"]
                fails = row["fails"] or 0
                fail_rate = fails / total if total > 0 else 0

                if fail_rate > 0.8:
                    action = "INCREASE_TOLERANCE"
                    desc = f"Domain '{domain}' có {fail_rate:.0%} FAIL rate ({fails}/{total}) -> tăng tolerance hoặc đổi checker"
                elif fail_rate > 0.5:
                    action = "ADD_BIAS_CORRECTION"
                    desc = f"Domain '{domain}' có {fail_rate:.0%} FAIL rate -> thêm bias correction"
                else:
                    action = "MAINTAIN"
                    desc = f"Domain '{domain}' hoạt động ổn ({fail_rate:.0%} FAIL rate)"

                lessons.append({
                    "lesson_type": "DOMAIN_BIAS",
                    "lesson_description": desc,
                    "policy_action": action,
                    "policy_target": domain,
                    "policy_value": str(round(fail_rate, 2)),
                    "entity": "", "domain": domain, "source": "",
                    "ai_answer": "", "real_value": "", "verdict": "",
                    "error_type": "", "error_reason": "",
                })
        except Exception as e:
            logger.error(f"reflect_domain_bias error: {e}", exc_info=True)

        return lessons

    def _reflect_error_frequency(self) -> list[dict]:
        """Tìm pattern lỗi lặp lại."""
        lessons = []
        try:
            rows = db_query_all("""
                SELECT question, COUNT(*) as cnt, final_verdict
                FROM error_history
                WHERE final_verdict = 'FAIL'
                GROUP BY question
                HAVING cnt >= 2
                ORDER BY cnt DESC
                LIMIT 10
            """)
            for row in rows:
                q = row["question"]
                cnt = row["cnt"]
                action = "FLAG_RECURRING"
                desc = f"Câu hỏi '{q[:50]}...' sai {cnt} lần -> cần fix parser hoặc thêm rule"

                lessons.append({
                    "lesson_type": "ERROR_FREQUENCY",
                    "lesson_description": desc,
                    "policy_action": action,
                    "policy_target": q[:50],
                    "policy_value": str(cnt),
                    "entity": "", "domain": "", "source": "",
                    "ai_answer": "", "real_value": "", "verdict": "FAIL",
                    "error_type": "recurring", "error_reason": f"Sai {cnt} lần",
                })
        except Exception as e:
            logger.error(f"reflect_error_frequency error: {e}", exc_info=True)

        return lessons

    def _reflect_confidence_tuning(self) -> list[dict]:
        """Điều chỉnh confidence dựa trên lịch sử memory."""
        lessons = []
        try:
            rows = db_query_all("""
                SELECT frame, COUNT(*) as total,
                       SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active
                FROM memory
                GROUP BY frame
                HAVING total >= 3
            """)
            for row in rows:
                domain = row["frame"]
                total = row["total"]
                active = row["active"] or 0
                recover_rate = 1 - (active / total) if total > 0 else 0

                if recover_rate < 0.3:
                    action = "LOWER_CONFIDENCE"
                    desc = f"Domain '{domain}' chỉ {recover_rate:.0%} recovery rate -> giảm confidence cho predictions"
                else:
                    action = "MAINTAIN_CONFIDENCE"
                    desc = f"Domain '{domain}' recovery rate {recover_rate:.0%} -> OK"

                lessons.append({
                    "lesson_type": "CONFIDENCE_TUNING",
                    "lesson_description": desc,
                    "policy_action": action,
                    "policy_target": domain,
                    "policy_value": str(round(recover_rate, 2)),
                    "entity": "", "domain": domain, "source": "",
                    "ai_answer": "", "real_value": "", "verdict": "",
                    "error_type": "", "error_reason": "",
                })
        except Exception as e:
            logger.error(f"reflect_confidence_tuning error: {e}", exc_info=True)

        return lessons

    def _reflect_route_optimization(self) -> list[dict]:
        """Ưu tiên route qua KB cho entities đã verified nhiều."""
        lessons = []
        try:
            rows = db_query_all("""
                SELECT entity, attribute, times_verified, confidence
                FROM knowledge
                WHERE times_verified >= 3 AND confidence >= 0.8
                ORDER BY times_verified DESC
                LIMIT 10
            """)
            for row in rows:
                entity = row["entity"]
                attr = row["attribute"]
                times_v = row["times_verified"]
                conf = row["confidence"]

                action = "USE_KB_FIRST"
                desc = f"Entity '{entity}.{attr}' verified {times_v}x (conf={conf:.0%}) -> ưu tiên KB, không cần API"

                lessons.append({
                    "lesson_type": "ROUTE_OPTIMIZATION",
                    "lesson_description": desc,
                    "policy_action": action,
                    "policy_target": f"{entity}.{attr}",
                    "policy_value": str(times_v),
                    "entity": entity, "domain": attr, "source": "",
                    "ai_answer": "", "real_value": "", "verdict": "",
                    "error_type": "", "error_reason": "",
                })
        except Exception as e:
            logger.error(f"reflect_route_optimization error: {e}", exc_info=True)

        return lessons

    # ============================================================
    # LEARN — Lưu bài học vào experiences table
    # ============================================================
    def learn(self, lessons: list[dict]) -> int:
        """[V89 OPT] Lưu bài học vào SQLite — batch INSERT."""
        if not lessons:
            return 0

        rows = []
        for lesson in lessons:
            ts = datetime.now().astimezone().isoformat()
            # [V104.35 #74] TẠI SAO: sha256 included timestamp → every call unique
            # → no dedup → unbounded experiences table growth. Fix: hash on lesson
            # identity (type+target+action), not timestamp. ts stored separately.
            sha256 = hashlib.sha256(
                f"{lesson['lesson_type']}|{lesson['policy_target']}|{lesson.get('policy_action', '')}".encode()
            ).hexdigest()
            rows.append((
                ts,
                lesson.get("question", ""),
                lesson.get("entity", ""),
                lesson.get("domain", ""),
                lesson.get("source", ""),
                lesson.get("ai_answer", ""),
                lesson.get("real_value", ""),
                lesson.get("verdict", ""),
                lesson.get("error_type", ""),
                lesson.get("error_reason", ""),
                lesson["lesson_type"],
                lesson["lesson_description"],
                lesson["policy_action"],
                lesson["policy_target"],
                lesson["policy_value"],
                sha256,
            ))

        try:
            from scp.core.db_manager import _db_lock, get_db
            sql = """INSERT OR IGNORE INTO experiences
                (timestamp, question, entity, domain, source, ai_answer, real_value,
                 verdict, error_type, error_reason, lesson_type, lesson_description,
                 policy_action, policy_target, policy_value, sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            with _db_lock:
                conn = get_db()
                conn.executemany(sql, rows)
                if conn.in_transaction:
                    conn.commit()
            return len(rows)
        except Exception as e:
            logger.error(f"Experience batch save error: {e}", exc_info=True)
            # Fallback: individual inserts
            saved = 0
            for row in rows:
                try:
                    db_exec("""INSERT INTO experiences
                        (timestamp, question, entity, domain, source, ai_answer, real_value,
                         verdict, error_type, error_reason, lesson_type, lesson_description,
                         policy_action, policy_target, policy_value, applied, sha256)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""", row)
                    saved += 1
                except Exception as e:
                    logger.debug(f"experience row insert failed (sha256 dedup or schema mismatch): {e}", exc_info=True)
            return saved

    # ============================================================
    # ENFORCE — Áp dụng policy lên engine
    # ============================================================
    def get_active_policies(self) -> dict[str, Any]:
        """
        Trả về policies hiện tại để engine áp dụng.

        Returns:
            {
                "source_priorities": {source: priority_level},
                "domain_tolerances": {domain: tolerance_multiplier},
                "kb_priorities": [entity.attribute, ...],
                "recurring_errors": [question, ...],
                "confidence_adjustments": {domain: adjustment},
            }
        """
        policies = {
            "source_priorities": {},
            "domain_tolerances": {},
            "kb_priorities": [],
            "recurring_errors": [],
            "confidence_adjustments": {},
        }

        applied_ids = []
        try:
            rows = db_query_all("""
                SELECT id, lesson_type, policy_action, policy_target, policy_value
                FROM experiences
                WHERE applied = 0
                ORDER BY timestamp DESC
            """)

            for row in rows:
                ltype = row["lesson_type"]
                action = row["policy_action"]
                target = row["policy_target"]
                value = row["policy_value"]
                applied_ids.append(row["id"])

                if ltype == "SOURCE_RELIABILITY":
                    policies["source_priorities"][target] = {
                        "action": action,
                        "reliability": float(value) if value else 0,
                    }
                elif ltype == "DOMAIN_BIAS":
                    if action == "INCREASE_TOLERANCE":
                        policies["domain_tolerances"][target] = 2.0  # Double tolerance
                    elif action == "ADD_BIAS_CORRECTION":
                        policies["domain_tolerances"][target] = 1.5
                elif ltype == "ROUTE_OPTIMIZATION":
                    if action == "USE_KB_FIRST":
                        policies["kb_priorities"].append(target)
                elif ltype == "ERROR_FREQUENCY":
                    if action == "FLAG_RECURRING":
                        policies["recurring_errors"].append(target)
                elif ltype == "CONFIDENCE_TUNING":
                    if action == "LOWER_CONFIDENCE":
                        policies["confidence_adjustments"][target] = 0.5  # Reduce by half
        except Exception as e:
            logger.error(f"get_active_policies error: {e}", exc_info=True)

        # [V93.6] Return lesson ids so caller can mark_applied() after persisting policies
        policies["_lesson_ids"] = applied_ids
        return policies

    def mark_applied(self, lesson_ids: list[int]):
        """Đánh dấu bài học đã áp dụng."""
        for lid in lesson_ids:
            db_exec("UPDATE experiences SET applied = 1, applied_at = ? WHERE id = ?",
                    (datetime.now().astimezone().isoformat(), lid))

    # ============================================================
    # RUN — 1 cycle phản tỉnh + học
    # ============================================================
    def run_reflection_cycle(self) -> dict:
        """Chạy 1 cycle: Reflect -> Learn -> Report."""
        print(f"\n{'='*60}")
        print("  [BRAIN] EXPERIENCE ENGINE — REFLECTION CYCLE")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # Step 1: Reflect
        print("\n  [DOC] STEP 1: REFLECT — Đọc 3 nguồn trí nhớ")
        memory_count = db_query_one("SELECT COUNT(*) as cnt FROM memory")["cnt"]
        error_count = db_query_one("SELECT COUNT(*) as cnt FROM error_history")["cnt"]
        try:
            knowledge_count = db_query_one("SELECT COUNT(*) as cnt FROM knowledge")["cnt"]
        except Exception:
            logger.warning('ExperienceEngine.run_reflection_cycle: Exception not handled', exc_info=True)
            knowledge_count = 0

        print(f"     Memory:       {memory_count} entries")
        print(f"     Knowledge:    {knowledge_count} entries")
        print(f"     ErrorHistory: {error_count} entries")

        lessons = self.reflect()
        print(f"\n  ? STEP 2: LEARN — Rút {len(lessons)} bài học")

        # Group by type
        by_type = defaultdict(int)
        for lesson in lessons:
            by_type[lesson["lesson_type"]] += 1
            print(f"     [{lesson['lesson_type']:25s}] {lesson['lesson_description'][:70]}")

        # Step 2: Save
        saved = self.learn(lessons)
        print(f"\n  ? Saved {saved} lessons to experiences table")

        # Step 3: Active policies
        policies = self.get_active_policies()
        # [V104.35 #73] TẠI SAO: mark_applied defined but never called → lessons
        # re-read every cycle → wasted DB I/O. Fix: mark them applied now.
        lesson_ids = policies.get("_lesson_ids", [])
        policy_handoff = {
            "status": "NO_UNAPPLIED_LESSONS",
            "eligible_lesson_count": 0,
            "applied_count": 0,
        }
        if lesson_ids:
            try:
                from scp.core.db_manager import DATA_DIR, DB_PATH
                from scp.core.policy_materializer import PolicyMaterializer
                materializer = PolicyMaterializer(db_path=DB_PATH, data_dir=DATA_DIR)
                candidate = materializer.materialize_candidate()
                meta = candidate.get("_meta", {})
                eligible_ids = [int(x) for x in meta.get("eligible_lesson_ids", [])]
                if eligible_ids:
                    promoted = materializer.promote()
                    applied_count = materializer.mark_applied(eligible_ids)
                    materializer.record_applied(eligible_ids, applied_count)
                    policy_handoff = {
                        "status": "APPLIED",
                        "eligible_lesson_count": len(eligible_ids),
                        "applied_count": applied_count,
                        "policy_sha256": promoted.get("policy_sha256"),
                    }
                else:
                    policy_handoff = {
                        "status": "NO_ELIGIBLE_POLICY_LESSONS",
                        "eligible_lesson_count": 0,
                        "applied_count": 0,
                        "lessons_seen": meta.get("lesson_count_seen", 0),
                    }
            except Exception as e:
                logger.error(f"Policy handoff failed; lessons remain unapplied: {e}", exc_info=True)
                policy_handoff = {
                    "status": "HANDOFF_FAILED",
                    "eligible_lesson_count": 0,
                    "applied_count": 0,
                    "error": type(e).__name__,
                }
        print("\n  ??  STEP 3: ACTIVE POLICIES")
        print(f"     Source priorities: {len(policies['source_priorities'])} sources")
        for src, info in policies["source_priorities"].items():
            print(f"       - {src}: {info['action']} (reliability={info['reliability']:.0%})")
        print(f"     Domain tolerances: {len(policies['domain_tolerances'])} domains")
        print(f"     KB priorities: {len(policies['kb_priorities'])} entities")
        print(f"     Recurring errors: {len(policies['recurring_errors'])} questions")
        print(f"     Confidence adjustments: {len(policies['confidence_adjustments'])} domains")

        # Summary
        report = {
            "memory_entries": memory_count,
            "knowledge_entries": knowledge_count,
            "error_entries": error_count,
            "lessons_reflected": len(lessons),
            "lessons_saved": saved,
            "lessons_by_type": dict(by_type),
            "active_policies": {
                "source_priorities": len(policies["source_priorities"]),
                "domain_tolerances": len(policies["domain_tolerances"]),
                "kb_priorities": len(policies["kb_priorities"]),
                "recurring_errors": len(policies["recurring_errors"]),
                "confidence_adjustments": len(policies["confidence_adjustments"]),
            },
            "policies": policies,
            "policy_handoff": policy_handoff,
        }

        print("\n  [STATS] SUMMARY")
        print(f"     Reflected: {len(lessons)} lessons from {memory_count + knowledge_count + error_count} total memories")
        print(f"     Saved: {saved} new lessons")
        print(f"     Active policies: {sum(report['active_policies'].values())}")
        print(f"{'='*60}")

        return report

    def get_stats(self) -> dict:
        """Thống kê experiences."""
        try:
            total = db_query_one("SELECT COUNT(*) as cnt FROM experiences")["cnt"]
            applied = db_query_one("SELECT COUNT(*) as cnt FROM experiences WHERE applied = 1")["cnt"]
            by_type = {}
            for r in db_query_all("SELECT lesson_type, COUNT(*) as cnt FROM experiences GROUP BY lesson_type"):
                by_type[r["lesson_type"]] = r["cnt"]
            return {"total_experiences": total, "applied": applied, "by_type": by_type}
        except Exception:
            logger.warning('ExperienceEngine.get_stats: Exception not handled', exc_info=True)
            return {"total_experiences": 0, "applied": 0, "by_type": {}}


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="SCP V14 Experience Engine")
    parser.add_argument("--lien-tuc", action="store_true", help="Chạy 24/7")
    parser.add_argument("--chinh-sach", action="store_true", help="Xem policies hiện tại")
    parser.add_argument("--nghi", type=int, default=0, help="Giây nghỉ (mặc định 0)")
    args = parser.parse_args()

    exp = ExperienceEngine()

    if args.chinh_sach:
        policies = exp.get_active_policies()
        print(json.dumps(policies, indent=2, ensure_ascii=False, default=str))
        return

    if args.lien_tuc:
        running = [True]
        def handler(sig, frame):
            running[0] = False
        signal.signal(signal.SIGINT, handler)

        cycle = 0
        while running[0]:
            cycle += 1
            print(f"\n  Cycle {cycle}")
            exp.run_reflection_cycle()
            if args.nghi > 0 and running[0]:
                time.sleep(args.nghi)
        print(f"\n  Đã dừng. {cycle} cycles.")
    else:
        exp.run_reflection_cycle()
