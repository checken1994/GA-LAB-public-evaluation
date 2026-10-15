"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
SCP V14 — Self-Healing Engine
"""
import logging
import random
from datetime import datetime

from scp.core.db_manager import db_exec, db_query_all

logger = logging.getLogger("scp.v14")

# [B311-fix 2026-09-30] RNG dùng để tạo hậu số của issue/knowledge ID
# (ISSUE-<timestamp>-<n>, KNOW-<timestamp>-<n>): chỉ cần distinct-enough để
# giảm va chạm khi INSERT, KHÔNG phải secret/token cần unguessable. Dùng
# instance SystemRandom RIÊNG ở module level (pattern:
# scp/security/gcg_attack.py `_GCG_RNG`) thay cho global RNG để tách biệt với
# mọi lời random.seed() của module khác và giữ nguyên khoảng giá trị
# randint() như cũ (behavior-preserving).
_HEALING_RNG = random.SystemRandom()

class ErrorClassifier:
    @staticmethod
    def classify(verdict, reason, frame):
        reason_lower = (reason or "").lower()
        if frame == "unknown" or "không xác định" in reason_lower:
            return type('ErrCls', (), {'error_type': "classifier_error", 'domain': "classifier", 'detail': "Classifier không nhận diện", 'fixable': True})()
        if any(kw in reason_lower for kw in ["inapplicable", "không parse", "no checker"]):
            return type('ErrCls', (), {'error_type': "parser_error", 'domain': frame, 'detail': "Parser lỗi", 'fixable': True})()
        return type('ErrCls', (), {'error_type': "logic_error", 'domain': frame, 'detail': "AI sai", 'fixable': False})()

class HealthStateMachine:
    def __init__(self):
        self.cache_states = {}
        self.cache_counters = {}
        try:
            self.cache_states = {r['domain']: r['state'] for r in db_query_all("SELECT domain, state FROM health_states")}
            self.cache_counters = {r['domain']: r for r in db_query_all("SELECT * FROM health_counters")}
        except Exception as e:
            logger.debug(f"[V104.37] core/healing_engine.py: e={e}", exc_info=True)

    def record(self, domain, verdict):
        if domain not in self.cache_counters:
            self.cache_counters[domain] = {"domain": domain, "pass": 0, "block": 0, "inapplicable": 0, "total": 0}  # nosec B105 — "pass" is a verdict counter key, not a password
        c = self.cache_counters[domain]
        c["total"] += 1
        if verdict == "PASS": c["pass"] += 1
        elif verdict in ("BLOCK", "FAIL"): c["block"] += 1
        else: c["inapplicable"] += 1
        try:
            db_exec("INSERT OR REPLACE INTO health_counters (domain, pass, block, inapplicable, total) VALUES (?, ?, ?, ?, ?)",
                    (domain, c["pass"], c["block"], c["inapplicable"], c["total"]))
        except Exception as e:
            logger.debug(f"[V104.37] core/healing_engine.py: e={e}", exc_info=True)
        # [V89 FIX] Also write to health_states (was read but never written)
        pass_rate = c["pass"] / max(1, c["total"])
        if pass_rate > 0.8:
            state = "HEALTHY"
        elif pass_rate > 0.5:
            state = "DEGRADED"
        elif pass_rate > 0.2:
            state = "CRITICAL"
        else:
            state = "FAILED"
        self.cache_states[domain] = state
        try:
            db_exec("INSERT OR REPLACE INTO health_states (domain, state, last_updated) VALUES (?, ?, ?)",
                    (domain, state, datetime.now().isoformat()))
        except Exception as e:
            logger.debug(f"[V104.37] core/healing_engine.py: e={e}", exc_info=True)

class RecoveryQueue:
    def create_issue(self, domain, question, ai_answer, error_type, cause, fix_action="none"):
        from datetime import datetime
        issue_id = f"ISSUE-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{_HEALING_RNG.randint(0, 9999):04d}"
        try:
            db_exec("INSERT OR IGNORE INTO recovery_issues (id, timestamp, domain, question, ai_answer, error_type, cause, fix_action, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (issue_id, datetime.now().isoformat(), domain, question, ai_answer[:200] if ai_answer else "", error_type, cause[:200] if cause else "", fix_action, "OPEN"))
            return issue_id
        except Exception as exc:
            logger.warning("healing_engine: recovery issue insert failed, issue id None: %s", exc, exc_info=True)
            return None

class KnowledgeMemory:
    def add(self, question, ai_answer, domain, error_type, cause, fix_action, fix_artifact, evidence, confidence):
        from datetime import datetime
        know_id = f"KNOW-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{_HEALING_RNG.randint(1000,9999)}"
        try:
            db_exec("INSERT OR IGNORE INTO knowledge_memory (id, timestamp, question, ai_answer, domain, error_type, cause, fix_action, fix_artifact, evidence, confidence, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (know_id, datetime.now().isoformat(), question, ai_answer[:200], domain, error_type, cause[:200], fix_action, fix_artifact[:200], evidence[:200], confidence, "active"))
        except Exception as e:
            logger.debug(f"[V104.37] core/healing_engine.py: e={e}", exc_info=True)

class SelfHealingEngine:
    def __init__(self):
        self.error_classifier = ErrorClassifier()
        self.health = HealthStateMachine()
        self.recovery = RecoveryQueue()
        self.knowledge = KnowledgeMemory()
        self.error_history = ErrorHistory()

class ErrorHistory:
    def record(self, question, ai_answer, frame, v13_verdict, final_verdict, verdict_detail, error_type, source, real_value, ai_value, reason):
        import hashlib
        from datetime import datetime
        ts = datetime.now().isoformat()
        sha256 = hashlib.sha256(f"{question}|{ai_answer}".encode()).hexdigest()[:16]
        try:
            db_exec("INSERT INTO error_history (timestamp, question, ai_answer, frame, v13_verdict, final_verdict, verdict_detail, error_type, source, real_value, ai_value, reason, sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (ts, question, ai_answer[:500], frame, v13_verdict, final_verdict, verdict_detail, error_type, source, str(real_value) if real_value else None, str(ai_value) if ai_value else None, reason[:500], sha256))
        except Exception as e:
            logger.debug(f"[V104.37] core/healing_engine.py: e={e}", exc_info=True)

    def get_similar_errors(self, question, limit=5):
        try:
            # [Fix 4-a-017] Escape LIKE pattern special chars (% and _) in the
            # user input BEFORE interpolating it into the LIKE pattern.
            # Otherwise a search for '50%' matches every row that contains
            # '50' followed by anything (i.e. ~everything), and 'a_b' matches
            # 'aXb', 'aYb', etc. We use the ESCAPE clause so backslash is the
            # escape char inside the LIKE pattern.
            #
            # Example: input '50% off_code' → escaped '50\% off\_code' → LIKE
            # pattern '%50\% off\_code%' ESCAPE '\' matches only rows that
            # literally contain '50% off_code'.
            # DNA #9 (no harm — unescaped LIKE = unexpected matches → wrong
            # healing suggestion → could mask real error patterns).
            raw = question.lower()[:30]
            # Backslash first (so we don't double-escape the backslashes we add)
            escaped = raw.replace("\\", "\\\\")
            escaped = escaped.replace("%", r"\%")
            escaped = escaped.replace("_", r"\_")
            return db_query_all(
                "SELECT * FROM error_history WHERE LOWER(question) LIKE ? ESCAPE '\\' ORDER BY timestamp DESC LIMIT ?",
                (f"%{escaped}%", limit),
            )
        except Exception as exc:
            logger.warning("healing_engine: error_history query failed, returning empty: %s", exc, exc_info=True)
            return []
