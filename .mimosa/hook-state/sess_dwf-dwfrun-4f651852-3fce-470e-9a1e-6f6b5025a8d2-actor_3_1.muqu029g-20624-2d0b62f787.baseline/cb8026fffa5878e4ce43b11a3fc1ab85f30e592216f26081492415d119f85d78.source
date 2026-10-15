import pytest

from scp.knowledge.contradiction_authority import (
    ContradictionAuthority,
    ContradictionRelation,
)
from scp.knowledge.knowledge_control_db import KnowledgeControlDB


@pytest.fixture
def db(tmp_path):
    return KnowledgeControlDB(tmp_path / "test_knowledge.sqlite")

@pytest.fixture
def auth(db):
    return ContradictionAuthority(db)

def test_assess_temporal_change(auth):
    claim_a = {"id": "c1", "scope": {"env": "prod"}}
    claim_b = {"id": "c2", "scope": {"env": "prod"}}
    ev_a = {"evidence_id": "e1", "observed_at": "2024-01-01T00:00:00Z"}
    ev_b = {"evidence_id": "e2", "observed_at": "2024-01-02T00:00:00Z", "is_update": True}
    
    record = auth.assess_conflict(claim_a, claim_b, ev_a, ev_b)
    assert record.relation == ContradictionRelation.TEMPORAL_CHANGE
    
    cid = auth.register(record)
    assert cid.startswith("ctd_")

def test_assess_scope_mismatch(auth):
    claim_a = {"id": "c1", "scope": {"env": "prod"}}
    claim_b = {"id": "c2", "scope": {"env": "staging"}}
    ev_a = {"evidence_id": "e1", "observed_at": "2024-01-01T00:00:00Z"}
    ev_b = {"evidence_id": "e2", "observed_at": "2024-01-01T00:00:00Z"}
    
    record = auth.assess_conflict(claim_a, claim_b, ev_a, ev_b)
    assert record.relation == ContradictionRelation.SCOPE_MISMATCH

def test_assess_direct_contradiction(auth):
    claim_a = {"id": "c1", "scope": {"env": "prod"}}
    claim_b = {"id": "c2", "scope": {"env": "prod"}}
    ev_a = {"evidence_id": "e1", "observed_at": "2024-01-01T00:00:00Z"}
    ev_b = {"evidence_id": "e2", "observed_at": "2024-01-01T00:00:00Z"}  # Same time
    
    record = auth.assess_conflict(claim_a, claim_b, ev_a, ev_b)
    assert record.relation == ContradictionRelation.DIRECT_CONTRADICTION
