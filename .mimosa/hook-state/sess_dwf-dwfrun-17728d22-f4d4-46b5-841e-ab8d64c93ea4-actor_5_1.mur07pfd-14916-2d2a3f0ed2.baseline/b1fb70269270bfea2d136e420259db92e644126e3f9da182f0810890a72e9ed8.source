"""
LAYER 2: UNKNOWN STATE — 3 miền nhận thức.

UNKNOWN không phải failure — là miền nhận thức thứ 3.

4 subtype:
    INSUFFICIENT_EVIDENCE   — không đủ sources
    INSUFFICIENT_CONFIDENCE — sources disagree quá nhiều
    INSUFFICIENT_CONTEXT    — câu hỏi ambiguous
    PENDING_VERIFICATION    — đang chờ re-verify/prediction

Extracted from `meta/cognitive_engine.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("scp.cognitive")

# [ROOT-FIX 40-A] Was unlimited → Cognitive Engine enqueued 495 retries for
# 376 unique questions → infinite retry loop → 100% UNKNOWN in logs.
# Fix: cap per-question retries at MAX_RETRIES. After this, let it stay
# UNKNOWN (genuine unknowns, not attack-fails that Healing should not
# re-judge either). DNA SCP #1 (Reality > Model) + #7 (AutoFix safe).
MAX_RETRIES = 3


@dataclass
class UnknownState:
    """
    UNKNOWN không phải failure — là miền nhận thức thứ 3.

    4 subtype:
        INSUFFICIENT_EVIDENCE   — không đủ sources
        INSUFFICIENT_CONFIDENCE — sources disagree quá nhiều
        INSUFFICIENT_CONTEXT    — câu hỏi ambiguous
        PENDING_VERIFICATION    — đang chờ re-verify/prediction
    """
    subtype: str
    reason: str
    what_is_needed: str       # Cần gì để quyết định?
    what_is_missing: str      # Thiếu gì?
    can_be_resolved: bool     # Có thể resolve không?
    resolution_strategy: str  # Làm sao để resolve?


class UnknownStateClassifier:
    """
    Classify UNKNOWN verdicts thành subtypes cụ thể.

    Thay vì "UNKNOWN = failure", UNKNOWN trở thành:
        "Chưa đủ điều kiện quyết định — đây là gì cần thiết"
    """

    def __init__(self):
        # [ROOT-FIX 40-A] Per-question retry counter. Keys are question text,
        # values are how many times we've enqueued this question for retry.
        # Bounded by MAX_RETRIES to prevent the 495-retry infinite loop.
        self._retry_counts: dict[str, int] = {}

    def classify(self, verdict: str, confidence: float,
                 sources_succeeded: list[str], sources_failed: list[str],
                 domain: str, why_threshold: float,
                 evidence: dict, question: str = "") -> UnknownState | None:
        """Classify UNKNOWN verdict.

         When can_be_resolved=True, also enqueues to pending_resolutions table
              so CuriosityAsker can pick up and retry later.
        """
        if verdict != "UNKNOWN":
            return None

        unknown_state: UnknownState | None = None

        # INSUFFICIENT_EVIDENCE — không đủ sources
        if len(sources_succeeded) == 0:
            unknown_state = UnknownState(
                subtype="INSUFFICIENT_EVIDENCE",
                reason=f"All sources failed ({len(sources_failed)} attempted)",
                what_is_needed="At least 1 working source",
                what_is_missing=f"All {len(sources_failed)} sources failed",
                can_be_resolved=True,
                resolution_strategy="Retry later when APIs recover, or add new sources",
            )

        # INSUFFICIENT_CONFIDENCE — sources disagree
        elif len(sources_succeeded) >= 2 and confidence < 0.3:
            unknown_state = UnknownState(
                subtype="INSUFFICIENT_CONFIDENCE",
                reason=f"Sources disagree — confidence={confidence:.2f}",
                what_is_needed="Sources must agree within tolerance",
                what_is_missing="Source consensus",
                can_be_resolved=True,
                resolution_strategy="Add more sources or investigate discrepancy",
            )

        # PENDING_VERIFICATION — awaiting re-verify
        elif evidence.get("self_suspend"):
            unknown_state = UnknownState(
                subtype="PENDING_VERIFICATION",
                reason=f"Self-suspended: confidence {confidence:.2f} < threshold {why_threshold:.2f}",
                what_is_needed="Re-verification after cooldown",
                what_is_missing="Temporal stability confirmation",
                can_be_resolved=True,
                resolution_strategy="Wait for ReVerifyScheduler to re-judge",
            )

        # INSUFFICIENT_CONTEXT — question ambiguous
        elif domain == "unknown":
            unknown_state = UnknownState(
                subtype="INSUFFICIENT_CONTEXT",
                reason="Cannot classify question into any domain",
                what_is_needed="Clearer question or better classifier",
                what_is_missing="Domain context",
                can_be_resolved=False,
                resolution_strategy="Improve RealityClassifier training data",
            )

        # Default UNKNOWN
        else:
            unknown_state = UnknownState(
                subtype="UNCLASSIFIED",
                reason="Unknown reason",
                what_is_needed="Investigation",
                what_is_missing="Unknown",
                can_be_resolved=False,
                resolution_strategy="Manual review required",
            )

        #  If resolvable, enqueue to pending_resolutions for CuriosityAsker
        if unknown_state.can_be_resolved and question:
            self._enqueue_pending_resolution(question, domain, unknown_state)

        return unknown_state

    def _enqueue_pending_resolution(self, question: str, domain: str,
                                     unknown_state: UnknownState):
        """ Add resolvable UNKNOWN to pending_resolutions table.

        CuriosityAsker reads this table and prioritizes re-asking these questions
        to close the UNKNOWN → Pending → Retry → Knowledge loop.

        [ROOT-FIX 40-A] Enforce MAX_RETRIES per question. Without this cap the
        same question was re-enqueued on every cycle (495 INSERTs for 376
        unique questions observed in production logs) → infinite retry loop
        → 100% UNKNOWN verdicts. After MAX_RETRIES we give up and let the
        question stay UNKNOWN (genuine unknown, not a transient failure).
        """
        # [ROOT-FIX 40-A] Check retry count BEFORE touching the DB.
        retry_count = self._retry_counts.get(question, 0)
        if retry_count >= MAX_RETRIES:
            logger.info(
                f"[UnknownState] Max retries ({MAX_RETRIES}) reached for: "
                f"{question[:50]!r} — giving up (stays UNKNOWN)"
            )
            return  # Don't enqueue — let it stay UNKNOWN
        self._retry_counts[question] = retry_count + 1
        try:
            from scp.core.db_manager import db_exec, init_db
            init_db()
            db_exec("""
                CREATE TABLE IF NOT EXISTS pending_resolutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    question TEXT,
                    domain TEXT,
                    subtype TEXT,
                    reason TEXT,
                    resolution_strategy TEXT,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    last_attempt_ts TEXT
                )
            """)
            from datetime import datetime
            ts = datetime.now().astimezone().isoformat()
            db_exec(
                "INSERT INTO pending_resolutions "
                "(timestamp, question, domain, subtype, reason, resolution_strategy) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts, question[:500], domain, unknown_state.subtype,
                 unknown_state.reason[:300], unknown_state.resolution_strategy[:300])
            )
            logger.info(f"[UnknownState V50] Enqueued for retry: subtype={unknown_state.subtype} Q='{question[:50]}'")
        except Exception as e:
            logger.debug(f"pending_resolutions enqueue error: {e}", exc_info=True)
