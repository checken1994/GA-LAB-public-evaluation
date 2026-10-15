from __future__ import annotations

import json
from typing import Any

import pytest

from scp.task_kernel import (
    InvalidTransition,
    KernelError,
    StaleLease,
    TaskKernel,
)


def _setup_running_task(kernel: TaskKernel, task_id: str = "adv-1", owner: str = "adv-owner"):
    kernel.create_task(task_id, owner, "adversarial test goal", "R1")
    for s in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, s, actor="setup")
    lease = kernel.claim(task_id, "worker-1", ttl_seconds=300)
    kernel.start(task_id, lease.lease_id)
    return lease


def test_boot_recovery_decrements_queue_active_and_permits_subsequent_claims(tmp_path):
    db_path = tmp_path / "kernel.sqlite3"
    k1 = TaskKernel(db_path)
    try:
        _setup_running_task(k1, "adv-boot-1", "owner-alpha")
        status = k1.queue_status()
        owner_entry = next(o for o in status["owners"] if o["owner"] == "owner-alpha")
        assert owner_entry["active"] == 1
    finally:
        k1.close()

    # Reboot
    k_boot = TaskKernel(db_path)
    try:
        report = k_boot.recover_on_boot()
        assert len(report["recovered"]) == 1

        # Queue active count MUST be decremented to 0
        status_after = k_boot.queue_status()
        owner_after = next(o for o in status_after["owners"] if o["owner"] == "owner-alpha")
        assert owner_after["active"] == 0, "queue_accounts.active leaked across boot recovery"

        # Subsequent claim_next for owner-alpha must not be blocked
        k_boot.create_task("adv-boot-2", "owner-alpha", "second task", "R1")
        for s in ("PLANNING", "READY", "QUEUED"):
            k_boot.transition("adv-boot-2", s, actor="setup")
        claimed = k_boot.claim_next("worker-2", max_active_per_owner=1)
        assert claimed is not None, "owner was permanently blocked by leaked queue_accounts quota"
        assert claimed.task_id == "adv-boot-2"
    finally:
        k_boot.close()


