"""Behavioral tests for Self-Model and CapabilityMap (26-P0.10).

Validates:
- Complete-SCP reference and bindings resolution
- Capability status transitions across maturity ladder (M1 -> M5)
- Proof SHA isolation (historical proofs from other commits never verify current commit)
- Proof immutability SQLite trigger (capability_proofs_no_update)
- Metadata validation during proof recording (tested_sha and evidence_level exact match)
- Degradation when binding implementation module is missing
- Unknown capability handling (M0_IDEA fallback)
- Blindspot tracking and filtering lifecycle
"""
import sqlite3
from pathlib import Path

import pytest
import yaml

from scp.contracts.maturity import Maturity
from scp.epistemic.evidence_store import EvidenceStore
from scp.self_model.capability_map import CapabilityMap, CapabilityStatus

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_REF = PROJECT_ROOT / "spec" / "complete_scp_reference.yaml"
SPEC_BIND = PROJECT_ROOT / "spec" / "implementation_bindings.yaml"


def _create_map(tmp_path, ref_path=None, bind_path=None):
    ev_store = EvidenceStore(tmp_path / "ev.db", tmp_path / "objs")
    gov_db = tmp_path / "gov.db"
    cmap = CapabilityMap(
        governance_db_path=gov_db,
        evidence_store=ev_store,
        reference_path=ref_path or SPEC_REF,
        bindings_path=bind_path or SPEC_BIND,
    )
    return cmap, ev_store


def test_capability_map_status_transitions_through_maturity_levels(tmp_path):
    cmap, ev_store = _create_map(tmp_path)
    try:
        tested_sha = "commit_sha_12345"
        cap_id = "epistemic.evidence"

        # Baseline: static present (M2)
        base = cmap.recompute_capability(cap_id, tested_sha)
        assert base["status"] == CapabilityStatus.STATIC_PRESENT.value
        assert base["maturity"] == Maturity.M2_STATIC_PRESENT.value

        # Level B proof -> INTEGRATED (M3)
        ev_b = ev_store.observe(
            kind="TEST_RESULT",
            content=b"level B evidence integration test",
            collector_id="pytest",
            collector_version="1.0",
            metadata={"tested_sha": tested_sha, "evidence_level": "B"},
        )
        cmap.record_proof(
            capability_id=cap_id,
            evidence_id=ev_b["evidence_id"],
            evidence_level="B",
            tested_sha=tested_sha,
        )
        res_b = cmap.recompute_capability(cap_id, tested_sha)
        assert res_b["status"] == CapabilityStatus.INTEGRATED.value
        assert res_b["maturity"] == Maturity.M3_INTEGRATED.value

        # Level C proof -> RUNTIME_VERIFIED (M4)
        ev_c = ev_store.observe(
            kind="TEST_RESULT",
            content=b"level C evidence runtime test",
            collector_id="pytest",
            collector_version="1.0",
            metadata={"tested_sha": tested_sha, "evidence_level": "C"},
        )
        cmap.record_proof(
            capability_id=cap_id,
            evidence_id=ev_c["evidence_id"],
            evidence_level="C",
            tested_sha=tested_sha,
        )
        res_c = cmap.recompute_capability(cap_id, tested_sha)
        assert res_c["status"] == CapabilityStatus.RUNTIME_VERIFIED.value
        assert res_c["maturity"] == Maturity.M4_RUNTIME_VERIFIED.value

        # Level D proof -> RECOVERY_VERIFIED (M5)
        ev_d = ev_store.observe(
            kind="TEST_RESULT",
            content=b"level D evidence recovery test",
            collector_id="pytest",
            collector_version="1.0",
            metadata={"tested_sha": tested_sha, "evidence_level": "D"},
        )
        cmap.record_proof(
            capability_id=cap_id,
            evidence_id=ev_d["evidence_id"],
            evidence_level="D",
            tested_sha=tested_sha,
        )
        res_d = cmap.recompute_capability(cap_id, tested_sha)
        assert res_d["status"] == CapabilityStatus.RECOVERY_VERIFIED.value
        assert res_d["maturity"] == Maturity.M5_RECOVERY_VERIFIED.value
    finally:
        cmap.close()
        ev_store.db.close()


def test_capability_map_proof_sha_isolation(tmp_path):
    cmap, ev_store = _create_map(tmp_path)
    try:
        sha_alpha = "commit_sha_alpha"
        sha_beta = "commit_sha_beta"
        cap_id = "epistemic.evidence"

        ev_d = ev_store.observe(
            kind="TEST_RESULT",
            content=b"level D proof for alpha commit",
            collector_id="pytest",
            collector_version="1.0",
            metadata={"tested_sha": sha_alpha, "evidence_level": "D"},
        )
        cmap.record_proof(
            capability_id=cap_id,
            evidence_id=ev_d["evidence_id"],
            evidence_level="D",
            tested_sha=sha_alpha,
        )

        # Recomputing for sha_alpha has M5
        res_alpha = cmap.recompute_capability(cap_id, sha_alpha)
        assert res_alpha["status"] == CapabilityStatus.RECOVERY_VERIFIED.value

        # Recomputing for sha_beta ignores sha_alpha proof
        res_beta = cmap.recompute_capability(cap_id, sha_beta)
        assert res_beta["status"] == CapabilityStatus.STATIC_PRESENT.value
        assert res_beta["maturity"] == Maturity.M2_STATIC_PRESENT.value
        assert any("historical proof(s) belong to other SHA(s) and were ignored" in lim for lim in res_beta["limitations"])
    finally:
        cmap.close()
        ev_store.db.close()


