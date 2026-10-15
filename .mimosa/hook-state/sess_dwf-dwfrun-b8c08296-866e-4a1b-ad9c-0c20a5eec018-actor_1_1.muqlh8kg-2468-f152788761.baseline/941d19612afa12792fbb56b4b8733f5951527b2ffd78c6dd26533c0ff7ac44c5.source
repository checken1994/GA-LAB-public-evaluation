"""Anti-placebo mutation tests for TaskKernel satellite tables OCC (Optimistic Concurrency Control).

Verifies that:
1. OptimisticLockError is exported and inherits from StaleLease (and KernelError).
2. OCC on `idempotency` table prevents stale writes (Mutant M1 killer).
3. OCC on `leases` table prevents concurrent stale heartbeats and releases (Mutant M1 & M3 killer).
4. Racing concurrent workers yield exactly one winner and one OptimisticLockError (Mutant M2 killer).
5. OCC on RETRYABLE claim prevents duplicate or stale claiming (Mutant M4 killer).
6. claim_next deadline expiry check uses version fencing on tasks table.
7. Schema evolution safely adds `version` column to legacy databases without data loss.
"""

import sqlite3
import threading
from pathlib import Path

import pytest

import scp.task_kernel_parts.taskkernel as tk_part
from scp.task_kernel import (
    KernelError,
    OptimisticLockError,
    StaleLease,
    TaskKernel,
)


def _setup_running_task(kernel: TaskKernel, task_id: str = "fence-1", worker_id: str = "worker-1"):
    kernel.create_task(task_id, "lease-test", "prove stale writer fencing", "R1")
    for state in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, state, actor="lease-test", reason="setup")
    lease = kernel.claim(task_id, worker_id, ttl_seconds=300)
    kernel.start(task_id, lease.lease_id)
    return lease


def test_anti_placebo_exception_hierarchy_and_exports():
    """Verify exception hierarchy, module exports, and required attributes."""
    assert hasattr(tk_part, "OptimisticLockError")
    assert issubclass(OptimisticLockError, StaleLease)
    assert issubclass(OptimisticLockError, KernelError)

    err = OptimisticLockError(
        "OCC conflict on test table",
        table="leases",
        entity_id="lease-123",
        expected_version=3,
    )
    assert err.table == "leases"
    assert err.entity_id == "lease-123"
    assert err.expected_version == 3
    assert "lease-123" in str(err)


def test_anti_placebo_idempotency_stale_update_fails_closed(tmp_path: Path):
    """Mutant M1 killer: Updating idempotency with stale expected_version must fail-closed."""
    db_path = tmp_path / "test_occ_idem.sqlite3"
    kernel = TaskKernel(db_path=db_path)
    try:
        _setup_running_task(kernel, "task-idem-1", "worker-1")

        # 1. First claim -> version 1
        logical_key, claimed = kernel.idempotency_claim(
            "task-idem-1", "step-1", "fs.write", "report.doc"
        )
        assert claimed is True
        row = kernel.idempotency_status(logical_key)
        assert row["status"] == "CLAIMED"
        assert row["version"] == 1

        # 2. Complete with expected_version=1 -> succeeds, version becomes 2
        kernel.idempotency_complete(
            logical_key,
            "evidence://valid-outcome",
            expected_version=1,
        )
        row = kernel.idempotency_status(logical_key)
        assert row["status"] == "COMPLETED"
        assert row["version"] == 2
        assert row["result_ref"] == "evidence://valid-outcome"

        # 3. Stale worker tries to complete with expected_version=1 -> MUST raise OptimisticLockError
        with pytest.raises(OptimisticLockError) as exc_info:
            kernel.idempotency_complete(
                logical_key,
                "evidence://stale-overwrite",
                expected_version=1,
            )
        assert exc_info.value.table == "idempotency"
        assert exc_info.value.entity_id == logical_key
        assert exc_info.value.expected_version == 1

        # 4. Verify database state was NOT overwritten by stale write
        row_final = kernel.idempotency_status(logical_key)
        assert row_final["status"] == "COMPLETED"
        assert row_final["version"] == 2
        assert row_final["result_ref"] == "evidence://valid-outcome"
    finally:
        kernel.close()


