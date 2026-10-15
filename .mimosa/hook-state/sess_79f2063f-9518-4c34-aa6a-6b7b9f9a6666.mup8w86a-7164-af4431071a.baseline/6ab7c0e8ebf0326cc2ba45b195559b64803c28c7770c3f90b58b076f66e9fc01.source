"""
SCP V98 — AttackPolicyEngine
Copyright (c) 2026 Minh. MIT License.

MỚI (implement từ scratch) — safety gates + decision matrix cho counter response.

Naming convention: <Purpose>Engine (world standard).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("scp.security.attack_policy")


@dataclass
class AttackPolicy:
    """Policy quyết định phase phản công."""
    phase: int = 0  # 0 (skip) | 1 | 2 | 3
    actions: list[str] = field(default_factory=list)
    notes: str = ""
    safe_to_counter: bool = False
    counter_risk_level: str = "unknown"  # unknown | safe | low | medium | high

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "actions": self.actions,
            "notes": self.notes,
            "safe_to_counter": self.safe_to_counter,
            "counter_risk_level": self.counter_risk_level,
        }


class AttackPolicyEngine:
    """Decide counter response phase based on classification + governance + target verify.

    Naming convention: <Purpose>Engine (world standard).

    Phase rules:
      Phase 0: skip — no counter needed
      Phase 1: LOG + ALERT + BLOCK IP (no honeypot)
      Phase 2: TARPIT + CANARY + HONEYPOT (only if safe_to_counter)
      Phase 3: POISON + REVERSE_PROBE (only if safe + critical severity)

    Safety gates (IRON RULES — không bao giờ violate):
      - safe_to_counter == False → Phase 1 only
      - verified_target == False → Phase 1 only
      - residential/tor/shared → Phase 1 only, KHÔNG BAO GIỜ escalate
      - Phase 3 → bắt buộc audit log + human alert
    """

    def decide(
        self,
        classification: dict[str, Any],
        target_verification: dict[str, Any] | None = None,
        governance_decision: dict[str, Any] | None = None,
    ) -> AttackPolicy:
        """Decide phase + actions based on inputs.

        Args:
            classification: Dict with actor, attack_type, severity, confidence
            target_verification: Dict with safe_to_counter, is_residential, is_tor, etc.
            governance_decision: Dict with decision (UPHOLD/KILL/ESCALATE)

        Returns:
            AttackPolicy with phase + actions
        """
        severity = classification.get("severity", "none")
        actor = classification.get("actor", "human")
        attack_type = classification.get("attack_type", "none")

        target_verification = target_verification or {}
        safe_to_counter = target_verification.get("safe_to_counter", False)
        is_residential = target_verification.get("is_residential", False)
        is_tor = target_verification.get("is_tor", False)
        is_shared = target_verification.get("is_shared_hosting", False)

        governance_decision = governance_decision or {}
        gov_action = governance_decision.get("decision", "UPHOLD")

        # Initialize policy
        policy = AttackPolicy(
            phase=0,
            actions=[],
            notes="",
            safe_to_counter=safe_to_counter,
            counter_risk_level=target_verification.get("counter_risk_level", "unknown"),
        )

        # === SAFETY GATES (IRON RULES) ===
        # If residential/tor/shared → Phase 1 MAX, never escalate
        if is_residential or is_tor or is_shared:
            policy.notes = "SAFETY GATE: residential/tor/shared → Phase 1 only"
            if severity in ("high", "critical"):
                policy.phase = 1
                policy.actions = ["log", "alert_human", "block_ip"]
            elif severity == "medium":
                policy.phase = 1
                policy.actions = ["log", "alert_human"]
            else:
                policy.phase = 1 if attack_type != "none" else 0
                policy.actions = ["log"] if policy.phase == 1 else []
            return policy

        # If not safe_to_counter → Phase 1 only
        if not safe_to_counter:
            policy.notes = "SAFETY GATE: safe_to_counter=False → Phase 1 only"
            if severity in ("high", "critical", "medium"):
                policy.phase = 1
                policy.actions = ["log", "alert_human", "block_ip"]
            elif severity == "low":
                policy.phase = 1
                policy.actions = ["log", "alert_human"]
            else:
                policy.phase = 0
            return policy

        # === GOVERNANCE OVERRIDE ===
        if gov_action == "UPHOLD":
            # Governance said OK — no counter needed
            policy.phase = 0
            policy.notes = "Governance UPHOLD — no counter"
            return policy

        if gov_action == "ESCALATE":
            # Governance said escalate — Phase 1 + human review
            policy.phase = 1
            policy.actions = ["log", "alert_human", "human_review"]
            policy.notes = "Governance ESCALATE — human review required"
            return policy

        # gov_action == "KILL" — proceed with counter based on severity

        # === PHASE DECISION (safe_to_counter == True) ===
        if severity == "critical" and attack_type in ("injection", "exfil"):
            # Phase 3: POISON + REVERSE_PROBE
            policy.phase = 3
            policy.actions = [
                "log", "alert_human", "block_ip",
                "tarpit", "canary_inject", "honeypot",
                "poison_response", "reverse_probe",
                "audit_log",  # bắt buộc Phase 3
            ]
            policy.notes = "Phase 3: critical injection/exfil — full counter"
        elif severity in ("critical", "high") and actor == "ai_agent_2026":
            # Phase 2: TARPIT + CANARY + HONEYPOT
            policy.phase = 2
            policy.actions = ["log", "alert_human", "block_ip", "tarpit", "canary_inject", "honeypot"]
            policy.notes = "Phase 2: ai_agent_2026 + high/critical"
        elif severity == "medium":
            # Phase 1: LOG + ALERT + BLOCK
            policy.phase = 1
            policy.actions = ["log", "alert_human", "block_ip"]
            policy.notes = "Phase 1: medium severity"
        elif severity == "low":
            # Phase 1: LOG only
            policy.phase = 1
            policy.actions = ["log"]
            policy.notes = "Phase 1: low severity"
        else:
            # No counter
            policy.phase = 0
            policy.notes = "No counter needed"

        return policy


__all__ = ["AttackPolicy", "AttackPolicyEngine"]
