"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

#!/usr/bin/env python3
"""
SCP V14 META-COGNITION — Tầng trên cùng quản lý toàn bộ hệ thống.

5 tầng còn thiếu (theo audit):
  1. GOAL MEMORY     — Nhớ mission dài hạn, đã thử gì, còn thiếu gì
  2. CURIOSITY ENGINE — Sinh câu hỏi dựa trên Information Gain (không random)
  3. WORLD MODEL      — Graph quan hệ (không chỉ fact riêng lẻ)
  4. ABSTRACTION      — Lesson -> Principle -> Policy
  5. IDENTITY         — Mission, boundary, values, forbidden goals

Luồng Meta-Cognition:
    Mission (tôi là ai? phục vụ ai?)
        ?
    Goal (mục tiêu hiện tại là gì?)
        ?
    Curiosity (đâu là câu hỏi có Information Gain cao nhất?)
        ?
    Brain (kiến thức hiện có)
        ?
    Experience (bài học từ quá khứ)
        ?
    Prediction (dự đoán -> chờ -> verify)
        ?
    Reality (kiểm chứng thực tế)
        ?
    Mission Update (đã tiến bộ? cần đổi hướng?)

Chạy:
    python v14_meta.py                    # Chạy 1 meta-cycle
    python v14_meta.py --lien-tuc          # 24/7
    python v14_meta.py --hoi "Mission"     # Xem mission hiện tại
    python v14_meta.py --world             # Xem world model graph
"""
# [G3-CONSOLIDATE RE-17] Meta namespace status:
# - This file: MetaCognitionEngine + 5 sub-engines (GoalMemory, CuriosityEngine,
#   WorldModel, AbstractionEngine, Identity) — 929 LOC, 24/7-only (run_247.py).
# - NOT related to: scp/meta/scp_meta.py (council), scp/meta/meta_schema.py (DDL).
# - The 'meta' namespace contains 3 UNRELATED things:
#   1. meta.py — MetaCognitionEngine (5 sub-engines, 929 LOC)
#   2. scp_meta.py — SCPMeta council (4 enums + SCPMetaReview dataclass, 61 LOC)
#   3. meta_schema.py — DDL init (5 meta_* tables, 108 LOC)
# - No rename attempted (would break imports) — this marker documents reality.

import argparse
import os
import random
import signal
import sys
import time
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import logging

from scp.core.db_manager import db_exec, db_query_all, db_query_one, init_db
from scp.core.scp_v14 import SCPV14 as SCPV13

# [Task 7-A Modularity] init_meta_db tách ra meta_schema.py (giảm meta.py từ 1018 → 925 LOC)
from scp.meta.meta_schema import init_meta_db

logger = logging.getLogger("scp.meta")


# ============================================================
# INIT — Tạo tables cho Meta-Cognition (implementation in meta_schema.py)
# ============================================================
# (init_meta_db được import từ meta_schema.py — single source of truth)


# [G3-CONSOLIDATE RE-18] Sub-engine usage (5 sub-engines defined below):
# - GoalMemory        (line 104)   — DEAD in /ask; LIVE in 24/7 (engine_parts/scpv14_process_mixin.py:271
#                                     creates one to log "Reduce error rate" goals after healing)
# - CuriosityEngine   (line 175)   — DEAD in /ask; only MetaCognitionEngine.run_meta_cycle() + run_247.py
# - WorldModel        (line 462)   — DEAD in /ask; only MetaCognitionEngine.run_meta_cycle() + run_247.py
# - AbstractionEngine (line 585)   — DEAD in /ask; only MetaCognitionEngine.run_meta_cycle() + run_247.py
# - Identity          (line 743)   — DEAD in /ask; only MetaCognitionEngine.run_meta_cycle() + run_247.py
#                                     (NOTE: class is named `Identity`, not `IdentityManager` — task brief typo)
# - MetaCognitionEngine (line 790) — DEAD in /ask; only engine.py:228 (24/7) + run_247.py:161 (24/7).
#                                     /ask path uses scp.core.scp_v14.SCPV14 (stub) via judge.py:15, NOT engine.py:SCPV14.
# grep evidence (Task M3 spec): `rg -n "CuriosityEngine|WorldModel|AbstractionEngine|IdentityManager|GoalMemory"
#   scp/runtime/judge.py scp/runtime/judge_parts/ scp/api_server.py` → 0 matches.
# 5/5 sub-engines are 24/7-only, NOT /ask. This file is dead on the /ask path.


