import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scp.contracts import (
    DataClass,
    EventEnvelope,
    EvidenceLevel,
    Maturity,
    Verdict,
    at_least,
    content_id,
    ensure_aware_utc,
    is_valid_id,
    max_severity,
    new_id,
    parse_maturity,
    parse_verdict,
    require_id,
)

# ==============================================================================
# T02 - COMMON CONTRACT PRIMITIVES (26-P0.2)
# ==============================================================================


def test_verdicts_are_exactly_canonical_and_parse_fails_closed():
    assert {v.value for v in Verdict} == {"VERIFIED", "CONTRADICTED", "INSUFFICIENT", "UNKNOWN"}
    assert parse_verdict("unknown") is Verdict.UNKNOWN
    with pytest.raises(ValueError):
        parse_verdict("PASS")  # PASS is for gates, never epistemic truth
    with pytest.raises(ValueError):
        parse_verdict("probably-fine")


def test_maturity_ladder_orders_and_rejects_unknown():
    assert at_least("M4", "M3") is True
    assert at_least("M2", "M3") is False
    assert parse_maturity("m4") is Maturity.M4_RUNTIME_VERIFIED
    with pytest.raises(ValueError):
        parse_maturity("M9")


def test_data_class_severity_composes_conservatively():
    assert max_severity(DataClass.PUBLIC, DataClass.SENSITIVE) is DataClass.SENSITIVE
    assert max_severity("internal", "secret", "public") is DataClass.SECRET
    # [P0-12a] Missing/unknown classification is a SENSITIVE floor - an
    # unclassified input must never lower the composed class.
    assert max_severity(DataClass.PUBLIC, None) is DataClass.SENSITIVE
    assert max_severity(DataClass.PUBLIC, None, DataClass.INTERNAL) is DataClass.SENSITIVE
    assert max_severity(DataClass.SECRET, None) is DataClass.SECRET
    assert max_severity() is DataClass.PUBLIC


def test_ids_random_occurrence_and_deterministic_content():
    first, second = new_id("ev"), new_id("ev")
    assert first != second and is_valid_id(first) and first.startswith("ev_")
    with pytest.raises(ValueError):
        new_id("Bad-Prefix")
    with pytest.raises(ValueError):
        require_id("not-an-id")
    with pytest.raises(ValueError):
        require_id(new_id("claim"), expected_prefix="ev")

    digest_a = content_id(b"same-bytes")
    assert digest_a == content_id(b"same-bytes")
    assert digest_a.startswith("sha256:")
    assert new_id("ev") != content_id(b"same-bytes"), "occurrence id and content id are different families"


def test_time_rejects_naive_datetimes():
    aware = ensure_aware_utc(datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc))
    assert aware.tzinfo is not None
    with pytest.raises(ValueError):
        ensure_aware_utc(datetime(2026, 9, 2, 12, 0, 0))  # naive - provenance rejected


def test_event_envelope_fails_closed_on_unknown_schema_and_serializes_stably():
    envelope = EventEnvelope(
        event_type="EVIDENCE_OBSERVED",
        actor_type="service",
        actor_id="evidence-store",
        payload={"k": "v"},
        subject_refs=("claim_1",),
        data_class="INTERNAL",
    )
    assert is_valid_id(envelope.event_id) and envelope.event_id.startswith("evt_")
    first = envelope.canonical_json()
    assert first == envelope.canonical_json(), "serialization must be stable"
    assert '"data_class":"INTERNAL"' in first

    with pytest.raises(ValueError):
        EventEnvelope(
            event_type="X", actor_type="service", actor_id="a", schema_version=2,
        )
    with pytest.raises(ValueError):
        EventEnvelope(
            event_type="X", actor_type="service", actor_id="a", data_class="TOPSECRET",
        )


def test_evidence_level_parses_and_rejects_garbage():
    assert EvidenceLevel("C") is EvidenceLevel.C
    with pytest.raises(ValueError):
        EvidenceLevel("E")
