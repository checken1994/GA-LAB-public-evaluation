from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from scp.contracts.time import now_utc_iso
from scp.knowledge.ontology import KnowledgeObject, KnowledgeStatus, validate_transition


class DecisionAction(str, Enum):
    PROMOTE = "PROMOTE"
    HOLD = "HOLD"
    UNDER_REVIEW = "UNDER_REVIEW"
    DEMOTE = "DEMOTE"
    RETIRE = "RETIRE"
    BLOCKED = "BLOCKED"

@dataclass
class PromotionDecision:
    action: DecisionAction | str
    from_status: KnowledgeStatus | str
    to_status: KnowledgeStatus | str
    reason_codes: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    missing_pieces: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    scope: dict[str, Any] = field(default_factory=dict)
    valid_until: str = ""
    decision_timestamp: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.action, str):
            self.action = DecisionAction(self.action.upper())
        if not self.decision_timestamp:
            self.decision_timestamp = now_utc_iso()

@dataclass
class PromotionContext:
    """Contextual evidence provided to the promotion contract."""
    provenance_present: bool = False
    unresolved_structural_contradictions: int = 0
    unresolved_material_contradictions: int = 0
    contradiction_scan_completed: bool = False
    evidence_count: int = 0
    independent_lineage_count: int = 0
    reality_verified: bool = False
    evidence_authority_verified: bool = False
    scope_match: bool = False
    repeated_verification: bool = False
    temporal_stability: bool = False
    adversarial_check_passed: bool = False
    revalidation_failed: bool = False
    obsolete: bool = False

def evaluate_promotion(obj: KnowledgeObject, target_status: KnowledgeStatus, ctx: PromotionContext) -> PromotionDecision:
    """
    Evaluates the machine-readable Knowledge Promotion Contract.
    Returns a PromotionDecision instead of raising exceptions, following fail-closed logic.
    """
    try:
        validate_transition(obj.status, target_status)
    except ValueError as e:
        return PromotionDecision(
            action=DecisionAction.BLOCKED,
            from_status=obj.status,
            to_status=target_status,
            reason_codes=["INVALID_TRANSITION"],
            missing_pieces=[str(e)]
        )

    missing = []
    contradictions = []

    # Check Downward Paths
    if target_status == KnowledgeStatus.UNDER_REVIEW:
        if ctx.revalidation_failed or ctx.unresolved_material_contradictions > 0:
            return PromotionDecision(
                action=DecisionAction.UNDER_REVIEW,
                from_status=obj.status,
                to_status=target_status,
                reason_codes=["EVIDENCE_CONTRADICTION", "REVALIDATION_FAILED"]
            )
        else:
            return PromotionDecision(
                action=DecisionAction.HOLD,
                from_status=obj.status,
                to_status=obj.status,
                reason_codes=["NO_TRIGGER_FOR_REVIEW"]
            )

    if target_status == KnowledgeStatus.RETIRED:
        if ctx.obsolete:
            return PromotionDecision(
                action=DecisionAction.RETIRE,
                from_status=obj.status,
                to_status=target_status,
                reason_codes=["OBSOLETE_KNOWLEDGE"]
            )

    # Check Upward (Promotion) Paths
    if target_status == KnowledgeStatus.CURATED:
        if not obj.scope:
            missing.append("scope_defined")
        if not ctx.provenance_present:
            missing.append("provenance_present")
        if ctx.unresolved_structural_contradictions > 0:
            contradictions.append("unresolved_structural_contradictions")

    elif target_status == KnowledgeStatus.CORROBORATED:
        if len(obj.evidence_refs) < 2 or ctx.evidence_count < 2:
            missing.append("evidence_count >= 2")
        if obj.independent_lineages < 2 or ctx.independent_lineage_count < 2:
            missing.append("independent_lineage >= 2")
        if not ctx.contradiction_scan_completed:
            missing.append("contradiction_scan_completed")

    elif target_status == KnowledgeStatus.VERIFIED:
        if not ctx.reality_verified:
            missing.append("reality_verification")
        if not ctx.evidence_authority_verified:
            missing.append("evidence_authority")
        if not ctx.scope_match:
            missing.append("scope_match")
        if not obj.validity:
            missing.append("validity_window")
        if ctx.unresolved_material_contradictions > 0:
            contradictions.append("unresolved_material_contradictions")

    elif target_status == KnowledgeStatus.GOLD:
        if not ctx.repeated_verification:
            missing.append("repeated_verification")
        if obj.independent_lineages < 3 or ctx.independent_lineage_count < 3:
            missing.append("independent_lineage >= 3")
        if not ctx.temporal_stability:
            missing.append("temporal_stability")
        if not ctx.adversarial_check_passed:
            missing.append("adversarial_check_passed")
        if not ctx.provenance_present:
            missing.append("provenance_complete")

    if missing or contradictions:
        return PromotionDecision(
            action=DecisionAction.HOLD,
            from_status=obj.status,
            to_status=obj.status,  # Held at current status
            reason_codes=["REQUIREMENTS_NOT_MET"],
            missing_pieces=missing,
            contradictions=contradictions,
            scope=obj.scope,
            evidence_refs=obj.evidence_refs
        )

    # If all constraints pass
    return PromotionDecision(
        action=DecisionAction.PROMOTE,
        from_status=obj.status,
        to_status=target_status,
        reason_codes=["ALL_REQUIREMENTS_MET"],
        scope=obj.scope,
        evidence_refs=obj.evidence_refs,
        valid_until=obj.validity.get("ttl", "") if isinstance(obj.validity, dict) else ""
    )
