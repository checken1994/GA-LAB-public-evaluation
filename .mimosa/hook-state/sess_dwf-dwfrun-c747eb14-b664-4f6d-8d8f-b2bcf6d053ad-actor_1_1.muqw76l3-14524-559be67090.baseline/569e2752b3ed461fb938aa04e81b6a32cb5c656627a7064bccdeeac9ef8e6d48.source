"""Regression pins for A2 AUDIT-F-01 (consumer side) — migration candidate evidence.

Consumer ``history/migration.py::scan_evolution_db`` previously promoted any
lesson row with the self-attested ``fix_verified=1`` flag and
``success_rate >= 0.8`` straight into ``verified_lesson_candidates``. The
evolution DB schema (scp/meta/kb_evolve.py, ``CREATE TABLE lessons``) stores
NO evidence/receipt reference, so a row cannot prove its own verification —
the consumer cross-checked nothing.

Post-fix contract (fail-closed, no schema invented on the consumer side):
- a self-attested flag without a persisted evidence/receipt reference is
  classified ``unproven_branch`` and quarantined — NEVER a candidate;
- a row that DOES carry a real evidence reference (e.g. a persisted
  verification receipt column) is accepted as ``candidate_only``;
- unverified or sub-threshold lessons are never candidates (unchanged).

The unproven-branch pin FAILS against the pre-fix consumer (which emitted
``candidate_only``) and passes after it (old-fails/new-passes).
"""
from __future__ import annotations

import json
import sqlite3

import pytest

import scp.autofix.evolution  # noqa: F401  # initialize mixin wiring (module-load order)
from scp.history.migration import HistoryMigration, MigrationConfig
from scp.meta.kb_evolve import KBAccumulationStore, Lesson


def _make_lesson(name: str, *, fix_verified: bool, success_rate: float) -> Lesson:
    return Lesson(
        lesson_id=f"les-{name}",
        timestamp=1_700_000_000.0,
        bug_type="BareExceptPass",
        bug_file="scp/demo.py",
        bug_line=10,
        root_cause=f"root cause {name}",
        lesson=f"lesson {name}",
        fix_pattern="replace pass with logging",
        fix_verified=fix_verified,
        occurrence_count=1,
        success_rate=success_rate,
    )


def _scan(store: KBAccumulationStore) -> dict:
    migration = HistoryMigration(MigrationConfig())
    return migration.scan_evolution_db(store.db_path)


def test_self_attested_lesson_without_evidence_is_unproven_branch(tmp_path):
    """fix_verified=1 + rate 0.9 but NO persisted evidence -> UNPROVEN_BRANCH."""
    store = KBAccumulationStore(data_dir=str(tmp_path / "kb"))
    store.save_lesson(_make_lesson("selfattest", fix_verified=True, success_rate=0.9))

    result = _scan(store)

    assert result["verified_lesson_candidates"] == [], (
        "a self-attested flag is not evidence: must not be promoted to candidate"
    )
    unproven = result["lesson_candidates_unproven_branch"]
    assert len(unproven) == 1
    assert unproven[0]["lesson_id"] == "les-selfattest"
    assert unproven[0]["disposition"] == "unproven_branch"
    assert "evidence" in unproven[0]["reason"]
    # The manifest must quarantine it too (no silent drop, no silent pass).
    assert any(
        q.get("lesson_id") == "les-selfattest" and q["disposition"] == "unproven_branch"
        for q in _scan_quarantine(store)
    )


def _scan_quarantine(store: KBAccumulationStore) -> list[dict]:
    migration = HistoryMigration(MigrationConfig())
    migration.scan_evolution_db(store.db_path)
    return migration.quarantine


def test_lesson_with_real_evidence_reference_is_candidate(tmp_path):
    """A row carrying a REAL persisted evidence reference passes the cross-check.

    The production schema has no such column yet; this pin adds one explicitly
    (the consumer reads it defensively without inventing schema) to prove the
    accept-branch works the day the producer persists receipts.
    """
    store = KBAccumulationStore(data_dir=str(tmp_path / "kb"))
    store.save_lesson(_make_lesson("receipted", fix_verified=True, success_rate=0.9))

    receipt = {"action": "fixed", "reality_test_result": "pass",
               "post_fix_verification": {"ok": True}}
    with sqlite3.connect(store.db_path) as conn:
        conn.execute("ALTER TABLE lessons ADD COLUMN verification_receipt_json TEXT")
        conn.execute(
            "UPDATE lessons SET verification_receipt_json=? WHERE lesson_id=?",
            (json.dumps(receipt), "les-receipted"),
        )

    result = _scan(store)

    candidates = result["verified_lesson_candidates"]
    assert len(candidates) == 1
    assert candidates[0]["lesson_id"] == "les-receipted"
    assert candidates[0]["disposition"] == "candidate_only"
    assert candidates[0]["evidence_ref"].startswith("verification_receipt_json:")
    assert result["lesson_candidates_unproven_branch"] == []


def test_unverified_and_subthreshold_lessons_stay_out_of_candidates(tmp_path):
    store = KBAccumulationStore(data_dir=str(tmp_path / "kb"))
    store.save_lesson(_make_lesson("unverified", fix_verified=False, success_rate=1.0))
    store.save_lesson(_make_lesson("lowrate", fix_verified=True, success_rate=0.5))

    result = _scan(store)

    assert result["verified_lesson_candidates"] == []
    ids = {u["lesson_id"] for u in result["lesson_candidates_unproven_branch"]}
    assert ids == set(), "rows failing the flag/rate gate are not even unproven candidates"
