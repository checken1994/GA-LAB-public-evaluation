import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scp.epistemic import EvidenceIntegrityError, EvidenceStore

# ==============================================================================
# T06 - EVIDENCE STORE (26-P0.05): immutable core, content dedupe, occurrence
# preservation, restart persistence, tamper detection, orphan reconciliation,
# missing-blob fail-closed.
# ==============================================================================


def _store(tmp_path):
    return EvidenceStore(tmp_path / "epistemic.sqlite3", tmp_path / "objects")


def _observe(store, content=b"observed-payload", **overrides):
    kwargs = dict(
        kind="RUNTIME_OBSERVATION",
        content=content,
        collector_id="test-collector",
        collector_version="1.0",
    )
    kwargs.update(overrides)
    return store.observe(**kwargs)


def test_same_content_twice_same_blob_two_occurrences(tmp_path):
    store = _store(tmp_path)
    first = _observe(store)
    second = _observe(store, metadata={"fetch": "second"})

    assert first["evidence_id"] != second["evidence_id"], "occurrence identity must never be deduped"
    assert first["content_hash"] == second["content_hash"], "content identity must match"
    blobs = store.db.query("SELECT COUNT(*) AS n FROM content_blobs")
    assert blobs[0]["n"] == 1, "content blob must be stored exactly once"
    assert store.read_content(first["evidence_id"]) == b"observed-payload"
    assert store.read_content(second["evidence_id"]) == b"observed-payload"


def test_evidence_table_is_machine_immutable(tmp_path):
    store = _store(tmp_path)
    record = _observe(store)
    with pytest.raises(Exception) as exc_info:
        store.db.execute(
            "UPDATE evidence SET source_id='tampered' WHERE evidence_id=?", (record["evidence_id"],)
        )
    assert "immutable" in str(exc_info.value), "the immutability trigger must abort raw UPDATEs"


def test_restart_persistence_and_tamper_detection(tmp_path):
    db_path = tmp_path / "epistemic.sqlite3"
    objects = tmp_path / "objects"
    store = EvidenceStore(db_path, objects)
    record = _observe(store, content=b"durable-bytes", source_id="src_1")
    store.db.close()

    reopened = EvidenceStore(db_path, objects)
    assert reopened.read_content(record["evidence_id"]) == b"durable-bytes"

    # Tamper with the payload on disk -> fail-closed, never returned as valid.
    blob = objects / record["content_ref"]
    blob.write_bytes(b"tampered-bytes")
    with pytest.raises(EvidenceIntegrityError, match="hash mismatch"):
        reopened.get(record["evidence_id"])

    # Missing blob (C4) -> fail-closed with MISSING state, metadata still durable.
    blob.unlink()
    with pytest.raises(EvidenceIntegrityError, match="MISSING"):
        reopened.get(record["evidence_id"])
    row = reopened.db.query(
        "SELECT source_id, kind FROM evidence WHERE evidence_id=?", (record["evidence_id"],)
    )
    assert row and row[0]["source_id"] == "src_1"


def test_supersede_never_rewrites_history(tmp_path):
    store = _store(tmp_path)
    old = _observe(store, content=b"old-value")
    new = store.supersede(
        old["evidence_id"],
        kind="RUNTIME_OBSERVATION",
        content=b"corrected-value",
        collector_id="test-collector",
        collector_version="1.1",
    )
    assert old["evidence_id"] != new["evidence_id"]
    links = store.db.query(
        "SELECT relation FROM evidence_links WHERE parent_evidence_id=? AND child_evidence_id=?",
        (old["evidence_id"], new["evidence_id"]),
    )
    assert links and links[0]["relation"] == "SUPERSEDES"
    assert store.read_content(old["evidence_id"]) == b"old-value", "history must survive the correction"


def test_crash_rollback_leaves_orphan_blob_and_reconciles(tmp_path, monkeypatch):
    """C2/C3: DB transaction rolls back after the blob was renamed -> the blob
    becomes an orphan that the scanner must find (never silently trusted)."""
    from scp.epistemic import evidence_store as es_module

    store = _store(tmp_path)
    fixed_id = "ev_" + "0" * 24
    monkeypatch.setattr(es_module, "new_id", lambda prefix: fixed_id)

    _observe(store, content=b"forced-id-blob")  # consumes the fixed id
    with pytest.raises(Exception):
        _observe(store, content=b"second-occurrence-same-id")  # PK conflict -> rollback

    count = store.db.query("SELECT COUNT(*) AS n FROM evidence")[0]["n"]
    assert count == 1, "failed occurrence must not leave a half-written evidence row"
    orphans = store.scan_orphans()
    assert len(orphans) == 1, f"renamed-but-unreferenced blob must be reported as orphan: {orphans}"


def test_purge_keeps_metadata_and_records_retention_event(tmp_path):
    store = _store(tmp_path)
    record = _observe(store, content=b"purge-me")
    event_id = store.purge_payload(record["evidence_id"], reason="raw expired", policy="raw_7d")

    assert event_id.startswith("ret_")
    with pytest.raises(EvidenceIntegrityError, match="PURGED"):
        store.get(record["evidence_id"])
    events = store.db.query("SELECT reason, policy FROM retention_events WHERE retention_event_id=?", (event_id,))
    assert events and events[0]["reason"] == "raw expired"
    row = store.db.query("SELECT kind, content_hash FROM evidence WHERE evidence_id=?", (record["evidence_id"],))
    assert row, "metadata + hash must stay durable after payload purge"


def test_model_response_kind_is_accepted_and_labeled(tmp_path):
    store = _store(tmp_path)
    record = _observe(store, kind="MODEL_RESPONSE", content=b"model said X")
    assert record["kind"] == "MODEL_RESPONSE"
    # Semantic note enforced by docs/tests: this proves "model said X", never "X is true".
    with pytest.raises(ValueError):
        _observe(store, kind="DIVINE_TRUTH", content=b"nope")
