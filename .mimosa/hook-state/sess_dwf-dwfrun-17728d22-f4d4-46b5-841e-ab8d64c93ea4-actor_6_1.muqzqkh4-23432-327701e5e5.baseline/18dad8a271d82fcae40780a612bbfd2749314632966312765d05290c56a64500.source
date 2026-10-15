"""
SCP V4 FORTRESS — AI Defense Citadel
Copyright (c) 2026 [Author: Minh / SCP V4 Project]
All rights reserved.

File: governance.py
Purpose: Governance layer — converts antibody verdicts + council confidence
         into a final UPHOLD / KILL / ESCALATE decision. The Governance
         class is the single authority that may stop a pipeline run.
"""


import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# [OPT-14 / Gà §17] AntiClosureMeta — tracks block rate over time so
# anti-closure policy doesn't itself become a form of closure.
from .anti_closure_meta import get_anti_closure_meta
from .constitution import Constitution, PrincipleId, get_default_constitution

# [ROOT-FIX Task 38-A / Issue 1] DNA #6 Evidence: scp/meta/severity.py was
# DEAD CODE (0 importers). Docstring claimed "cả 2 module import từ đây" but
# in reality both governance_v97.py and antibody_system.py hardcoded strings
# "critical"/"high"/"medium". Now both modules import from severity.py so
# severity strings cannot drift out of sync.
from .severity import CRITICAL_SEVERITIES, Severity, normalize_severity

logger = logging.getLogger(__name__)


class GovernanceAction(str, Enum):
    UPHOLD = "UPHOLD"        # accept the candidate answer
    KILL = "KILL"            # reject and abstain
    ESCALATE = "ESCALATE"    # defer to human / higher council


@dataclass
class GovernanceDecision:
    decision: GovernanceAction
    reason: str
    final_verdict: str            # human-readable verdict string
    confidence: float = 0.0
    principle_violations: list[str] = field(default_factory=list)
    triggered_by: list[str] = field(default_factory=list)  # antibody names
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "final_verdict": self.final_verdict,
            "confidence": round(float(self.confidence), 4),
            "principle_violations": self.principle_violations,
            "triggered_by": self.triggered_by,
            "metadata": self.metadata,
        }


class PluginFlags(dict[str, Any]):
    """Loose dict alias for per-plugin boolean/metric flags."""


