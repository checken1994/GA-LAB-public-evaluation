"""Governed local containment bridge for S10 Risk Intelligence.

Risk Intelligence may recommend bounded containment but never calls tools
itself. The only production effect exposed here is revocation through the
CapabilityAuthority, and only for explicitly owned infrastructure.
"""
from __future__ import annotations

from scp.risk_intelligence.evidence_bundle import EmergencyEvidenceBundle
from scp.security.capability_epoch import CapabilityAuthority


class ContainmentCoordinator:
    def __init__(self, capability_authority: CapabilityAuthority) -> None:
        self.capability_authority = capability_authority

    def contain(self, bundle: EmergencyEvidenceBundle, *, owned_scope: bool,
                actor: str = "governance_authority") -> dict:
        if not owned_scope:
            raise PermissionError("local containment is restricted to owned infrastructure")
        actions = tuple(bundle.recommended_actions or ())
        if not actions:
            raise ValueError("containment requires an evidence-bundle recommendation")
        action = str(actions[0]).strip()
        if not action:
            raise ValueError("containment recommendation is empty")
        status = self.capability_authority.revoke(reason=action, actor=actor)
        return {
            "decision": "CAPABILITY_REVOKED",
            "incident_id": bundle.incident_id,
            "action": action,
            "authority": "CapabilityAuthority",
            "status": status,
        }


__all__ = ["ContainmentCoordinator"]
