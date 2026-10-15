
from scp.knowledge.ontology import KnowledgeObject, KnowledgeStatus
from scp.knowledge.promotion_contract import (
    DecisionAction,
    PromotionContext,
    evaluate_promotion,
)


def _base_obj() -> KnowledgeObject:
    return KnowledgeObject(
        type="FACT",
        title="Test fact",
        content={"key": "val"},
        status=KnowledgeStatus.RAW,
        scope={"domain": "test"},
        evidence_refs=["ev1", "ev2"],
        independent_lineages=2,
        validity={"ttl": "3600"}
    )

def test_raw_to_curated():
    obj = _base_obj()
    ctx = PromotionContext(provenance_present=True, unresolved_structural_contradictions=0)
    
    # Should pass
    decision = evaluate_promotion(obj, KnowledgeStatus.CURATED, ctx)
    assert decision.action == DecisionAction.PROMOTE
    assert decision.to_status == KnowledgeStatus.CURATED
    
    # Missing scope
    obj_no_scope = _base_obj()
    obj_no_scope.scope = {}
    decision = evaluate_promotion(obj_no_scope, KnowledgeStatus.CURATED, ctx)
    assert decision.action == DecisionAction.HOLD
    assert "scope_defined" in decision.missing_pieces
        
    # Missing provenance
    ctx.provenance_present = False
    decision = evaluate_promotion(obj, KnowledgeStatus.CURATED, ctx)
    assert decision.action == DecisionAction.HOLD
    assert "provenance_present" in decision.missing_pieces
    ctx.provenance_present = True
    
    # Structural contradiction
    ctx.unresolved_structural_contradictions = 1
    decision = evaluate_promotion(obj, KnowledgeStatus.CURATED, ctx)
    assert decision.action == DecisionAction.HOLD
    assert "unresolved_structural_contradictions" in decision.contradictions

def test_curated_to_corroborated():
    obj = _base_obj()
    obj.status = KnowledgeStatus.CURATED
    ctx = PromotionContext(
        evidence_count=2,
        independent_lineage_count=2,
        contradiction_scan_completed=True
    )
    decision = evaluate_promotion(obj, KnowledgeStatus.CORROBORATED, ctx)
    assert decision.action == DecisionAction.PROMOTE
    
    # Not enough evidence
    ctx.evidence_count = 1
    decision = evaluate_promotion(obj, KnowledgeStatus.CORROBORATED, ctx)
    assert decision.action == DecisionAction.HOLD
    assert "evidence_count >= 2" in decision.missing_pieces
    ctx.evidence_count = 2
    
    # Not enough lineage
    ctx.independent_lineage_count = 1
    decision = evaluate_promotion(obj, KnowledgeStatus.CORROBORATED, ctx)
    assert decision.action == DecisionAction.HOLD
    assert "independent_lineage >= 2" in decision.missing_pieces
    
def test_corroborated_to_verified():
    obj = _base_obj()
    obj.status = KnowledgeStatus.CORROBORATED
    ctx = PromotionContext(
        reality_verified=True,
        evidence_authority_verified=True,
        scope_match=True,
        unresolved_material_contradictions=0
    )
    decision = evaluate_promotion(obj, KnowledgeStatus.VERIFIED, ctx)
    assert decision.action == DecisionAction.PROMOTE
    
    # No reality check
    ctx.reality_verified = False
    decision = evaluate_promotion(obj, KnowledgeStatus.VERIFIED, ctx)
    assert decision.action == DecisionAction.HOLD
    assert "reality_verification" in decision.missing_pieces

def test_verified_to_gold():
    obj = _base_obj()
    obj.status = KnowledgeStatus.VERIFIED
    obj.independent_lineages = 3
    ctx = PromotionContext(
        repeated_verification=True,
        independent_lineage_count=3,
        temporal_stability=True,
        adversarial_check_passed=True,
        provenance_present=True
    )
    decision = evaluate_promotion(obj, KnowledgeStatus.GOLD, ctx)
    assert decision.action == DecisionAction.PROMOTE
    
    # Less than 3 lineages
    ctx.independent_lineage_count = 2
    decision = evaluate_promotion(obj, KnowledgeStatus.GOLD, ctx)
    assert decision.action == DecisionAction.HOLD
    assert "independent_lineage >= 3" in decision.missing_pieces

def test_downward_paths():
    obj = _base_obj()
    obj.status = KnowledgeStatus.VERIFIED
    ctx = PromotionContext(revalidation_failed=True)
    
    # Send to UNDER_REVIEW
    decision = evaluate_promotion(obj, KnowledgeStatus.UNDER_REVIEW, ctx)
    assert decision.action == DecisionAction.UNDER_REVIEW
    assert "REVALIDATION_FAILED" in decision.reason_codes
    
    # Obsolete to RETIRED
    ctx_retire = PromotionContext(obsolete=True)
    decision = evaluate_promotion(obj, KnowledgeStatus.RETIRED, ctx_retire)
    assert decision.action == DecisionAction.RETIRE
    assert "OBSOLETE_KNOWLEDGE" in decision.reason_codes

def test_invalid_jumps():
    obj = _base_obj()
    ctx = PromotionContext()
    # RAW cannot jump to VERIFIED
    decision = evaluate_promotion(obj, KnowledgeStatus.VERIFIED, ctx)
    assert decision.action == DecisionAction.BLOCKED
    assert "INVALID_TRANSITION" in decision.reason_codes
