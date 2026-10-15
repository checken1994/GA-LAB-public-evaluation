"""Adversarial Boundary & State Machine Stress Test Suite for GAP-13.

Empirical Challenger: challenger_gap13_2
Mission:
1. Attack commit_approval() from all 17 non-WAITING_APPROVAL lifecycle states:
   (CREATED, PLANNING, READY, QUEUED, LEASED, RUNNING, WAITING_TOOL, CHECKPOINTED,
    VERIFYING, UNKNOWN, RECOVERING, RECONCILING, HUMAN_REVIEW, RETRY_SCHEDULED,
    COMPLETED, FAILED, CANCELLED).
2. Attack raw transition() from WAITING_APPROVAL with arbitrary parameters, reasons,
   actors, leases, event_ids, and payloads.
3. Attack global kill switch activation during approval.
4. Terminal state immutability & resurrection attempts across all terminal states.
5. Concurrency races and physical SQLite zero-mutation fail-closed verification.

Protocols: FA-01 through FA-13, Zero-Trust, Fail-Closed, Exploit Mandate (FA-09),
Empirical Closure (FA-12), Causal Test Coverage (FA-13).
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from scp.core.capability_token import (
    CapabilityToken,
    compute_token_signature,
    get_capability_secret,
)
from scp.task_kernel import (
    STATES,
    TERMINAL,
    InvalidTransition,
    KillSwitchActive,
    OptimisticLockError,
    TaskKernel,
)


def _inspect_db(db_path: str | Path, query: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Physical SQLite table inspection bypassing RAM/kernel cache (FA-08/FA-12)."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _make_valid_cap_token(task_id: str, scope: str = "approval:grant") -> CapabilityToken:
    secret = get_capability_secret()
    now_ts = time.time()
    sig = compute_token_signature(secret, scope, 0, f"tok-{task_id}", now_ts)
    return CapabilityToken(scope, 0, f"tok-{task_id}", now_ts, sig)


def _drive_task_to_state(kernel: TaskKernel, state: str, task_id: str, owner: str = "owner-adv") -> dict[str, Any]:
    """Deterministically drive a task into any target state in TaskKernel."""
    worker = "worker-adv"
    if state == "CREATED":
        kernel.create_task(task_id, owner, f"drive to {state}", "R2")
    elif state == "PLANNING":
        kernel.create_task(task_id, owner, f"drive to {state}", "R2")
        kernel.transition(task_id, "PLANNING", actor="planner")
    elif state == "WAITING_APPROVAL":
        _drive_task_to_state(kernel, "PLANNING", task_id, owner)
        kernel.transition(task_id, "WAITING_APPROVAL", actor="risk_policy", reason="gated_risk")
    elif state == "READY":
        _drive_task_to_state(kernel, "PLANNING", task_id, owner)
        kernel.transition(task_id, "READY", actor="planner")
    elif state == "QUEUED":
        _drive_task_to_state(kernel, "READY", task_id, owner)
        kernel.transition(task_id, "QUEUED", actor="dispatcher")
    elif state == "LEASED":
        _drive_task_to_state(kernel, "QUEUED", task_id, owner)
        kernel.claim(task_id, worker)
    elif state == "RUNNING":
        _drive_task_to_state(kernel, "QUEUED", task_id, owner)
        lease = kernel.claim(task_id, worker)
        kernel.start(task_id, lease.lease_id)
    elif state == "WAITING_TOOL":
        _drive_task_to_state(kernel, "RUNNING", task_id, owner)
        task = kernel.get_task(task_id)
        kernel.transition(task_id, "WAITING_TOOL", lease_id=task["active_lease_id"])
    elif state == "CHECKPOINTED":
        _drive_task_to_state(kernel, "RUNNING", task_id, owner)
        task = kernel.get_task(task_id)
        kernel.transition(task_id, "CHECKPOINTED", lease_id=task["active_lease_id"])
    elif state == "VERIFYING":
        _drive_task_to_state(kernel, "RUNNING", task_id, owner)
        task = kernel.get_task(task_id)
        kernel.transition(task_id, "VERIFYING", lease_id=task["active_lease_id"])
    elif state == "UNKNOWN":
        _drive_task_to_state(kernel, "WAITING_TOOL", task_id, owner)
        task = kernel.get_task(task_id)
        kernel.transition(task_id, "UNKNOWN", lease_id=task["active_lease_id"])
    elif state == "RECOVERING":
        _drive_task_to_state(kernel, "UNKNOWN", task_id, owner)
        kernel._system_authority = True
        try:
            kernel.transition(task_id, "RECOVERING", actor="boot_recovery")
        finally:
            kernel._system_authority = False
    elif state == "RECONCILING":
        _drive_task_to_state(kernel, "RECOVERING", task_id, owner)
        kernel._system_authority = True
        try:
            kernel.transition(task_id, "RECONCILING", actor="recovery_agent")
        finally:
            kernel._system_authority = False
    elif state == "HUMAN_REVIEW":
        _drive_task_to_state(kernel, "RUNNING", task_id, owner)
        task = kernel.get_task(task_id)
        kernel.transition(task_id, "HUMAN_REVIEW", lease_id=task["active_lease_id"])
    elif state == "RETRY_SCHEDULED":
        kernel.create_task(task_id, owner, f"drive to {state}", "R2", max_attempts=3)
        kernel.transition(task_id, "PLANNING", actor="planner")
        kernel.transition(task_id, "READY", actor="planner")
        kernel.transition(task_id, "QUEUED", actor="dispatcher")
        lease = kernel.claim(task_id, worker)
        kernel.start(task_id, lease.lease_id)
        kernel.commit_failed(task_id, lease.lease_id, worker, "RETRYABLE", "ref://retry-1", {"err": "transient"})
    elif state == "COMPLETED":
        _drive_task_to_state(kernel, "VERIFYING", task_id, owner)
        task = kernel.get_task(task_id)
        kernel.commit_completed(task_id, task["active_lease_id"], "VERIFIED", "ev://audit_passed")
    elif state == "FAILED":
        kernel.create_task(task_id, owner, f"drive to {state}", "R2", max_attempts=1)
        kernel.transition(task_id, "PLANNING", actor="planner")
        kernel.transition(task_id, "READY", actor="planner")
        kernel.transition(task_id, "QUEUED", actor="dispatcher")
        lease = kernel.claim(task_id, worker)
        kernel.start(task_id, lease.lease_id)
        kernel.commit_failed(task_id, lease.lease_id, worker, "FATAL", "ref://fatal-err", {"err": "fatal"})
    elif state == "CANCELLED":
        _drive_task_to_state(kernel, "PLANNING", task_id, owner)
        kernel.transition(task_id, "CANCELLED", actor="user", reason="manual_cancel")
    else:
        raise ValueError(f"Unknown state: {state}")
    return kernel.get_task(task_id)


# ==============================================================================
# SUITE 1: Attack commit_approval() on All 17 Non-WAITING_APPROVAL States
# ==============================================================================

@pytest.mark.parametrize("target_state", sorted(list(STATES)))
def test_attack_commit_approval_on_all_non_waiting_states(tmp_path: Path, target_state: str):
    """Attack 1: Calling commit_approval() with a valid token MUST fail closed on all non-WAITING_APPROVAL states."""
    db_path = tmp_path / f"adv_state_{target_state.lower()}.sqlite3"
    kernel = TaskKernel(db_path)
    try:
        task_id = f"task-adv-{target_state.lower()}"
        task_record = _drive_task_to_state(kernel, target_state, task_id)
        initial_version = task_record["version"]
        assert task_record["state"] == target_state

        valid_token = _make_valid_cap_token(task_id, "approval:grant")

        # Attack: Attempt to approve task that is NOT in WAITING_APPROVAL
        with pytest.raises(InvalidTransition) as exc_info:
            kernel.commit_approval(task_id, approval_token=valid_token, actor="rogue_approver")

        err_msg = str(exc_info.value)
        if target_state in TERMINAL:
            assert "terminal task is immutable" in err_msg
        else:
            assert "cannot be approved; task must be in WAITING_APPROVAL" in err_msg

        # FA-12 Step 4: Verify physical SQLite database rows - STRICT ZERO MUTATION
        t_rows = _inspect_db(db_path, "SELECT state, version FROM tasks WHERE task_id=?", (task_id,))
        assert len(t_rows) == 1
        assert t_rows[0]["state"] == target_state, f"Task state mutated from {target_state} to {t_rows[0]['state']}!"
        assert t_rows[0]["version"] == initial_version, "Task version was bumped under failed approval!"

        # Verify no TASK_APPROVED event was appended to journal
        ev_rows = _inspect_db(
            db_path,
            "SELECT type FROM events WHERE task_id=? AND type='TASK_APPROVED'",
            (task_id,),
        )
        assert len(ev_rows) == 0, "TASK_APPROVED event was written to journal for non-waiting task!"
    finally:
        kernel.close()


# ==============================================================================
# SUITE 2: Attack Raw transition() from WAITING_APPROVAL
# ==============================================================================

def test_attack_raw_transition_to_ready_under_all_variants(tmp_path: Path):
    """Attack 2.1 - 2.4: Calling transition(task_id, 'READY') from WAITING_APPROVAL must be strictly blocked."""
    db_path = tmp_path / "adv_raw_trans.sqlite3"
    kernel = TaskKernel(db_path)
    try:
        task_id = "task-wa-raw"
        _drive_task_to_state(kernel, "WAITING_APPROVAL", task_id)
        t_before = kernel.get_task(task_id)
        assert t_before["state"] == "WAITING_APPROVAL"
        initial_ver = t_before["version"]

        # Variant A: default parameters
        with pytest.raises(InvalidTransition) as exc_a:
            kernel.transition(task_id, "READY")
        assert "direct transition from WAITING_APPROVAL to READY is forbidden" in str(exc_a.value)

        # Variant B: malicious actor and override payload
        with pytest.raises(InvalidTransition) as exc_b:
            kernel.transition(
                task_id,
                "READY",
                actor="super_admin_impostor",
                reason="emergency_bypass_r3_gate",
                payload={"elevated": True, "force": 1, "auth_override": True},
            )
        assert "direct transition from WAITING_APPROVAL to READY is forbidden" in str(exc_b.value)

        # Variant C: spoofed lease_id and expected_version
        with pytest.raises(InvalidTransition) as exc_c:
            kernel.transition(
                task_id,
                "READY",
                lease_id="lease-spoofed-999",
                expected_version=initial_ver,
            )
        assert "direct transition from WAITING_APPROVAL to READY is forbidden" in str(exc_c.value)

        # Variant D: spoofed event_id
        with pytest.raises(InvalidTransition) as exc_d:
            kernel.transition(
                task_id,
                "READY",
                event_id="evt-forged-approval-bypass",
            )
        assert "direct transition from WAITING_APPROVAL to READY is forbidden" in str(exc_d.value)

        # Physical SQLite check: State remains WAITING_APPROVAL, version unchanged
        t_rows = _inspect_db(db_path, "SELECT state, version FROM tasks WHERE task_id=?", (task_id,))
        assert t_rows[0]["state"] == "WAITING_APPROVAL"
        assert t_rows[0]["version"] == initial_ver
    finally:
        kernel.close()


def test_attack_raw_transition_to_all_illegal_states_from_waiting_approval(tmp_path: Path):
    """Attack 2.5: Any transition from WAITING_APPROVAL to other non-CANCELLED states is blocked."""
    db_path = tmp_path / "adv_illegal_wa_targets.sqlite3"
    kernel = TaskKernel(db_path)
    try:
        task_id = "task-wa-targets"
        _drive_task_to_state(kernel, "WAITING_APPROVAL", task_id)

        # All states in STATES except CANCELLED (which is allowed)
        for target in sorted(list(STATES)):
            if target == "CANCELLED":
                continue
            with pytest.raises(InvalidTransition):
                kernel.transition(task_id, target, actor="attacker")

        # Test arbitrary unknown states
        for bogus in ["APPROVED", "BYPASS", "SUPERUSER", "", "root", "READY "]:
            with pytest.raises(InvalidTransition):
                kernel.transition(task_id, bogus, actor="attacker")

        # Task must still be in WAITING_APPROVAL
        assert kernel.get_task(task_id)["state"] == "WAITING_APPROVAL"

        # Legitimate cancellation is allowed
        kernel.transition(task_id, "CANCELLED", actor="operator", reason="cancelled_by_operator")
        assert kernel.get_task(task_id)["state"] == "CANCELLED"

        # But now task is CANCELLED (terminal), further transitions or approvals are rejected
        with pytest.raises(InvalidTransition) as exc_post_cancel:
            kernel.transition(task_id, "READY")
        assert "CANCELLED->READY" in str(exc_post_cancel.value) or "terminal task is immutable" in str(exc_post_cancel.value)

        valid_token = _make_valid_cap_token(task_id)
        with pytest.raises(InvalidTransition) as exc_post_app:
            kernel.commit_approval(task_id, approval_token=valid_token, actor="operator")
        assert "terminal task is immutable" in str(exc_post_app.value)
    finally:
        kernel.close()


# ==============================================================================
# SUITE 3: Attack Global Kill Switch Activation during Approval
# ==============================================================================

def test_attack_global_kill_switch_during_commit_approval(tmp_path: Path):
    """Attack 3: Global kill switch MUST prevent commit_approval() fail-closed."""
    db_path = tmp_path / "adv_kill_approval.sqlite3"
    kernel = TaskKernel(db_path)
    try:
        task_id = "task-kill-switch"
        _drive_task_to_state(kernel, "WAITING_APPROVAL", task_id)
        valid_token = _make_valid_cap_token(task_id, "approval:grant")
        initial_ver = kernel.get_task(task_id)["version"]

        # 1. Activate global kill switch
        epoch = kernel.set_global_kill(True, actor="sentinel_kill")
        assert epoch >= 1

        # 2. Attempt commit_approval while kill switch is active
        with pytest.raises(KillSwitchActive) as exc_kill:
            kernel.commit_approval(task_id, approval_token=valid_token, actor="operator")
        assert "global kill switch active" in str(exc_kill.value)

        # 3. Verify SQLite DB state: Task is UNTOUCHED
        t_rows = _inspect_db(db_path, "SELECT state, version FROM tasks WHERE task_id=?", (task_id,))
        assert t_rows[0]["state"] == "WAITING_APPROVAL"
        assert t_rows[0]["version"] == initial_ver

        ev_rows = _inspect_db(
            db_path,
            "SELECT type FROM events WHERE task_id=? AND type='TASK_APPROVED'",
            (task_id,),
        )
        assert len(ev_rows) == 0

        # 4. Deactivate global kill switch
        kernel.set_global_kill(False, actor="sentinel_unkill")

        # 5. commit_approval now succeeds normally
        res = kernel.commit_approval(task_id, approval_token=valid_token, actor="operator")
        assert res["state"] == "READY"
        assert res["version"] == initial_ver + 1

        # Physical DB verification of successful approval
        t_rows_post = _inspect_db(db_path, "SELECT state, version FROM tasks WHERE task_id=?", (task_id,))
        assert t_rows_post[0]["state"] == "READY"
        assert t_rows_post[0]["version"] == initial_ver + 1
    finally:
        kernel.close()


def test_attack_per_task_kill_on_waiting_approval(tmp_path: Path):
    """Attack 3.3: Per-task kill switch (set_task_kill) moves WAITING_APPROVAL to CANCELLED and freezes it."""
    db_path = tmp_path / "adv_task_kill.sqlite3"
    kernel = TaskKernel(db_path)
    try:
        task_id = "task-per-task-kill"
        _drive_task_to_state(kernel, "WAITING_APPROVAL", task_id)
        valid_token = _make_valid_cap_token(task_id, "approval:grant")

        # Operator triggers emergency task kill
        killed_record = kernel.set_task_kill(task_id, actor="emergency_kill_guard")
        assert killed_record["state"] == "CANCELLED"

        # Physical SQLite check
        t_rows = _inspect_db(db_path, "SELECT state FROM tasks WHERE task_id=?", (task_id,))
        assert t_rows[0]["state"] == "CANCELLED"

        # Attempt commit_approval on killed task -> must raise terminal task is immutable
        with pytest.raises(InvalidTransition) as exc_app:
            kernel.commit_approval(task_id, approval_token=valid_token, actor="operator")
        assert "terminal task is immutable" in str(exc_app.value)

        # Attempt transition to READY -> must raise terminal task is immutable
        with pytest.raises(InvalidTransition) as exc_tr:
            kernel.transition(task_id, "READY")
        assert "CANCELLED->READY" in str(exc_tr.value) or "terminal task is immutable" in str(exc_tr.value)

        # Calling set_task_kill again on already cancelled task must fail
        with pytest.raises(InvalidTransition) as exc_repeat_kill:
            kernel.set_task_kill(task_id, actor="emergency_kill_guard")
        assert "terminal task is immutable" in str(exc_repeat_kill.value)
    finally:
        kernel.close()


# ==============================================================================
# SUITE 4: Terminal State Immutability & Resurrection Attacks
# ==============================================================================

@pytest.mark.parametrize("terminal_state", ["COMPLETED", "FAILED", "CANCELLED"])
def test_terminal_state_resurrection_strictly_prohibited(tmp_path: Path, terminal_state: str):
    """Attack 4: Terminal tasks can NEVER be resurrected or transitioned under any method."""
    db_path = tmp_path / f"adv_terminal_{terminal_state.lower()}.sqlite3"
    kernel = TaskKernel(db_path)
    try:
        task_id = f"task-term-{terminal_state.lower()}"
        _drive_task_to_state(kernel, terminal_state, task_id)
        t_record = kernel.get_task(task_id)
        assert t_record["state"] == terminal_state
        initial_ver = t_record["version"]

        valid_token = _make_valid_cap_token(task_id, "approval:grant")

        # 1. Attack via commit_approval()
        with pytest.raises(InvalidTransition) as exc_app:
            kernel.commit_approval(task_id, approval_token=valid_token, actor="operator")
        assert "terminal task is immutable" in str(exc_app.value)

        # 2. Attack via set_task_kill()
        with pytest.raises(InvalidTransition) as exc_kill:
            kernel.set_task_kill(task_id, actor="operator")
        assert "terminal task is immutable" in str(exc_kill.value)

        # 3. Attack via transition to all active states
        resurrection_targets = ["READY", "PLANNING", "CREATED", "QUEUED", "RUNNING", "WAITING_APPROVAL"]
        for target in resurrection_targets:
            with pytest.raises(InvalidTransition):
                kernel.transition(task_id, target, actor="resurrector")

        # 4. Verify physical SQLite rows remain untouched
        t_rows = _inspect_db(db_path, "SELECT state, version FROM tasks WHERE task_id=?", (task_id,))
        assert t_rows[0]["state"] == terminal_state
        assert t_rows[0]["version"] == initial_ver
    finally:
        kernel.close()


# ==============================================================================
# SUITE 5: Concurrency Race & OCC Fencing on commit_approval()
# ==============================================================================

def test_concurrent_commit_approval_race_exactly_one_winner(tmp_path: Path):
    """Attack 5: Concurrent approval race condition stress. Exactly ONE thread must succeed; all others fail."""
    db_path = tmp_path / "adv_race_approval.sqlite3"
    kernel_init = TaskKernel(db_path)
    task_id = "task-race-1"
    _drive_task_to_state(kernel_init, "WAITING_APPROVAL", task_id)
    kernel_init.close()

    num_threads = 6
    barrier = threading.Barrier(num_threads)
    results: list[dict[str, Any]] = []

    def _worker_attempt(thread_id: int):
        k = TaskKernel(db_path)
        tok = _make_valid_cap_token(task_id, "approval:grant")
        barrier.wait()
        try:
            res = k.commit_approval(task_id, approval_token=tok, actor=f"operator_{thread_id}")
            results.append({"thread": thread_id, "status": "SUCCESS", "task": res})
        except (OptimisticLockError, InvalidTransition) as e:
            results.append({"thread": thread_id, "status": "BLOCKED", "error": str(e)})
        except Exception as e:
            results.append({"thread": thread_id, "status": "UNEXPECTED", "error": f"{type(e).__name__}: {e}"})
        finally:
            k.close()

    threads = [threading.Thread(target=_worker_attempt, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = [r for r in results if r["status"] == "SUCCESS"]
    blocked = [r for r in results if r["status"] == "BLOCKED"]
    unexpected = [r for r in results if r["status"] == "UNEXPECTED"]

    assert len(unexpected) == 0, f"Unexpected errors during concurrency race: {unexpected}"
    assert len(successes) == 1, f"Expected exactly 1 winner, got {len(successes)}: {results}"
    assert len(blocked) == num_threads - 1

    # Verify physical SQLite database state
    t_rows = _inspect_db(db_path, "SELECT state, version FROM tasks WHERE task_id=?", (task_id,))
    assert len(t_rows) == 1
    assert t_rows[0]["state"] == "READY"
    # Version should have bumped by exactly 1 (from 3 to 4)
    assert t_rows[0]["version"] == 4

    ev_rows = _inspect_db(
        db_path,
        "SELECT type FROM events WHERE task_id=? AND type='TASK_APPROVED'",
        (task_id,),
    )
    assert len(ev_rows) == 1, f"Expected exactly 1 TASK_APPROVED journal event, found {len(ev_rows)}"
