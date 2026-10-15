from __future__ import annotations

from pathlib import Path

import pytest

from scp.epistemic.evidence_store import EvidenceStore
from scp.self_model import CapabilityMap

ROOT = Path(__file__).resolve().parents[2]


def _make(tmp_path):
    evidence = EvidenceStore(tmp_path / "epistemic.sqlite", tmp_path / "objects")
    model = CapabilityMap(
        governance_db_path=tmp_path / "governance.sqlite",
        evidence_store=evidence,
        reference_path=ROOT / "spec" / "complete_scp_reference.yaml",
        bindings_path=ROOT / "spec" / "implementation_bindings.yaml",
    )
    return evidence, model


def _proof(evidence, *, sha: str, level: str):
    return evidence.observe(
        kind="TEST_RESULT",
        content=f"proof-{sha}-{level}".encode(),
        collector_id="pytest",
        collector_version="1",
        metadata={"tested_sha": sha, "evidence_level": level},
    )


def test_self_model_has_no_direct_mark_verified_api(tmp_path):
    evidence, model = _make(tmp_path)
    assert not hasattr(model, "mark_verified")
    state = model.recompute_capability("epistemic.evidence", "sha-A")
    assert state["maturity"] == "M2"  # importable != runtime proof
    assert state["status"] == "STATIC_PRESENT"
    model.close()
    evidence.db.close()


def test_same_sha_c_evidence_is_required_for_runtime_verified(tmp_path):
    evidence, model = _make(tmp_path)
    old = _proof(evidence, sha="sha-old", level="C")
    model.record_proof(
        capability_id="epistemic.evidence",
        evidence_id=old["evidence_id"],
        evidence_level="C",
        tested_sha="sha-old",
    )
    state = model.recompute_capability("epistemic.evidence", "sha-new")
    assert state["maturity"] == "M2"
    assert "historical proof" in " ".join(state["limitations"])

    current = _proof(evidence, sha="sha-new", level="C")
    model.record_proof(
        capability_id="epistemic.evidence",
        evidence_id=current["evidence_id"],
        evidence_level="C",
        tested_sha="sha-new",
    )
    state = model.recompute_capability("epistemic.evidence", "sha-new")
    assert state["maturity"] == "M4"
    assert state["status"] == "RUNTIME_VERIFIED"
    assert current["evidence_id"] in state["evidence_refs"]
    model.close()
    evidence.db.close()


def test_proof_metadata_must_match_requested_sha_and_level(tmp_path):
    evidence, model = _make(tmp_path)
    ev = _proof(evidence, sha="sha-A", level="B")
    with pytest.raises(ValueError):
        model.record_proof(
            capability_id="epistemic.evidence",
            evidence_id=ev["evidence_id"],
            evidence_level="C",
            tested_sha="sha-A",
        )
    with pytest.raises(ValueError):
        model.record_proof(
            capability_id="epistemic.evidence",
            evidence_id=ev["evidence_id"],
            evidence_level="B",
            tested_sha="sha-B",
        )
    model.close()
    evidence.db.close()
