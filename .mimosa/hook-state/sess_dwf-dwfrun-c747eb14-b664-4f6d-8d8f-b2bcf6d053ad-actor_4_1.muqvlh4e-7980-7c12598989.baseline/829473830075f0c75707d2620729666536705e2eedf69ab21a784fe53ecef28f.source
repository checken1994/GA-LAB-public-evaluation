"""[ZONE-FIX 2026-09-26] Regression — the CI acceptance A12 oracle must reject
HUMAN_REVIEW tasks outside the expected review set.

BEFORE the fix, scripts/run_scp_acceptance_ci.py allowed ANY task to end in
HUMAN_REVIEW (terminal-set check only) — strictly weaker than the main
runner's A12 oracle in scripts/run_scp_acceptance.py, which requires the
observed nonterminal set to equal the exact expected review ids. Probe-verified:
an unexpected stuck task passed the CI oracle. HUMAN_REVIEW must now equal
the expected review ids; an early stop leaves the final evidence incomplete.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scp.task_kernel import TaskKernel
from scripts.run_scp_acceptance import (
    AcceptanceFailure,
    AcceptanceSuite,
    stable_task_id,
)
from scripts.run_scp_acceptance_ci import _final_state_invariant


class _StubRuntime:
    def __init__(self, db_path: Path):
        self.db_path = db_path


class _StubSuite:
    def __init__(self, db_path: Path):
        self.runtime = _StubRuntime(db_path)

    contradiction_payload = staticmethod(AcceptanceSuite.contradiction_payload)
    verified_payload = staticmethod(AcceptanceSuite.verified_payload)


def _stuck_in_human_review(kernel: TaskKernel, task_id: str) -> None:
    """Create a task with an intact journal chain, stuck in HUMAN_REVIEW."""
    kernel.create_task(task_id, owner="probe", goal="probe task")
    kernel._append_event(
        task_id, "STATE_TRANSITION", "CREATED", "HUMAN_REVIEW",
        "probe", "crafted stuck task", None,
    )
    kernel.conn.execute(
        "UPDATE tasks SET state='HUMAN_REVIEW' WHERE task_id=?", (task_id,)
    )


def test_unexpected_human_review_task_is_rejected(tmp_path):
    db = tmp_path / "kernel.db"
    kernel = TaskKernel(db)
    expected_id = stable_task_id(
        "scp-a04-contradiction", AcceptanceSuite.contradiction_payload()
    )
    _stuck_in_human_review(kernel, expected_id)
    _stuck_in_human_review(kernel, "unrelated-regression-stuck-task")
    kernel.close()

    with pytest.raises(AcceptanceFailure) as excinfo:
        _final_state_invariant(_StubSuite(db))
    assert "unexpected HUMAN_REVIEW" in str(excinfo.value)


def test_expected_only_human_review_set_still_passes(tmp_path):
    """All mandatory review tasks must be present in the final evidence."""
    db = tmp_path / "kernel_ok.db"
    kernel = TaskKernel(db)
    for key, payload in [
        ("scp-a04-contradiction", AcceptanceSuite.contradiction_payload()),
        ("scp-a06-provider-outage", AcceptanceSuite.verified_payload("a06")),
        ("scp-a09-hard-crash", AcceptanceSuite.verified_payload("a09")),
    ]:
        _stuck_in_human_review(kernel, stable_task_id(key, payload))
    kernel.close()

    report = _final_state_invariant(_StubSuite(db))
    assert report.get("quick_check") == "ok"
    assert report.get("human_review_within_expected_set") is True
    assert report.get("hidden_active_count") == 0