def test_transition_to_human_review_or_recovering_releases_lease_and_queue_quota(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _setup_running_task(kernel, "adv-hr-1", "owner-beta")
        assert kernel.queue_status()["owners"][0]["active"] == 1

        # Worker moves task to HUMAN_REVIEW (non-terminal, non-leased)
        kernel.transition("adv-hr-1", "HUMAN_REVIEW", actor="worker-1", reason="need_human")

        # In DB, lease must be released
        lease_row = kernel.conn.execute("SELECT * FROM leases WHERE lease_id=?", (lease.lease_id,)).fetchone()
        assert lease_row["released"] == 1, "lease remained unreleased after transition out of leased state"

        # Queue slot must be released
        assert kernel.queue_status()["owners"][0]["active"] == 0, "queue slot leaked on transition to HUMAN_REVIEW"

        # Instance bound lease must be cleared
        assert "adv-hr-1" not in getattr(kernel, "_bound_leases", {})

        # Owner can claim another task immediately
        kernel.create_task("adv-hr-2", "owner-beta", "second task", "R1")
        for s in ("PLANNING", "READY", "QUEUED"):
            kernel.transition("adv-hr-2", s, actor="setup")
        claimed = kernel.claim_next("worker-2", max_active_per_owner=1)
        assert claimed is not None
    finally:
        kernel.close()


def test_checkpoint_rejected_on_non_running_or_mismatched_task(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _setup_running_task(kernel, "adv-cp-1", "owner-gamma")
        # Transition out of running to HUMAN_REVIEW
        kernel.transition("adv-cp-1", "HUMAN_REVIEW", actor="worker-1", reason="need_human")

        # Checkpoint on task in HUMAN_REVIEW must fail
        with pytest.raises((InvalidTransition, StaleLease)):
            kernel.checkpoint(
                "adv-cp-1",
                lease.lease_id,
                "step-1",
                "RUNNING",
                {"action": "test"},
                0,
                "idem-cp-1",
            )
    finally:
        kernel.close()


def test_rogue_worker_cannot_hijack_transition_by_quoting_active_lease_id(tmp_path):
    db_path = tmp_path / "kernel.sqlite3"
    worker_legit = TaskKernel(db_path)
    worker_rogue = TaskKernel(db_path)
    try:
        lease = _setup_running_task(worker_legit, "adv-hijack-1", "owner-delta")

        # Rogue worker reads active_lease_id from DB
        active_lease = worker_rogue.get_task("adv-hijack-1")["active_lease_id"]
        assert active_lease == lease.lease_id

        # Rogue worker attempts to transition task using stolen lease_id
        with pytest.raises(StaleLease):
            worker_rogue.transition("adv-hijack-1", "HUMAN_REVIEW", lease_id=active_lease)

        # Task remains in RUNNING for legitimate worker
        assert worker_legit.get_task("adv-hijack-1")["state"] == "RUNNING"
        # Legitimate worker can transition
        worker_legit.transition("adv-hijack-1", "VERIFYING", actor="worker-1")
        assert worker_legit.get_task("adv-hijack-1")["state"] == "VERIFYING"
    finally:
        worker_legit.close()
        worker_rogue.close()


def test_release_increments_version_with_occ(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _setup_running_task(kernel, "adv-rel-1", "owner-epsilon")
        v_before = kernel.get_task("adv-rel-1")["version"]

        kernel.release("adv-rel-1", lease.lease_id)
        task_after = kernel.get_task("adv-rel-1")
        assert task_after["version"] == v_before + 1, "release() must increment version"
        assert task_after["active_lease_id"] is None
        assert task_after["active_fencing_token"] == 0
    finally:
        kernel.close()


def test_rebuild_projection_reconstructs_active_lease_and_fencing_token(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _setup_running_task(kernel, "adv-proj-1", "owner-zeta")
        task_before = kernel.get_task("adv-proj-1")
        assert task_before["active_lease_id"] == lease.lease_id
        assert task_before["active_fencing_token"] == lease.fencing_token

        # Rebuild projection
        rebuilt = kernel.rebuild_projection("adv-proj-1")
        assert rebuilt["active_lease_id"] == lease.lease_id
        assert rebuilt["active_fencing_token"] == lease.fencing_token

        # Now transition to CANCELLED
        kernel.set_task_kill("adv-proj-1", actor="test")
        rebuilt_cancelled = kernel.rebuild_projection("adv-proj-1")
        assert rebuilt_cancelled["state"] == "CANCELLED"
        assert rebuilt_cancelled["active_lease_id"] is None
        assert rebuilt_cancelled["active_fencing_token"] == 0
    finally:
        kernel.close()


def test_rogue_worker_cannot_start_heartbeat_release_or_checkpoint(tmp_path):
    db_path = tmp_path / "kernel.sqlite3"
    worker_legit = TaskKernel(db_path)
    worker_rogue = TaskKernel(db_path)
    try:
        worker_legit.create_task("adv-auth-1", "owner-eta", "adversarial auth goal", "R1")
        for s in ("PLANNING", "READY", "QUEUED"):
            worker_legit.transition("adv-auth-1", s, actor="setup")
        lease = worker_legit.claim("adv-auth-1", "worker-legit", ttl_seconds=300)

        # Rogue worker cannot call start()
        with pytest.raises(StaleLease):
            worker_rogue.start("adv-auth-1", lease.lease_id)

        # Legitimate worker starts task
        worker_legit.start("adv-auth-1", lease.lease_id)

        # Rogue worker cannot call heartbeat()
        with pytest.raises(StaleLease):
            worker_rogue.heartbeat("adv-auth-1", lease.lease_id)

        # Rogue worker cannot call checkpoint()
        with pytest.raises(StaleLease):
            worker_rogue.checkpoint(
                "adv-auth-1",
                lease.lease_id,
                "step-1",
                "RUNNING",
                {"action": "test"},
                0,
                "idem-auth-1",
            )

        # Rogue worker cannot call release()
        with pytest.raises(StaleLease):
            worker_rogue.release("adv-auth-1", lease.lease_id)

        # Legitimate worker can heartbeat, checkpoint, and release
        worker_legit.heartbeat("adv-auth-1", lease.lease_id)
        cp_id = worker_legit.checkpoint(
            "adv-auth-1",
            lease.lease_id,
            "step-1",
            "RUNNING",
            {"action": "test"},
            0,
            "idem-auth-1",
        )
        assert cp_id.startswith("cp_")
        worker_legit.release("adv-auth-1", lease.lease_id)
        assert worker_legit.get_task("adv-auth-1")["active_lease_id"] is None
    finally:
        worker_legit.close()
        worker_rogue.close()


def test_enter_reconciling_releases_leases_and_decrements_queue_active(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _setup_running_task(kernel, "adv-rec-1", "owner-theta")
        idem_key, claimed = kernel.idempotency_claim("adv-rec-1", "step-1", "http.post", "https://api.test/charge")
        assert claimed is True
        disp = kernel.record_action_dispatched(
            "adv-rec-1",
            lease.lease_id,
            "step-1",
            {"action": "charge"},
            1,
            idem_key,
            "provider-req-1",
        )
        cp_id = disp["checkpoint_id"]
        assert kernel.get_task("adv-rec-1")["state"] == "UNKNOWN"

        # Enter reconciling
        kernel.enter_reconciling("adv-rec-1", cp_id)
        task_rec = kernel.get_task("adv-rec-1")
        assert task_rec["state"] == "RECONCILING"
        assert task_rec["active_lease_id"] is None

        # Lease must be released in SQLite
        lease_row = kernel.conn.execute("SELECT released FROM leases WHERE lease_id=?", (lease.lease_id,)).fetchone()
        assert lease_row["released"] == 1, "lease remained unreleased in enter_reconciling"

        # Queue active count must be decremented
        owner_status = next(o for o in kernel.queue_status()["owners"] if o["owner"] == "owner-theta")
        assert owner_status["active"] == 0, "queue active count leaked in enter_reconciling"

        # Zombie heartbeat must fail
        with pytest.raises(StaleLease):
            kernel.heartbeat("adv-rec-1", lease.lease_id)

        # Reconcile outcome NOT_APPLIED moves task to QUEUED
        kernel.reconcile_unknown("adv-rec-1", cp_id, "NOT_APPLIED", "ev_not_applied", "verifier-1")
        assert kernel.get_task("adv-rec-1")["state"] == "QUEUED"

        # Owner can claim the queued task without queue starvation
        claimed_next = kernel.claim_next("worker-2", max_active_per_owner=1)
        assert claimed_next is not None, "owner was starved after reconcile NOT_APPLIED"
        assert claimed_next.task_id == "adv-rec-1"
    finally:
        kernel.close()


def test_expire_leases_recovers_verifying_and_checkpointed_tasks(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        # 1. VERIFYING task with expired lease
        l_ver = _setup_running_task(kernel, "adv-exp-ver", "owner-iota")
        kernel.transition("adv-exp-ver", "VERIFYING")
        # Force expiration in DB
        kernel.conn.execute("UPDATE leases SET expires_at=0 WHERE lease_id=?", (l_ver.lease_id,))

        # 2. CHECKPOINTED task with expired lease
        l_cp = _setup_running_task(kernel, "adv-exp-cp", "owner-kappa")
        kernel.checkpoint("adv-exp-cp", l_cp.lease_id, "s1", "RUNNING", {"a": 1}, 1, "idem-exp-cp")
        kernel.transition("adv-exp-cp", "CHECKPOINTED")
        kernel.conn.execute("UPDATE leases SET expires_at=0 WHERE lease_id=?", (l_cp.lease_id,))

        expired = kernel.expire_leases()
        assert l_ver.lease_id in expired
        assert l_cp.lease_id in expired

        # VERIFYING task must transition to HUMAN_REVIEW (fail-closed)
        t_ver = kernel.get_task("adv-exp-ver")
        assert t_ver["state"] == "HUMAN_REVIEW", f"Expected HUMAN_REVIEW, got {t_ver['state']}"
        assert t_ver["active_lease_id"] is None

        # CHECKPOINTED task must transition to QUEUED (resumable)
        t_cp = kernel.get_task("adv-exp-cp")
        assert t_cp["state"] == "QUEUED", f"Expected QUEUED, got {t_cp['state']}"
        assert t_cp["active_lease_id"] is None
    finally:
        kernel.close()


def test_rogue_worker_cannot_commit_completed_or_verification_result(tmp_path):
    db_path = tmp_path / "kernel.sqlite3"
    worker_legit = TaskKernel(db_path)
    worker_rogue = TaskKernel(db_path)
    try:
        lease = _setup_running_task(worker_legit, "adv-complete-1", "owner-lambda")
        worker_legit.transition("adv-complete-1", "VERIFYING")

        # Rogue worker reads active_lease_id and tries to call commit_completed
        active_lease = worker_rogue.get_task("adv-complete-1")["active_lease_id"]
        assert active_lease == lease.lease_id

        with pytest.raises(StaleLease):
            worker_rogue.commit_completed("adv-complete-1", active_lease, "VERIFIED", "test://fake-evidence")

        # Rogue worker also cannot call commit_verification_result
        with pytest.raises(StaleLease):
            worker_rogue.commit_verification_result(
                "adv-complete-1",
                active_lease,
                {"verdict": "VERIFIED", "verifier_id": "rogue", "evidence_ref": "test://fake"},
            )

        # Legitimate worker can complete task
        completed_task = worker_legit.commit_completed("adv-complete-1", lease.lease_id, "VERIFIED", "test://legit")
        assert completed_task["state"] == "COMPLETED"
        assert completed_task["active_lease_id"] is None
    finally:
        worker_legit.close()
        worker_rogue.close()


def test_rebuild_projection_preserves_active_lease_for_unknown_state(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _setup_running_task(kernel, "adv-proj-unk-1", "owner-mu")
        idem, _ = kernel.idempotency_claim("adv-proj-unk-1", "s1", "http.post", "https://api.test/charge")
        kernel.record_action_dispatched("adv-proj-unk-1", lease.lease_id, "s1", {"a": 1}, 1, idem, "req-1")

        task_before = kernel.get_task("adv-proj-unk-1")
        assert task_before["state"] == "UNKNOWN"
        assert task_before["active_lease_id"] == lease.lease_id

        # Rebuild projection must retain the active lease for UNKNOWN tasks
        rebuilt = kernel.rebuild_projection("adv-proj-unk-1")
        assert rebuilt["state"] == "UNKNOWN"
        assert rebuilt["active_lease_id"] == lease.lease_id
        assert rebuilt["active_fencing_token"] == lease.fencing_token
    finally:
        kernel.close()


def test_occ_conflict_precedes_state_transition_validation(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        kernel.create_task("adv-occ-1", "owner-nu", "occ test goal")
        # Task version is 1 in CREATED
        kernel.transition("adv-occ-1", "PLANNING")
        # Task version is now 2 in PLANNING

        # Attempt transition specifying stale expected_version=1
        with pytest.raises(StaleLease) as excinfo:
            kernel.transition("adv-occ-1", "PLANNING", expected_version=1)
        assert "concurrency conflict" in str(excinfo.value)
    finally:
        kernel.close()


def test_kernel_cancel_method_alias_and_quota_cleanup(tmp_path):
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _setup_running_task(kernel, "adv-cancel-1", "owner-xi")
        cancelled = kernel.cancel("adv-cancel-1")
        assert cancelled["state"] == "CANCELLED"
        assert cancelled["active_lease_id"] is None
        assert cancelled["active_fencing_token"] == 0

        # Lease is marked released and quota is cleaned up
        lease_row = kernel.conn.execute("SELECT * FROM leases WHERE lease_id=?", (lease.lease_id,)).fetchone()
        assert lease_row["released"] == 1

        queue_status = kernel.queue_status()
        owner_status = next(o for o in queue_status["owners"] if o["owner"] == "owner-xi")
        assert owner_status["active"] == 0
    finally:
        kernel.close()


def test_gap11_raw_transition_to_completed_is_strictly_forbidden(tmp_path):
    """GAP-11: Raw transition() to COMPLETED must raise InvalidTransition.

    Tasks can only be completed via commit_completed() with valid evidence and lease.
    """
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _setup_running_task(kernel, "adv-gap11-1", "owner-gap11")
        kernel.transition("adv-gap11-1", "VERIFYING")

        # Rogue attempt: bypass evidence verification via transition()
        with pytest.raises(InvalidTransition) as excinfo:
            kernel.transition(
                "adv-gap11-1",
                "COMPLETED",
                lease_id=lease.lease_id,
                actor="rogue_worker",
                reason="fake pass attempt",
            )
        assert "direct transition to COMPLETED is forbidden" in str(excinfo.value)

        # Verify DB state is unmodified
        task = kernel.get_task("adv-gap11-1")
        assert task["state"] == "VERIFYING"
        events = kernel.get_events("adv-gap11-1")
        assert not any(e["to_state"] == "COMPLETED" for e in events)

        # Legitimate path: commit_completed with valid evidence
        completed = kernel.commit_completed(
            "adv-gap11-1",
            lease.lease_id,
            "VERIFIED",
            "evidence://audit/proof-hash-1234",
        )
        assert completed["state"] == "COMPLETED"
    finally:
        kernel.close()


def test_gap11_adversarial_replay_attack_blocked(tmp_path):
    """GAP-11 Adversarial: Replaying an existing TASK_COMPLETED event_id must fail closed."""
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        lease = _setup_running_task(kernel, "adv-gap11-replay-1", "owner-replay")
        kernel.transition("adv-gap11-replay-1", "VERIFYING")
        completed = kernel.commit_completed(
            "adv-gap11-replay-1",
            lease.lease_id,
            "VERIFIED",
            "evidence://valid/proof-1",
        )
        assert completed["state"] == "COMPLETED"
        events = kernel.get_events("adv-gap11-replay-1")
        completed_evt = [e for e in events if e["to_state"] == "COMPLETED"][0]
        completed_event_id = completed_evt["event_id"]

        # Setup victim task in VERIFYING
        lease_victim = _setup_running_task(kernel, "adv-gap11-victim", "owner-replay")
        kernel.transition("adv-gap11-victim", "VERIFYING")

        # Attack: replay the valid COMPLETED event_id on the victim task
        with pytest.raises(InvalidTransition) as excinfo:
            kernel.transition(
                "adv-gap11-victim",
                "COMPLETED",
                event_id=completed_event_id,
                lease_id=lease_victim.lease_id,
                actor="verifier",
                reason="postcondition_verified",
            )
        assert "direct transition to COMPLETED is forbidden" in str(excinfo.value)
        task_victim = kernel.get_task("adv-gap11-victim")
        assert task_victim["state"] == "VERIFYING"
    finally:
        kernel.close()


def test_gap11_adversarial_all_states_direct_transition_blocked(tmp_path):
    """GAP-11 Adversarial: transition() to COMPLETED is blocked from non-existent and unstarted tasks."""
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        # 1. Non-existent task
        with pytest.raises(InvalidTransition) as excinfo:
            kernel.transition("non-existent-task-id", "COMPLETED")
        assert "direct transition to COMPLETED is forbidden" in str(excinfo.value)

        # 2. Freshly created task (CREATED state)
        kernel.create_task("adv-created-task", "owner-created", "goal")
        with pytest.raises(InvalidTransition) as excinfo:
            kernel.transition("adv-created-task", "COMPLETED")
        assert "direct transition to COMPLETED is forbidden" in str(excinfo.value)
        assert kernel.get_task("adv-created-task")["state"] == "CREATED"

        # 3. Task in PLANNING state
        kernel.transition("adv-created-task", "PLANNING")
        with pytest.raises(InvalidTransition) as excinfo:
            kernel.transition("adv-created-task", "COMPLETED")
        assert "direct transition to COMPLETED is forbidden" in str(excinfo.value)
        assert kernel.get_task("adv-created-task")["state"] == "PLANNING"
    finally:
        kernel.close()


def test_gap11_rebuild_projection_with_tampered_journal_fails_closed(tmp_path):
    """GAP-11 Adversarial: Raw SQLite tampering with events table fails journal integrity and rebuild refuses."""
    import sqlite3
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        _setup_running_task(kernel, "adv-tamper-1", "owner-tamper")
        kernel.transition("adv-tamper-1", "VERIFYING")

        # Directly inject forged COMPLETED event with broken hash into SQLite
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO events(event_id, task_id, seq, type, from_state, to_state, actor, reason, payload_json, event_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "evt_forged_raw",
                "adv-tamper-1",
                99,
                "STATE_TRANSITION",
                "VERIFYING",
                "COMPLETED",
                "forger",
                "fake",
                "{}",
                "fake_hash_value",
                "2026-09-08T00:00:00Z",
            ),
        )
        conn.commit()
        conn.close()

        # Rebuild projection MUST fail-closed due to invalid journal integrity
        with pytest.raises(KernelError) as excinfo:
            kernel.rebuild_projection("adv-tamper-1")
        assert "journal integrity invalid" in str(excinfo.value)

        # Verify DB tasks table was NOT modified
        assert kernel.get_task("adv-tamper-1")["state"] == "VERIFYING"
    finally:
        kernel.close()


def test_watchdog_lease_expiry_racing_commit_completed_blocks_stale_worker(tmp_path):
    """Adversarial R2: Expired lease watchdog racing against commit_completed().

    Verifies that passive TTL expiry or active watchdog expiry strictly blocks
    commit_completed() with StaleLease and cannot force a COMPLETED state.
    """
    import time
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        # 1. Passive TTL expiry
        lease1 = _setup_running_task(kernel, "adv-watchdog-1", "owner-watchdog")
        kernel.transition("adv-watchdog-1", "VERIFYING")
        # Manually expire the lease in DB
        kernel.conn.execute("UPDATE leases SET expires_at=? WHERE lease_id=?", (time.time() - 1.0, lease1.lease_id))

        with pytest.raises(StaleLease):
            kernel.commit_completed(
                "adv-watchdog-1",
                lease1.lease_id,
                "VERIFIED",
                "evidence://passive-expired",
            )
        assert kernel.get_task("adv-watchdog-1")["state"] == "VERIFYING"

        # 2. Active watchdog expiry via expire_leases()
        lease2 = _setup_running_task(kernel, "adv-watchdog-2", "owner-watchdog")
        kernel.transition("adv-watchdog-2", "VERIFYING")
        expired = kernel.expire_leases(now=time.time() + 1000.0)
        assert lease2.lease_id in expired
        # Task must now be in HUMAN_REVIEW
        assert kernel.get_task("adv-watchdog-2")["state"] == "HUMAN_REVIEW"
        assert kernel.get_task("adv-watchdog-2")["active_lease_id"] is None

        # Stale worker attempts commit_completed()
        with pytest.raises(StaleLease):
            kernel.commit_completed(
                "adv-watchdog-2",
                lease2.lease_id,
                "VERIFIED",
                "evidence://stale-worker-after-watchdog",
            )
        assert kernel.get_task("adv-watchdog-2")["state"] == "HUMAN_REVIEW"
        events2 = kernel.get_events("adv-watchdog-2")
        assert not any(e["to_state"] == "COMPLETED" for e in events2)
    finally:
        kernel.close()


def test_fencing_token_staleness_blocks_commit_completed_after_reclaim(tmp_path):
    """Adversarial R2: Fencing token staleness strictly rejects commit_completed()."""
    import time
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        lease1 = _setup_running_task(kernel, "adv-fence-1", "owner-fence")
        # Expire lease1
        kernel.expire_leases(now=time.time() + 1000.0)
        assert kernel.get_task("adv-fence-1")["state"] == "RECOVERING"

        # Re-queue task and claim by worker 2
        kernel.transition("adv-fence-1", "QUEUED")
        lease2 = kernel.claim("adv-fence-1", "worker-2", ttl_seconds=60.0)
        assert lease2.fencing_token > lease1.fencing_token
        kernel.start("adv-fence-1", lease2.lease_id)
        kernel.transition("adv-fence-1", "VERIFYING")

        # Worker 1 (stale fencing token) attempts commit_completed()
        with pytest.raises(StaleLease):
            kernel.commit_completed(
                "adv-fence-1",
                lease1.lease_id,
                "VERIFIED",
                "evidence://stale-token-commit",
            )

        task = kernel.get_task("adv-fence-1")
        assert task["state"] == "VERIFYING"
        assert task["active_lease_id"] == lease2.lease_id
        assert task["active_fencing_token"] == lease2.fencing_token
    finally:
        kernel.close()


def test_multithreaded_lease_watchdog_race_with_commit_completed(tmp_path):
    """Adversarial R2: True concurrent race between expire_leases() and commit_completed()."""
    import concurrent.futures
    import time
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    thread_kernels = []
    try:
        num_tasks = 8
        tasks = []
        # [FLAKE-FIX 2026-09-24] Determinism contract: setup claims use a generous
        # TTL (30s, the product default) so the sequential setup phase can never
        # lose to wall-clock expiry across its fsync'd transactions (CI run
        # 36123219523: ttl=0.1s expired between claim() and transition() on a
        # loaded runner -> StaleLease at setup, before any thread started).
        # Expiry is driven by the watchdog's synthetic clock instead
        # (expire_leases(now=...)), so the race under test is a pure
        # execution-order race between the expire transaction and the commit
        # transaction; both terminal states stay reachable and the assertions
        # below are unchanged.
        for i in range(num_tasks):
            tid = f"adv-race-{i}"
            kernel.create_task(tid, "owner-race", f"goal {i}")
            for s in ("PLANNING", "READY", "QUEUED"):
                kernel.transition(tid, s, actor="setup")
            lease = kernel.claim(tid, f"worker-{i}", ttl_seconds=30.0)
            kernel.start(tid, lease.lease_id)
            kernel.transition(tid, "VERIFYING", lease_id=lease.lease_id)
            tasks.append((tid, lease.lease_id))

        def watchdog_action(tid, lid):
            try:
                time.sleep(0.02)
                k = TaskKernel(db_file)
                thread_kernels.append(k)
                # Synthetic now=+120s deterministically treats every setup lease
                # (expires_at <= setup_end + 30s) as expired whenever this
                # watchdog runs within ~90s of setup end.
                k.expire_leases(now=time.time() + 120.0)
            except Exception:
                pass

        def commit_action(tid, lid):
            try:
                time.sleep(0.02)
                k = TaskKernel(db_file)
                thread_kernels.append(k)
                k._bound_leases[tid] = lid
                k.commit_completed(tid, lid, "VERIFIED", f"evidence://{tid}")
            except Exception:
                pass

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = []
            for tid, lid in tasks:
                futures.append(executor.submit(watchdog_action, tid, lid))
                futures.append(executor.submit(commit_action, tid, lid))
            concurrent.futures.wait(futures)

        for tid, lid in tasks:
            task = kernel.get_task(tid)
            assert task["state"] in {"COMPLETED", "HUMAN_REVIEW"}, f"Task {tid} in unexpected state: {task['state']}"
            events = kernel.get_events(tid)
            event_types = [e["type"] for e in events]
            if task["state"] == "COMPLETED":
                assert "TASK_COMPLETED" in event_types
                assert event_types[-1] == "TASK_COMPLETED"
            elif task["state"] == "HUMAN_REVIEW":
                assert "LEASE_EXPIRED" in event_types
                assert "TASK_COMPLETED" not in event_types
    finally:
        for tk in thread_kernels:
            try:
                tk.close()
            except Exception:
                pass
        kernel.close()


def test_multiprocess_direct_transition_to_completed_blocked(tmp_path):
    """Adversarial R3: Direct transition to COMPLETED across OS process boundary is blocked."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    db_path = tmp_path / "multiproc.sqlite3"
    kernel = TaskKernel(db_path)
    try:
        lease = _setup_running_task(kernel, "adv-mp-1", "owner-mp")
        kernel.transition("adv-mp-1", "VERIFYING", lease_id=lease.lease_id)

        # Worker subprocess attempts kernel.transition(..., "COMPLETED")
        code = (
            "import sys\n"
            "from pathlib import Path\n"
            "from scp.task_kernel import TaskKernel, InvalidTransition\n"
            "k = TaskKernel(Path(sys.argv[1]))\n"
            "try:\n"
            "    k.transition(sys.argv[2], 'COMPLETED', lease_id=sys.argv[3])\n"
            "    sys.exit(1)\n"
            "except InvalidTransition:\n"
            "    sys.exit(0)\n"
            "finally:\n"
            "    k.close()\n"
        )
        cmd = [
            sys.executable,
            "-c",
            code,
            str(db_path),
            "adv-mp-1",
            lease.lease_id,
        ]
        repo_root = Path(__file__).resolve().parents[2]
        proc = subprocess.run(
            cmd,
            env={**os.environ, "PYTHONPATH": str(repo_root)},
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0, f"Subprocess succeeded or failed unexpectedly: {proc.stdout} {proc.stderr}"
        assert kernel.get_task("adv-mp-1")["state"] == "VERIFYING"
        events = kernel.get_events("adv-mp-1")
        assert not any(e["to_state"] == "COMPLETED" for e in events)
    finally:
        kernel.close()


def test_full_lifecycle_checkpointed_and_waiting_tool_transitions(tmp_path):
    """FA-13 Group 1: Lifecycle transitions through CHECKPOINTED and WAITING_TOOL."""
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        # Branch 1: RUNNING -> CHECKPOINTED -> RUNNING -> VERIFYING -> commit_completed
        lease1 = _setup_running_task(kernel, "adv-cp-1", "owner-cp")
        kernel.transition("adv-cp-1", "CHECKPOINTED", lease_id=lease1.lease_id)
        assert kernel.get_task("adv-cp-1")["state"] == "CHECKPOINTED"
        kernel.transition("adv-cp-1", "RUNNING", lease_id=lease1.lease_id)
        assert kernel.get_task("adv-cp-1")["state"] == "RUNNING"
        kernel.transition("adv-cp-1", "VERIFYING", lease_id=lease1.lease_id)
        completed1 = kernel.commit_completed("adv-cp-1", lease1.lease_id, "VERIFIED", "evidence://cp-1")
        assert completed1["state"] == "COMPLETED"

        # Branch 2: RUNNING -> WAITING_TOOL -> VERIFYING -> commit_completed
        lease2 = _setup_running_task(kernel, "adv-wt-1", "owner-wt")
        kernel.transition("adv-wt-1", "WAITING_TOOL", lease_id=lease2.lease_id)
        assert kernel.get_task("adv-wt-1")["state"] == "WAITING_TOOL"
        kernel.transition("adv-wt-1", "VERIFYING", lease_id=lease2.lease_id)
        assert kernel.get_task("adv-wt-1")["state"] == "VERIFYING"
        completed2 = kernel.commit_completed("adv-wt-1", lease2.lease_id, "VERIFIED", "evidence://wt-1")
        assert completed2["state"] == "COMPLETED"
    finally:
        kernel.close()


def test_lifecycle_recovering_reconciling_branches(tmp_path):
    """FA-13 Group 1: Lifecycle transitions through RECOVERING and RECONCILING."""
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        # Branch 1: RUNNING -> RECOVERING -> RECONCILING -> QUEUED -> LEASED -> RUNNING -> VERIFYING -> COMPLETED
        lease1 = _setup_running_task(kernel, "adv-rec-1", "owner-rec")
        kernel.transition("adv-rec-1", "RECOVERING", lease_id=lease1.lease_id)
        assert kernel.get_task("adv-rec-1")["state"] == "RECOVERING"

        kernel.transition("adv-rec-1", "RECONCILING")
        assert kernel.get_task("adv-rec-1")["state"] == "RECONCILING"

        # Transition to QUEUED
        kernel.transition("adv-rec-1", "QUEUED")
        assert kernel.get_task("adv-rec-1")["state"] == "QUEUED"

        lease2 = kernel.claim("adv-rec-1", "worker-2", ttl_seconds=60)
        kernel.start("adv-rec-1", lease2.lease_id)
        kernel.transition("adv-rec-1", "VERIFYING", lease_id=lease2.lease_id)
        completed = kernel.commit_completed("adv-rec-1", lease2.lease_id, "VERIFIED", "evidence://rec-1")
        assert completed["state"] == "COMPLETED"

        # Branch 2: RECONCILING -> CHECKPOINTED
        lease_rec2 = _setup_running_task(kernel, "adv-rec-2", "owner-rec")
        kernel.transition("adv-rec-2", "RECOVERING", lease_id=lease_rec2.lease_id)
        kernel.transition("adv-rec-2", "RECONCILING")
        kernel.transition("adv-rec-2", "CHECKPOINTED")
        assert kernel.get_task("adv-rec-2")["state"] == "CHECKPOINTED"

        # Branch 3: RECONCILING -> HUMAN_REVIEW -> READY -> QUEUED
        lease_rec3 = _setup_running_task(kernel, "adv-rec-3", "owner-rec")
        kernel.transition("adv-rec-3", "RECOVERING", lease_id=lease_rec3.lease_id)
        kernel.transition("adv-rec-3", "RECONCILING")
        kernel.transition("adv-rec-3", "HUMAN_REVIEW")
        assert kernel.get_task("adv-rec-3")["state"] == "HUMAN_REVIEW"
        kernel.transition("adv-rec-3", "READY")
        assert kernel.get_task("adv-rec-3")["state"] == "READY"
        kernel.transition("adv-rec-3", "QUEUED")
        assert kernel.get_task("adv-rec-3")["state"] == "QUEUED"

        # Branch 4: WAITING_TOOL -> UNKNOWN -> RECOVERING (under system authority)
        lease_rec4 = _setup_running_task(kernel, "adv-rec-4", "owner-rec")
        kernel.transition("adv-rec-4", "WAITING_TOOL", lease_id=lease_rec4.lease_id)
        kernel.transition("adv-rec-4", "UNKNOWN", lease_id=lease_rec4.lease_id)
        assert kernel.get_task("adv-rec-4")["state"] == "UNKNOWN"
        kernel._system_authority = True
        try:
            kernel.transition("adv-rec-4", "RECOVERING", actor="system_watchdog")
            assert kernel.get_task("adv-rec-4")["state"] == "RECOVERING"
        finally:
            kernel._system_authority = False
    finally:
        kernel.close()


def test_cancellation_from_all_valid_pre_terminal_states(tmp_path):
    """FA-13 Group 2: Cancellation from CREATED, PLANNING, READY, QUEUED, RUNNING."""
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        # 1. From CREATED
        kernel.create_task("adv-cancel-1", "owner-c", "cancel from created")
        c1 = kernel.cancel("adv-cancel-1")
        assert c1["state"] == "CANCELLED"
        with pytest.raises(InvalidTransition):
            kernel.transition("adv-cancel-1", "PLANNING")

        # 2. From PLANNING
        kernel.create_task("adv-cancel-2", "owner-c", "cancel from planning")
        kernel.transition("adv-cancel-2", "PLANNING")
        c2 = kernel.cancel("adv-cancel-2")
        assert c2["state"] == "CANCELLED"

        # 3. From READY
        kernel.create_task("adv-cancel-3", "owner-c", "cancel from ready")
        kernel.transition("adv-cancel-3", "PLANNING")
        kernel.transition("adv-cancel-3", "READY")
        c3 = kernel.cancel("adv-cancel-3")
        assert c3["state"] == "CANCELLED"

        # 4. From QUEUED
        kernel.create_task("adv-cancel-4", "owner-c", "cancel from queued")
        kernel.transition("adv-cancel-4", "PLANNING")
        kernel.transition("adv-cancel-4", "READY")
        kernel.transition("adv-cancel-4", "QUEUED")
        c4 = kernel.cancel("adv-cancel-4")
        assert c4["state"] == "CANCELLED"

        # 5. From RUNNING
        _setup_running_task(kernel, "adv-cancel-5", "owner-c")
        c5 = kernel.cancel("adv-cancel-5")
        assert c5["state"] == "CANCELLED"
        assert kernel.get_task("adv-cancel-5")["active_lease_id"] is None
    finally:
        kernel.close()


@pytest.mark.asyncio
async def test_ask_kernel_adapter_caller_fail_and_finalize_integration(tmp_path, monkeypatch):
    """FA-13 Group 4: AskKernelAdapter integration covering fail() and finalize() -> commit_completed()."""
    import scp.runtime.judge_llm as judge_mod
    from scp.ask_kernel_adapter import AskKernelAdapter

    async def _fake_judge(question: str, ai_answer: str, context: str = "") -> bool:
        return True

    monkeypatch.setattr(judge_mod, "_llm_judge_async", _fake_judge)
    monkeypatch.setenv("SCP_MULTI_LLM_CROSSCHECK", "0")

    db_path = str(tmp_path / "adapter_kernel.sqlite3")
    trace_path = str(tmp_path / "adapter_trace.jsonl")
    adapter = AskKernelAdapter(db_path=db_path, trace_path=trace_path)
    try:
        class DummyReq:
            question = "what color is the sky?"
            contexts = ["sky is blue"]
            retrieved_context = ""
            session_id = "caller-test"

        req = DummyReq()

        # Part 1: adapter.fail() sets task state to FAILED
        task1 = adapter.begin(req.question, list(req.contexts), req.retrieved_context, "session-fail")
        t1_id = task1["task_id"]
        assert adapter.kernel.get_task(t1_id)["state"] == "RUNNING"
        adapter.fail(task1, reason="upstream handler failed")
        assert adapter.kernel.get_task(t1_id)["state"] == "FAILED"

        # Part 2: adapter.finalize() commits verified task to COMPLETED via commit_completed()
        task2 = adapter.begin(req.question, list(req.contexts), req.retrieved_context, "session-complete")
        t2_id = task2["task_id"]
        assert adapter.kernel.get_task(t2_id)["state"] == "RUNNING"

        passing_response = {
            "final_answer": "The sky is blue",
            "verdict": "PASS",
            "governance_decision": "UPHOLD",
            "v98_classification": {"provenance": "input_context_only"},
        }

        res = await adapter.finalize(task2, passing_response, req)
        assert res["verification"]["verdict"] == "VERIFIED"
        assert res["task"]["state"] == "COMPLETED"
        assert adapter.kernel.get_task(t2_id)["state"] == "COMPLETED"
        events = adapter.kernel.get_events(t2_id)
        assert any(e["type"] == "TASK_COMPLETED" and e["to_state"] == "COMPLETED" for e in events)
    finally:
        adapter.kernel.close()


# =========================================================================
# GAP-12 REMEDIATION: 9 CAUSAL BRANCH TESTS (FA-12 & FA-13)
# =========================================================================

def test_branch_1_direct_transition_to_failed_forbidden_from_all_states(tmp_path):
    """Branch 1: Direct transition(..., 'FAILED') is forbidden from all states."""
    db_path = str(tmp_path / "b1_kernel.sqlite3")
    kernel = TaskKernel(db_path)
    try:
        kernel.create_task("task-b1-1", "owner-1", "test b1", max_attempts=3)
        kernel.transition("task-b1-1", "PLANNING", actor="planner")

        # Vector 1: from PLANNING
        with pytest.raises(InvalidTransition, match="direct transition to FAILED is forbidden"):
            kernel.transition("task-b1-1", "FAILED", actor="rogue", reason="arbitrary_fail")
        assert kernel.get_task("task-b1-1")["state"] == "PLANNING"

        # Vector 2: from RUNNING
        kernel.transition("task-b1-1", "READY", actor="planner")
        kernel.transition("task-b1-1", "QUEUED", actor="scheduler")
        lease = kernel.claim("task-b1-1", "worker-1")
        kernel.start("task-b1-1", lease.lease_id)
        assert kernel.get_task("task-b1-1")["state"] == "RUNNING"

        with pytest.raises(InvalidTransition, match="direct transition to FAILED is forbidden"):
            kernel.transition("task-b1-1", "FAILED", lease_id=lease.lease_id, actor="worker-1", reason="worker_fail")
        assert kernel.get_task("task-b1-1")["state"] == "RUNNING"

        # Vector 3: from VERIFYING
        kernel.transition("task-b1-1", "VERIFYING", lease_id=lease.lease_id, actor="worker-1")
        assert kernel.get_task("task-b1-1")["state"] == "VERIFYING"

        with pytest.raises(InvalidTransition, match="direct transition to FAILED is forbidden"):
            kernel.transition("task-b1-1", "FAILED", lease_id=lease.lease_id, actor="worker-1", reason="verifier_fail")
        assert kernel.get_task("task-b1-1")["state"] == "VERIFYING"
    finally:
        kernel.close()


def test_branch_2_commit_failed_invalid_lease_or_nonexistent_task(tmp_path):
    """Branch 2: commit_failed() rejects nonexistent task, invalid lease, or released lease."""
    from scp.task_kernel import NotFound

    db_path = str(tmp_path / "b2_kernel.sqlite3")
    kernel = TaskKernel(db_path)
    try:
        kernel.create_task("task-b2", "owner-1", "test b2")
        kernel.transition("task-b2", "PLANNING")
        kernel.transition("task-b2", "READY")
        kernel.transition("task-b2", "QUEUED")
        lease = kernel.claim("task-b2", "worker-1")
        kernel.start("task-b2", lease.lease_id)

        # 1. Nonexistent task
        with pytest.raises(NotFound):
            kernel.commit_failed(
                "nonexistent-task",
                lease.lease_id,
                actor="worker-1",
                failure_classification="FATAL",
                indictment_ref="ref://b2/1",
            )

        # 2. Invalid lease ID
        with pytest.raises(StaleLease):
            kernel.commit_failed(
                "task-b2",
                "nonexistent-lease-xyz",
                actor="worker-1",
                failure_classification="FATAL",
                indictment_ref="ref://b2/2",
            )

        # 3. Released lease
        kernel.release("task-b2", lease.lease_id)
        with pytest.raises(Exception):
            kernel.commit_failed(
                "task-b2",
                lease.lease_id,
                actor="worker-1",
                failure_classification="FATAL",
                indictment_ref="ref://b2/3",
            )
    finally:
        kernel.close()


def test_branch_3_commit_failed_stolen_lease_actor_mismatch(tmp_path):
    """Branch 3: commit_failed() rejects stolen lease when actor != lease.worker_id."""
    db_path = str(tmp_path / "b3_kernel.sqlite3")
    kernel = TaskKernel(db_path)
    try:
        kernel.create_task("task-b3", "owner-1", "test b3")
        kernel.transition("task-b3", "PLANNING")
        kernel.transition("task-b3", "READY")
        kernel.transition("task-b3", "QUEUED")
        lease = kernel.claim("task-b3", "legitimate-worker")
        kernel.start("task-b3", lease.lease_id)

        # Saboteur uses the valid lease_id but rogue actor name
        with pytest.raises(InvalidTransition, match="does not match lease worker"):
            kernel.commit_failed(
                "task-b3",
                lease.lease_id,
                actor="rogue-saboteur",
                failure_classification="FATAL",
                indictment_ref="ref://b3/stolen",
            )

        # Verify task is still safely RUNNING under legitimate worker
        task = kernel.get_task("task-b3")
        assert task["state"] == "RUNNING"
        assert task["active_lease_id"] == lease.lease_id
    finally:
        kernel.close()


def test_branch_4_commit_failed_missing_or_empty_indictment_rejected(tmp_path):
    """Branch 4: commit_failed() fails-closed when indictment_ref is empty or whitespace."""
    db_path = str(tmp_path / "b4_kernel.sqlite3")
    kernel = TaskKernel(db_path)
    try:
        kernel.create_task("task-b4", "owner-1", "test b4")
        kernel.transition("task-b4", "PLANNING")
        kernel.transition("task-b4", "READY")
        kernel.transition("task-b4", "QUEUED")
        lease = kernel.claim("task-b4", "worker-1")
        kernel.start("task-b4", lease.lease_id)

        with pytest.raises(KernelError, match="indictment_ref is required"):
            kernel.commit_failed(
                "task-b4",
                lease.lease_id,
                actor="worker-1",
                failure_classification="FATAL",
                indictment_ref="",
            )

        with pytest.raises(KernelError, match="indictment_ref is required"):
            kernel.commit_failed(
                "task-b4",
                lease.lease_id,
                actor="worker-1",
                failure_classification="FATAL",
                indictment_ref="    ",
            )
    finally:
        kernel.close()


def test_branch_5_commit_failed_retryable_preserves_retry_budget(tmp_path):
    """Branch 5: commit_failed() with RETRYABLE classification and attempts < max_attempts routes to RETRY_SCHEDULED."""
    db_path = str(tmp_path / "b5_kernel.sqlite3")
    kernel = TaskKernel(db_path)
    try:
        kernel.create_task("task-b5", "owner-1", "test b5", max_attempts=3)
        kernel.transition("task-b5", "PLANNING")
        kernel.transition("task-b5", "READY")
        kernel.transition("task-b5", "QUEUED")
        lease = kernel.claim("task-b5", "worker-1")
        kernel.start("task-b5", lease.lease_id)

        # Attempt 1 fails with transient timeout
        updated = kernel.commit_failed(
            "task-b5",
            lease.lease_id,
            actor="worker-1",
            failure_classification="RETRYABLE",
            indictment_ref="ref://b5/attempt1",
            details={"error": "network timeout"},
        )
        assert updated["state"] in ("RETRY_SCHEDULED", "UNKNOWN")
        assert updated["attempts"] == 1
        assert updated["active_lease_id"] is None

        # Confirm event journal recorded TASK_RETRY_SCHEDULED
        events = kernel.get_events("task-b5")
        retry_events = [e for e in events if e["type"] == "TASK_RETRY_SCHEDULED"]
        assert len(retry_events) == 1
        payload = json.loads(retry_events[0]["payload_json"])
        assert payload["attempts"] == 1
        assert payload["max_attempts"] == 3
        assert payload["indictment_ref"] == "ref://b5/attempt1"
    finally:
        kernel.close()


def test_branch_6_commit_failed_retry_budget_exhausted_moves_to_terminal_failed(tmp_path):
    """Branch 6: commit_failed() when retry budget is exhausted moves task to terminal FAILED."""
    db_path = str(tmp_path / "b6_kernel.sqlite3")
    kernel = TaskKernel(db_path)
    try:
        # Task with max_attempts = 1
        kernel.create_task("task-b6", "owner-1", "test b6", max_attempts=1)
        kernel.transition("task-b6", "PLANNING")
        kernel.transition("task-b6", "READY")
        kernel.transition("task-b6", "QUEUED")
        lease = kernel.claim("task-b6", "worker-1")
        kernel.start("task-b6", lease.lease_id)

        updated = kernel.commit_failed(
            "task-b6",
            lease.lease_id,
            actor="worker-1",
            failure_classification="RETRYABLE",
            indictment_ref="ref://b6/exhausted",
            details={"error": "exhausted attempt 1 of 1"},
        )
        assert updated["state"] == "FAILED"
        assert updated["attempts"] == 1
        assert updated["active_lease_id"] is None

        events = kernel.get_events("task-b6")
        failed_events = [e for e in events if e["type"] == "TASK_FAILED"]
        assert len(failed_events) == 1
        assert failed_events[0]["to_state"] == "FAILED"
    finally:
        kernel.close()


def test_branch_7_commit_failed_fatal_classification_terminates_immediately(tmp_path):
    """Branch 7: commit_failed() with FATAL classification terminates immediately regardless of attempts."""
    db_path = str(tmp_path / "b7_kernel.sqlite3")
    kernel = TaskKernel(db_path)
    try:
        # Task with max_attempts = 10
        kernel.create_task("task-b7", "owner-1", "test b7", max_attempts=10)
        kernel.transition("task-b7", "PLANNING")
        kernel.transition("task-b7", "READY")
        kernel.transition("task-b7", "QUEUED")
        lease = kernel.claim("task-b7", "worker-1")
        kernel.start("task-b7", lease.lease_id)

        updated = kernel.commit_failed(
            "task-b7",
            lease.lease_id,
            actor="worker-1",
            failure_classification="FATAL",
            indictment_ref="ref://b7/fatal_crash",
            details={"error": "corrupted input invariant"},
        )
        assert updated["state"] == "FAILED"
        assert updated["attempts"] == 1
        assert updated["active_lease_id"] is None

        events = kernel.get_events("task-b7")
        failed_events = [e for e in events if e["type"] == "TASK_FAILED"]
        assert len(failed_events) == 1
        payload = json.loads(failed_events[0]["payload_json"])
        assert payload["failure_classification"] == "FATAL"
    finally:
        kernel.close()


def test_branch_8_ask_kernel_adapter_fail_integration(tmp_path):
    """Branch 8: AskKernelAdapter.fail() properly calls commit_failed() and records indictment."""
    from scp.ask_kernel_adapter import AskKernelAdapter

    db_path = str(tmp_path / "b8_kernel.sqlite3")
    trace_path = str(tmp_path / "b8_trace.jsonl")
    adapter = AskKernelAdapter(db_path=db_path, trace_path=trace_path)
    try:
        task = adapter.begin("test question?", ["context 1"], "", "session-b8")
        task_id = task["task_id"]
        assert adapter.kernel.get_task(task_id)["state"] == "RUNNING"

        adapter.fail(task, reason="upstream_handler_timeout", failure_classification="FATAL")
        task_after = adapter.kernel.get_task(task_id)
        assert task_after["state"] == "FAILED"
        assert task_after["active_lease_id"] is None

        events = adapter.kernel.get_events(task_id)
        failed_events = [e for e in events if e["type"] == "TASK_FAILED"]
        assert len(failed_events) == 1
        payload = json.loads(failed_events[0]["payload_json"])
        assert "ask://" in payload["indictment_ref"]
        assert payload["actor"] == "ask-route-worker"
    finally:
        adapter.kernel.close()


@pytest.mark.asyncio
async def test_branch_9_task_kernel_bridge_policy_denial_integration(tmp_path):
    """Branch 9: TaskKernelHandsBridge routes policy denial to commit_failed() with verified indictment.

    [C1s2 TRIAGE 2026-09-12] Pre-existing failure root-caused: this test pinned
    the PRE-M4 contract where a missing capability token still created kernel
    state (task/lease/checkpoint) and only failed at the executor PEP afterwards.
    Commit 0d13c85 (M4 FIX 2026-09-11) deliberately changed the product contract
    to fail closed: a request with no parsable capability token raises
    PermissionError (CapabilityRequiredError, FA-05) BEFORE action resolution and
    BEFORE any TaskKernel mutation. The product is correct (fail-closed, no
    kernel side effects for unauthorized callers); this test pinned the outdated
    ordering. Strictness INCREASED, no assertion loosened:
    - Leg A (new): missing token -> PermissionError AND no kernel task exists
      (deterministic task id from request_key proves zero kernel mutation).
    - Leg B (original intent preserved): WITH a valid token the executor policy
      denial is still routed to commit_failed() -> FAILED state with a
      hands:// indictment, exactly one TASK_FAILED event, actor pinned, and the
      journal hash chain still verifies.
    """
    import time as _time

    from scp.core.capability_token import (
        CapabilityToken,
        compute_token_signature,
        get_capability_secret,
    )
    from scp.hands.task_kernel_bridge import TaskKernelHandsBridge
    from scp.task_kernel import NotFound, TaskKernel

    class FakeActionDef:
        mutates_state = True
        risk = "R1"

    class FakeRegistry:
        def require(self, action):
            return FakeActionDef()

    class FakePolicyDeniedExecutor:
        def __init__(self):
            self.data_dir = str(tmp_path)
            self.registry = FakeRegistry()
            class FakeAuth:
                def status(self):
                    return {"epoch": 1}
            self.capability_authority = FakeAuth()

        def _audit(self, event: str, payload: dict[str, Any]) -> None:
            pass

        async def execute(self, action, params, capability_level, approved, dry_run, capability_token=None):
            return {
                "success": False,
                "error": "CapabilityRequiredError: capability token required but missing",
                "requiresRecovery": False,
                "safeToRetry": False,
            }

    db_path = str(tmp_path / "b9_kernel.sqlite3")
    kernel = TaskKernel(db_path)
    bridge = TaskKernelHandsBridge(executor=FakePolicyDeniedExecutor(), kernel=kernel)
    try:
        # Leg A — M4 fail-closed ordering: missing token is a PermissionError
        # before ANY kernel mutation (no task, no lease, no checkpoint).
        with pytest.raises(PermissionError) as perm_exc:
            await bridge.execute(
                action="restricted_read",
                params={"target": "/etc/shadow"},
                capability_level=2,
                approved=False,
                request_key="b9-policy-denial-no-token",
                capability_token=None,
            )
        assert "CapabilityRequiredError" in str(perm_exc.value)
        assert "FA-05" in str(perm_exc.value)
        unmutated_task_id = bridge._task_id("b9-policy-denial-no-token")
        with pytest.raises(NotFound):
            kernel.get_task(unmutated_task_id)

        # Leg B — original Branch 9 intent: a token-carrying request that the
        # executor PEP denies is routed to commit_failed() with indictment.
        secret = get_capability_secret()
        now_ts = _time.time()
        token_sig = compute_token_signature(secret, "hands:restricted_read", 1, "tok-b9-denial", now_ts)
        valid_token = CapabilityToken("hands:restricted_read", 1, "tok-b9-denial", now_ts, token_sig)

        result = await bridge.execute(
            action="restricted_read",
            params={"target": "/etc/shadow"},
            capability_level=2,
            approved=False,
            request_key="b9-policy-denial-with-token",
            capability_token=valid_token,
        )
        assert result["success"] is False
        assert result["kernel"]["taskState"] == "FAILED"

        task_id = result["kernel"]["taskId"]
        task = kernel.get_task(task_id)
        assert task["state"] == "FAILED"
        assert task["active_lease_id"] is None

        events = kernel.get_events(task_id)
        failed_events = [e for e in events if e["type"] == "TASK_FAILED"]
        assert len(failed_events) == 1
        payload = json.loads(failed_events[0]["payload_json"])
        assert "hands://" in payload["indictment_ref"]
        assert "/policy_denied/restricted_read" in payload["indictment_ref"]
        assert payload["actor"] == bridge.worker_id

        journal_report = kernel.verify_journal(task_id)
        assert journal_report["hash_chain_valid"] is True, journal_report
    finally:
        kernel.close()


# ==============================================================================
# GAP-13: Unauthenticated WAITING_APPROVAL Bypass Remediation (FA-13 Causal Matrix)
# ==============================================================================


def test_gap13_branch_1_direct_transition_to_ready_blocked(tmp_path):
    """BR-1: Raw unauthenticated transition from WAITING_APPROVAL to READY must be blocked."""
    kernel = TaskKernel(tmp_path / "gap13_br1.sqlite3")
    try:
        kernel.create_task("task-br1", "owner-1", "br1 goal", "R3")
        kernel.transition("task-br1", "PLANNING", actor="planner")
        kernel.transition("task-br1", "WAITING_APPROVAL", actor="risk_policy")

        with pytest.raises(InvalidTransition) as exc_info:
            kernel.transition("task-br1", "READY", actor="attacker")

        assert "direct transition from WAITING_APPROVAL to READY is forbidden" in str(exc_info.value)

        # Database state remains WAITING_APPROVAL, version unchanged
        task = kernel.get_task("task-br1")
        assert task["state"] == "WAITING_APPROVAL"
        assert task["version"] == 3

        # 0 unauthorized events recorded
        events = kernel.get_events("task-br1")
        assert not any(e["to_state"] == "READY" for e in events)
    finally:
        kernel.close()


def test_gap13_branch_2_commit_approval_missing_token_rejected(tmp_path):
    """BR-2: Calling commit_approval with None or empty token must be rejected fail-closed."""
    from scp.core.capability_token import InvalidTokenSignatureError

    kernel = TaskKernel(tmp_path / "gap13_br2.sqlite3")
    try:
        kernel.create_task("task-br2", "owner-1", "br2 goal", "R2")
        kernel.transition("task-br2", "PLANNING")
        kernel.transition("task-br2", "WAITING_APPROVAL")

        with pytest.raises((InvalidTokenSignatureError, KernelError)):
            kernel.commit_approval("task-br2", approval_token=None, actor="attacker")

        with pytest.raises((InvalidTokenSignatureError, KernelError)):
            kernel.commit_approval("task-br2", approval_token="", actor="attacker")

        with pytest.raises((InvalidTokenSignatureError, KernelError)):
            kernel.commit_approval("task-br2", approval_token="   ", actor="attacker")

        task = kernel.get_task("task-br2")
        assert task["state"] == "WAITING_APPROVAL"
    finally:
        kernel.close()


def test_gap13_branch_3_commit_approval_tampered_signature_rejected(tmp_path):
    """BR-3: CapabilityToken or compact token with forged/tampered signature must be rejected."""
    import time

    from scp.core.capability_token import (
        CapabilityToken,
        InvalidTokenSignatureError,
        mint_token,
    )

    kernel = TaskKernel(tmp_path / "gap13_br3.sqlite3")
    try:
        kernel.create_task("task-br3", "owner-1", "br3 goal", "R2")
        kernel.transition("task-br3", "PLANNING")
        kernel.transition("task-br3", "WAITING_APPROVAL")

        # Forged CapabilityToken
        forged_cap = CapabilityToken(
            subject="approval:grant",
            epoch=0,
            token_id="tok-forged",
            issued_at=time.time(),
            signature="0123456789abcdef" * 4,
        )
        with pytest.raises(InvalidTokenSignatureError):
            kernel.commit_approval("task-br3", approval_token=forged_cap, actor="attacker")

        # Tampered compact token
        valid_minted = mint_token(issuer="operator", scope="approval:grant", capability_level=2)
        payload_part, _ = valid_minted.rsplit(".", 1)
        tampered_compact = f"{payload_part}.badsignature1234567890"

        with pytest.raises(InvalidTokenSignatureError):
            kernel.commit_approval("task-br3", approval_token=tampered_compact, actor="attacker")

        task = kernel.get_task("task-br3")
        assert task["state"] == "WAITING_APPROVAL"
    finally:
        kernel.close()


def test_gap13_branch_4_commit_approval_wrong_scope_rejected(tmp_path):
    """BR-4: Token with valid signature but unauthorized scope (lacking approval:grant) must be rejected."""
    import time

    from scp.core.capability_token import (
        CapabilityToken,
        compute_token_signature,
        get_capability_secret,
        mint_token,
    )

    kernel = TaskKernel(tmp_path / "gap13_br4.sqlite3")
    try:
        kernel.create_task("task-br4", "owner-1", "br4 goal", "R2")
        kernel.transition("task-br4", "PLANNING")
        kernel.transition("task-br4", "WAITING_APPROVAL")

        secret = get_capability_secret()
        now_ts = time.time()
        sig = compute_token_signature(secret, "hands:read_only", 0, "tok-wrong-scope", now_ts)
        token_wrong = CapabilityToken(
            subject="hands:read_only",
            epoch=0,
            token_id="tok-wrong-scope",
            issued_at=now_ts,
            signature=sig,
        )

        with pytest.raises(InvalidTransition) as exc_info:
            kernel.commit_approval("task-br4", approval_token=token_wrong, actor="attacker")
        assert "does not authorize 'approval:grant'" in str(exc_info.value)

        # Also test compact token with wrong scope
        compact_wrong = mint_token(issuer="operator", scope="database:read", capability_level=1)
        with pytest.raises(InvalidTransition) as exc_info2:
            kernel.commit_approval("task-br4", approval_token=compact_wrong, actor="attacker")
        assert "does not authorize 'approval:grant'" in str(exc_info2.value)

        task = kernel.get_task("task-br4")
        assert task["state"] == "WAITING_APPROVAL"
    finally:
        kernel.close()


def test_gap13_branch_5_commit_approval_mismatched_task_id_rejected(tmp_path):
    """BR-5: Token scoped to a specific task_id cannot be reused on a different task."""
    import time

    from scp.core.capability_token import (
        CapabilityToken,
        compute_token_signature,
        get_capability_secret,
    )

    kernel = TaskKernel(tmp_path / "gap13_br5.sqlite3")
    try:
        kernel.create_task("task-br5", "owner-1", "br5 goal", "R2")
        kernel.transition("task-br5", "PLANNING")
        kernel.transition("task-br5", "WAITING_APPROVAL")

        secret = get_capability_secret()
        now_ts = time.time()
        sig = compute_token_signature(secret, "approval:grant:other_task_999", 0, "tok-mismatch", now_ts)
        token_mismatched = CapabilityToken(
            subject="approval:grant:other_task_999",
            epoch=0,
            token_id="tok-mismatch",
            issued_at=now_ts,
            signature=sig,
        )

        with pytest.raises(InvalidTransition) as exc_info:
            kernel.commit_approval("task-br5", approval_token=token_mismatched, actor="attacker")
        assert "does not authorize 'approval:grant' for task 'task-br5'" in str(exc_info.value)

        task = kernel.get_task("task-br5")
        assert task["state"] == "WAITING_APPROVAL"
    finally:
        kernel.close()


def test_gap13_branch_6_commit_approval_expired_token_rejected(tmp_path):
    """BR-6: Expired compact token or expired operator signature must be rejected fail-closed."""
    import hashlib
    import hmac
    import time

    from scp.core.capability_token import get_capability_secret, mint_token

    kernel = TaskKernel(tmp_path / "gap13_br6.sqlite3")
    try:
        kernel.create_task("task-br6", "owner-1", "br6 goal", "R2")
        kernel.transition("task-br6", "PLANNING")
        kernel.transition("task-br6", "WAITING_APPROVAL")

        # Expired minted token (ttl negative)
        expired_token = mint_token(issuer="operator", scope="approval:grant", capability_level=2, ttl_seconds=-100)
        with pytest.raises(InvalidTransition):
            kernel.commit_approval("task-br6", approval_token=expired_token, actor="attacker")

        # Expired operator signature (> 300s in the past)
        secret = get_capability_secret()
        old_ts = time.time() - 600.0
        canonical = f"operator_approval:task-br6:operator:{old_ts:.6f}".encode()
        old_sig = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
        expired_op_sig = {
            "type": "operator_signature",
            "actor": "operator",
            "task_id": "task-br6",
            "timestamp": old_ts,
            "signature": old_sig,
        }
        with pytest.raises(InvalidTransition) as exc_info:
            kernel.commit_approval("task-br6", approval_token=expired_op_sig, actor="operator")
        assert "expired" in str(exc_info.value).lower()

        task = kernel.get_task("task-br6")
        assert task["state"] == "WAITING_APPROVAL"
    finally:
        kernel.close()


def test_gap13_branch_7_commit_approval_valid_capability_token_success(tmp_path):
    """BR-7: Legitimate approval via valid CapabilityToken transitions task to READY with event journal."""
    import time

    from scp.core.capability_token import (
        CapabilityToken,
        compute_token_signature,
        get_capability_secret,
        mint_token,
    )

    kernel = TaskKernel(tmp_path / "gap13_br7.sqlite3")
    try:
        kernel.create_task("task-br7", "owner-1", "br7 goal", "R2")
        kernel.transition("task-br7", "PLANNING")
        kernel.transition("task-br7", "WAITING_APPROVAL")

        secret = get_capability_secret()
        now_ts = time.time()
        sig = compute_token_signature(secret, "approval:grant", 0, "tok-legit-br7", now_ts)
        valid_token = CapabilityToken(
            subject="approval:grant",
            epoch=0,
            token_id="tok-legit-br7",
            issued_at=now_ts,
            signature=sig,
        )

        res = kernel.commit_approval("task-br7", approval_token=valid_token, actor="security_auditor")
        assert res["state"] == "READY"
        assert res["version"] == 4

        events = kernel.get_events("task-br7")
        approved_events = [e for e in events if e["type"] == "TASK_APPROVED"]
        assert len(approved_events) == 1
        ev = approved_events[0]
        assert ev["from_state"] == "WAITING_APPROVAL"
        assert ev["to_state"] == "READY"
        assert ev["actor"] == "security_auditor"
        payload = json.loads(ev["payload_json"])
        assert payload["token_id"] == "tok-legit-br7"
        assert payload["scope"] == "approval:grant"

        # Also test with task-specific scoped compact token on second task
        kernel.create_task("task-br7b", "owner-1", "br7b goal", "R3")
        kernel.transition("task-br7b", "PLANNING")
        kernel.transition("task-br7b", "WAITING_APPROVAL")

        compact_scoped = mint_token(issuer="governance", scope="approval:grant:task-br7b", capability_level=3)
        res_b = kernel.commit_approval("task-br7b", approval_token=compact_scoped, actor="gov_lead")
        assert res_b["state"] == "READY"
    finally:
        kernel.close()


def test_gap13_branch_8_commit_approval_valid_operator_signature_success(tmp_path):
    """BR-8: Legitimate approval via valid HMAC Operator Signature transitions task to READY."""
    import hashlib
    import hmac
    import time

    from scp.core.capability_token import get_capability_secret

    kernel = TaskKernel(tmp_path / "gap13_br8.sqlite3")
    try:
        kernel.create_task("task-br8", "owner-1", "br8 goal", "R3")
        kernel.transition("task-br8", "PLANNING")
        kernel.transition("task-br8", "WAITING_APPROVAL")

        secret = get_capability_secret()
        now_ts = time.time()
        canonical = f"operator_approval:task-br8:chief_operator:{now_ts:.6f}".encode()
        sig = hmac.new(secret, canonical, hashlib.sha256).hexdigest()

        op_sig_payload = {
            "type": "operator_signature",
            "actor": "chief_operator",
            "task_id": "task-br8",
            "timestamp": now_ts,
            "signature": sig,
        }

        res = kernel.commit_approval("task-br8", approval_token=op_sig_payload, actor="chief_operator")
        assert res["state"] == "READY"
        assert res["version"] == 4

        events = kernel.get_events("task-br8")
        approved_events = [e for e in events if e["type"] == "TASK_APPROVED"]
        assert len(approved_events) == 1
        payload = json.loads(approved_events[0]["payload_json"])
        assert payload["token_type"] == "operator_signature"
        assert payload["actor"] == "chief_operator"
    finally:
        kernel.close()


def test_gap13_branch_9_commit_approval_occ_version_mismatch_rejected(tmp_path):
    """BR-9: Calling commit_approval with mismatched expected_version raises OptimisticLockError."""
    import time

    from scp.core.capability_token import (
        CapabilityToken,
        compute_token_signature,
        get_capability_secret,
    )
    from scp.task_kernel import OptimisticLockError

    kernel = TaskKernel(tmp_path / "gap13_br9.sqlite3")
    try:
        kernel.create_task("task-br9", "owner-1", "br9 goal", "R2")
        kernel.transition("task-br9", "PLANNING")
        kernel.transition("task-br9", "WAITING_APPROVAL")
        current_version = kernel.get_task("task-br9")["version"]

        secret = get_capability_secret()
        now_ts = time.time()
        sig = compute_token_signature(secret, "approval:grant", 0, "tok-occ", now_ts)
        valid_token = CapabilityToken("approval:grant", 0, "tok-occ", now_ts, sig)

        # Provide stale expected_version
        with pytest.raises(OptimisticLockError) as exc_info:
            kernel.commit_approval(
                "task-br9",
                approval_token=valid_token,
                actor="operator",
                expected_version=current_version + 99,
            )
        assert "concurrency conflict" in str(exc_info.value)

        # Task version untouched
        assert kernel.get_task("task-br9")["version"] == current_version
        assert kernel.get_task("task-br9")["state"] == "WAITING_APPROVAL"
    finally:
        kernel.close()


def test_gap13_branch_10_commit_approval_wrong_lifecycle_state_rejected(tmp_path):
    """BR-10: Calling commit_approval on non-WAITING_APPROVAL task raises InvalidTransition."""
    import time

    from scp.core.capability_token import (
        CapabilityToken,
        compute_token_signature,
        get_capability_secret,
    )

    kernel = TaskKernel(tmp_path / "gap13_br10.sqlite3")
    try:
        kernel.create_task("task-br10", "owner-1", "br10 goal", "R1")
        secret = get_capability_secret()
        now_ts = time.time()
        sig = compute_token_signature(secret, "approval:grant", 0, "tok-wrong-state", now_ts)
        valid_token = CapabilityToken("approval:grant", 0, "tok-wrong-state", now_ts, sig)

        # 1. On CREATED state
        with pytest.raises(InvalidTransition) as exc_1:
            kernel.commit_approval("task-br10", approval_token=valid_token, actor="operator")
        assert "task must be in WAITING_APPROVAL" in str(exc_1.value)

        # 2. On PLANNING state
        kernel.transition("task-br10", "PLANNING")
        with pytest.raises(InvalidTransition) as exc_2:
            kernel.commit_approval("task-br10", approval_token=valid_token, actor="operator")
        assert "task must be in WAITING_APPROVAL" in str(exc_2.value)

        # 3. On CANCELLED (terminal) state
        kernel.transition("task-br10", "CANCELLED")
        with pytest.raises(InvalidTransition) as exc_3:
            kernel.commit_approval("task-br10", approval_token=valid_token, actor="operator")
        assert "terminal task is immutable" in str(exc_3.value)
    finally:
        kernel.close()


def test_gap13_branch_11_full_lifecycle_with_approval_gate(tmp_path):
    """BR-11: Complete lifecycle PLANNING -> WAITING_APPROVAL -> READY -> QUEUED -> LEASED -> RUNNING -> COMPLETED."""
    import time

    from scp.core.capability_token import (
        CapabilityToken,
        compute_token_signature,
        get_capability_secret,
    )

    kernel = TaskKernel(tmp_path / "gap13_br11.sqlite3")
    try:
        # Step 1: Create & Gate task
        kernel.create_task("task-br11", "owner-1", "br11 full lifecycle", "R3")
        kernel.transition("task-br11", "PLANNING")
        kernel.transition("task-br11", "WAITING_APPROVAL", reason="high_risk_tier")
        assert kernel.get_task("task-br11")["state"] == "WAITING_APPROVAL"

        # Step 2: Approve task via commit_approval
        secret = get_capability_secret()
        now_ts = time.time()
        sig = compute_token_signature(secret, "approval:grant:task-br11", 0, "tok-br11", now_ts)
        token = CapabilityToken("approval:grant:task-br11", 0, "tok-br11", now_ts, sig)

        approved_task = kernel.commit_approval("task-br11", approval_token=token, actor="board_approver")
        assert approved_task["state"] == "READY"

        # Step 3: Queue task
        kernel.transition("task-br11", "QUEUED")
        assert kernel.get_task("task-br11")["state"] == "QUEUED"

        # Step 4: Claim and Start task
        lease = kernel.claim("task-br11", "worker-1", ttl_seconds=300)
        kernel.start("task-br11", lease.lease_id)
        assert kernel.get_task("task-br11")["state"] == "RUNNING"

        # Step 5: Transition to VERIFYING and complete via commit_completed
        kernel.transition("task-br11", "VERIFYING", actor="worker-1", lease_id=lease.lease_id)
        completed_task = kernel.commit_completed(
            "task-br11",
            lease_id=lease.lease_id,
            verifier_verdict="VERIFIED",
            evidence_ref="ref://evidence/br11_full_audit_passed",
        )
        assert completed_task["state"] == "COMPLETED"

        # Step 6: Verify Event Journal Integrity
        events = kernel.get_events("task-br11")
        event_types = [e["type"] for e in events]
        assert "TASK_CREATED" in event_types
        assert "TASK_APPROVED" in event_types
        assert "LEASE_GRANTED" in event_types
        assert "TASK_COMPLETED" in event_types

        # Verify hash chain unbroken
        for i in range(1, len(events)):
            assert events[i]["seq"] == events[i - 1]["seq"] + 1
            assert events[i]["prev_event_hash"] == events[i - 1]["event_hash"]
    finally:
        kernel.close()
