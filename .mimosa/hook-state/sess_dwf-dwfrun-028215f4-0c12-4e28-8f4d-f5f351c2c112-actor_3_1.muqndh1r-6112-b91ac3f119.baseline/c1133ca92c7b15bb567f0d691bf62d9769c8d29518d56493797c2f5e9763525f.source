"""
[OPT-14] CapabilityLevel — Gà §12: "Quản trị 6 mức"

WHY re-implement: was 9-line stub with just enum, no logic.
Proper implementation needs:
  - Level checking (can SCP do X at current level?)
  - Level transitions (when to escalate/de-escalate)
  - Audit trail (who changed level, when, why)

Wired into: scp/autofix/engine.py (AutoFix checks capability level before applying)
  - Level 0 (ANALYSIS_ONLY): AutoFix can scan but not apply
  - Level 2 (SANDBOX): AutoFix can apply to test files only
  - Level 4 (NARROW_PRODUCTION): AutoFix can apply to specific modules
  - Level 5 (FULL_PRODUCTION): AutoFix unrestricted
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger("scp.meta.capability_levels")


class CapabilityLevel(IntEnum):
    """Gà §12: 6 mức quản trị năng lực AI."""
    ANALYSIS_ONLY = 0      # Chỉ phân tích, không hành động
    SIMULATION = 1         # Mô phỏng, không ảnh hưởng thực
    SANDBOX = 2            # Thực thi trong sandbox
    LIMITED_ENV = 3        # Môi trường giới hạn (test/staging)
    NARROW_PRODUCTION = 4  # Production nhưng scope hẹp
    FULL_PRODUCTION = 5    # Production toàn phần


@dataclass
class CapabilityAuditEntry:
    timestamp: float
    old_level: int
    new_level: int
    reason: str
    actor: str = "system"


class CapabilityManager:
    """Manage SCP's current capability level + audit trail.

    Gà §12: AI không được tự nâng cấp — cần human approval.
    """

    # What each level allows
    LEVEL_PERMISSIONS = {
        CapabilityLevel.ANALYSIS_ONLY: ["scan", "report", "log"],
        CapabilityLevel.SIMULATION: ["scan", "report", "log", "simulate"],
        CapabilityLevel.SANDBOX: ["scan", "report", "log", "simulate", "apply_sandbox"],
        CapabilityLevel.LIMITED_ENV: ["scan", "report", "log", "simulate", "apply_sandbox", "apply_test"],
        CapabilityLevel.NARROW_PRODUCTION: ["scan", "report", "log", "simulate", "apply_sandbox", "apply_test", "apply_narrow"],
        CapabilityLevel.FULL_PRODUCTION: ["*"],  # all permissions
    }

    def __init__(self, initial_level: CapabilityLevel = CapabilityLevel.ANALYSIS_ONLY):
        self._current_level = initial_level
        self._audit_trail: list[CapabilityAuditEntry] = []
        self._record_change(0, initial_level, "initialization", "system")

    def get_current_level(self) -> CapabilityLevel:
        return self._current_level

    def can_do(self, action: str) -> bool:
        """Check if current level allows this action."""
        permissions = self.LEVEL_PERMISSIONS.get(self._current_level, [])
        return "*" in permissions or action in permissions

    def request_escalation(self, target_level: CapabilityLevel, reason: str,
                          actor: str = "human") -> bool:
        """Request to escalate to higher level.

        Gà §12: AI cannot self-escalate — requires human actor.
        Returns True if escalation approved.
        """
        if actor == "ai" or actor == "system":
            logger.warning("[CapabilityManager] AI cannot self-escalate (Gà §12) — denied")
            return False
        if target_level <= self._current_level:
            logger.info(f"[CapabilityManager] target {target_level} <= current {self._current_level} — no escalation needed")
            return True
        old_level = self._current_level
        self._current_level = target_level
        self._record_change(old_level, target_level, reason, actor)
        logger.info(f"[CapabilityManager] escalated {old_level} → {target_level} by {actor}: {reason}")
        return True

    def de_escalate(self, reason: str, actor: str = "system") -> None:
        """Lower capability level (safer). AI can self-de-escalate."""
        if self._current_level > CapabilityLevel.ANALYSIS_ONLY:
            old_level = self._current_level
            self._current_level = CapabilityLevel(self._current_level - 1)
            self._record_change(old_level, self._current_level, reason, actor)
            logger.info(f"[CapabilityManager] de-escalated {old_level} → {self._current_level}: {reason}")

    def _record_change(self, old: int, new: int, reason: str, actor: str) -> None:
        self._audit_trail.append(CapabilityAuditEntry(
            timestamp=time.time(), old_level=old, new_level=new,
            reason=reason, actor=actor,
        ))

    def get_audit_trail(self, limit: int = 10) -> list[dict]:
        """Get recent audit entries."""
        entries = self._audit_trail[-limit:] if limit > 0 else self._audit_trail
        return [
            {"timestamp": e.timestamp, "old": e.old_level, "new": e.new_level,
             "reason": e.reason, "actor": e.actor}
            for e in entries
        ]

    # ---- [SCP-DNA-FIX R13-3 BUG-013] Dashboard aggregation ----
    # Gà §12 "AI cannot self-escalate" is enforced via `can_do()` checks
    # (engine.py:796 reads the level), but the 3 human-side methods
    # (`request_escalation`, `de_escalate`, `get_audit_trail`) had 0 callers
    # → operators were forced to edit `SCP_CAPABILITY_LEVEL` env var + restart.
    # The fix below is a single dashboard aggregation method that returns
    # current level + recent audit trail in one call.
    #
    # TODO(parent — scp/api_server.py owner): wire these into FastAPI routes:
    #     @app.get("/v105/capability/status")
    #     async def capability_status():
    #         return get_capability_manager().escalation_status()
    #
    #     @app.post("/v105/capability/escalate")
    #     async def escalate(level: int, reason: str):
    #         ok = get_capability_manager().request_escalation(
    #             CapabilityLevel(level), reason, actor="human_via_api")
    #         return {"approved": ok}
    #
    #     @app.post("/v105/capability/de-escalate")
    #     async def de_escalate(reason: str):
    #         get_capability_manager().de_escalate(reason, actor="human_via_api")
    #         return {"status": "de-escalated"}
    #
    # Until those routes exist, this method is callable programmatically.
    def escalation_status(self) -> dict:
        """Dashboard snapshot — current level + permissions + audit trail.

        Returns:
            {
              "current_level": int,
              "current_level_name": str,
              "permissions": list[str],
              "audit_trail": list[dict],   # recent 10 entries
              "audit_trail_length": int,   # total entries
            }
        """
        permissions = self.LEVEL_PERMISSIONS.get(self._current_level, [])
        return {
            "current_level": int(self._current_level),
            "current_level_name": self._current_level.name,
            "permissions": list(permissions),
            "audit_trail": self.get_audit_trail(limit=10),
            "audit_trail_length": len(self._audit_trail),
        }

    def stats(self) -> dict:
        return {
            "current_level": int(self._current_level),
            "level_name": self._current_level.name,
            "audit_trail_length": len(self._audit_trail),
        }


# Module-level singleton — engine imports this for default behavior.
# Default level = FULL_PRODUCTION (preserves existing behavior — Tier-1/2/4
# auto-fixes continue to work as before). Operators who want the Gà §12
# capability-gating safety net set SCP_CAPABILITY_LEVEL=ANALYSIS_ONLY (or
# any lower level) to force SCP to request explicit escalation before
# applying auto-fixes.
#
# TẠI SAO: defaulting to ANALYSIS_ONLY would silently disable Tier-1/2
# auto-fixes that existing tests + the STARTUP-GATE rely on — that violates
# the "no harm" DNA SCP principle. FULL_PRODUCTION = no behavior change
# unless operator opts in.
import os as _os


def _resolve_default_level() -> CapabilityLevel:
    """Read SCP_CAPABILITY_LEVEL env var at call time (not import time).

    TẠI SAO: tests may set the env var after import — reading at import
    time would freeze the level permanently and break test isolation.
    """
    name = _os.environ.get("SCP_CAPABILITY_LEVEL", "FULL_PRODUCTION").upper()
    try:
        return CapabilityLevel[name]
    except KeyError:
        # Fail-open to FULL_PRODUCTION is the current contract — but an unknown
        # level name silently widening capability must be visible.
        logger.warning("capability_levels: unknown SCP_CAPABILITY_LEVEL %r, falling back to FULL_PRODUCTION", name, exc_info=True)
        return CapabilityLevel.FULL_PRODUCTION


_capability_manager: CapabilityManager | None = None


def get_capability_manager() -> CapabilityManager:
    """Get the singleton CapabilityManager.

    [ROOT-FIX 47] Re-check env var each call — was cached at first call.
    If SCP_CAPABILITY_LEVEL changed (e.g., user edits .env + restarts),
    singleton must reflect new level.

    Default level from SCP_CAPABILITY_LEVEL env var (default: FULL_PRODUCTION
    to preserve existing behavior — operators opt in to lower levels).
    """
    global _capability_manager
    _current_env_level = _resolve_default_level()
    if _capability_manager is None:
        _capability_manager = CapabilityManager(_current_env_level)
    elif _capability_manager.get_current_level() != _current_env_level:
        # [ROOT-FIX 47] Env var changed — update singleton level
        # (but don't reset audit trail — keep history)
        _capability_manager._current_level = _current_env_level
    return _capability_manager


__all__ = ["CapabilityLevel", "CapabilityManager", "CapabilityAuditEntry", "get_capability_manager"]
