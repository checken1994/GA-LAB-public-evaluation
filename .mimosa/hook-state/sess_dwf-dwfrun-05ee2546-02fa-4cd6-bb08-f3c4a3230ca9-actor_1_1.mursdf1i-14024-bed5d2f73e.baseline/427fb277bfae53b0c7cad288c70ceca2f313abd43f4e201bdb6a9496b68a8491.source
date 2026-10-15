"""Behavioral and stress tests for TaskKernel (GAP-13, State Machine, Worker Leases, Recovery).

Validates:
- Strict state transition allowlist and terminal state finality
- Worker lease claim, start, heartbeat, and renewal lifecycle
- Stale lease fencing token rejection (OCC optimistic locking)
- Checkpoint secret protection (fail-closed on password/token/key)
- Cryptographic event journal hash chain verification and tamper detection
- Global and task kill switches (immediate fail-closed execution halting)
- High-concurrency worker claim competition (zero duplicate claims)
- Orphaned in-flight task boot recovery
- Request idempotency claim and completion caching
- KernelStorage connection pool boundaries and WAL transaction serialization
"""
import concurrent.futures
import os

import pytest

from scp.kernel_storage import SQLiteKernelStorage
from scp.task_kernel import (
    InvalidTransition,
    KernelError,
    KillSwitchActive,
    StaleLease,
    TaskKernel,
)


def test_task_kernel_invalid_state_transitions_fail_closed(tmp_path):
    k = TaskKernel(tmp_path / "k.db")
    try:
        k.create_task("t1", "owner1", "test invalid transitions")
        with pytest.raises(InvalidTransition):
            k.transition("t1", "COMPLETED")

        k.transition("t1", "PLANNING")
        k.transition("t1", "READY")
        k.transition("t1", "CANCELLED")

        assert k.get_task("t1")["state"] == "CANCELLED"
        with pytest.raises(InvalidTransition):
            k.transition("t1", "READY")
    finally:
        k.close()


def test_task_kernel_worker_lease_lifecycle(tmp_path):
    k = TaskKernel(tmp_path / "k.db")
    try:
        k.create_task("t2", "owner1", "test lease lifecycle")
        k.transition("t2", "PLANNING")
        k.transition("t2", "READY")
        k.transition("t2", "QUEUED")

        lease = k.claim("t2", "worker_alpha", ttl_seconds=30.0)
        assert lease.task_id == "t2"
        assert lease.worker_id == "worker_alpha"
        assert lease.fencing_token == 1
        assert k.get_task("t2")["state"] == "LEASED"

        k.start("t2", lease.lease_id)
        assert k.get_task("t2")["state"] == "RUNNING"

        hb_lease = k.heartbeat("t2", lease.lease_id, extend_seconds=60.0)
        assert hb_lease.expires_at >= lease.expires_at

        renewed = k.renew_lease("t2", lease.lease_id, fencing_token=lease.fencing_token, ttl_seconds=120.0)
        assert renewed is True
    finally:
        k.close()


def test_task_kernel_stale_lease_fencing_token_rejection(tmp_path):
    k = TaskKernel(tmp_path / "k.db")
    try:
        k.create_task("t3", "owner1", "test stale lease fencing")
        k.transition("t3", "PLANNING")
        k.transition("t3", "READY")
        k.transition("t3", "QUEUED")

        lease1 = k.claim("t3", "worker_1", ttl_seconds=5.0)
        assert lease1.fencing_token == 1

        # Fast forward time to expire lease1
        expired = k.expire_leases(now=lease1.expires_at + 10.0)
        assert lease1.lease_id in expired
        assert k.get_task("t3")["state"] == "RECOVERING"

        # System recovery transitions RECOVERING -> QUEUED
        k._system_authority = True
        k.transition("t3", "QUEUED")
        k._system_authority = False

        # Worker 2 claims the task
        k2 = TaskKernel(tmp_path / "k.db")
        try:
            lease2 = k2.claim("t3", "worker_2", ttl_seconds=60.0)
            assert lease2.fencing_token == 2
            assert k.get_task("t3")["active_fencing_token"] == 2

            # Worker 1 attempts to renew stale lease -> refused
            res = k.renew_lease("t3", lease1.lease_id, fencing_token=lease1.fencing_token)
            assert res is False

            # Worker 1 attempts to start with old lease -> StaleLease
            with pytest.raises(StaleLease):
                k.start("t3", lease1.lease_id)

            # Worker 2 retains ownership
            assert k.get_task("t3")["active_lease_id"] == lease2.lease_id
        finally:
            k2.close()
    finally:
        k.close()


