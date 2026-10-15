"""[Agent2-KernelKeeper regression 2026-09-29] Semantics gaps left by 77d44816.

Commit 77d44816 changed kernel.in_flight_count() to exclude HUMAN_REVIEW
(admission control agrees with dedupe) and added pending_review_count().
This test pins the new contract AND proves the old strictness is preserved:

R1 (old-code-fails / new-code-passes):
    scripts/run_scp_acceptance.py + scripts/run_scp_acceptance_ci.py still
    compared in_flight_count() against the expected HUMAN_REVIEW review set
    (len == 3). After 77d44816 in_flight_count() is 0 there by definition, so
    the A12 acceptance oracle could only ever fail (0 != 3) — a stale
    semantics assumption. The oracle must assert the backlog via
    pending_review_count() while hidden-active execution stays guarded by the
    observed_nonterminal / hidden_active checks.

R2 (strictness preserved by 77d44816):
    A genuinely RUNNING ask still counts toward the admission cap: with
    SCP_ASK_MAX_INFLIGHT=1, begin() for a second unrelated ask must raise
    backpressure while a HUMAN_REVIEW backlog does NOT block intake.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from scp.task_kernel import TaskKernel

REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_human_review(kernel: TaskKernel, task_id: str) -> None:
    kernel.create_task(task_id, "test", "review")
    for state in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, state)
    lease = kernel.claim(task_id, "worker", ttl_seconds=30)
    kernel.start(task_id, lease.lease_id)
    kernel.transition(task_id, "HUMAN_REVIEW")


def test_acceptance_oracles_count_review_backlog_not_in_flight() -> None:
    """R1: acceptance A12 oracle must use pending_review_count().

    Old code (git show 77d44816:scripts/...): kernel.in_flight_count() ==
    len(expected_review_ids) — with the new admission semantics the oracle
    asserts 0 == 3 and can never pass, i.e. the old assertion fails this
    contract test by construction.
    """
    for rel in (
        "scripts/run_scp_acceptance.py",
        "scripts/run_scp_acceptance_ci.py",
    ):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "in_flight_count() == len(expected_review_ids)" not in text, (
            f"{rel}: stale A12 oracle — in_flight_count() excludes HUMAN_REVIEW "
            "since 77d44816, so comparing it to the review set asserts 0 == N "
            "and the acceptance suite can never pass"
        )
        assert "pending_review_count() == len(expected_review_ids)" in text, (
            f"{rel}: A12 backlog oracle must count the HUMAN_REVIEW backlog "
            "via pending_review_count()"
        )


def test_kernel_docstring_points_to_existing_counter() -> None:
    """R1 (doc): in_flight_count() must not reference a non-existent
    pending_count() — the escape hatch it names must be callable."""
    from scp.task_kernel_parts import taskkernel as tk_module

    src = Path(tk_module.__file__).read_text(encoding="utf-8")
    m = re.search(r"def in_flight_count\(.*?\"\"\"(.*?)\"\"\"", src, re.DOTALL)
    assert m, "in_flight_count docstring not found"
    assert "pending_count()" not in m.group(1), (
        "in_flight_count docstring references pending_count() which does not "
        "exist; the counter is pending_review_count()"
    )
    kernel = TaskKernel(":memory:")
    try:
        assert callable(kernel.pending_review_count)
        assert kernel.pending_review_count() == 0
    finally:
        kernel.close()


def test_human_review_backlog_never_gates_intake_but_running_does(tmp_path, monkeypatch) -> None:
    """R2: end-to-end admission contract after 77d44816.

    Old code (pre-77d44816, in_flight_count including HUMAN_REVIEW) fails the
    first half: with a backlog of 1 withheld ask and cap 1, begin() raised
    backpressure at zero real load. New code admits the new ask. The second
    half pins the preserved strictness: a genuinely RUNNING ask still counts
    and must trip the cap.
    """
    from scp.ask_kernel_adapter import AskKernelAdapter, KernelError

    monkeypatch.setenv("SCP_ASK_MAX_INFLIGHT", "1")
    adapter = AskKernelAdapter(str(tmp_path / "admission.sqlite3"))
    try:
        # Simulate an accumulated withheld backlog (the 199-task incident
        # shape) plus verify it is telemetry, not execution load.
        _make_human_review(adapter.kernel, "withheld-1")
        assert adapter.kernel.pending_review_count() == 1
        assert adapter.kernel.in_flight_count() == 0

        # A brand-new unrelated ask must be admitted (pre-77d44816 this
        # raised 'backpressure: in-flight ask tasks at cap 1').
        handle = adapter.begin(
            "a brand new question", [], "", session_id="sess-admission"
        )
        assert adapter.kernel.get_task(handle["task_id"])["state"] == "RUNNING"
        assert adapter.kernel.in_flight_count() == 1

        # Strictness preserved: at cap with a genuinely RUNNING ask, a new
        # ask is still rejected fail-closed.
        with pytest.raises(KernelError, match="backpressure"):
            adapter.begin(
                "another unrelated question", [], "", session_id="sess-admission-2"
            )
    finally:
        adapter.kernel.close()
