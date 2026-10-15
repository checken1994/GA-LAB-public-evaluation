"""Comprehensive functional tests for Epistemic Engine (26-P0.05 - 26-P0.07).

Validates:
- EvidenceStore immutability trigger (evidence_no_update)
- Record tampering detection (record_hash mismatch)
- Blob tampering detection (C4 tamper / hash mismatch)
- Missing blob fail-closed behavior
- Retention payload purging and event auditing
- Evidence superseding and link relations
- Orphan blob scanning and staging cleanup
- LineageStore DB default UNKNOWN_INDEPENDENCE
- Independence requires explicit basis
- Independence assessment and shared-lineage collapsing
- URL canonicalization and credential stripping
- Repository canonicalization and hex sha verification
- FalsificationEngine skeptical status and deviation thresholds
- EpistemicBoundary contradiction recording into OpenQuestionAuthority
"""
import sqlite3

import pytest

from scp.epistemic.evidence_store import EvidenceIntegrityError, EvidenceStore
from scp.epistemic.lineage import IndependenceStatus, LineageStore
from scp.epistemic.source_identity import (
    canonicalize_repository,
    canonicalize_url,
)
from scp.knowledge.open_question_authority import QuestionTrigger
from scp.meta.epistemic_boundary import EpistemicBoundary, MissingPieceFinding
from scp.meta.falsification_engine import (
    Deviation,
    FalsificationEngine,
    FalsificationStatus,
)


def test_evidence_store_immutable_trigger_fails_closed(tmp_path):
    store = EvidenceStore(tmp_path / "ev.db", tmp_path / "objs")
    try:
        ev = store.observe(
            kind="TEST_RESULT",
            content=b"initial test result",
            collector_id="pytest",
            collector_version="1.0",
        )
        with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError), match="evidence is immutable - supersede instead"):
            store.db.execute(
                "UPDATE evidence SET kind='FILE_OBSERVATION' WHERE evidence_id=?",
                (ev["evidence_id"],),
            )
    finally:
        store.db.close()


def test_evidence_store_record_tampering_fails_closed(tmp_path):
    store = EvidenceStore(tmp_path / "ev.db", tmp_path / "objs")
    try:
        ev = store.observe(
            kind="TEST_RESULT",
            content=b"legitimate observation",
            collector_id="pytest",
            collector_version="1.0",
        )
        # Drop trigger to simulate out-of-band / offline DB tampering
        store.db.execute("DROP TRIGGER IF EXISTS evidence_no_update")
        store.db.execute(
            "UPDATE evidence SET collector_id='hacked_collector' WHERE evidence_id=?",
            (ev["evidence_id"],),
        )
        store.db._conn.commit()

        check = store.verify_integrity(ev["evidence_id"])
        assert check["ok"] is False
        assert any("record_hash mismatch" in err for err in check["errors"])

        with pytest.raises(EvidenceIntegrityError, match="failed integrity"):
            store.get(ev["evidence_id"])
    finally:
        store.db.close()


def test_evidence_store_blob_tampering_c4_fails_closed(tmp_path):
    store = EvidenceStore(tmp_path / "ev.db", tmp_path / "objs")
    try:
        ev = store.observe(
            kind="TEST_RESULT",
            content=b"original data for C4 check",
            collector_id="pytest",
            collector_version="1.0",
        )
        blob_path = tmp_path / "objs" / ev["content_ref"]
        assert blob_path.is_file()
        blob_path.write_bytes(b"tampered content bytes")

        check = store.verify_integrity(ev["evidence_id"])
        assert check["ok"] is False
        assert check["payload_state"] == "MISSING"
        assert any("blob content hash mismatch (C4 tamper)" in err for err in check["errors"])

        with pytest.raises(EvidenceIntegrityError, match="failed integrity"):
            store.read_content(ev["evidence_id"])
    finally:
        store.db.close()


def test_evidence_store_missing_blob_fails_closed(tmp_path):
    store = EvidenceStore(tmp_path / "ev.db", tmp_path / "objs")
    try:
        ev = store.observe(
            kind="TEST_RESULT",
            content=b"data to be removed",
            collector_id="pytest",
            collector_version="1.0",
        )
        blob_path = tmp_path / "objs" / ev["content_ref"]
        blob_path.unlink()

        check = store.verify_integrity(ev["evidence_id"])
        assert check["ok"] is False
        assert any("blob file missing (C4)" in err for err in check["errors"])

        with pytest.raises(EvidenceIntegrityError, match="failed integrity"):
            store.read_content(ev["evidence_id"])
    finally:
        store.db.close()


