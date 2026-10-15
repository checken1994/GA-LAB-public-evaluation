import os
import tempfile

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.epistemic import EVIDENCE_KINDS, EvidenceStore


def test_subsystem_epistemic_importable():
    """Epistemic evidence store: verify observing, persisting, and reading evidence records."""
    assert "TEST_RESULT" in EVIDENCE_KINDS
    assert "RUNTIME_OBSERVATION" in EVIDENCE_KINDS
    
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "ev.sqlite3")
        obj_dir = os.path.join(td, "objects")
        store = EvidenceStore(db_path, obj_dir)
        try:
            ev = store.observe(
                kind="TEST_RESULT",
                content=b"test run: 100% pass",
                collector_id="pytest",
                collector_version="1.0",
                metadata={"test_file": "test_subsystem_epistemic.py"},
            )
            assert ev["evidence_id"].startswith("ev_")
            assert ev["kind"] == "TEST_RESULT"
            
            # Read back payload
            content = store.read_content(ev["evidence_id"])
            assert content == b"test run: 100% pass"
        finally:
            store.db.close()
