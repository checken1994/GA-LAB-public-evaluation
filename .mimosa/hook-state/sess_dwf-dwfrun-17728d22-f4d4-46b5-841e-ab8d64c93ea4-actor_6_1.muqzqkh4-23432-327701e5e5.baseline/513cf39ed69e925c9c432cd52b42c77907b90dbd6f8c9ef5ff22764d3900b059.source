import pytest

from scp.knowledge.knowledge_control_db import KnowledgeControlDB
from scp.knowledge.promotion_authority import DecisionAction, PromotionAuthority


@pytest.fixture
def fixture_db(tmp_path):
    return KnowledgeControlDB(tmp_path / "test_knowledge.sqlite")

@pytest.fixture
def auth(fixture_db):
    return PromotionAuthority(fixture_db, "spec/knowledge_promotion.yaml")

def test_promotion_raw_to_curated_pass(auth):
    context = {
        "schema_valid": True,
        "scope_defined": True,
        "provenance_present": True
    }
    decision = auth.assess("k1", "RAW", "CURATED", context)
    assert decision.action == DecisionAction.PROMOTE
    assert decision.decided_status == "CURATED"
    
    auth.commit(decision)
    history = auth.db.get_knowledge_history("k1")
    assert len(history) == 1
    assert history[0]["to_status"] == "CURATED"

def test_promotion_curated_to_corroborated_fail(auth):
    # Missing independent_support_policy
    context = {
        "unresolved_material_contradictions": 0
    }
    decision = auth.assess("k1", "CURATED", "CORROBORATED", context)
    assert decision.action == DecisionAction.HOLD
    assert decision.decided_status == "CURATED" # stays at curated
    assert len(decision.missing_pieces) > 0
    assert "independent_support_policy" in decision.missing_pieces[0]

def test_promotion_unknown_profile(auth):
    decision = auth.assess("k1", "RAW", "CURATED", {}, profile_name="nonexistent")
    assert decision.action == DecisionAction.BLOCKED
    assert "BLOCKED_UNKNOWN_PROMOTION_POLICY" in decision.reason_codes