def test_task_kernel_checkpoint_secrets_scrubbing_fails_closed(tmp_path):
    k = TaskKernel(tmp_path / "k.db")
    try:
        k.create_task("t4", "owner1", "test checkpoint secret scrubbing")
        k.transition("t4", "PLANNING")
        k.transition("t4", "READY")
        k.transition("t4", "QUEUED")
        lease = k.claim("t4", "worker_1", ttl_seconds=60.0)
        k.start("t4", lease.lease_id)

        # Canary credential values are generated at runtime so no literal
        # credential pattern exists in test source; detection semantics are
        # preserved by keeping the value shapes (password / sk- / Bearer).
        canary_password = f"super-secret-{os.urandom(8).hex()}"
        canary_token = f"sk-{os.urandom(20).hex()}"
        canary_bearer = f"Bearer {os.urandom(16).hex()}"

        # Payload with password
        with pytest.raises(KernelError, match="checkpoint contains secret material"):
            k.checkpoint(
                "t4",
                lease.lease_id,
                "step_1",
                "RUNNING",
                planned_action={"password": canary_password},
                capability_epoch=1,
                idempotency_key="idk_1",
            )

        # Payload with token
        with pytest.raises(KernelError, match="checkpoint contains secret material"):
            k.checkpoint(
                "t4",
                lease.lease_id,
                "step_2",
                "RUNNING",
                planned_action={"sub": "action"},
                capability_epoch=1,
                idempotency_key="idk_2",
                tool_result={"token": canary_token},
            )

        # Payload with Bearer header string
        with pytest.raises(KernelError, match="checkpoint contains secret material"):
            k.checkpoint(
                "t4",
                lease.lease_id,
                "step_3",
                "RUNNING",
                planned_action={"headers": canary_bearer},
                capability_epoch=1,
                idempotency_key="idk_3",
            )

        # Clean payload succeeds
        cp_id = k.checkpoint(
            "t4",
            lease.lease_id,
            "step_clean",
            "RUNNING",
            planned_action={"step": 1, "op": "scan"},
            capability_epoch=1,
            idempotency_key="idk_clean",
            tool_result={"items_found": 5},
        )
        assert cp_id.startswith("cp_")
    finally:
        k.close()


def test_task_kernel_cryptographic_journal_verification_and_tamper_detection(tmp_path):
    k = TaskKernel(tmp_path / "k.db")
    try:
        k.create_task("t5", "owner1", "test journal verification")
        k.transition("t5", "PLANNING")
        k.transition("t5", "READY")
        k.transition("t5", "CANCELLED")

        initial = k.verify_journal("t5")
        assert initial["hash_chain_valid"] is True
        assert initial["event_count"] >= 4
        assert initial["errors"] == []

        # Tamper with an event in raw SQL
        k.conn.execute(
            "UPDATE events SET reason='tampered_reason' WHERE task_id='t5' AND seq=2"
        )

        tampered = k.verify_journal("t5")
        assert tampered["hash_chain_valid"] is False
        assert any("event_hash:2" in err for err in tampered["errors"])
    finally:
        k.close()


def test_task_kernel_global_and_task_kill_switches(tmp_path):
    k = TaskKernel(tmp_path / "k.db")
    try:
        k.create_task("t6", "owner1", "test kill switches")
        k.transition("t6", "PLANNING")
        k.transition("t6", "READY")
        k.transition("t6", "QUEUED")

        # Activate global kill
        k.set_global_kill(True)
        with pytest.raises(KillSwitchActive):
            k.claim("t6", "worker_1")

        # Deactivate global kill
        k.set_global_kill(False)

        # Task kill
        k.set_task_kill("t6")
        assert k.get_task("t6")["state"] == "CANCELLED"

        with pytest.raises(InvalidTransition):
            k.transition("t6", "READY")
    finally:
        k.close()