def test_capability_map_immutable_proof_trigger_fails_closed(tmp_path):
    cmap, ev_store = _create_map(tmp_path)
    try:
        tested_sha = "commit_sha_immutable_test"
        cap_id = "epistemic.evidence"
        ev = ev_store.observe(
            kind="TEST_RESULT",
            content=b"immutable proof check",
            collector_id="pytest",
            collector_version="1.0",
            metadata={"tested_sha": tested_sha, "evidence_level": "B"},
        )
        pid = cmap.record_proof(
            capability_id=cap_id,
            evidence_id=ev["evidence_id"],
            evidence_level="B",
            tested_sha=tested_sha,
        )
        with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError), match="capability proof is immutable"):
            cmap.db.execute("UPDATE capability_proofs SET evidence_level='D' WHERE proof_id=?", (pid,))
    finally:
        cmap.close()
        ev_store.db.close()


def test_capability_map_rejects_mismatched_evidence_metadata(tmp_path):
    cmap, ev_store = _create_map(tmp_path)
    try:
        tested_sha = "sha_exact_match"
        cap_id = "epistemic.evidence"
        ev = ev_store.observe(
            kind="TEST_RESULT",
            content=b"metadata mismatch check",
            collector_id="pytest",
            collector_version="1.0",
            metadata={"tested_sha": tested_sha, "evidence_level": "B"},
        )

        with pytest.raises(ValueError, match="tested_sha mismatch"):
            cmap.record_proof(
                capability_id=cap_id,
                evidence_id=ev["evidence_id"],
                evidence_level="B",
                tested_sha="sha_different",
            )

        with pytest.raises(ValueError, match="evidence level mismatch"):
            cmap.record_proof(
                capability_id=cap_id,
                evidence_id=ev["evidence_id"],
                evidence_level="C",
                tested_sha=tested_sha,
            )
    finally:
        cmap.close()
        ev_store.db.close()


def test_capability_map_unknown_capability_returns_m0_idea(tmp_path):
    cmap, ev_store = _create_map(tmp_path)
    try:
        res = cmap.recompute_capability("nonexistent.random.capability", "sha_any")
        assert res["status"] == CapabilityStatus.UNKNOWN.value
        assert res["maturity"] == Maturity.M0_IDEA.value
        assert any("not declared in Complete-SCP reference" in lim for lim in res["limitations"])
    finally:
        cmap.close()
        ev_store.db.close()


def test_capability_map_degraded_when_implementation_missing(tmp_path):
    ref_file = tmp_path / "custom_ref.yaml"
    bind_file = tmp_path / "custom_bind.yaml"

    ref_file.write_text(
        yaml.dump({
            "reference": {"version": "test-v1"},
            "capabilities": {
                "test.missing_impl": {"description": "Capability with missing module"},
            },
        }),
        encoding="utf-8",
    )
    bind_file.write_text(
        yaml.dump({
            "bindings": {
                "test.missing_impl": {
                    "implementations": ["scp.definitely_does_not_exist_module_xyz"],
                },
            },
        }),
        encoding="utf-8",
    )

    cmap, ev_store = _create_map(tmp_path, ref_path=ref_file, bind_path=bind_file)
    try:
        tested_sha = "sha_degraded_test"
        cap_id = "test.missing_impl"

        # Initially degraded/declared because implementation is missing
        base = cmap.recompute_capability(cap_id, tested_sha)
        assert any("missing implementation bindings" in lim for lim in base["limitations"])

        # Recording evidence when module is missing degrades to DEGRADED
        ev = ev_store.observe(
            kind="TEST_RESULT",
            content=b"evidence exists for missing module",
            collector_id="pytest",
            collector_version="1.0",
            metadata={"tested_sha": tested_sha, "evidence_level": "C"},
        )
        cmap.record_proof(
            capability_id=cap_id,
            evidence_id=ev["evidence_id"],
            evidence_level="C",
            tested_sha=tested_sha,
        )

        res = cmap.recompute_capability(cap_id, tested_sha)
        assert res["status"] == CapabilityStatus.DEGRADED.value
        assert any("evidence exists but current implementation binding is unavailable" in lim for lim in res["limitations"])
    finally:
        cmap.close()
        ev_store.db.close()


def test_capability_map_blindspots_lifecycle(tmp_path):
    cmap, ev_store = _create_map(tmp_path)
    try:
        bid = cmap.add_blindspot(
            capability_id="epistemic.evidence",
            unobservable="unreachable kernel worker",
            reason="process crash isolation",
            affected_claims=["claim_durability_1", "claim_durability_2"],
            needed_evidence=["crash_dump_evidence"],
            needed_instrumentation=["os_signal_watcher"],
        )
        assert bid.startswith("blind_")

        all_blindspots = cmap.list_blindspots()
        matching = [b for b in all_blindspots if b["blindspot_id"] == bid]
        assert len(matching) == 1
        assert matching[0]["unobservable"] == "unreachable kernel worker"
        assert matching[0]["status"] == "OPEN"

        # Filtered query
        filtered = cmap.list_blindspots(capability_id="epistemic.evidence")
        assert any(b["blindspot_id"] == bid for b in filtered)

        empty = cmap.list_blindspots(capability_id="unrelated.capability")
        assert len(empty) == 0
    finally:
        cmap.close()
        ev_store.db.close()


def test_capability_map_clean_database_close(tmp_path):
    cmap, ev_store = _create_map(tmp_path)
    try:
        cmap.add_blindspot(
            capability_id="epistemic.evidence",
            unobservable="test",
            reason="test close",
        )
    finally:
        cmap.close()
        ev_store.db.close()

    # Once closed, operating on the connection raises ProgrammingError
    with pytest.raises(sqlite3.ProgrammingError):
        cmap.db.query("SELECT * FROM self_model_blindspots")
