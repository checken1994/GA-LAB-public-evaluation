
import pytest

from scp.epistemic.evidence_store import EvidenceStore
from scp.knowledge.doubt_engine import (
    DoubtAuthority,
    DoubtType,
    MissingPiece,
)
from scp.self_model.capability_map import CapabilityMap


@pytest.fixture
def mock_capability_map(tmp_path):
    # Mock minimal YAMLs for the real CapabilityMap
    ref_path = tmp_path / "ref.yaml"
    ref_path.write_text("""
capabilities:
  scp.network.http: {}
  scp.local.fs: {}
  scp.host.ssh: {}
""")
    
    bind_path = tmp_path / "bind.yaml"
    bind_path.write_text("""
bindings:
  scp.network.http:
    implementations: ["os"]  # os is importable -> STATIC_PRESENT
  scp.local.fs:
    implementations: ["pathlib"]
  scp.host.ssh:
    implementations: ["some_missing_lib_404"]
""")

    # We need an EvidenceStore
    es_db = tmp_path / "es.sqlite3"
    es = EvidenceStore(str(es_db), str(tmp_path / 'objects'))
    
    cap_db = tmp_path / "cap.sqlite3"
    cap_map = CapabilityMap(
        governance_db_path=cap_db,
        evidence_store=es,
        reference_path=ref_path,
        bindings_path=bind_path
    )
    
    # Let's mock proof to make scp.network.http RUNTIME_VERIFIED
    sha = "abc1234"
    # Insert evidence
    ev_id = es.observe(kind='TEST_RESULT', content=b'test', collector_id='x', collector_version='1', metadata={'tested_sha': 'abc1234', 'evidence_level': 'C'})['evidence_id']
    cap_map.record_proof(
        capability_id="scp.network.http",
        evidence_id=ev_id,
        evidence_level="C",
        tested_sha=sha
    )
    
    yield cap_map, sha

def test_formulate_open_question_with_capability(mock_capability_map):
    cap_map, sha = mock_capability_map
    authority = DoubtAuthority(cap_map, sha)
    
    piece = MissingPiece(
        description="Need to verify API response",
        needed_capability_id="scp.network.http",
        discriminating_observation="HTTP 200 vs HTTP 404"
    )
    
    record = authority.formulate_doubt(
        doubt_id="D-001",
        doubt_type=DoubtType.OPEN_QUESTION,
        unknown_statement="Does the external API exist?",
        blocking_reason="Never called it before",
        dependent_claims=["C-123", "C-124"],
        missing_pieces=[piece],
        hypotheses=["It exists", "It does not exist"]
    )
    
    assert record.id == "D-001"
    assert record.type == DoubtType.OPEN_QUESTION
    # scp.network.http is RUNTIME_VERIFIED (Level C) -> capable!
    assert record.capability_can_obtain is True
    # Should not add blindspot for OPEN_QUESTION if capable
    bs = cap_map.list_blindspots("scp.network.http")
    assert len(bs) == 0

def test_formulate_blind_spot_without_capability(mock_capability_map):
    cap_map, sha = mock_capability_map
    authority = DoubtAuthority(cap_map, sha)
    
    piece = MissingPiece(
        description="Check if server actually rebooted",
        needed_capability_id="scp.host.ssh",
        discriminating_observation="Uptime drops to 0"
    )
    
    record = authority.formulate_doubt(
        doubt_id="D-002",
        doubt_type=DoubtType.BLIND_SPOT,
        unknown_statement="Máy chủ ngoài Internet thực sự đã reboot?",
        blocking_reason="No access to host internals",
        dependent_claims=["C-999"],
        missing_pieces=[piece]
    )
    
    # scp.host.ssh has missing bindings -> DEGRADED/UNKNOWN -> Not capable
    assert record.capability_can_obtain is False
    # A blindspot was registered!
    # Wait, in DoubtAuthority, we only register blindspot if doubt_type != BLIND_SPOT.
    # Because if it's already a BLIND_SPOT doubt, we don't need to double-register, 
    # but let's test a CONTRADICTION missing capability.

def test_formulate_contradiction_registers_blindspot(mock_capability_map):
    cap_map, sha = mock_capability_map
    authority = DoubtAuthority(cap_map, sha)
    
    piece = MissingPiece(
        description="SSH into server to check state",
        needed_capability_id="scp.host.ssh",
        discriminating_observation="Server process running"
    )
    
    record = authority.formulate_doubt(
        doubt_id="D-003",
        doubt_type=DoubtType.CONTRADICTION,
        unknown_statement="Log says success but DB says failed",
        blocking_reason="Conflicting reports",
        dependent_claims=["C-000"],
        missing_pieces=[piece]
    )
    
    assert record.capability_can_obtain is False
    
    # It should have registered a blindspot in CapabilityMap
    blindspots = cap_map.list_blindspots("scp.host.ssh")
    assert len(blindspots) == 1
    assert blindspots[0]["unobservable"] == "Server process running"
