"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""
from __future__ import annotations

# [G3-CONSOLIDATE P1-06] Verifier consolidation status:
# - This verifier: LIVE-UNIQUE
# - Canonical verifier: scp/core/multi_source_verifier.py::AsyncMultiSourceVerifier
# - Unique role: SCHEDULED RE-VERIFICATION queue — enqueues low-confidence
#   PASS/PARTIAL/UNKNOWN verdicts (cooldown 5 min), then re-judges them
#   via judge.judge() and compares verdict stability. This is NOT a
#   verifier in the same sense as the others — it does not fetch sources
#   or compute confidence; it orchestrates a time-delayed re-run of the
#   entire judge pipeline. Distinct from canonical AsyncMultiSourceVerifier
#   which does live in-request source verification.
# - Wired to /ask: YES — judge.py:613-617 instantiates ReVerifyScheduler
#   (judge.reverify_scheduler); judgecore_mixin.py:2727-2729 enqueues after
#   each verdict; judgebg_mixin.py:101-103 processes pending items every
#   300s in the background.
# - Known bug (Task 2-B finding B5, NOT fixed here — out of scope):
#   Line 217 (now ~245 after this marker added) calls
#   `hasattr(self.judge, 'cognitive_gate')` but judge.py:624 sets
#   `self.cognitive` (different attribute name). CognitiveGate feedback loop
#   is therefore DEAD. Documented in worklog Task 2-B / Task 9-A.

