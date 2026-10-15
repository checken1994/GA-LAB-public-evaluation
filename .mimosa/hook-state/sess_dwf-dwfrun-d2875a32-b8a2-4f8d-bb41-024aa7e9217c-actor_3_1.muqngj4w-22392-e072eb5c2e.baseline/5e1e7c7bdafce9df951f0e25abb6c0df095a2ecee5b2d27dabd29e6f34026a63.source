"""Regression pins for A3 F-M2 — falsification engine honest refutation record.

Previously ``FalsificationEngine.record_refutation()`` returned
``errorstore_grew: True`` unconditionally while never writing to any store:
the claim never matched reality. Post-fix the engine persists each refutation
to the REAL ``scp.brain.error_store.ErrorStore`` and the response reports
exactly what happened:

- successful append   -> ``errorstore_grew: True`` + ``errorstore_id``;
- spam-filter reject  -> ``errorstore_grew: False`` + ``errorstore_note``;
- store failure       -> ``errorstore_grew: False`` + ``errorstore_note``;
- ``calculate_scope()['errorstore_size']`` reports the count of records
  actually persisted by this engine (never the fictional 50K target figure).

The unavailable/rejected/scope pins FAIL against the pre-fix implementation
(which always claimed growth) and PASS after it (old-fails/new-passes).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scp.brain.error_store import ErrorStore
from scp.meta.falsification_engine import FalsificationEngine


class _BrokenStore:
    """Fault-injecting store: every add() raises (simulates dead disk)."""

    def add(self, **_kwargs):  # noqa: ANN003
        raise OSError("disk dead")


@pytest.fixture
def engine_with_store(tmp_path: Path) -> FalsificationEngine:
    return FalsificationEngine(
        error_store=ErrorStore(path=str(tmp_path / "error_store.jsonl"))
    )


def test_record_refutation_persists_to_real_error_store(engine_with_store):
    """A successful refutation must really append a record to the store."""
    resp = engine_with_store.record_refutation(
        question="Is medicine X safe in pregnancy?",
        v4_verdict="UNREFUTED_IN_CURRENT_SCOPE",
        reality="CONTRAINDICATED in 1st trimester — FDA category D",
    )
    assert resp["recorded"] is True
    assert resp["errorstore_grew"] is True
    assert resp["errorstore_id"] and resp["errorstore_id"].startswith("err-")
    assert resp["errorstore_note"] is None

    # Reality check: the record exists in the store FILE on disk.
    lines = (engine_with_store._error_store.path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["id"] == resp["errorstore_id"]
    assert record["verdict"] == "REFUTED"
    assert record["domain"] == "falsification"
    assert record["error_type"] == "v4_refutation"
    assert record["details"]["refutation_id"] == resp["refutation_id"]


def test_record_refutation_reports_store_failure_honestly():
    """When the store cannot be written, the response must NOT claim growth."""
    engine = FalsificationEngine(error_store=_BrokenStore())
    resp = engine.record_refutation(
        question="Did the benchmark validate accuracy?",
        v4_verdict="UNREFUTED_IN_CURRENT_SCOPE",
        reality="benchmark crashed before scoring",
    )
    assert resp["errorstore_grew"] is False, (
        "errorstore_grew=True without a real append is a manufactured claim"
    )
    assert resp["errorstore_note"] is not None
    assert "errorstore_unavailable" in resp["errorstore_note"]
    assert "disk dead" in resp["errorstore_note"]
    # The in-memory refutation is still recorded (learning is not lost).
    assert len(engine.refutations) == 1


def test_record_refutation_reports_spam_rejection_honestly(engine_with_store):
    """A spam-filtered question is NOT persisted — response must say so."""
    resp = engine_with_store.record_refutation(
        question="hi",  # too_short per the store's spam filter
        v4_verdict="UNREFUTED_IN_CURRENT_SCOPE",
        reality="question was junk",
    )
    assert resp["errorstore_grew"] is False
    assert resp["errorstore_note"] is not None
    assert resp["errorstore_note"].startswith("errorstore_rejected:")
    assert "too_short" in resp["errorstore_note"]


def test_calculate_scope_reports_persisted_count_not_target(engine_with_store):
    """errorstore_size must be the honest persisted count, never 50K+fiction."""
    before = engine_with_store.calculate_scope()
    assert before["errorstore_size"] == 0
    assert before["errorstore_target_capacity"] == 50000

    engine_with_store.record_refutation(
        question="Does the ledger verify orphan intents?",
        v4_verdict="UNREFUTED_IN_CURRENT_SCOPE",
        reality="orphan intents passed verification",
    )
    after = engine_with_store.calculate_scope()
    assert after["errorstore_size"] == 1, (
        "scope report must reflect reality: exactly one persisted record"
    )


def test_lazy_default_error_store_wiring(monkeypatch, tmp_path: Path):
    """With no injected store, record_refutation lazily builds the default
    ErrorStore (deferred import) and persists through it."""
    created: dict = {}

    class _FakeStore:
        def __init__(self, path: str = "data/error_store.jsonl"):
            created["path"] = path
            self.records: list[dict] = []

        def add(self, **kwargs):
            self.records.append(kwargs)
            return {"id": "err-fake-1"}

    import scp.brain.error_store as error_store_module

    monkeypatch.setattr(error_store_module, "ErrorStore", _FakeStore)

    engine = FalsificationEngine()
    resp = engine.record_refutation(
        question="Was the deadline honored by the scheduler?",
        v4_verdict="PASS",
        reality="scheduler overran the wall-clock deadline",
    )
    assert created["path"] == "data/error_store.jsonl"
    assert resp["errorstore_grew"] is True
    assert resp["errorstore_id"] == "err-fake-1"
    assert engine._errorstore_persisted == 1
