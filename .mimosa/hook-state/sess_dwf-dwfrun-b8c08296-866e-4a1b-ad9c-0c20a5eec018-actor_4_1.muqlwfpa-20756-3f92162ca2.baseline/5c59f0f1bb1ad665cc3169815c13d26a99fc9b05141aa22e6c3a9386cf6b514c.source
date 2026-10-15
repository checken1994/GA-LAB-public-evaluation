from __future__ import annotations

from pathlib import Path

import pytest

from scp.contracts.data_class import DataClass, max_severity
from scp.epistemic.evidence_store import EvidenceStore
from scp.epistemic.evidence_writer import GovernedEvidenceWriter, PrivacyWriteDenied
from scp.governance.privacy import PrivacyWriteGate

ROOT = Path(__file__).resolve().parents[2]


def _writer(tmp_path):
    store = EvidenceStore(tmp_path / "epistemic.sqlite", tmp_path / "objects")
    gate = PrivacyWriteGate(ROOT / "spec" / "data_policies.yaml")
    return store, GovernedEvidenceWriter(store, gate)


def test_missing_classification_is_sensitive_floor():
    assert max_severity(DataClass.PUBLIC, None) is DataClass.SENSITIVE


def test_secret_is_redacted_before_persistence_and_class_escalates(tmp_path):
    store, writer = _writer(tmp_path)
    raw = b"api_key=supersecret1234567890"
    record = writer.observe(
        kind="HTTP_RESPONSE",
        content=raw,
        collector_id="test",
        collector_version="1",
        data_class=DataClass.PUBLIC,
    )
    persisted = store.read_content(record["evidence_id"])
    assert b"supersecret1234567890" not in persisted
    assert b"REDACTED" in persisted
    assert record["data_class"] == DataClass.SECRET.value
    assert "supersecret1234567890" not in record["metadata_json"]
    store.db.close()


def test_unredacted_sensitive_raw_is_denied_but_sanitized_keeps_class(tmp_path):
    store, writer = _writer(tmp_path)
    with pytest.raises(PrivacyWriteDenied):
        writer.observe(
            kind="RUNTIME_OBSERVATION",
            content=b"sensitive business context without deterministic PII marker",
            collector_id="test",
            collector_version="1",
            data_class=DataClass.SENSITIVE,
        )
    record = writer.observe(
        kind="RUNTIME_OBSERVATION",
        content=b"sanitized-sensitive-summary",
        collector_id="test",
        collector_version="1",
        data_class=DataClass.SENSITIVE,
        sanitized=True,
    )
    assert record["data_class"] == DataClass.SENSITIVE.value
    store.db.close()