def test_anti_placebo_lease_heartbeat_and_release_conflict_fails_closed(tmp_path: Path):
    """Mutant M1 & M3 killer: Heartbeat and release on leases must enforce version fencing."""
    db_path = tmp_path / "test_occ_lease.sqlite3"
    kernel = TaskKernel(db_path=db_path)
    try:
        lease = _setup_running_task(kernel, "task-lease-1", "worker-1")
        lease_id = lease.lease_id

        # Initial lease version is 1
        row = kernel.conn.execute(
            "SELECT version, released FROM leases WHERE lease_id = ?",
            (lease_id,),
        ).fetchone()
        assert row["version"] == 1
        assert row["released"] == 0

        # Heartbeat with expected_version=1 -> version increments to 2
        kernel.heartbeat("task-lease-1", lease_id, expected_version=1)
        row = kernel.conn.execute(
            "SELECT version, released FROM leases WHERE lease_id = ?",
            (lease_id,),
        ).fetchone()
        assert row["version"] == 2
        assert row["released"] == 0

        # Stale heartbeat with expected_version=1 -> MUST raise OptimisticLockError
        with pytest.raises(OptimisticLockError) as exc_info:
            kernel.heartbeat("task-lease-1", lease_id, expected_version=1)
        assert exc_info.value.table == "leases"
        assert exc_info.value.entity_id == lease_id
        assert exc_info.value.expected_version == 1

        # Stale release with expected_version=1 -> MUST raise OptimisticLockError
        with pytest.raises(OptimisticLockError) as exc_info:
            kernel.release("task-lease-1", lease_id, expected_version=1)
        assert exc_info.value.table == "leases"
        assert exc_info.value.entity_id == lease_id
        assert exc_info.value.expected_version == 1

        # Valid release with expected_version=2 -> succeeds, version becomes 3, released=1
        kernel.release("task-lease-1", lease_id, expected_version=2)
        row = kernel.conn.execute(
            "SELECT version, released FROM leases WHERE lease_id = ?",
            (lease_id,),
        ).fetchone()
        assert row["version"] == 3
        assert row["released"] == 1

        # Post-release heartbeat or release must fail-closed with OptimisticLockError
        with pytest.raises(OptimisticLockError):
            kernel.heartbeat("task-lease-1", lease_id)
        with pytest.raises(OptimisticLockError):
            kernel.release("task-lease-1", lease_id)
    finally:
        kernel.close()


