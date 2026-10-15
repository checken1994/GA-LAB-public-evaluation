from __future__ import annotations

import pytest

from scp.task_kernel import StaleLease, TaskKernel


def _running_task(kernel: TaskKernel, task_id: str = "transition-fence-1"):
    kernel.create_task(task_id, "lease-test", "prove post-driver transition fencing", "R1")
    for state in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, state, actor="lease-test", reason="setup")
    lease = kernel.claim(task_id, "worker-old", ttl_seconds=300)
    kernel.start(task_id, lease.lease_id)
    return lease


def _expire_without_watchdog_sweep(kernel: TaskKernel, lease_id: str) -> None:
    """Expire the wall-clock lease while leaving task state/released projection untouched."""
    kernel._begin()
    try:
        kernel.conn.execute(
            "UPDATE leases SET expires_at=0 WHERE lease_id=?",
            (lease_id,),
        )
        kernel._commit()
    except Exception:
        kernel._rollback()
        raise


def test_expired_unswept_lease_cannot_transition_task_or_journal(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _running_task(kernel)
        _expire_without_watchdog_sweep(kernel, lease.lease_id)

        before_task = kernel.get_task("transition-fence-1")
        before_events = kernel.get_events("transition-fence-1")
        assert before_task["state"] == "RUNNING"

        with pytest.raises(StaleLease):
            kernel.transition(
                "transition-fence-1",
                "VERIFYING",
                actor="stale-worker",
                reason="post_driver_result",
            )

        after_task = kernel.get_task("transition-fence-1")
        after_events = kernel.get_events("transition-fence-1")
        assert after_task["state"] == "RUNNING"
        assert after_task["version"] == before_task["version"]
        assert after_events == before_events
    finally:
        kernel.close()


def test_boot_recovery_temporarily_supersedes_but_does_not_erase_stale_fence(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _running_task(kernel)
        _expire_without_watchdog_sweep(kernel, lease.lease_id)

        report = kernel.recover_on_boot(actor="test-recovery")
        recovered = {entry["task_id"]: entry for entry in report["recovered"]}
        assert recovered["transition-fence-1"]["to"] == "HUMAN_REVIEW"
        assert kernel.get_task("transition-fence-1")["state"] == "HUMAN_REVIEW"
        assert kernel.verify_journal("transition-fence-1")["hash_chain_valid"] is True

        # Recovery is a temporary system authority. The old execution context
        # remains stale afterwards and cannot regain mutation rights.
        with pytest.raises(StaleLease):
            kernel.transition(
                "transition-fence-1",
                "READY",
                actor="stale-worker",
                reason="resume_after_recovery",
            )
        assert kernel.get_task("transition-fence-1")["state"] == "HUMAN_REVIEW"
    finally:
        kernel.close()
