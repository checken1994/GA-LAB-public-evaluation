"""
[OPT-14] AntiClosureMeta — Gà §17: "Anti-closure trở thành closure mới"

WHY re-implement: was 9-line stub with trivial block_rate >0.9 check.
Proper implementation needs:
  - Track block decisions over time
  - Detect when SCP becomes too restrictive (blocks everything)
  - Detect when SCP becomes too permissive (blocks nothing)
  - Alert when anti-closure itself becomes a form of closure

Wired into: scp/meta/governance_v97.py (governance decisions check this)
  - If block_rate > 0.9 for sustained period → anti-closure became closure
  - If block_rate < 0.05 for sustained period → SCP too permissive (no defense)
"""
from __future__ import annotations

import logging
import time
from collections import deque

logger = logging.getLogger("scp.meta.anti_closure_meta")


class AntiClosureMeta:
    """Gà §17: Monitor if anti-closure becomes closure.

    Philosophy: A system designed to prevent closure (over-restriction) can
    itself become a form of closure if it blocks too much.

    Healthy block rate: 5-30% (defends attacks, allows legitimate queries)
    Unhealthy: >90% (too restrictive) or <5% (too permissive)
    """

    MAX_HISTORY = 1000  # track last 1000 decisions
    SUSTAINED_PERIOD = 100  # need 100 decisions to establish pattern
    HIGH_BLOCK_THRESHOLD = 0.9  # >90% blocks = closure risk
    LOW_BLOCK_THRESHOLD = 0.05  # <5% blocks = permissive risk

    # Decisions that count as "block" — i.e., SCP rejected the candidate.
    BLOCK_DECISIONS = frozenset({"KILL", "FAIL", "ESCALATE", "BLOCK", "DENY"})

    def __init__(self):
        self._decisions: deque[str] = deque(maxlen=self.MAX_HISTORY)
        self._alerts: list[dict] = []

    def record_decision(self, decision: str) -> None:
        """Record a governance decision (UPHOLD/KILL/ESCALATE/FAIL/PASS)."""
        self._decisions.append(decision.upper())
        # Check for closure patterns every SUSTAINED_PERIOD decisions
        if len(self._decisions) % self.SUSTAINED_PERIOD == 0:
            self._check_closure_risk()

    def _check_closure_risk(self) -> dict | None:
        """Check if recent decisions show closure risk."""
        if len(self._decisions) < self.SUSTAINED_PERIOD:
            return None
        recent = list(self._decisions)[-self.SUSTAINED_PERIOD:]
        block_count = sum(1 for d in recent if d in self.BLOCK_DECISIONS)
        block_rate = block_count / len(recent)
        alert = None
        if block_rate > self.HIGH_BLOCK_THRESHOLD:
            alert = {
                "type": "closure_risk",
                "block_rate": block_rate,
                "threshold": self.HIGH_BLOCK_THRESHOLD,
                "message": f"Anti-closure became closure: {block_rate:.1%} blocks in last {len(recent)} decisions",
                "recommendation": "Review recent KILL/FAIL decisions — may be too restrictive",
            }
            logger.warning(f"[AntiClosureMeta] {alert['message']}")
        elif block_rate < self.LOW_BLOCK_THRESHOLD:
            alert = {
                "type": "permissive_risk",
                "block_rate": block_rate,
                "threshold": self.LOW_BLOCK_THRESHOLD,
                "message": f"SCP too permissive: only {block_rate:.1%} blocks in last {len(recent)} decisions",
                "recommendation": "Review recent PASS decisions — may be missing attacks",
            }
            logger.warning(f"[AntiClosureMeta] {alert['message']}")
        if alert:
            self._alerts.append({**alert, "timestamp": time.time()})
        return alert

    def get_block_rate(self) -> float:
        """Get current block rate (0.0 to 1.0)."""
        if not self._decisions:
            return 0.0
        block_count = sum(1 for d in self._decisions if d in self.BLOCK_DECISIONS)
        return block_count / len(self._decisions)

    def get_alerts(self, limit: int = 10) -> list[dict]:
        """Get recent alerts."""
        return self._alerts[-limit:] if limit > 0 else self._alerts

    def check(self, decisions: list | None = None) -> dict:
        """Compatibility method — accepts list of decisions or uses internal."""
        if decisions is None:
            decisions = list(self._decisions)
        if not decisions:
            return {"ok": True, "block_rate": 0.0}
        block_rate = sum(1 for d in decisions if str(d).upper() in ("BLOCK", "KILL", "FAIL")) / len(decisions)
        if block_rate > self.HIGH_BLOCK_THRESHOLD:
            return {"warning": "Anti-closure becoming closure", "block_rate": block_rate}
        return {"ok": True, "block_rate": block_rate}

    def stats(self) -> dict:
        return {
            "total_decisions": len(self._decisions),
            "block_rate": self.get_block_rate(),
            "alerts_count": len(self._alerts),
            "recent_alert": self._alerts[-1] if self._alerts else None,
        }


# Module-level singleton — Governance uses this to record each decision.
_anti_closure_meta: AntiClosureMeta | None = None


def get_anti_closure_meta() -> AntiClosureMeta:
    """Get the singleton AntiClosureMeta instance."""
    global _anti_closure_meta
    if _anti_closure_meta is None:
        _anti_closure_meta = AntiClosureMeta()
    return _anti_closure_meta


__all__ = ["AntiClosureMeta", "get_anti_closure_meta"]