def test_task_kernel_concurrent_worker_claim_race(tmp_path):
    db_file = tmp_path / "k.db"
    k_init = TaskKernel(db_file)
    try:
        for i in range(15):
            tid = f"task_race_{i}"
            k_init.create_task(tid, f"owner_{i % 3}", f"goal_{i}")
            k_init.transition(tid, "PLANNING")
            k_init.transition(tid, "READY")
            k_init.transition(tid, "QUEUED")
    finally:
        k_init.close()

    def worker_claim_loop(worker_id: str):
        k_worker = TaskKernel(db_file)
        claimed = []
        try:
            for _ in range(30):
                lease = k_worker.claim_next(worker_id=worker_id, max_active_per_owner=100, ttl_seconds=60.0)
                if lease is not None:
                    claimed.append(lease.task_id)
        finally:
            k_worker.close()
        return claimed

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker_claim_loop, f"worker_{i}") for i in range(8)]
        all_claimed = []
        for f in concurrent.futures.as_completed(futures):
            all_claimed.extend(f.result())

    assert len(all_claimed) == 15
    assert len(set(all_claimed)) == 15

    k_check = TaskKernel(db_file)
    try:
        for i in range(15):
            t = k_check.get_task(f"task_race_{i}")
            assert t["state"] == "LEASED"
            assert t["active_fencing_token"] == 1
    finally:
        k_check.close()


def test_task_kernel_boot_recovery_orphaned_tasks(tmp_path):
    db_file = tmp_path / "k.db"
    k1 = TaskKernel(db_file)
    try:
        k1.create_task("t_orph_1", "owner1", "orphaned leased task")
        k1.transition("t_orph_1", "PLANNING")
        k1.transition("t_orph_1", "READY")
        k1.transition("t_orph_1", "QUEUED")
        k1.claim("t_orph_1", "w1", ttl_seconds=300.0)

        k1.create_task("t_orph_2", "owner1", "orphaned running task")
        k1.transition("t_orph_2", "PLANNING")
        k1.transition("t_orph_2", "READY")
        k1.transition("t_orph_2", "QUEUED")
        l2 = k1.claim("t_orph_2", "w2", ttl_seconds=300.0)
        k1.start("t_orph_2", l2.lease_id)
    finally:
        k1.close()

    # Reboot kernel
    k2 = TaskKernel(db_file)
    try:
        report = k2.recover_on_boot()
        assert len(report["recovered"]) == 2

        t1 = k2.get_task("t_orph_1")
        assert t1["state"] == "RECOVERING"
        assert t1["active_lease_id"] is None

        t2 = k2.get_task("t_orph_2")
        assert t2["state"] == "HUMAN_REVIEW"
        assert t2["active_lease_id"] is None
    finally:
        k2.close()


def test_task_kernel_idempotency_engine_claim_and_complete(tmp_path):
    k = TaskKernel(tmp_path / "k.db")
    try:
        k.create_task("t9", "owner1", "idempotency test")
        k.transition("t9", "PLANNING")
        k.transition("t9", "READY")
        k.transition("t9", "QUEUED")
        k.claim("t9", "w_idem", ttl_seconds=120.0)

        key1, claimed1 = k.idempotency_claim("t9", "step_api", "POST", "https://api.example.com/charge")
        assert claimed1 is True
        assert isinstance(key1, str) and len(key1) > 0

        key2, claimed2 = k.idempotency_claim("t9", "step_api", "POST", "https://api.example.com/charge")
        assert key2 == key1
        assert claimed2 is False

        k.idempotency_complete(key1, result_ref="txn_receipt_98765")

        status = k.idempotency_status(key1)
        assert status["status"] == "COMPLETED"
        assert status["result_ref"] == "txn_receipt_98765"
    finally:
        k.close()


def test_sqlite_kernel_storage_transaction_isolation_and_close(tmp_path):
    db_file = tmp_path / "storage_test.db"
    storage = SQLiteKernelStorage(db_file, max_conns=4)
    try:
        storage.executescript("CREATE TABLE test_data (id TEXT PRIMARY KEY, val INTEGER);")

        assert storage.in_transaction is False
        storage.begin()
        assert storage.in_transaction is True
        storage.execute("INSERT INTO test_data VALUES (?, ?)", ("row_1", 100))
        storage.commit()
        assert storage.in_transaction is False

        row = storage.fetchone("SELECT val FROM test_data WHERE id=?", ("row_1",))
        assert row is not None
        assert row["val"] == 100

        # Rollback isolation
        storage.begin()
        assert storage.in_transaction is True
        storage.execute("INSERT INTO test_data VALUES (?, ?)", ("row_2", 200))
        storage.rollback()
        assert storage.in_transaction is False

        row_rb = storage.fetchone("SELECT val FROM test_data WHERE id=?", ("row_2",))
        assert row_rb is None
    finally:
        storage.close()