def test_evidence_store_purge_payload_and_retention_event(tmp_path):
    store = EvidenceStore(tmp_path / "ev.db", tmp_path / "objs")
    try:
        ev = store.observe(
            kind="TEST_RESULT",
            content=b"content subject to GDPR",
            collector_id="pytest",
            collector_version="1.0",
        )
        blob_path = tmp_path / "objs" / ev["content_ref"]
        assert blob_path.is_file()

        ret_id = store.purge_payload(
            ev["evidence_id"],
            reason="GDPR erasure request",
            policy="retention-v1",
        )
        assert ret_id.startswith("ret_")
        assert not blob_path.exists()

        rows = store.db.query(
            "SELECT * FROM retention_events WHERE retention_event_id=?", (ret_id,)
        )
        assert len(rows) == 1
        assert rows[0]["target"] == ev["evidence_id"]
        assert rows[0]["reason"] == "GDPR erasure request"
        assert rows[0]["policy"] == "retention-v1"

        with pytest.raises(EvidenceIntegrityError, match="failed integrity"):
            store.read_content(ev["evidence_id"])
    finally:
        store.db.close()


def test_evidence_store_supersede_and_link(tmp_path):
    store = EvidenceStore(tmp_path / "ev.db", tmp_path / "objs")
    try:
        ev1 = store.observe(
            kind="TEST_RESULT",
            content=b"initial version v1",
            collector_id="pytest",
            collector_version="1.0",
        )
        replacement = store.supersede(
            ev1["evidence_id"],
            kind="TEST_RESULT",
            content=b"corrected version v2",
            collector_id="pytest",
            collector_version="1.0",
        )
        assert replacement["evidence_id"] != ev1["evidence_id"]

        links = store.db.query(
            "SELECT * FROM evidence_links WHERE parent_evidence_id=? AND child_evidence_id=?",
            (ev1["evidence_id"], replacement["evidence_id"]),
        )
        assert len(links) == 1
        assert links[0]["relation"] == "SUPERSEDES"

        # ev1 is unaltered in table
        orig = store.get(ev1["evidence_id"])
        assert orig["content_hash"] == ev1["content_hash"]
    finally:
        store.db.close()


def test_evidence_store_scan_orphans_and_staging_cleanup(tmp_path):
    store = EvidenceStore(tmp_path / "ev.db", tmp_path / "objs")
    try:
        orphan_blob = tmp_path / "objs" / "sha256" / "fa" / "ce" / "facefeed12345678"
        orphan_blob.parent.mkdir(parents=True, exist_ok=True)
        orphan_blob.write_bytes(b"unreferenced orphaned blob data")

        leftover_staging = tmp_path / "objs" / ".staging" / "staged_leftover.hex"
        leftover_staging.parent.mkdir(parents=True, exist_ok=True)
        leftover_staging.write_bytes(b"staging leftover from crash")

        orphans = store.scan_orphans()
        assert str(orphan_blob) in orphans

        # Re-instantiating store cleans up .staging leftovers
        store2 = EvidenceStore(tmp_path / "ev.db", tmp_path / "objs")
        try:
            assert not leftover_staging.exists()
        finally:
            store2.db.close()
    finally:
        store.db.close()


def test_lineage_store_unknown_independence_default(tmp_path):
    lineage = LineageStore(tmp_path / "lineage.db")
    try:
        rel = lineage.ensure_relation("src_beta", "src_alpha")
        assert rel.source_a == "src_alpha"
        assert rel.source_b == "src_beta"
        assert rel.status == IndependenceStatus.UNKNOWN_INDEPENDENCE
    finally:
        lineage.close()


def test_lineage_store_independent_requires_explicit_basis(tmp_path):
    lineage = LineageStore(tmp_path / "lineage.db")
    try:
        with pytest.raises(ValueError, match="INDEPENDENT requires an explicit independence basis"):
            lineage.record_relation(
                "src_1",
                "src_2",
                status=IndependenceStatus.INDEPENDENT,
                basis=[{"type": "different_domain"}],
            )

        rel = lineage.record_relation(
            "src_1",
            "src_2",
            status=IndependenceStatus.INDEPENDENT,
            basis=[{"type": "independent_primary_observation"}],
        )
        assert rel.status == IndependenceStatus.INDEPENDENT
    finally:
        lineage.close()