class Governance:
    """
    Central governance authority.

    Decision matrix (simplified):
        - any CRITICAL antibody fail        -> KILL
        - HIGH severity + low council conf  -> KILL
        - HIGH severity + high council conf -> ESCALATE
        - MEDIUM severity                   -> ESCALATE (warn + human review)
        - all pass + high council conf      -> UPHOLD
        - council escalation flag set       -> ESCALATE regardless
    """

    def __init__(self, constitution: Constitution | None = None) -> None:
        self.constitution = constitution or get_default_constitution()
        # tunable thresholds
        self.council_conf_high = 0.75
        self.council_conf_low = 0.45
        self.kill_conf_threshold = 0.15  # [FIX] was 0.3, DNA #5: low conf → UNKNOWN not KILL

    # ------------------------------------------------------------------ #
    def decide(
        self,
        ctx: dict[str, Any] | None,
        verdict: dict[str, Any],
        plugin_flags: dict[str, Any] | None = None,
        council_confidence: float = 1.0,
        council_escalation: bool = False,
    ) -> GovernanceDecision:
        plugin_flags = plugin_flags or {}
        ctx = ctx or {}

        # 1) collect antibody results (if passed in verdict).
        antibody_results: list[dict[str, Any]] = verdict.get("antibody_results", []) or []
        failed_results = [r for r in antibody_results if not r.get("passed", True)]
        raw_severities = [r.get("severity", "info") for r in failed_results]
        # Normalize at the policy boundary. Unknown values stay visible as
        # None and are handled fail-closed below; they must never mean INFO.
        severities = [normalize_severity(raw) for raw in raw_severities]
        unknown_severities = sorted({str(raw) for raw, normalized in zip(raw_severities, severities) if normalized is None})
        triggered_by = [r.get("antibody", "?") for r in failed_results]

        principle_violations: list[str] = []
        action = GovernanceAction.UPHOLD
        reason = "All antibodies passed; council confidence acceptable."
        conf = float(verdict.get("confidence", council_confidence))

        # [ROOT-FIX Task 38-A / Issue 1] Use canonical Severity values at the
        # policy boundary. A failed result is independently unsafe to uphold,
        # even when its provider label is low/info/unknown.
        has_critical = any(s == Severity.CRITICAL.value for s in severities)
        has_high = any(s == Severity.HIGH.value for s in severities)
        has_medium = any(s == Severity.MEDIUM.value for s in severities)
        has_unknown_severity = any(s is None for s in severities)
        has_unresolved_failure = bool(failed_results)
        # Defensive metadata sentinel: CRITICAL/HIGH remain the kill-capable
        # severity set, while branches below distinguish them explicitly.
        _kill_severity_values = {member.value for member in CRITICAL_SEVERITIES}
        _has_kill_severity = any(  # noqa: F841 — audit sentinel
            s in _kill_severity_values for s in severities
        )

        # 2) principle violation mapping
        if has_critical:
            principle_violations.extend([
                self.constitution.get(PrincipleId.SAFETY).name,
                self.constitution.get(PrincipleId.NO_HALLUCINATION).name,
            ])
        if has_high:
            principle_violations.append(self.constitution.get(PrincipleId.ACCURACY).name)
        if verdict.get("hallucination_detected"):
            principle_violations.append(self.constitution.get(PrincipleId.NO_HALLUCINATION).name)
        if verdict.get("missing_evidence"):
            principle_violations.append(self.constitution.get(PrincipleId.EVIDENCE_FIRST).name)
        if plugin_flags.get("privacy_leak"):
            principle_violations.append(self.constitution.get(PrincipleId.PRIVACY).name)

        # 3) decision logic
        # [V104.42 #D] TẠI SAO: Constitution Principle.weight was decorative
        # (0 callers). R14-KB2 DELETED weight field + violation_severity().
        # Now: check Principle.default_action for violated principles — if
        # any has default_action=KILL, override to KILL regardless of severity.
        # [FIX #4] DNA #5: missing_evidence → ESCALATE (not KILL)
        _missing_evidence_safe = verdict.get("missing_evidence") and not verdict.get("hallucination_detected")
        if _missing_evidence_safe:
            # Skip constitution KILL for evidence-starved answers
            action = GovernanceAction.ESCALATE
            reason = "Missing evidence → ESCALATE (DNA #5: not KILL)"
            return GovernanceDecision(
                decision=action, reason=reason,
                final_verdict="UNKNOWN — insufficient evidence",
                confidence=conf, principle_violations=principle_violations,
                triggered_by=triggered_by,
                metadata={"severities": severities, "unknown_severities": unknown_severities,
                          "failed_antibody_count": len(failed_results),
                          "council_confidence": council_confidence,
                          "council_escalation": council_escalation, "plugin_flags": plugin_flags}
            )
        _constitution_kill = False
        for pv in principle_violations:
            for pid in PrincipleId:
                p = self.constitution.get(pid)
                if p and p.name == pv and getattr(p, 'default_action', '') == 'KILL':
                    _constitution_kill = True
                    reason = f"Constitution Principle '{pv}' has default_action=KILL — abstain."
                    break
            if _constitution_kill:
                break

        # [EXEC-2 M4] Constitution KILL is INVOLIABLE — must win over council_escalation.
        # FRESH-3 finding: previously `if council_escalation:` was checked FIRST, so a
        # council ESCALATE could override a Constitution KILL. That violated the
        # Constitution's "inviolable" promise — a principle with default_action=KILL
        # must always result in abstention, never mere escalation. Fix: check
        # `_constitution_kill` FIRST; council_escalation only applies if Constitution
        # does not mandate KILL.
        if _constitution_kill:
            action = GovernanceAction.KILL
            # reason already set above ("Constitution Principle '...' has default_action=KILL — abstain.")
        elif council_escalation:
            action = GovernanceAction.ESCALATE
            reason = "Council explicitly requested escalation."
        elif has_critical:
            action = GovernanceAction.KILL
            reason = "CRITICAL antibody failure — Safety/No-Hallucination violated."
        elif has_high and council_confidence < self.council_conf_low:
            action = GovernanceAction.KILL
            reason = "HIGH severity failure with low council confidence — abstain."
        elif has_high:
            action = GovernanceAction.ESCALATE
            reason = "HIGH severity failure — escalate for human review."
        elif has_medium:
            action = GovernanceAction.ESCALATE
            reason = "MEDIUM severity failure — escalate for human review."
        elif conf < self.kill_conf_threshold:
            action = GovernanceAction.KILL
            reason = f"Confidence {conf:.2f} below kill threshold {self.kill_conf_threshold}."
        # Any failed antibody without a recognized blocking severity must still
        # be visible to a human. This closes the previous error/warning →
        # UPHOLD fall-through while preserving CRITICAL/HIGH/MEDIUM precedence.
        elif has_unknown_severity or has_unresolved_failure:
            action = GovernanceAction.ESCALATE
            if unknown_severities:
                reason = f"Unknown antibody severity {unknown_severities!r} — escalate fail-closed."
            else:
                reason = "Antibody failure without a blocking severity — escalate fail-closed."

        # 4) final verdict string
        final_verdict = self._final_verdict(action, conf, principle_violations, verdict)

        decision = GovernanceDecision(
            decision=action,
            reason=reason,
            final_verdict=final_verdict,
            confidence=conf,
            principle_violations=principle_violations,
            triggered_by=triggered_by,
            metadata={
                "severities": severities,
                "unknown_severities": unknown_severities,
                "failed_antibody_count": len(failed_results),
                "council_confidence": round(float(council_confidence), 4),
                "council_escalation": council_escalation,
                "plugin_flags": plugin_flags,
            },
        )
        logger.info(
            "Governance decision: %s (conf=%.2f) violations=%s",
            action.value, conf, principle_violations,
        )
        # [OPT-14 / Gà §17] Record decision in AntiClosureMeta so we can detect
        # if governance becomes too restrictive (blocks >90% sustained) or too
        # permissive (blocks <5% sustained). Anti-closure itself must not
        # become closure.
        try:
            acm = get_anti_closure_meta()
            acm.record_decision(action.value)
            recent_alert = acm.get_alerts(limit=1)
            if recent_alert:
                decision.metadata["anti_closure_alert"] = recent_alert[-1]
        except Exception as _acm_err:
            logger.debug(f"[Governance] AntiClosureMeta record skipped: {_acm_err}", exc_info=True)
        return decision

    # ------------------------------------------------------------------ #
    @staticmethod
    def _final_verdict(
        action: GovernanceAction,
        conf: float,
        violations: list[str],
        verdict: dict[str, Any],
    ) -> str:
        if action == GovernanceAction.UPHOLD:
            return f"Answer accepted (confidence={conf:.2f})."
        if action == GovernanceAction.KILL:
            v = ", ".join(violations) or "unknown"
            return f"Answer rejected — principle violations: {v}. Abstaining."
        # ESCALATE
        return f"Answer held for human review — confidence={conf:.2f}, violations: {', '.join(violations) or 'none'}."


__all__ = [
    "GovernanceAction",
    "GovernanceDecision",
    "PluginFlags",
    "Governance",
]
