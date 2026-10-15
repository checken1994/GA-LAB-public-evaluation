from __future__ import annotations

from pathlib import Path

import pytest

from scp.task_kernel import InvalidTransition, KernelError, TaskKernel


def test_task_contract_rejects_boundary_values(tmp_path: Path) -> None:
    kernel = TaskKernel(tmp_path / "contract.sqlite3")
    try:
        defaults = kernel.create_task("defaults", "test", "goal")
        assert defaults["deadline_ms"] == 120_000
        assert defaults["priority"] == 5
        boundary = kernel.create_task(
            "valid-boundary", "test", "goal", deadline_ms=1, priority=0, risk_tier="R3"
        )
        assert boundary["deadline_ms"] == 1
        assert boundary["priority"] == 0
        with pytest.raises(KernelError, match="invalid task contract"):
            kernel.create_task("bad-deadline", "test", "goal", deadline_ms=0)
        with pytest.raises(KernelError, match="invalid task priority"):
            kernel.create_task("bad-priority-low", "test", "goal", priority=-1)
        with pytest.raises(KernelError, match="invalid task priority"):
            kernel.create_task("bad-priority-high", "test", "goal", priority=101)
        with pytest.raises(KernelError, match="invalid risk tier"):
            kernel.create_task("bad-risk", "test", "goal", risk_tier="R4")
    finally:
        kernel.close()


def test_transition_contract_and_happy_lifecycle(tmp_path: Path) -> None:
    kernel = TaskKernel(tmp_path / "lifecycle.sqlite3")
    task_id = "mutation-lifecycle"
    try:
        kernel.create_task(task_id, "test", "lifecycle")
        with pytest.raises(InvalidTransition):
            kernel.transition(task_id, "RUNNING")
        for state in ("PLANNING", "READY", "QUEUED"):
            kernel.transition(task_id, state)
        lease = kernel.claim(task_id, "worker", ttl_seconds=30)
        kernel.start(task_id, lease.lease_id)
        kernel.transition(task_id, "VERIFYING")
        kernel.commit_completed(task_id, lease.lease_id, "VERIFIED", "test://evidence")

        assert kernel.get_task(task_id)["state"] == "COMPLETED"
        journal = kernel.verify_journal(task_id)
        assert journal["hash_chain_valid"] is True
        assert journal["event_count"] == 8
    finally:
        kernel.close()


def test_human_review_counted_by_pending_review_not_in_flight(tmp_path: Path) -> None:
    """[FIX 2026-09-29] HUMAN_REVIEW is a RECORDED fail-closed decision
    (answer withheld, waiting on the human flow) — ask_kernel_adapter's
    dedupe contract (_duplicate_is_reaskable) already treats it as finished.
    Admission control must agree with dedupe: in_flight_count() counts only
    tasks that have NOT reached a decision, so an accumulated HUMAN_REVIEW
    backlog cannot permanently choke every new /ask (observed 2026-09-29:
    199 withheld tasks -> 'backpressure: in-flight ask tasks at cap 200'
    with zero real load). HUMAN_REVIEW itself stays non-terminal and can
    still legally transition back to READY for the human re-queue flow.
    """
    kernel = TaskKernel(tmp_path / "human-review.sqlite3")
    try:
        kernel.create_task("review-task", "test", "review")
        kernel.transition("review-task", "PLANNING")
        kernel.transition("review-task", "READY")
        kernel.transition("review-task", "QUEUED")
        lease = kernel.claim("review-task", "worker", ttl_seconds=30)
        kernel.start("review-task", lease.lease_id)
        kernel.transition("review-task", "HUMAN_REVIEW")

        # The withheld task is review backlog, not execution load.
        assert kernel.get_task("review-task")["state"] == "HUMAN_REVIEW"
        assert kernel.in_flight_count() == 0
        assert kernel.pending_review_count() == 1

        # A genuinely running task still counts as in-flight.
        kernel.create_task("running-task", "test", "review")
        for state in ("PLANNING", "READY", "QUEUED"):
            kernel.transition("running-task", state)
        lease2 = kernel.claim("running-task", "worker", ttl_seconds=30)
        kernel.start("running-task", lease2.lease_id)
        assert kernel.in_flight_count() == 1
        assert kernel.pending_review_count() == 1

        # Human re-queue flow remains legal: HUMAN_REVIEW -> READY.
        kernel.transition("review-task", "READY")
        assert kernel.get_task("review-task")["state"] == "READY"
        assert kernel.pending_review_count() == 0
        assert kernel.in_flight_count() == 2
    finally:
        kernel.close()