def test_lineage_store_assess_independent_support_collapses_shared(tmp_path):
    lineage = LineageStore(tmp_path / "lineage.db")
    try:
        lineage.record_relation(
            "s1", "s2",
            status=IndependenceStatus.SAME_LINEAGE,
            basis=[{"type": "same_author"}],
        )
        lineage.record_relation(
            "s3", "s4",
            status=IndependenceStatus.LIKELY_SHARED_LINEAGE,
            basis=[{"type": "syndication"}],
        )
        for a in ("s1", "s2"):
            for b in ("s3", "s4"):
                lineage.record_relation(
                    a, b,
                    status=IndependenceStatus.INDEPENDENT,
                    basis=[{"type": "explicit_distinct_origin"}],
                )

        res = lineage.assess_independent_support(["s1", "s2", "s3", "s4"])
        assert res["source_count"] == 4
        assert res["shared_components"] == [["s1", "s2"], ["s3", "s4"]]
        assert res["known_independent_lineages"] == 2
        assert res["shared_lineage_pairs"] == 2
    finally:
        lineage.close()


def test_source_store_url_canonicalization_and_credential_rejection():
    u1 = canonicalize_url("HTTP://EXAMPLE.COM:80/path?x=1#frag")
    assert u1 == "http://example.com/path?x=1"

    u2 = canonicalize_url("https://example.com:443/")
    assert u2 == "https://example.com/"

    with pytest.raises(ValueError, match="credentials"):
        canonicalize_url("http://user:pass@example.com/")

    with pytest.raises(ValueError, match="http/https"):
        canonicalize_url("ftp://example.com/file")


def test_source_store_repo_canonicalization():
    repo = canonicalize_repository(
        repository="owner/repo",
        commit_sha="a1b2c3d4",
        path="src/lib.py",
    )
    assert repo == "github:owner/repo@a1b2c3d4:src/lib.py"

    with pytest.raises(ValueError, match="hexadecimal"):
        canonicalize_repository(
            repository="owner/repo",
            commit_sha="invalid_sha_g!",
            path="src/lib.py",
        )

    with pytest.raises(ValueError, match="owner/name"):
        canonicalize_repository(repository="invalidrepo")


def test_falsification_engine_skeptical_status_and_deviations():
    assert FalsificationStatus.UNREFUTED_IN_CURRENT_SCOPE.is_skeptical() is True
    assert FalsificationStatus.NO_CONTRADICTION_FOUND.is_skeptical() is True
    assert FalsificationStatus.HUMAN_DECISION_REQUIRED.requires_human() is True
    assert FalsificationStatus.REFUTED_BY_REALITY.requires_human() is True

    assert FalsificationEngine._classify_severity(0.015) == "LOW"
    assert FalsificationEngine._classify_severity(0.08) == "MEDIUM"
    assert FalsificationEngine._classify_severity(0.20) == "HIGH"
    assert FalsificationEngine._classify_severity(0.30) == "CRITICAL"

    dev = Deviation(
        field="revenue",
        llm_value="100",
        reference_value="120",
        delta=0.1667,
        severity="HIGH",
    )
    d_dict = dev.to_dict()
    assert d_dict["field"] == "revenue"
    assert d_dict["severity"] == "HIGH"
    assert d_dict["delta"] == 0.1667


def test_epistemic_boundary_records_contradiction_and_open_question(tmp_path):
    db_file = tmp_path / "learning.sqlite"
    boundary = EpistemicBoundary(db_path=str(db_file))
    finding = MissingPieceFinding(
        blind_spot="network timeout",
        affected_coverage="web_test",
        evidence_refs=["ev_12345"],
    )
    boundary.record_contradiction(finding)
    assert boundary.verdict == "CONTRADICTED"
    assert len(boundary.findings) == 1

    with sqlite3.connect(db_file) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM open_questions").fetchall()
        assert len(rows) >= 1
        assert rows[0]["trigger"] == QuestionTrigger.CONTRADICTION.value
        assert "web_test" in rows[0]["question"]

        mp_rows = conn.execute("SELECT * FROM missing_pieces").fetchall()
        assert len(mp_rows) >= 1
        assert "network timeout" in mp_rows[0]["description"]
