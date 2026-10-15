from __future__ import annotations

import time

from scp.task_kernel import TaskKernel


def _setup_kernel_with_task(tmp_path, task_id="t-r3"):
    db_path = tmp_path / "kernel_r3.sqlite3"
    kernel = TaskKernel(db_path)
    kernel.create_task(task_id, "owner-r3", "test sec-r3", "R1")
    for state in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, state, actor="test", reason="setup")
    return kernel


def test_expire_leases_preserves_active_task_when_stale_lease_expires(tmp_path):
    """SEC-R3-02: If a stale lease expires, but the task has a different active lease,
    do NOT modify the task's state or active_lease_id."""
    kernel = _setup_kernel_with_task(tmp_path, "t-stale")
    try:
        now = time.time()
        # Create an old expired lease in the leases table using a transaction
        kernel.conn.begin()
        kernel.conn.execute(
            "INSERT INTO leases(lease_id, task_id, attempt_id, worker_id, issued_at, expires_at, heartbeat_at, fencing_token, global_kill_epoch, released) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
            ("lease_old", "t-stale", "att_old", "worker-1", now - 100, now - 50, now - 100, 1, 0),
        )
        kernel.conn.commit()

        # Task is claimed and running under a fresh lease
        fresh_lease = kernel.claim("t-stale", "worker-2", ttl_seconds=300)
        kernel.start("t-stale", fresh_lease.lease_id)

        task_before = kernel.get_task("t-stale")
        assert task_before["state"] == "RUNNING"
        assert task_before["active_lease_id"] == fresh_lease.lease_id

        # Run lease expiration sweep at current time
        # This will sweep lease_old (expires_at = now - 50)
        expired = kernel.expire_leases(now=now)

        assert "lease_old" in expired
        assert fresh_lease.lease_id not in expired

        # Task state MUST remain RUNNING with active_lease_id == fresh_lease.lease_id
        task_after = kernel.get_task("t-stale")
        assert task_after["state"] == "RUNNING"
        assert task_after["active_lease_id"] == fresh_lease.lease_id
        assert task_after["version"] == task_before["version"]

        # The old lease row must be marked released
        old_lease_row = kernel.conn.execute(
            "SELECT released FROM leases WHERE lease_id='lease_old'"
        ).fetchone()
        assert old_lease_row["released"] == 1
    finally:
        kernel.close()


def test_expire_leases_handles_occ_conflict_on_lease_update(tmp_path):
    """SEC-R3-01: When UPDATE leases matches 0 rows (e.g. concurrent release),
    OptimisticLockError is raised internally and caught, rolling back the single
    lease update without crashing the sweep."""
    kernel = _setup_kernel_with_task(tmp_path, "t-occ")
    try:
        time.time()
        lease = kernel.claim("t-occ", "worker-occ", ttl_seconds=10)
        kernel.start("t-occ", lease.lease_id)

        # Hook execute to simulate concurrent release between candidate fetch and lease update
        orig_execute = kernel.conn.execute

        def hooked_execute(sql, *args, **kwargs):
            if "UPDATE leases SET released=1" in sql and (lease.lease_id,) in args:
                # Concurrent transaction already marked released=1:
                orig_execute("UPDATE leases SET released=1 WHERE lease_id=?", (lease.lease_id,))
            return orig_execute(sql, *args, **kwargs)

        kernel.conn.execute = hooked_execute

        expired = kernel.expire_leases(now=lease.expires_at + 1)
        # Because cur_lease.rowcount == 0, OptimisticLockError was triggered,
        # transaction rolled back, and lease_id was not added to expired
        assert lease.lease_id not in expired
    finally:
        kernel.close()


def test_expire_leases_isolated_transactions_continue_sweep_after_single_conflict(tmp_path):
    """SEC-R3-01: Transaction isolation per expired lease ensures that an OCC conflict
    on one lease does not abort the sweep for subsequent expired leases."""
    kernel = TaskKernel(tmp_path / "kernel_multi.sqlite3")
    try:
        # Create two tasks
        kernel.create_task("t-1", "owner-1", "task 1", "R1")
        kernel.create_task("t-2", "owner-2", "task 2", "R1")
        for tid in ("t-1", "t-2"):
            for state in ("PLANNING", "READY", "QUEUED"):
                kernel.transition(tid, state, actor="test", reason="setup")

        now = time.time()
        # Insert two expired leases directly within transaction
        kernel.conn.begin()
        kernel.conn.execute(
            "INSERT INTO leases(lease_id, task_id, attempt_id, worker_id, issued_at, expires_at, heartbeat_at, fencing_token, global_kill_epoch, released) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
            ("lease-conflict", "t-1", "att-1", "w-1", now - 100, now - 50, now - 100, 1, 0),
        )
        kernel.conn.execute(
            "INSERT INTO leases(lease_id, task_id, attempt_id, worker_id, issued_at, expires_at, heartbeat_at, fencing_token, global_kill_epoch, released) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
            ("lease-success", "t-2", "att-2", "w-2", now - 100, now - 40, now - 100, 1, 0),
        )
        kernel.conn.execute("INSERT OR IGNORE INTO queue_accounts(owner, active, dispatch_count) VALUES ('owner-1', 1, 1)")
        kernel.conn.execute("INSERT OR IGNORE INTO queue_accounts(owner, active, dispatch_count) VALUES ('owner-2', 1, 1)")
        # Update tasks to LEASED with active_lease_id
        kernel.conn.execute("UPDATE tasks SET state='LEASED', active_lease_id='lease-conflict' WHERE task_id='t-1'")
        kernel.conn.execute("UPDATE tasks SET state='LEASED', active_lease_id='lease-success' WHERE task_id='t-2'")
        kernel.conn.commit()

        # Hook execute so that lease-conflict triggers OptimisticLockError on UPDATE leases
        orig_execute = kernel.conn.execute

        def hooked_execute(sql, *args, **kwargs):
            if "UPDATE leases SET released=1" in sql and ("lease-conflict",) in args:
                # Pre-release it so rowcount is 0
                orig_execute("UPDATE leases SET released=1 WHERE lease_id='lease-conflict'")
            return orig_execute(sql, *args, **kwargs)

        kernel.conn.execute = hooked_execute

        # Run sweep
        expired = kernel.expire_leases(now=now)

        # lease-conflict failed due to OCC conflict, but lease-success MUST succeed!
        assert "lease-conflict" not in expired
        assert "lease-success" in expired

        # Task 2 state moved to RECOVERING
        t2 = kernel.get_task("t-2")
        assert t2["state"] == "RECOVERING"
        assert t2["active_lease_id"] is None
    finally:
        kernel.close()


def test_expire_leases_occ_on_queue_accounts_update(tmp_path):
    """SEC-R3-01: When UPDATE queue_accounts matches 0 rows, OptimisticLockError
    is raised and rolled back."""
    kernel = _setup_kernel_with_task(tmp_path, "t-qacc")
    try:
        time.time()
        lease = kernel.claim("t-qacc", "worker-qacc", ttl_seconds=10)
        kernel.start("t-qacc", lease.lease_id)

        # Delete queue_accounts row for owner-r3 so UPDATE queue_accounts updates 0 rows
        kernel.conn.begin()
        kernel.conn.execute("DELETE FROM queue_accounts WHERE owner='owner-r3'")
        kernel.conn.commit()

        expired = kernel.expire_leases(now=lease.expires_at + 1)
        assert lease.lease_id not in expired

        # Task should NOT have been committed as RECOVERING because transaction was rolled back
        task = kernel.get_task("t-qacc")
        assert task["state"] == "RUNNING"
    finally:
        kernel.close()
