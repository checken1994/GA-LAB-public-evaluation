"""
[OPT-28] AutoFixMonitor — track success rate + diagnosis breakdown.

DNA SCP #8 KB accumulation: learn from past fixes.
Tracks:
  - Total bugs attempted
  - Success rate (by bug type)
  - Failure breakdown (LLM vs format vs validation vs rollback)
  - Provider performance (which LLM provider succeeds most)

[Idea 5 — VERIFY-THEN-PROMOTE] (Sourcery pattern):
  Per-bug_type success/failure streak tracking.
  - 10 consecutive successes → promote Tier 2 → Tier 1 (silent auto-fix allowed)
  - 3 consecutive failures/rollbacks → demote Tier 1 → Tier 2 (require logging)
  - Streak resets on opposite outcome.
  DNA SCP #12: "Không tăng quyền chỉ vì lập luận tăng" — promotion requires
  EVIDENCE (streak), not just argument. Demotion is automatic on failure.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("scp.autofix.monitor")

# [Idea 5] Promotion/demotion thresholds
_PROMOTE_STREAK = 10   # consecutive successes → promote Tier 2 → Tier 1
_DEMOTE_STREAK = 3     # consecutive failures → demote Tier 1 → Tier 2


@dataclass
class FixAttempt:
    bug_id: str
    bug_type: str
    provider: str  # ollama:<model> (e.g. ollama:deepseek-r1:8b) or openrouter
    diagnosis: str  # from diagnostic.py
    success: bool
    elapsed_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


class AutoFixMonitor:
    """Monitor AutoFix performance over time."""

    def __init__(self, max_history: int = 1000):
        self._attempts: list[FixAttempt] = []
        self._max_history = max_history
        # [Idea 5] Per-bug_type streak tracking
        self._success_streaks: dict[str, int] = {}
        self._failure_streaks: dict[str, int] = {}
        # Promoted/demoted bug types (persist until streak breaks)
        self._promoted: set[str] = set()   # bug_types promoted to Tier 1
        self._demoted: set[str] = set()    # bug_types demoted to Tier 2

    def record(self, attempt: FixAttempt) -> None:
        """Record a fix attempt + update streaks."""
        self._attempts.append(attempt)
        if len(self._attempts) > self._max_history:
            self._attempts = self._attempts[-self._max_history:]
        # [Idea 5] Update streaks
        self._update_streak(attempt.bug_type, attempt.success)

    def _update_streak(self, bug_type: str, success: bool) -> None:
        """Track consecutive success/failure per bug_type."""
        if success:
            self._success_streaks[bug_type] = self._success_streaks.get(bug_type, 0) + 1
            self._failure_streaks[bug_type] = 0
            # Promote if threshold reached
            if self._success_streaks[bug_type] >= _PROMOTE_STREAK:
                if bug_type not in self._promoted:
                    logger.info(
                        f"[Idea5] PROMOTE {bug_type} → Tier 1 "
                        f"(streak={self._success_streaks[bug_type]})"
                    )
                    self._promoted.add(bug_type)
                    self._demoted.discard(bug_type)
        else:
            self._failure_streaks[bug_type] = self._failure_streaks.get(bug_type, 0) + 1
            self._success_streaks[bug_type] = 0
            # Demote if threshold reached
            if self._failure_streaks[bug_type] >= _DEMOTE_STREAK:
                if bug_type not in self._demoted:
                    logger.warning(
                        f"[Idea5] DEMOTE {bug_type} → Tier 2 "
                        f"(failure streak={self._failure_streaks[bug_type]})"
                    )
                    self._demoted.add(bug_type)
                    self._promoted.discard(bug_type)

    def get_tier_adjustment(self, bug_type: str) -> int:
        """Returns tier delta: -1 (promote to Tier 1), +1 (demote to Tier 2), 0 (no change).

        Called by classifier/engine to adjust the base tier based on historical evidence.
        DNA SCP #12: promotion requires EVIDENCE (streak ≥ 10), not argument.
        """
        if bug_type in self._promoted:
            return -1  # promote (lower tier number = more autonomy)
        if bug_type in self._demoted:
            return +1  # demote (higher tier number = less autonomy)
        return 0

    def get_streaks(self) -> dict:
        """Return current streak state for debugging/dashboarding."""
        return {
            "promoted": sorted(self._promoted),
            "demoted": sorted(self._demoted),
            "success_streaks": dict(self._success_streaks),
            "failure_streaks": dict(self._failure_streaks),
            "promote_threshold": _PROMOTE_STREAK,
            "demote_threshold": _DEMOTE_STREAK,
        }

    def get_stats(self) -> dict:
        """Get aggregated stats."""
        if not self._attempts:
            return {"total": 0, "message": "No attempts recorded"}

        total = len(self._attempts)
        success = sum(1 for a in self._attempts if a.success)

        # By bug type
        by_bug_type: dict[str, dict] = {}
        for a in self._attempts:
            if a.bug_type not in by_bug_type:
                by_bug_type[a.bug_type] = {"total": 0, "success": 0, "failure": 0}
            by_bug_type[a.bug_type]["total"] += 1
            if a.success:
                by_bug_type[a.bug_type]["success"] += 1
            else:
                by_bug_type[a.bug_type]["failure"] += 1

        # By diagnosis
        by_diagnosis: dict[str, int] = {}
        for a in self._attempts:
            by_diagnosis[a.diagnosis] = by_diagnosis.get(a.diagnosis, 0) + 1

        # By provider
        by_provider: dict[str, dict] = {}
        for a in self._attempts:
            if a.provider not in by_provider:
                by_provider[a.provider] = {"total": 0, "success": 0, "success_rate": 0.0}
            by_provider[a.provider]["total"] += 1
            if a.success:
                by_provider[a.provider]["success"] += 1
        # [AUTOFIX-T1] PLC0206 — iterate with .items() instead of key→index.
        for _p, stats in by_provider.items():
            t = stats["total"]
            stats["success_rate"] = stats["success"] / t if t > 0 else 0.0

        return {
            "total_attempts": total,
            "success_count": success,
            "failure_count": total - success,
            "success_rate": success / total if total > 0 else 0.0,
            "by_bug_type": by_bug_type,
            "by_diagnosis": by_diagnosis,
            "by_provider": by_provider,
        }

    def get_recent(self, limit: int = 10) -> list[dict]:
        """Get recent attempts."""
        return [
            {
                "bug_id": a.bug_id,
                "bug_type": a.bug_type,
                "provider": a.provider,
                "diagnosis": a.diagnosis,
                "success": a.success,
                "elapsed_ms": a.elapsed_ms,
            }
            for a in self._attempts[-limit:]
        ]


# Singleton
_monitor: AutoFixMonitor | None = None

def get_monitor() -> AutoFixMonitor:
    global _monitor
    if _monitor is None:
        _monitor = AutoFixMonitor()
    return _monitor


__all__ = ["AutoFixMonitor", "FixAttempt", "get_monitor"]