#!/usr/bin/env python3
"""
SCP V36 — Re-Verification Scheduler.

L4 GAP FIX: Self-Suspend có (V34) nhưng chưa auto-retry.
Module này tự động tìm verdicts bị self-suspend → re-verify sau cooldown.

Luồng:
    1. Find verdicts with self_suspend flag (từ verdict_cache hoặc error_history)
    2. Wait cooldown (vd 5 min)
    3. Re-judge với same question + AI answer
    4. Nếu verdict stable (vẫn PASS) → clear self_suspend, boost confidence
    5. Nếu verdict changed (FAIL/UNKNOWN) → log to error_history, update calibration

Closed-loop: PASS (low conf) → wait → re-verify → confirm or falsify
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("scp.reverify")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from scp.core.db_manager import db_exec, db_query_all, db_query_one, init_db


def init_reverify_db():
    """Tạo reverify queue table."""
    db_exec("""
        CREATE TABLE IF NOT EXISTS reverify_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            question TEXT NOT NULL,
            ai_answer TEXT,
            domain TEXT,
            original_verdict TEXT,
            original_confidence REAL,
            cooldown_minutes INTEGER DEFAULT 5,
            scheduled_at TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            reverify_verdict TEXT,
            reverify_confidence REAL,
            reverify_at TEXT,
            verdict_stable BOOLEAN,
            notes TEXT
        )
    """)
    db_exec("CREATE INDEX IF NOT EXISTS idx_reverify_status ON reverify_queue(status)")
    db_exec("CREATE INDEX IF NOT EXISTS idx_reverify_scheduled ON reverify_queue(scheduled_at)")


class ReVerifyScheduler:
    """
    Re-Verification Scheduler — auto retry self-suspend verdicts.

    Usage:
        scheduler = ReVerifyScheduler(judge=judge)
        scheduler.enqueue_if_needed(question, ai_answer, domain, verdict, confidence)
        scheduler.process_pending()  # Run periodically
    """

    def __init__(self, judge=None, default_cooldown_minutes: int = 5):
        init_db()
        init_reverify_db()
        self.judge = judge
        self.default_cooldown = default_cooldown_minutes

    def enqueue_if_needed(self, question: str, ai_answer: str,
                          domain: str, verdict: str, confidence: float,
                          why_threshold: float, evidence_type: str) -> str | None:
        """
        Enqueue verdict for re-verification if self-suspend conditions met.

        Conditions:
            - verdict == PASS
            - confidence < why_threshold
            - evidence_type not deterministic

        Returns:
            reverify_id if enqueued, None otherwise.
        """
        # Only enqueue non-deterministic domains
        deterministic_types = {
            "deterministic_calculation", "deterministic_evaluation",
            "codata_constants", "biological_database"
        }
        if evidence_type in deterministic_types:
            return None
        # [V104.25 #6 FIX] Also enqueue PARTIAL and UNKNOWN (was: only PASS)
        if verdict not in ("PASS", "PARTIAL", "UNKNOWN"):
            return None
        if confidence >= why_threshold:
            return None

        # Enqueue
        try:
            ts = datetime.now().astimezone().isoformat()
            scheduled_at = (datetime.now().astimezone() + timedelta(minutes=self.default_cooldown)).isoformat()
            # [V104.21 #2 FIX] Use INSERT ... RETURNING id (was: last_insert_rowid race)
            row = db_query_one("""
                INSERT INTO reverify_queue
                (timestamp, question, ai_answer, domain, original_verdict,
                 original_confidence, cooldown_minutes, scheduled_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                RETURNING id
            """, (ts, question[:500], ai_answer[:200], domain, verdict,
                  confidence, self.default_cooldown, scheduled_at))
            return str(row["id"]) if row else None
        except Exception as e:
            logger.warning(f"ReVerify enqueue error: {e}", exc_info=True)
            return None

    def get_pending(self, limit: int = 50) -> list[dict]:
        """Get pending re-verify items past scheduled_at."""
        now = datetime.now().astimezone().isoformat()
        try:
            rows = db_query_all(
                "SELECT * FROM reverify_queue "
                "WHERE status = 'pending' AND scheduled_at <= ? "
                "ORDER BY scheduled_at ASC LIMIT ?",
                (now, limit)
            )
            return [dict(r) for r in rows] if rows else []
        except Exception as e:
            logger.warning(f"ReVerify get_pending error: {e}", exc_info=True)
            return []

    def process_pending(self, limit: int = 10) -> dict[str, Any]:
        """
        Process pending re-verify items.

        Returns:
            {processed, stable, changed, errors}
        """
        if not self.judge:
            return {"error": "no judge", "processed": 0, "stable": 0, "changed": 0, "errors": 0}

        pending = self.get_pending(limit=limit)
        if not pending:
            return {"processed": 0, "stable": 0, "changed": 0, "errors": 0}

        processed = 0
        stable = 0
        changed = 0
        errors = 0

        for item in pending:
            try:
                # Re-judge
                v = self.judge.judge(item["question"], item["ai_answer"] or "")
                reverify_verdict = v.verdict
                reverify_confidence = v.confidence

                # Compare with original
                verdict_stable = (reverify_verdict == item["original_verdict"])

                # Update DB
                now = datetime.now().astimezone().isoformat()
                db_exec("""
                    UPDATE reverify_queue
                    SET status = 'done', reverify_verdict = ?,
                        reverify_confidence = ?, reverify_at = ?,
                        verdict_stable = ?, notes = ?
                    WHERE id = ?
                """, (
                    reverify_verdict, reverify_confidence, now,
                    verdict_stable,
                    f"Original: {item['original_verdict']} ({item['original_confidence']:.3f}) → "
                    f"Reverify: {reverify_verdict} ({reverify_confidence:.3f})",
                    item["id"],
                ))

                processed += 1
                if verdict_stable:
                    stable += 1
                else:
                    changed += 1
                    logger.info(f"ReVerify CHANGED: '{item['question'][:50]}' "
                                f"{item['original_verdict']} → {reverify_verdict}")

                    # [V104.43 #AW] TẠI SAO: was only UPDATE queue row + log.
                    # Closed-loop "confirm or falsify" stopped at audit row — didn't
                    # fix KB confidence or call cognitive_gate feedback.
                    # Fix: (1) lower KB confidence for changed facts, (2) call
                    # cognitive_gate.record_reverify_outcome if available.
                    try:
                        # 1. Lower KB confidence for the question's entity
                        _q = item["question"][:200]
                        db_exec(
                            "UPDATE knowledge SET confidence = MIN(confidence, 0.3) "
                            "WHERE entity = ? AND attribute = 'verified_value'",
                            (_q.lower(),)
                        )
                        logger.info(f"[V104.43 #AW] KB confidence lowered for changed fact: {_q[:50]}")
                    except Exception as _kb_err:
                        logger.debug(f"[V104.43 #AW] KB fix error: {_kb_err}", exc_info=True)

                    try:
                        # 2. Call cognitive_gate feedback if available
                        if hasattr(self, 'judge') and self.judge and hasattr(self.judge, 'cognitive_gate') and self.judge.cognitive_gate:
                            self.judge.cognitive_gate.record_reverify_outcome(
                                question=item["question"],
                                reverify_verdict=reverify_verdict,
                            )
                            logger.info("[V104.43 #AW] CognitiveGate feedback recorded")
                    except Exception as _gate_err:
                        logger.debug(f"[V104.43 #AW] CognitiveGate feedback error: {_gate_err}", exc_info=True)

            except Exception as e:
                errors += 1
                logger.warning(f"ReVerify process error: {e}", exc_info=True)
                # Mark as error
                db_exec("UPDATE reverify_queue SET status = 'error', notes = ? WHERE id = ?",
                        (str(e)[:200], item["id"]))

        return {
            "processed": processed,
            "stable": stable,
            "changed": changed,
            "errors": errors,
        }

    def get_stats(self) -> dict[str, Any]:
        """Stats cho reverify queue."""
        try:
            total = db_query_one("SELECT COUNT(*) as cnt FROM reverify_queue")["cnt"]
            pending = db_query_one("SELECT COUNT(*) as cnt FROM reverify_queue WHERE status = 'pending'")["cnt"]
            done = db_query_one("SELECT COUNT(*) as cnt FROM reverify_queue WHERE status = 'done'")["cnt"]
            stable = db_query_one("SELECT COUNT(*) as cnt FROM reverify_queue WHERE verdict_stable = 1")["cnt"]
            changed = db_query_one("SELECT COUNT(*) as cnt FROM reverify_queue WHERE verdict_stable = 0 AND status = 'done'")["cnt"]

            return {
                "total": total,
                "pending": pending,
                "done": done,
                "stable": stable,
                "changed": changed,
                "stability_rate": round(stable / max(1, done), 3),
            }
        except Exception as e:
            logger.warning("Reverify scheduler get_stats failed: %s", e, exc_info=True)
            return {"error": str(e)}


# ============================================================
# MAIN
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCP V36 ReVerify Scheduler")
    parser.add_argument("--process", action="store_true", help="Process pending reverify items")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    from scp.core.circuit_breaker import CircuitBreakerRegistry
    CircuitBreakerRegistry().reset_all()
    from scp.runtime.judge import RealityJudge
    j = RealityJudge()
    scheduler = ReVerifyScheduler(judge=j)

    if args.stats:
        stats = scheduler.get_stats()
        print("\n  ReVerify Stats:")
        for k, v in stats.items():
            print(f"    {k:15s} {v}")
        return

    if args.process:
        print("\n  Processing pending reverify items...")
        result = scheduler.process_pending(limit=20)
        print(f"  Result: {result}")
        return

    print("Use --process or --stats")


if __name__ == "__main__":
    main()
