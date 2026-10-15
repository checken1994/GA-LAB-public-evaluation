from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scp.contracts.data_class import DataClass
from scp.epistemic.evidence_store import EvidenceIntegrityError, EvidenceStore
from scp.epistemic.evidence_writer import GovernedEvidenceWriter
from scp.governance.privacy import PrivacyWriteGate
from scp.governance.retention import RetentionManager

ROOT = Path(__file__).resolve().parents[2]


def test_retention_hold_and_shared_blob_reference_count(tmp_path):
    store = EvidenceStore(tmp_path / "epistemic.sqlite", tmp_path / "objects")
    writer = GovernedEvidenceWriter(store, PrivacyWriteGate(ROOT / "spec" / "data_policies.yaml"))
    retention = RetentionManager(store, ROOT / "spec" / "data_policies.yaml")

    one = writer.observe(
        kind="HTTP_RESPONSE",
        content=b"same-public-payload",
        collector_id="test",
        collector_version="1",
        data_class=DataClass.PUBLIC,
    )
    two = writer.observe(
        kind="HTTP_RESPONSE",
        content=b"same-public-payload",
        collector_id="test",
        collector_version="1",
        data_class=DataClass.PUBLIC,
    )
    assert one["content_hash"] == two["content_hash"]
    assert one["evidence_id"] != two["evidence_id"]

    hold = retention.add_hold(evidence_id=two["evidence_id"], reason="active audit")
    future = datetime.now(timezone.utc) + timedelta(days=31)
    report = retention.purge_expired(now=future)
    assert one["evidence_id"] in report["purged"]
    assert two["evidence_id"] in report["held"]
    # Raw bytes must remain because the held occurrence still references the
    # shared content-addressed blob.
    assert store.read_content(two["evidence_id"]) == b"same-public-payload"

    retention.release_hold(hold)
    report = retention.purge_expired(now=future)
    assert two["evidence_id"] in report["purged"]
    # Immutable evidence metadata still exists even though payload is gone.
    rows = store.db.query("SELECT evidence_id,content_hash FROM evidence ORDER BY evidence_id")
    assert {row["evidence_id"] for row in rows} == {one["evidence_id"], two["evidence_id"]}
    with pytest.raises(EvidenceIntegrityError):
        store.get(two["evidence_id"])

    retention.close()
    store.db.close()