# ============================================================
# 1. GOAL MEMORY — Quản lý mission + goals dài hạn
# ============================================================
class GoalMemory:
    """
    Goal Memory — Nhớ mission, goals, đã thử gì, còn thiếu gì.

    3 cấp:
      - Mission: mục tiêu tối cao (không đổi)
      - Goal: mục tiêu dài hạn (thay đổi theo thời gian)
      - Sub-goal: mục tiêu ngắn hạn (hoàn thành được)

    Ví dụ:
      Mission: "Verify reality claims"
      Goal: "Cover 50+ domains with verified facts"
      Sub-goal: "Add 5 new chemistry compounds this week"
    """

    def add_goal(self, description: str, goal_type: str = "goal",
                 priority: int = 5, parent_id: int | None = None) -> int:
        """Thêm goal mới."""
        ts = datetime.now().astimezone().isoformat()
        db_exec("""
            INSERT INTO meta_goals (type, description, status, priority, created_at, parent_id)
            VALUES (?, ?, 'active', ?, ?, ?)
        """, (goal_type, description, priority, ts, parent_id))
        row = db_query_one("SELECT last_insert_rowid() as id")  # [V104.32 #20] RACE: see reverify_scheduler.py:122 for fix pattern
        return row["id"]

    def update_progress(self, goal_id: int, progress: float, notes: str = ""):
        """Cập nhật tiến độ goal."""
        db_exec("""
            UPDATE meta_goals SET progress = ?, notes = ?, updated_at = ?
            WHERE id = ?
        """, (progress, notes, datetime.now().astimezone().isoformat(), goal_id))

    def complete_goal(self, goal_id: int, notes: str = ""):
        """Đánh dấu goal hoàn thành."""
        db_exec("""
            UPDATE meta_goals SET status = 'completed', progress = 1.0,
            notes = ?, updated_at = ? WHERE id = ?
        """, (notes, datetime.now().astimezone().isoformat(), goal_id))

    def get_active_goals(self) -> list[dict]:
        """Lấy tất cả goals đang active."""
        return db_query_all(
            "SELECT * FROM meta_goals WHERE status = 'active' ORDER BY priority DESC, created_at"
        )

    def get_mission(self) -> str:
        """Lấy mission hiện tại."""
        row = db_query_one("SELECT value FROM meta_identity WHERE key = 'mission'")
        return row["value"] if row else "Unknown"

    def get_long_term_goal(self) -> str:
        """Lấy long-term goal."""
        row = db_query_one("SELECT value FROM meta_identity WHERE key = 'long_term_goal'")
        return row["value"] if row else "Unknown"

    def get_stats(self) -> dict:
        try:
            total = db_query_one("SELECT COUNT(*) as cnt FROM meta_goals")["cnt"]
            active = db_query_one("SELECT COUNT(*) as cnt FROM meta_goals WHERE status='active'")["cnt"]
            completed = db_query_one("SELECT COUNT(*) as cnt FROM meta_goals WHERE status='completed'")["cnt"]
            avg_progress = db_query_one("SELECT AVG(progress) as avg FROM meta_goals WHERE status='active'")["avg"] or 0
            return {"total": total, "active": active, "completed": completed,
                    "avg_progress": round(avg_progress, 2)}
        except Exception as exc:
            logger.warning("meta: goal stats query failed, reporting zeros: %s", exc, exc_info=True)
            return {"total": 0, "active": 0, "completed": 0, "avg_progress": 0}