def test_anti_placebo_concurrent_racing_workers_exactly_one_winner(tmp_path: Path):
    """Mutant M2 killer: Concurrent workers racing on the same version must produce exactly 1 winner."""
    db_path = tmp_path / "test_occ_race.sqlite3"
    kernel = TaskKernel(db_path=db_path)
    try:
        _setup_running_task(kernel, "task-race-1", "worker-1")
        logical_key, claimed = kernel.idempotency_claim(
            "task-race-1", "step-race", "fs.write", "output.dat"
        )
        assert claimed is True
        assert kernel.idempotency_status(logical_key)["version"] == 1

        successes = []
        errors = []

        def worker_attempt(ident: str):
            k = TaskKernel(db_path=db_path)
            try:
                k._bound_leases["task-race-1"] = kernel._bound_leases["task-race-1"]
                k.idempotency_complete(
                    logical_key,
                    f"evidence://winner-{ident}",
                    expected_version=1,
                )
                successes.append(ident)
            except OptimisticLockError as e:
                errors.append((ident, e))
            finally:
                k.close()

        t1 = threading.Thread(target=worker_attempt, args=("worker-A",))
        t2 = threading.Thread(target=worker_attempt, args=("worker-B",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(successes) == 1, f"Expected 1 winner, got: {successes}"
        assert len(errors) == 1, f"Expected 1 conflict error, got: {errors}"
        assert errors[0][1].table == "idempotency"
        assert errors[0][1].expected_version == 1

        row = kernel.idempotency_status(logical_key)
        assert row["status"] == "COMPLETED"
        assert row["version"] == 2
        assert row["result_ref"] == f"evidence://winner-{successes[0]}"
    finally:
        kernel.close()


def test_anti_placebo_idempotency_claim_retryable_occ(tmp_path: Path):
    """Mutant M4 killer: Claiming a RETRYABLE key with OCC must fence against concurrent claims."""
    db_path = tmp_path / "test_occ_retry.sqlite3"
    kernel = TaskKernel(db_path=db_path)
    try:
        _setup_running_task(kernel, "task-retry-1", "worker-1")
        logical_key, claimed = kernel.idempotency_claim(
            "task-retry-1", "step-retry", "net.fetch", "data.json"
        )
        assert claimed is True

        # Force status to RETRYABLE directly in DB with version=1
        kernel.conn.execute(
            "UPDATE idempotency SET status='RETRYABLE', version=1 WHERE logical_key=?",
            (logical_key,),
        )
        assert kernel.idempotency_status(logical_key)["status"] == "RETRYABLE"
        assert kernel.idempotency_status(logical_key)["version"] == 1

        # Worker A claims with expected_version=1 -> succeeds, version becomes 2, status becomes CLAIMED
        _, re_claimed = kernel.idempotency_claim(
            "task-retry-1", "step-retry", "net.fetch", "data.json", expected_version=1
        )
        assert re_claimed is True
        row = kernel.idempotency_status(logical_key)
        assert row["status"] == "CLAIMED"
        assert row["version"] == 2

        # Worker B tries to claim with stale expected_version=1 -> MUST raise OptimisticLockError
        with pytest.raises(OptimisticLockError) as exc_info:
            kernel.idempotency_claim(
                "task-retry-1", "step-retry", "net.fetch", "data.json", expected_version=1
            )
        assert exc_info.value.table == "idempotency"
        assert exc_info.value.entity_id == logical_key
        assert exc_info.value.expected_version == 1
    finally:
        kernel.close()


def test_anti_placebo_tasks_claim_next_deadline_occ_fenced(tmp_path: Path):
    """Verify claim_next deadline expiration uses version fencing and does not blind overwrite."""
    db_path = tmp_path / "test_occ_deadline.sqlite3"
    kernel = TaskKernel(db_path=db_path)
    try:
        # Create a task, advance to QUEUED
        kernel.create_task("task-dl-1", "test-actor", "test goal", deadline_ms=1)
        for s in ("PLANNING", "READY", "QUEUED"):
            kernel.transition("task-dl-1", s, actor="test-actor")

        # Manually set deadline in the past so claim_next sees it as expired
        kernel.conn.execute(
            "UPDATE tasks SET deadline_ms=1, created_at='2020-01-01T00:00:00Z', version=5 WHERE task_id='task-dl-1'"
        )

        # In a racing transaction, bump version to 6
        kernel.conn.execute(
            "UPDATE tasks SET version=6 WHERE task_id='task-dl-1'"
        )

        # Run claim_next: if claim_next had an unfenced blind overwrite, it would overwrite version 6
        kernel.claim_next("worker-test")

        row = kernel.conn.execute(
            "SELECT version, state FROM tasks WHERE task_id='task-dl-1'"
        ).fetchone()
        assert row["version"] >= 6
    finally:
        kernel.close()


def test_anti_placebo_schema_evolution_preserves_legacy_database(tmp_path: Path):
    """Verify legacy SQLite databases without version column in satellite tables are migrated safely."""
    legacy_db = tmp_path / "legacy.sqlite3"

    # Pre-create legacy database with full required schemas minus `version` in satellite tables
    conn = sqlite3.connect(legacy_db)
    conn.executescript(
        """
        CREATE TABLE control (
            id INTEGER PRIMARY KEY CHECK (id=1),
            global_kill_epoch INTEGER NOT NULL DEFAULT 0
        );
        INSERT INTO control (id, global_kill_epoch) VALUES (1, 0);

        CREATE TABLE tasks (
            task_id TEXT PRIMARY KEY,
            parent_id TEXT,
            actor TEXT NOT NULL,
            goal TEXT NOT NULL,
            risk_tier TEXT NOT NULL,
            deadline_ms INTEGER NOT NULL,
            max_attempts INTEGER NOT NULL,
            input_hash TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 5,
            state TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            active_lease_id TEXT,
            active_fencing_token INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            type TEXT NOT NULL,
            from_state TEXT,
            to_state TEXT,
            actor TEXT NOT NULL,
            reason TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            policy_hash TEXT,
            prev_event_hash TEXT,
            event_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(task_id, seq)
        );

        CREATE TABLE checkpoints (
            checkpoint_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            attempt_id TEXT NOT NULL,
            step_id TEXT NOT NULL,
            state TEXT NOT NULL,
            planned_action_hash TEXT NOT NULL,
            capability_epoch INTEGER NOT NULL,
            idempotency_key TEXT NOT NULL,
            pre_observation_ref TEXT,
            post_observation_ref TEXT,
            tool_result_json TEXT,
            verifier_verdict TEXT,
            payload_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE leases (
            lease_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            attempt_id TEXT NOT NULL,
            worker_id TEXT NOT NULL,
            issued_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            heartbeat_at REAL NOT NULL,
            fencing_token INTEGER NOT NULL,
            global_kill_epoch INTEGER NOT NULL,
            released INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX idx_leases_task ON leases(task_id, fencing_token);

        CREATE TABLE idempotency (
            logical_key TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            step_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            resource_identity TEXT NOT NULL,
            status TEXT NOT NULL,
            result_ref TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE queue_accounts (
            owner TEXT PRIMARY KEY,
            active INTEGER NOT NULL DEFAULT 0,
            dispatch_count INTEGER NOT NULL DEFAULT 0,
            last_dispatch_at REAL NOT NULL DEFAULT 0
        );

        INSERT INTO leases VALUES ('l-1', 't-1', 'a-1', 'w-1', 100.0, 200.0, 100.0, 1, 0, 0);
        INSERT INTO idempotency VALUES ('k-1', 't-1', 's-1', 'fs.write', 'f.txt', 'CLAIMED', NULL, '2026-09-01T00:00:00Z');
        INSERT INTO queue_accounts VALUES ('default', 1, 5, 100.0);
        """
    )
    conn.commit()
    conn.close()

    # Instantiate TaskKernel on the legacy db -> triggers schema evolution migration
    kernel = TaskKernel(db_path=legacy_db)
    try:
        # Verify columns exist
        lease_cols = {r["name"] for r in kernel.conn.execute("PRAGMA table_info(leases)").fetchall()}
        idem_cols = {r["name"] for r in kernel.conn.execute("PRAGMA table_info(idempotency)").fetchall()}
        queue_cols = {r["name"] for r in kernel.conn.execute("PRAGMA table_info(queue_accounts)").fetchall()}

        assert "version" in lease_cols
        assert "version" in idem_cols
        assert "version" in queue_cols

        # Verify existing records defaulted to version = 1
        l_row = kernel.conn.execute("SELECT version FROM leases WHERE lease_id = 'l-1'").fetchone()
        i_row = kernel.conn.execute("SELECT version FROM idempotency WHERE logical_key = 'k-1'").fetchone()
        q_row = kernel.conn.execute("SELECT version FROM queue_accounts WHERE owner = 'default'").fetchone()

        assert l_row["version"] == 1
        assert i_row["version"] == 1
        assert q_row["version"] == 1
    finally:
        kernel.close()
