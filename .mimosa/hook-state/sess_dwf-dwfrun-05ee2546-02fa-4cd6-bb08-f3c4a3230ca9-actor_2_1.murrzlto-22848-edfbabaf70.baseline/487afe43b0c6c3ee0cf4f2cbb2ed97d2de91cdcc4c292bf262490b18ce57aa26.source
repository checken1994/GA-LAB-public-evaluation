from __future__ import annotations

import pytest

from scp.task_kernel import NotFound, StaleLease, TaskKernel, stable_hash


def _running_task(kernel: TaskKernel, task_id: str = "fence-1"):
    kernel.create_task(task_id, "lease-test", "prove stale writer fencing", "R1")
    for state in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, state, actor="lease-test", reason="setup")
    lease = kernel.claim(task_id, "worker-old", ttl_seconds=300)
    kernel.start(task_id, lease.lease_id)
    return lease


def _logical_key(task_id: str, step_id: str, action_type: str, resource_identity: str) -> str:
    return stable_hash(
        {
            "task_id": task_id,
            "step_id": step_id,
            "action_type": action_type,
            "resource_identity": resource_identity,
        }
    )


def test_stale_lease_cannot_create_idempotency_claim(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _running_task(kernel)
        kernel.expire_leases(now=lease.expires_at + 1)

        with pytest.raises(StaleLease):
            kernel.idempotency_claim("fence-1", "step-1", "fs.write", "report.doc")

        logical_key = _logical_key("fence-1", "step-1", "fs.write", "report.doc")
        with pytest.raises(NotFound):
            kernel.idempotency_status(logical_key)
    finally:
        kernel.close()


def test_stale_lease_cannot_complete_existing_idempotency_claim(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _running_task(kernel)
        logical_key, claimed = kernel.idempotency_claim(
            "fence-1", "step-1", "fs.write", "report.doc"
        )
        assert claimed is True
        assert kernel.idempotency_status(logical_key)["status"] == "CLAIMED"

        kernel.expire_leases(now=lease.expires_at + 1)

        with pytest.raises(StaleLease):
            kernel.idempotency_complete(logical_key, "evidence://stale-writer")

        row = kernel.idempotency_status(logical_key)
        assert row["status"] == "CLAIMED"
        assert row["result_ref"] is None
    finally:
        kernel.close()


def test_fresh_recovery_reader_can_probe_duplicate_without_mutating_it(tmp_path):
    db_path = tmp_path / "kernel.sqlite3"
    writer = TaskKernel(db_path)
    try:
        _running_task(writer)
        logical_key, claimed = writer.idempotency_claim(
            "fence-1", "step-1", "fs.write", "report.doc"
        )
        assert claimed is True
    finally:
        writer.close()

    reader = TaskKernel(db_path)
    try:
        same_key, claimed_again = reader.idempotency_claim(
            "fence-1", "step-1", "fs.write", "report.doc"
        )
        assert same_key == logical_key
        assert claimed_again is False
        row = reader.idempotency_status(logical_key)
        assert row["status"] == "CLAIMED"
        assert row["result_ref"] is None
    finally:
        reader.close()