# ============================================================
# 2. CURIOSITY ENGINE — Information Gain based question selection
# ============================================================
class CuriosityEngine:
    """
    Curiosity Engine — Sinh câu hỏi dựa trên Information Gain.

    Không random. Tính đâu là câu hỏi đáng hỏi nhất.

    5 loại curiosity:
      1. GAP         — Kiến thức còn thiếu (entity chưa có trong KB)
      2. CONTRADICTION — Hai nguồn cho kết quả khác nhau
      3. NOVELTY     — Entity mới chưa từng hỏi
      4. ANOMALY     — Value bất thường (>2 sigma so với baseline)
      5. EDGE_CASE   — Biên giới của domain (vd: nhiệt độ -89°C ở Nam Cực)

    Information Gain = f(gap_size, contradiction_severity, novelty_score, anomaly_z_score)
    """

    def generate_curious_questions(self, n: int = 10) -> list[dict]:
        """Sinh n câu hỏi có Information Gain cao nhất."""
        questions = []

        # 1. GAP — entity chưa có trong knowledge_summaries
        questions.extend(self._find_gaps(n // 3))

        # 2. CONTRADICTION — same entity, different values
        questions.extend(self._find_contradictions(n // 5))

        # 3. NOVELTY — entity mới chưa hỏi
        questions.extend(self._find_novelties(n // 3))

        # 4. ANOMALY — values bất thường
        questions.extend(self._find_anomalies(n // 5))

        # 5. EDGE_CASE — biên giới domain
        questions.extend(self._find_edge_cases(n // 5))

        # Sort by Information Gain (descending)
        questions.sort(key=lambda q: q.get("information_gain", 0), reverse=True)

        return questions[:n]

    def _find_gaps(self, n: int) -> list[dict]:
        """Tìm kiến thức còn thiếu.
         Disabled GeneratorKhamPha (removed from pipeline V67+).
        Now: find gaps from external_questions not yet in knowledge.
        """
        questions = []
        try:
            #  Find entities in external_questions that are NOT in knowledge table
            # Was: used GeneratorKhamPha.COMPOUNDS/CITIES/COINS (synthetic, removed V67)
            # Now: query external_questions for real entities not yet learned
            rows = db_query_all("""
                SELECT eq.question, eq.domain, eq.source
                FROM external_questions eq
                WHERE eq.used = 1
                  AND eq.question NOT IN (SELECT question FROM meta_curiosity)
                  AND LOWER(eq.question) NOT IN (
                      SELECT LOWER(SUBSTR(entity, 1, 100)) FROM knowledge
                  )
                ORDER BY eq.fetched_at DESC
                LIMIT ?
            """, (n,))
            for row in rows:
                questions.append({
                    "question": row['question'][:200],
                    "entity": row['question'][:30],
                    "domain": row.get('domain', 'gap') or 'gap',
                    "information_gain": 0.8,
                    "curiosity_type": "gap",
                    "reason": f"Entity '{row['question'][:30]}' chưa có trong Knowledge Base",
                })
        except Exception as e:
            logger.debug(f"Curiosity gap error: {e}", exc_info=True)

        return questions

    def _find_contradictions(self, n: int) -> list[dict]:
        """Tìm mâu thuẫn — same entity, different values.
        [V84 FIX] Dedup was BROKEN — SQL compared full question vs truncated (80 chars).
        Now: Python-level dedup — build exact string, check if exists.
        """
        questions = []
        try:
            # Get FAIL questions from error_history (grouped)
            rows = db_query_all("""
                SELECT e.question, e.frame, e.final_verdict, COUNT(*) as conflict_count
                FROM error_history e
                WHERE e.final_verdict = 'FAIL'
                GROUP BY e.question
                HAVING conflict_count > 0
                ORDER BY conflict_count DESC
                LIMIT ?
            """, (n * 5,))  # Get 5x more than needed (will filter in Python)

            for row in rows:
                # Build the EXACT same string that will be saved
                orig_q = row['question'].replace('Kiểm tra lại: ', '')
                q_text = f"Kiểm tra lại: {orig_q[:80]}"

                #  Python-level dedup — check if EXACT string exists
                existing = db_query_one(
                    "SELECT id FROM meta_curiosity WHERE question = ?",
                    (q_text,)
                )
                if existing:
                    continue  # Already exists — skip!

                # Also check if original question (without prefix) exists
                existing_orig = db_query_one(
                    "SELECT id FROM meta_curiosity WHERE question = ?",
                    (orig_q[:200],)
                )
                if existing_orig:
                    continue

                questions.append({
                    "question": q_text,
                    "entity": row["question"][:30],
                    "domain": row["frame"] or "unknown",
                    "information_gain": 0.9,
                    "curiosity_type": "contradiction",
                    "reason": f"{row['conflict_count']} FAIL verdicts on same question",
                })
                if len(questions) >= n:
                    break
        except Exception as e:
            logger.debug(f"[V104.37] meta/meta.py: e={e}", exc_info=True)
        return questions

    def _find_novelties(self, n: int) -> list[dict]:
        """Tìm entity mới — chưa từng hỏi.
         Disabled GeneratorKhamPha (removed from pipeline V67+).
        Now: find entities in external_questions not yet processed.
        """
        questions = []
        try:
            #  Find new entities from external_questions (real web questions)
            rows = db_query_all("""
                SELECT question, domain, source
                FROM external_questions
                WHERE used = 0
                ORDER BY fetched_at DESC
                LIMIT ?
            """, (n,))
            for row in rows:
                # Check not already in meta_curiosity
                existing = db_query_one(
                    "SELECT id FROM meta_curiosity WHERE question = ?",
                    (row['question'][:200],)
                )
                if existing:
                    continue
                questions.append({
                    "question": row['question'][:200],
                    "entity": row['question'][:30],
                    "domain": row.get('domain', 'novelty') or 'novelty',
                    "information_gain": 0.6,
                    "curiosity_type": "novelty",
                    "reason": f"Câu hỏi mới từ {row.get('source', 'web')}",
                })
        except Exception as e:
            logger.debug(f"Novelty error: {e}", exc_info=True)
        return questions

    def _find_anomalies(self, n: int) -> list[dict]:
        """Tìm values bất thường."""
        questions = []
        try:
            # [V76 DEDUP FIX] Exclude anomaly questions already asked
            # Was: same anomaly question sinh lại mỗi cycle (anomaly_count tăng dần)
            # Now: check if "Tại sao X có Y anomalies?" already asked
            rows = db_query_all("""
                SELECT question, frame, error_type, COUNT(*) as anomaly_count
                FROM error_history
                WHERE final_verdict = 'FAIL' AND error_type != ''
                GROUP BY frame, error_type
                ORDER BY anomaly_count DESC
                LIMIT ?
            """, (n,))
            for row in rows:
                #  Build question, check if already in meta_curiosity
                q_text = f"Tại sao {row['frame']} có {row['anomaly_count']} anomalies?"
                #  Skip if EXACT question already exists (regardless of asked status)
                # Was: only check asked=1 → duplicates generated before being asked
                existing = db_query_one(
                    "SELECT id FROM meta_curiosity WHERE question = ?",
                    (q_text,)
                )
                if existing:
                    continue
                #  Skip if any "Tại sao {frame} có" question already exists
                existing_pattern = db_query_one(
                    "SELECT id FROM meta_curiosity WHERE question LIKE ?",
                    (f"Tại sao {row['frame']} có%anomalies?",)
                )
                if existing_pattern:
                    continue
                questions.append({
                    "question": q_text,
                    "entity": row["frame"] or "unknown",
                    "domain": row["error_type"] or "unknown",
                    "information_gain": 0.85,
                    "curiosity_type": "anomaly",
                    "reason": f"{row['anomaly_count']} anomalies in frame={row['frame']}",
                })
        except Exception as e:
            logger.debug(f"[V104.37] meta/meta.py: e={e}", exc_info=True)
        return questions

    def _find_edge_cases(self, n: int) -> list[dict]:
        """Tìm edge cases — biên giới domain."""
        questions = []
        edge_cases = [
            ("Nhiệt độ hiện tại tại Antarctica là bao nhiêu?", "Antarctica", "weather", 0.7,
             "Edge case: nhiệt độ cực thấp"),
            ("Khối lượng phân tử uranium bằng bao nhiêu?", "uranium", "chemistry", 0.7,
             "Edge case: nguyên tố nặng"),
            ("Giá tether hiện tại là bao nhiêu USD?", "tether", "crypto", 0.6,
             "Edge case: stablecoin (giá ~$1)"),
            ("Chuyển đổi 1 USD sang CLP", "USD_CLP", "currency", 0.6,
             "Edge case: tỉ giá cao (~900 CLP/USD)"),
        ]
        random.shuffle(edge_cases)
        for q, entity, domain, ig, reason in edge_cases[:n]:
            questions.append({
                "question": q, "entity": entity, "domain": domain,
                "information_gain": ig, "curiosity_type": "edge_case", "reason": reason,
            })
        return questions

    def _build_question(self, entity: str, attribute: str) -> str:
        """Xây câu hỏi từ entity + attribute."""
        builders = {
            "molecular_weight": lambda e: f"Khối lượng phân tử {e} bằng bao nhiêu?",
            "temperature": lambda e: f"Nhiệt độ hiện tại tại {e} là bao nhiêu?",
            "price_usd": lambda e: f"Giá {e} hiện tại là bao nhiêu USD?",
        }
        return builders.get(attribute, lambda e: f"Thông tin về {e}?")(entity)

    def save_question(self, question: dict):
        """Lưu câu hỏi curiosity vào DB.
        [V85 FIX] THE ACTUAL ROOT CAUSE OF ALL DUPLICATES:
        This function had NO duplicate check! Every call to save_question()
        just INSERTed blindly. All dedup in _find_contradictions/_find_gaps
        was useless because save_question didn't check before inserting.

        Fix: CHECK if question already exists BEFORE INSERT.
        If exists → skip (don't insert duplicate).
        """
        #  THE REAL FIX — check before insert
        q_text = question["question"]
        existing = db_query_one(
            "SELECT id FROM meta_curiosity WHERE question = ?",
            (q_text,)
        )
        if existing:
            return  # Already exists — DON'T INSERT!

        ts = datetime.now().astimezone().isoformat()
        db_exec("""
            INSERT INTO meta_curiosity
            (timestamp, question, entity, domain, information_gain, curiosity_type, reason, asked)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (ts, q_text, question.get("entity", ""),
              question.get("domain", ""), question.get("information_gain", 0),
              question.get("curiosity_type", ""), question.get("reason", "")))

    def mark_asked(self, question_id: int, result: str = ""):
        """Đánh dấu câu hỏi đã hỏi."""
        db_exec("""
            UPDATE meta_curiosity SET asked = 1, asked_at = ?, result = ? WHERE id = ?
        """, (datetime.now().astimezone().isoformat(), result, question_id))

    def get_stats(self) -> dict:
        try:
            total = db_query_one("SELECT COUNT(*) as cnt FROM meta_curiosity")["cnt"]
            asked = db_query_one("SELECT COUNT(*) as cnt FROM meta_curiosity WHERE asked=1")["cnt"]
            by_type = {}
            for r in db_query_all("SELECT curiosity_type, COUNT(*) as cnt FROM meta_curiosity GROUP BY curiosity_type"):
                by_type[r["curiosity_type"]] = r["cnt"]
            return {"total_questions": total, "asked": asked, "by_type": by_type}
        except Exception as exc:
            logger.warning("meta: curiosity stats query failed, reporting zeros: %s", exc, exc_info=True)
            return {"total_questions": 0, "asked": 0, "by_type": {}}


# ============================================================
# 3. WORLD MODEL — Graph quan hệ
# ============================================================
class WorldModel:
    """
    World Model — Graph quan hệ giữa các entities.

    Không chỉ lưu fact riêng lẻ. Lưu quan hệ:
        CO2 -> is_a -> gas
        CO2 -> affects -> climate
        gas -> type_of -> matter
        climate -> influences -> weather

    Cho phép suy luận nhiều bước:
        CO2 -> affects -> climate -> influences -> weather
        -> "CO2 ảnh hưởng thời tiết"
    """

    def add_relation(self, subject: str, relation: str, obj: str,
                     confidence: float = 0.5, source: str = "") -> bool:
        """Thêm 1 quan hệ vào graph."""
        ts = datetime.now().astimezone().isoformat()
        try:
            # Upsert — nếu quan hệ đã tồn tại, tăng times_verified + confidence
            existing = db_query_one(
                "SELECT * FROM meta_world_model WHERE subject = ? AND relation = ? AND object = ?",
                (subject.lower(), relation, obj.lower())
            )
            if existing:
                new_conf = min(1.0, existing["confidence"] + 0.1)
                db_exec("""
                    UPDATE meta_world_model
                    SET confidence = ?, times_verified = ?, timestamp = ?
                    WHERE subject = ? AND relation = ? AND object = ?
                """, (new_conf, existing["times_verified"] + 1, ts,
                      subject.lower(), relation, obj.lower()))
                return False  # Updated, not new
            else:
                db_exec("""
                    INSERT INTO meta_world_model (subject, relation, object, confidence, source, timestamp, times_verified)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (subject.lower(), relation, obj.lower(), confidence, source, ts))
                return True  # New relation
        except Exception as e:
            logger.error(f"WorldModel add_relation error: {e}", exc_info=True)
            return False

    def get_relations(self, subject: str | None = None, relation: str | None = None,
                      obj: str | None = None) -> list[dict]:
        """Truy vấn quan hệ."""
        conditions = []
        params = []
        if subject:
            conditions.append("subject = ?")
            params.append(subject.lower())
        if relation:
            conditions.append("relation = ?")
            params.append(relation)
        if obj:
            conditions.append("object = ?")
            params.append(obj.lower())

        where = " AND ".join(conditions) if conditions else "1=1"
        return db_query_all(f"SELECT * FROM meta_world_model WHERE {where} ORDER BY confidence DESC", tuple(params))  # nosec B608 — input validated by SCP whitelist  # noqa: S608

    def get_neighbors(self, entity: str) -> dict[str, list[str]]:
        """Lấy hàng xóm của 1 entity (graph traversal)."""
        neighbors = defaultdict(list)
        rows = db_query_all(
            "SELECT relation, object FROM meta_world_model WHERE subject = ? AND confidence >= 0.5",
            (entity.lower(),)
        )
        for row in rows:
            neighbors[row["relation"]].append(row["object"])
        return dict(neighbors)

    def infer_chain(self, start: str, max_depth: int = 3) -> list[list[str]]:
        """
        Suy luận nhiều bước: start -> ? -> ? -> ?
        Trả về list of chains.
        """
        chains = [[start.lower()]]
        for _ in range(max_depth):
            new_chains = []
            for chain in chains:
                last = chain[-1]
                neighbors = self.get_neighbors(last)
                for relation, objects in neighbors.items():
                    for obj in objects:
                        if obj not in chain:  # Avoid cycles
                            new_chains.append(chain + [f"--{relation}-->", obj])
            if not new_chains:
                break
            chains = new_chains[:20]  # Limit
        return chains

    def auto_build_from_knowledge(self):
        """Tự xây graph từ knowledge table."""
        try:
            rows = db_query_all("SELECT DISTINCT entity, attribute FROM knowledge WHERE entity IS NOT NULL")
            for row in rows:
                entity = row["entity"]
                attr = row["attribute"]
                self.add_relation(entity, "has_property", attr, confidence=0.9, source="knowledge")
                # Classify entity
                if attr in ("molecular_weight",): self.add_relation(entity, "is_a", "chemical_compound", confidence=0.9, source="auto")
                elif attr in ("temperature",): self.add_relation(entity, "is_a", "location", confidence=0.9, source="auto")
                elif attr in ("price_usd",): self.add_relation(entity, "is_a", "cryptocurrency", confidence=0.9, source="auto")
                elif attr in ("result",): self.add_relation(entity, "is_a", "math_expression", confidence=0.9, source="auto")
        except Exception as e:
            logger.error(f"WorldModel auto_build error: {e}", exc_info=True)

    def get_stats(self) -> dict:
        try:
            total = db_query_one("SELECT COUNT(*) as cnt FROM meta_world_model")["cnt"]
            by_relation = {}
            for r in db_query_all("SELECT relation, COUNT(*) as cnt FROM meta_world_model GROUP BY relation"):
                by_relation[r["relation"]] = r["cnt"]
            return {"total_relations": total, "by_relation": by_relation}
        except Exception as exc:
            logger.warning("meta: world-model stats query failed, reporting zeros: %s", exc, exc_info=True)
            return {"total_relations": 0, "by_relation": {}}


# ============================================================
# 4. ABSTRACTION — Lesson -> Principle -> Policy
# ============================================================
class AbstractionEngine:
    """
    Abstraction Engine — Nâng bài học thành nguyên lý.

    Lesson (cụ thể) -> Principle (trừu tượng) -> Policy (áp dụng)

    Ví dụ:
        Lesson: "CoinGecko timeout 5 lần trong 1 giờ"
        Principle: "API unstable -> ưu tiên cache, giảm call frequency"
        Policy: "CoinGecko: cache_ttl=600s, max_retries=1"

     Cải thiện:
    - MIN_SAMPLES_FOR_PRINCIPLE = 10 (was 50, too high for early cycles)
    -  Reduced from 50 → 10 so principles appear faster
    - With 50, need 50 PASS/FAIL per domain before any principle → too slow
    - With 10, principles appear after ~10 samples (1-2 cycles)
    - Domain tagging theo frame thực tế (math/chemistry/geography/...)
    """

    # Ngưỡng tối thiểu samples để rút principle — tránh overfitting từ vài mẫu
    MIN_SAMPLES_FOR_PRINCIPLE = 10  #  was 50, reduced for faster principle abstraction

    def __init__(self):
        pass

    def abstract_from_lessons(self) -> list[dict]:
        """
         Read calibration_history (BOTH PASS+FAIL) → abstract principles.

        V27 bug: error_history chỉ log FAIL → fail_rate luôn 100% → principles sai.
        V40 fix: dùng calibration_history (has PASS + FAIL) → correct fail_rate.

        V40 dedup: check if similar principle exists before INSERT.
        """
        principles = []
        try:
            #  Use calibration_history (has both PASS + FAIL)
            # thay vì error_history (chỉ có FAIL → fail_rate luôn 100%)
            lessons = db_query_all("""
                SELECT
                    domain as lesson_type,
                    'calibration' as policy_target,
                    actual_verdict as policy_value,
                    confidence,
                    question
                FROM calibration_history
                WHERE actual_verdict IN ('FAIL', 'PASS', 'UNKNOWN', 'PARTIAL', 'CONFLICT')
                ORDER BY timestamp DESC
                LIMIT 5000
            """)

            if not lessons:
                return principles

            # Group by lesson_type (domain)
            by_type = defaultdict(list)
            for lesson in lessons:
                ltype = lesson.get("lesson_type", "unknown") or "unknown"
                by_type[ltype].append(lesson)

            # Abstract mỗi nhóm — chỉ nếu đủ samples (>= MIN_SAMPLES_FOR_PRINCIPLE)
            for ltype, group in by_type.items():
                if len(group) >= self.MIN_SAMPLES_FOR_PRINCIPLE:
                    #  Dedup — check if similar principle already exists
                    if not self._principle_exists(ltype, len(group)):
                        principle = self._create_principle(ltype, group)
                        if principle:
                            principles.append(principle)
        except Exception as e:
            logger.error(f"Abstraction error: {e}", exc_info=True)

        return principles

    def _principle_exists(self, domain: str, sample_count: int) -> bool:
        """ Check if a principle with same domain + similar sample_count already exists."""
        try:
            existing = db_query_all(
                "SELECT id, principle FROM meta_principles WHERE domain = ? ORDER BY id DESC LIMIT 5",
                (f"{domain}_processing",)
            )
            if not existing:
                return False
            # If any existing principle has similar sample_count (±10), skip
            for row in existing:
                p = row.get("principle", "")
                import re
                m = re.search(r'(\d+)\s+samples', p)
                if m:
                    existing_count = int(m.group(1))
                    if abs(existing_count - sample_count) <= 10:
                        return True  # Too similar, skip
            return False
        except Exception as exc:
            # Fail-open (return False = not similar) is the current dedup contract; visible now.
            logger.warning("meta: question dedup check failed, treating as dissimilar: %s", exc, exc_info=True)
            return False

    def _create_principle(self, lesson_type: str, lessons: list[dict]) -> dict | None:
        """
         Tạo/cập nhật principle rule — versioning + executable rules.
        Thay vì INSERT mới mỗi lần → UPDATE existing (version++).
        """
        try:
            from scp.meta.principle_rules import PrincipleRuleEngine
            rule_engine = PrincipleRuleEngine()

            total = len(lessons)
            fail_count = sum(1 for lesson in lessons if (lesson.get("policy_value") or "").upper() == "FAIL")
            pass_count = sum(1 for lesson in lessons if (lesson.get("policy_value") or "").upper() == "PASS")
            unknown_count = sum(1 for lesson in lessons if (lesson.get("policy_value") or "").upper() in ("UNKNOWN", "PARTIAL"))
            fail_rate = fail_count / total if total else 0
            pass_rate = pass_count / total if total else 0
            unknown_rate = unknown_count / total if total else 0

            evidence = {
                "samples": total,
                "fail_rate": fail_rate,
                "pass_rate": pass_rate,
                "unknown_rate": unknown_rate,
                "sources": "calibration",
            }

            # Update or create rule (versioning, not append)
            success = rule_engine.update_rule(lesson_type, evidence)
            if not success:
                return None

            rule = rule_engine.get_rule(lesson_type)
            if rule:
                return {
                    "principle": rule.get("principle", ""),
                    "domain": rule.get("domain", f"{lesson_type}_processing"),
                    "confidence": rule.get("confidence", 0.5),
                    "derived_from_count": total,
                    "version": rule.get("version", 1),
                    "rule_condition": rule.get("rule_condition", ""),
                    "rule_action": rule.get("rule_action", ""),
                    "fallback_chain": rule.get("fallback_chain", "[]"),
                }
        except Exception as e:
            logger.error(f"V41 principle rule error: {e}", exc_info=True)

        return None

    def get_active_principles(self) -> list[dict]:
        """Lấy all principles."""
        return db_query_all("SELECT * FROM meta_principles ORDER BY confidence DESC")

    def get_stats(self) -> dict:
        try:
            total = db_query_one("SELECT COUNT(*) as cnt FROM meta_principles")["cnt"]
            avg_conf = db_query_one("SELECT AVG(confidence) as avg FROM meta_principles")["avg"] or 0
            return {"total_principles": total, "avg_confidence": round(avg_conf, 2)}
        except Exception as exc:
            logger.warning("meta: principles stats query failed, reporting zeros: %s", exc, exc_info=True)
            return {"total_principles": 0, "avg_confidence": 0}


# ============================================================
# 5. IDENTITY — Mission, boundaries, values
# ============================================================
class Identity:
    """
    Identity — Định nghĩa SCP là ai, phục vụ ai, giới hạn gì.

    Trả lời câu hỏi:
      - Mission: SCP phục vụ mục đích gì?
      - Boundary: SCP làm gì, KHÔNG làm gì?
      - Values: SCP ưu tiên gì khi xung đột?
      - Forbidden: SCP tuyệt đối không làm gì?
    """

    def get(self, key: str) -> str:
        row = db_query_one("SELECT value FROM meta_identity WHERE key = ?", (key,))
        return row["value"] if row else ""

    def set(self, key: str, value: str):
        ts = datetime.now().astimezone().isoformat()
        db_exec("""
            INSERT OR REPLACE INTO meta_identity (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, ts))

    def get_mission(self) -> str:
        return self.get("mission")

    def get_boundaries(self) -> str:
        return self.get("boundary")

    def get_values(self) -> list[str]:
        rows = db_query_all("SELECT value FROM meta_identity WHERE key LIKE 'value_%' ORDER BY key")
        return [r["value"] for r in rows]

    def get_forbidden(self) -> list[str]:
        rows = db_query_all("SELECT value FROM meta_identity WHERE key LIKE 'forbidden_%' ORDER BY key")
        return [r["value"] for r in rows]

    def get_long_term_goal(self) -> str:
        return self.get("long_term_goal")

    def get_all(self) -> dict:
        rows = db_query_all("SELECT key, value FROM meta_identity")
        return {r["key"]: r["value"] for r in rows}


# ============================================================
# META-COGNITION ENGINE — Tầng trên cùng
# ============================================================
class MetaCognitionEngine:
    """
    Meta-Cognition Engine — Tầng điều phối cao nhất.

    Quản lý vòng lặp:
        Mission -> Goal -> Curiosity -> Brain -> Experience -> Prediction -> Reality -> Mission Update

    Mỗi cycle:
      1. REFLECT IDENTITY — Đọc mission + values
      2. CHECK GOALS — Đánh giá tiến độ goals
      3. GENERATE CURIOSITY — Sinh câu hỏi Information Gain cao
      4. UPDATE WORLD MODEL — Thêm quan hệ từ knowledge
      5. ABSTRACT PRINCIPLES — Nâng lessons thành principles
      6. REPORT — Báo cáo meta-state
    """

    def __init__(self):
        init_db()
        init_meta_db()
        self.identity = Identity()
        self.goals = GoalMemory()
        self.curiosity = CuriosityEngine()
        self.world = WorldModel()
        self.abstraction = AbstractionEngine()
        self.engine = SCPV13()
        self.cycle_count = 0

    def run_meta_cycle(self) -> dict:
        """Chạy 1 meta-cognition cycle."""
        self.cycle_count += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"  [BRAIN] META-COGNITION CYCLE {self.cycle_count}")
        logger.info(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*60}")

        # Step 1: Reflect Identity
        logger.info("\n  1.  IDENTITY")
        mission = self.identity.get_mission()
        ltg = self.identity.get_long_term_goal()
        values = self.identity.get_values()
        forbidden = self.identity.get_forbidden()
        logger.info(f"     Mission: {mission[:70]}")
        logger.info(f"     Long-term: {ltg[:70]}")
        logger.info(f"     Values: {len(values)} | Forbidden: {len(forbidden)}")

        # Step 2: Check Goals
        logger.info("\n  2.  GOALS")
        active_goals = self.goals.get_active_goals()
        goal_stats = self.goals.get_stats()
        logger.info(f"     Active: {goal_stats['active']} | Completed: {goal_stats['completed']}")
        logger.info(f"     Avg progress: {goal_stats['avg_progress']*100:.0f}%")
        for g in active_goals[:3]:
            logger.info(f"     [{g['priority']}] {g['description'][:60]} (progress: {g['progress']*100:.0f}%)")

        # Step 3: Generate Curiosity
        logger.info("\n  3.  CURIOSITY (Information Gain)")
        curious_questions = self.curiosity.generate_curious_questions(5)
        logger.info(f"     Generated: {len(curious_questions)} questions")
        for q in curious_questions[:3]:
            logger.info(f"     [{q['curiosity_type']:15s}] IG={q['information_gain']:.2f} | {q['question'][:50]}")
            logger.info(f"     Reason: {q['reason'][:70]}")
            self.curiosity.save_question(q)

        # Step 4: Update World Model
        logger.info("\n  4.  WORLD MODEL")
        self.world.auto_build_from_knowledge()
        world_stats = self.world.get_stats()
        logger.info(f"     Relations: {world_stats['total_relations']}")
        logger.info(f"     By relation: {world_stats.get('by_relation', {})}")

        # Step 5: Abstract Principles
        logger.info("\n  5.  ABSTRACTION (Lesson -> Principle)")
        new_principles = self.abstraction.abstract_from_lessons()
        logger.info(f"     New principles: {len(new_principles)}")
        for p in new_principles[:3]:
            logger.info(f"     [{p['domain']:25s}] conf={p['confidence']:.2f} | {p['principle'][:60]}")

        # Step 6: Execute curious questions (ask 1)
        if curious_questions:
            logger.info("\n  6.  EXECUTE (ask top curiosity question)")
            top_q = curious_questions[0]
            logger.info(f"     Asking: {top_q['question'][:60]}")
            logger.info(f"     Type: {top_q['curiosity_type']} | IG: {top_q['information_gain']:.2f}")
            try:
                result = self.engine.process(top_q["question"], "0")
                logger.info(f"     Verdict: {result.final_verdict}")
                if result.real_value is not None:
                    logger.info(f"     Real value: {result.real_value} (src: {result.source})")

                    # Learn from result -> update world model
                    if result.source:
                        self.world.add_relation(
                            top_q.get("entity", ""), "verified_by", result.source,
                            confidence=0.8, source="meta_cognition"
                        )
            except Exception as e:
                logger.warning("meta: principle verification step failed: %s", e, exc_info=True)
                logger.error(f"     Error: {e}")

        # Report
        logger.info("\n  [STATS] META-STATE:")
        logger.info(f"     Mission: {mission[:50]}")
        logger.info(f"     Goals: {goal_stats['active']} active, {goal_stats['completed']} completed")
        logger.info(f"     Curiosity: {self.curiosity.get_stats()['total_questions']} questions generated")
        logger.info(f"     World Model: {world_stats['total_relations']} relations")
        logger.info(f"     Principles: {self.abstraction.get_stats()['total_principles']} abstracted")
        logger.info(f"     Identity: {len(self.identity.get_all())} defined values")
        logger.info(f"{'='*60}")

        return {
            "cycle": self.cycle_count,
            "mission": mission[:50],
            "goals": goal_stats,
            "curiosity": self.curiosity.get_stats(),
            "world_model": world_stats,
            "principles": self.abstraction.get_stats(),
        }


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="SCP V14 Meta-Cognition Engine")
    parser.add_argument("--lien-tuc", action="store_true", help="24/7")
    parser.add_argument("--hoi", type=str, help="Hỏi meta (mission/goals/identity)")
    parser.add_argument("--world", action="store_true", help="Xem world model graph")
    parser.add_argument("--nghi", type=int, default=0, help="Giây nghỉ")
    args = parser.parse_args()

    meta = MetaCognitionEngine()

    if args.hoi:
        if args.hoi.lower() == "mission":
            print(f"\n  Mission: {meta.identity.get_mission()}")
            print(f"  Long-term: {meta.identity.get_long_term_goal()}")
        elif args.hoi.lower() == "identity":
            for k, v in meta.identity.get_all().items():
                print(f"  {k}: {v}")
        elif args.hoi.lower() == "goals":
            for g in meta.goals.get_active_goals():
                print(f"  [{g['priority']}] {g['description']} (progress: {g['progress']*100:.0f}%)")
        return

    if args.world:
        print("\n  WORLD MODEL GRAPH:")
        relations = meta.world.get_relations()
        for r in relations[:30]:
            print(f"  {r['subject']:20s} --{r['relation']:15s}--> {r['object']:20s} (conf={r['confidence']:.2f})")
        print(f"\n  Total: {len(relations)} relations")
        return

    if args.lien_tuc:
        running = [True]
        def handler(sig, frame):
            running[0] = False
        signal.signal(signal.SIGINT, handler)

        while running[0]:
            meta.run_meta_cycle()
            if args.nghi > 0 and running[0]:
                time.sleep(args.nghi)
        print(f"\n  Đã dừng. {meta.cycle_count} cycles.")
    else:
        meta.run_meta_cycle()
