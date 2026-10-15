#!/usr/bin/env python3
"""Adversarial Verification & Stress Test Harness for GAP-12 Remediation.

Empirical Challenger: challenger_2 (teamwork_preview_challenger)
Target Subsystems:
  - TaskKernel: commit_failed(), retry budget preservation, uncertain error handling, lease actor binding
  - Downstream integrations: AskKernelAdapter.fail(), TaskKernelHandsBridge.execute()
  - Database boundaries: Raw SQLite tables inspection (tasks, leases, events, queue_accounts)
Protocols: FA-08, FA-09, FA-12, FA-13
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

# Default test capability secret for standalone probe execution (GAP-09)
os.environ.setdefault(
    "SCP_CAPABILITY_SECRET",
    "test-capability-secret-for-automated-suites-only-32bytes",
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scp.task_kernel import (
    TaskKernel,
    InvalidTransition,
    KernelError,
    StaleLease,
    OptimisticLockError,
    NotFound,
    STATES,
)
from scp.ask_kernel_adapter import AskKernelAdapter
from scp.hands.task_kernel_bridge import TaskKernelHandsBridge


def inspect_sqlite(db_path: str, query: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Direct raw physical SQLite inspection bypassing ORM/RAM caches (FA-08/FA-12)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        return rows
    finally:
        conn.close()


def test_suite_1_retryable_lifecycle_and_exhaustion(tmp_path: Path):
    """Test Suite 1: Retry preservation across multi-attempt lifecycle until exhaustion."""
    print("\n--- [TEST SUITE 1] Retryable Lifecycle & Budget Exhaustion ---")
    db_path = str(tmp_path / "ts1_retryable.sqlite3")
    kernel = TaskKernel(db_path)
    try:
        task_id = "task-adv-retry-1"
        owner = "adv-owner"
        worker = "adv-worker-1"
        kernel.create_task(task_id, owner, "adversarial retry test", max_attempts=3)

        # Initial baseline
        kernel.transition(task_id, "PLANNING")
        kernel.transition(task_id, "READY")
        kernel.transition(task_id, "QUEUED")

        # -------------------------------------------------------------
        # ATTEMPT 1: Transient network timeout
        # -------------------------------------------------------------
        lease1 = kernel.claim(task_id, worker)
        kernel.start(task_id, lease1.lease_id)

        # Physical DB verification before failure
        t_rows = inspect_sqlite(db_path, "SELECT state, attempts, active_lease_id FROM tasks WHERE task_id=?", (task_id,))
        assert t_rows[0]["state"] == "RUNNING"
        assert t_rows[0]["attempts"] == 0
        q_rows = inspect_sqlite(db_path, "SELECT active FROM queue_accounts WHERE owner=?", (owner,))
        assert q_rows[0]["active"] == 1

        # Commit retryable failure on Attempt 1
        res1 = kernel.commit_failed(
            task_id=task_id,
            lease_id=lease1.lease_id,
            actor=worker,
            failure_classification="RETRYABLE",
            indictment_ref="ref://adv/timeout_1",
            details={"err": "timeout on gateway"},
        )
        assert res1["state"] == "RETRY_SCHEDULED", f"Expected RETRY_SCHEDULED, got {res1['state']}"
        assert res1["attempts"] == 1
        assert res1["active_lease_id"] is None

        # Physical DB check after Attempt 1
        t1_rows = inspect_sqlite(db_path, "SELECT state, attempts, active_lease_id, active_fencing_token FROM tasks WHERE task_id=?", (task_id,))
        assert t1_rows[0]["state"] == "RETRY_SCHEDULED"
        assert t1_rows[0]["attempts"] == 1
        assert t1_rows[0]["active_lease_id"] is None
        assert t1_rows[0]["active_fencing_token"] == 0

        l1_rows = inspect_sqlite(db_path, "SELECT released FROM leases WHERE lease_id=?", (lease1.lease_id,))
        assert l1_rows[0]["released"] == 1, "Lease must be released"

        q1_rows = inspect_sqlite(db_path, "SELECT active FROM queue_accounts WHERE owner=?", (owner,))
        assert q1_rows[0]["active"] == 0, "Queue active must decrement to 0"

        ev1 = inspect_sqlite(db_path, "SELECT type, to_state, payload_json FROM events WHERE task_id=? AND type='TASK_RETRY_SCHEDULED'", (task_id,))
        assert len(ev1) == 1
        p1 = json.loads(ev1[0]["payload_json"])
        assert p1["attempts"] == 1
        assert p1["max_attempts"] == 3
        assert p1["failure_classification"] == "RETRYABLE"
        print("  [*] Attempt 1 passed: correctly routed to RETRY_SCHEDULED, attempts=1, lease released, active=0")

        # -------------------------------------------------------------
        # ATTEMPT 2: Transient network error
        # -------------------------------------------------------------
        kernel.transition(task_id, "QUEUED", actor="scheduler")
        lease2 = kernel.claim(task_id, worker)
        kernel.start(task_id, lease2.lease_id)

        res2 = kernel.commit_failed(
            task_id=task_id,
            lease_id=lease2.lease_id,
            actor=worker,
            failure_classification="TRANSIENT",
            indictment_ref="ref://adv/transient_2",
            details={"err": "503 service unavailable"},
        )
        assert res2["state"] == "RETRY_SCHEDULED"
        assert res2["attempts"] == 2

        t2_rows = inspect_sqlite(db_path, "SELECT state, attempts FROM tasks WHERE task_id=?", (task_id,))
        assert t2_rows[0]["state"] == "RETRY_SCHEDULED"
        assert t2_rows[0]["attempts"] == 2
        print("  [*] Attempt 2 passed: correctly routed to RETRY_SCHEDULED, attempts=2")

        # -------------------------------------------------------------
        # ATTEMPT 3: Exhaustion (attempts reaches max_attempts = 3)
        # -------------------------------------------------------------
        kernel.transition(task_id, "QUEUED", actor="scheduler")
        lease3 = kernel.claim(task_id, worker)
        kernel.start(task_id, lease3.lease_id)

        res3 = kernel.commit_failed(
            task_id=task_id,
            lease_id=lease3.lease_id,
            actor=worker,
            failure_classification="RETRYABLE",
            indictment_ref="ref://adv/timeout_3",
            details={"err": "repeated timeout; budget exhausted"},
        )
        assert res3["state"] == "FAILED", f"Expected FAILED on exhaustion, got {res3['state']}"
        assert res3["attempts"] == 3

        t3_rows = inspect_sqlite(db_path, "SELECT state, attempts, active_lease_id FROM tasks WHERE task_id=?", (task_id,))
        assert t3_rows[0]["state"] == "FAILED"
        assert t3_rows[0]["attempts"] == 3
        assert t3_rows[0]["active_lease_id"] is None

        ev3 = inspect_sqlite(db_path, "SELECT type, to_state, payload_json FROM events WHERE task_id=? AND type='TASK_FAILED'", (task_id,))
        assert len(ev3) == 1
        p3 = json.loads(ev3[0]["payload_json"])
        assert p3["attempts"] == 3
        assert p3["max_attempts"] == 3
        print("  [*] Attempt 3 passed: budget exhausted, moved to terminal FAILED")

        # -------------------------------------------------------------
        # IMMUTABILITY OF TERMINAL FAILED
        # -------------------------------------------------------------
        try:
            kernel.commit_failed(
                task_id=task_id,
                lease_id=lease3.lease_id,
                actor=worker,
                failure_classification="FATAL",
                indictment_ref="ref://adv/after_failed",
            )
            assert False, "Should raise InvalidTransition or StaleLease on terminal task"
        except (InvalidTransition, StaleLease) as exc:
            assert "terminal" in str(exc).lower() or "released" in str(exc).lower()

        try:
            kernel.transition(task_id, "RUNNING", actor="rogue")
            assert False, "Should raise InvalidTransition when transitioning from terminal FAILED"
        except InvalidTransition:
            pass
        print("  [*] Terminal immutability confirmed: no further transitions allowed from FAILED")

    finally:
        kernel.close()


def test_suite_2_uncertain_errors_fail_closed_no_blind_retries(tmp_path: Path):
    """Test Suite 2: Uncertain classifications route to UNKNOWN without blind retries."""
    print("\n--- [TEST SUITE 2] Uncertain Errors Routing to UNKNOWN ---")
    db_path = str(tmp_path / "ts2_uncertain.sqlite3")
    kernel = TaskKernel(db_path)
    try:
        uncertain_cases = [
            ("UNKNOWN", "task-u1"),
            ("UNCERTAIN", "task-u2"),
            ("LOST_RESPONSE", "task-u3"),
            ("CRASH_AFTER_SUBMIT", "task-u4"),
        ]

        for classification, task_id in uncertain_cases:
            owner = f"owner-{task_id}"
            worker = f"worker-{task_id}"
            # Task has max_attempts = 10 (plenty of retries available)
            kernel.create_task(task_id, owner, "uncertain test", max_attempts=10)
            kernel.transition(task_id, "PLANNING")
            kernel.transition(task_id, "READY")
            kernel.transition(task_id, "QUEUED")
            lease = kernel.claim(task_id, worker)
            kernel.start(task_id, lease.lease_id)

            res = kernel.commit_failed(
                task_id=task_id,
                lease_id=lease.lease_id,
                actor=worker,
                failure_classification=classification,
                indictment_ref=f"ref://uncertain/{classification.lower()}",
                details={"crash_stage": "after external side effect"},
            )

            # MUST route to UNKNOWN, NOT RETRY_SCHEDULED or FAILED!
            assert res["state"] == "UNKNOWN", f"Expected UNKNOWN for {classification}, got {res['state']}"
            assert res["attempts"] == 1
            assert res["active_lease_id"] is None

            # Physical DB inspection
            t_rows = inspect_sqlite(db_path, "SELECT state, attempts FROM tasks WHERE task_id=?", (task_id,))
            assert t_rows[0]["state"] == "UNKNOWN"
            assert t_rows[0]["attempts"] == 1

            l_rows = inspect_sqlite(db_path, "SELECT released FROM leases WHERE lease_id=?", (lease.lease_id,))
            assert l_rows[0]["released"] == 1

            q_rows = inspect_sqlite(db_path, "SELECT active FROM queue_accounts WHERE owner=?", (owner,))
            assert q_rows[0]["active"] == 0

            ev_rows = inspect_sqlite(db_path, "SELECT type, to_state, reason FROM events WHERE task_id=? AND type='TASK_UNKNOWN_STATE'", (task_id,))
            assert len(ev_rows) == 1
            assert ev_rows[0]["to_state"] == "UNKNOWN"
            assert f"uncertain_state:{classification.lower()}" == ev_rows[0]["reason"]
            print(f"  [*] {classification} passed: routed strictly to UNKNOWN (no blind retry)")

    finally:
        kernel.close()


def test_suite_3_downstream_ask_kernel_adapter_integration(tmp_path: Path):
    """Test Suite 3: AskKernelAdapter.fail() physical SQLite integration."""
    print("\n--- [TEST SUITE 3] Downstream AskKernelAdapter.fail() Integration ---")
    db_path = str(tmp_path / "ts3_ask.sqlite3")
    trace_path = str(tmp_path / "ts3_ask_trace.jsonl")
    adapter = AskKernelAdapter(db_path=db_path, trace_path=trace_path)
    try:
        # Case 1: FATAL failure
        task1 = adapter.begin("What is SCP architecture?", ["ctx1"], "", "session-adv-ask-1")
        t1_id = task1["task_id"]
        assert adapter.kernel.get_task(t1_id)["state"] == "RUNNING"

        # Verify active queue account
        task_info = adapter.kernel.get_task(t1_id)
        owner = task_info["owner"]
        q_before = inspect_sqlite(db_path, "SELECT active FROM queue_accounts WHERE owner=?", (owner,))
        assert len(q_before) > 0 and q_before[0]["active"] >= 1

        adapter.fail(task1, reason="llm_provider_quota_exhausted", failure_classification="FATAL")

        # Physical DB verification
        t1_rows = inspect_sqlite(db_path, "SELECT state, attempts, active_lease_id FROM tasks WHERE task_id=?", (t1_id,))
        assert t1_rows[0]["state"] == "FAILED"
        assert t1_rows[0]["active_lease_id"] is None

        l1_rows = inspect_sqlite(db_path, "SELECT released FROM leases WHERE task_id=?", (t1_id,))
        assert l1_rows[0]["released"] == 1

        q_after = inspect_sqlite(db_path, "SELECT active FROM queue_accounts WHERE owner=?", (owner,))
        assert q_after[0]["active"] == q_before[0]["active"] - 1

        ev1_rows = inspect_sqlite(db_path, "SELECT type, to_state, payload_json FROM events WHERE task_id=? AND type='TASK_FAILED'", (t1_id,))
        assert len(ev1_rows) == 1
        p1 = json.loads(ev1_rows[0]["payload_json"])
        assert "ask://" in p1["indictment_ref"]
        assert p1["actor"] == "ask-route-worker"
        assert p1["failure_classification"] == "FATAL"
        print("  [*] Case 1 (FATAL) passed: physical DB confirmed FAILED, lease released, queue decremented")

        # Case 2: RETRYABLE failure in AskKernelAdapter
        task2 = adapter.begin("Can I retry this question?", ["ctx2"], "", "session-adv-ask-2")
        t2_id = task2["task_id"]
        adapter.fail(task2, reason="transient_network_timeout", failure_classification="RETRYABLE")

        t2_rows = inspect_sqlite(db_path, "SELECT state, attempts FROM tasks WHERE task_id=?", (t2_id,))
        assert t2_rows[0]["state"] == "RETRY_SCHEDULED"
        assert t2_rows[0]["attempts"] == 1

        l2_rows = inspect_sqlite(db_path, "SELECT released FROM leases WHERE task_id=?", (t2_id,))
        assert l2_rows[0]["released"] == 1

        ev2_rows = inspect_sqlite(db_path, "SELECT type, to_state, payload_json FROM events WHERE task_id=? AND type='TASK_RETRY_SCHEDULED'", (t2_id,))
        assert len(ev2_rows) == 1
        print("  [*] Case 2 (RETRYABLE) passed: physical DB confirmed RETRY_SCHEDULED for ask adapter")

    finally:
        adapter.kernel.close()


def test_suite_4_downstream_task_kernel_bridge_integration(tmp_path: Path):
    """Test Suite 4: TaskKernelHandsBridge.execute() physical SQLite integration."""
    print("\n--- [TEST SUITE 4] Downstream TaskKernelHandsBridge.execute() Integration ---")
    db_path = str(tmp_path / "ts4_bridge.sqlite3")
    kernel = TaskKernel(db_path)

    class FakeActionDef:
        mutates_state = True
        risk = "R1"

    class FakeRegistry:
        def require(self, action):
            return FakeActionDef()

    class FakePolicyBlockedExecutor:
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
                "error": "CapabilityRequiredError: explicit capability required for action",
                "requiresRecovery": False,
                "safeToRetry": False,
            }

    class FakePreDispatchCrashExecutor(FakePolicyBlockedExecutor):
        def __init__(self):
            super().__init__()
            # Corrupt authority to cause pre-dispatch exception
            self.capability_authority = None

    async def _run_cases():
        # Case 1: Policy blocked before dispatch
        bridge1 = TaskKernelHandsBridge(executor=FakePolicyBlockedExecutor(), kernel=kernel)
        res1 = await bridge1.execute(
            action="restricted_eval",
            params={"code": "os.system('id')"},
            capability_level=3,
            approved=False,
            capability_token=None,
        )
        assert res1["success"] is False
        assert res1["kernel"]["taskState"] == "FAILED"
        task1_id = res1["kernel"]["taskId"]

        # Physical DB check
        t1_rows = inspect_sqlite(db_path, "SELECT state, active_lease_id FROM tasks WHERE task_id=?", (task1_id,))
        assert t1_rows[0]["state"] == "FAILED"
        assert t1_rows[0]["active_lease_id"] is None

        l1_rows = inspect_sqlite(db_path, "SELECT released FROM leases WHERE task_id=?", (task1_id,))
        assert l1_rows[0]["released"] == 1

        ev1_rows = inspect_sqlite(db_path, "SELECT type, to_state, payload_json FROM events WHERE task_id=? AND type='TASK_FAILED'", (task1_id,))
        assert len(ev1_rows) == 1
        p1 = json.loads(ev1_rows[0]["payload_json"])
        assert "hands://" in p1["indictment_ref"]
        assert "policy_denied" in p1["indictment_ref"]
        assert p1["actor"] == bridge1.worker_id
        print("  [*] Case 1 (Policy Denied) passed: task FAILED, lease released, indictment recorded in physical DB")

        # Case 2: Pre-dispatch exception
        bridge2 = TaskKernelHandsBridge(executor=FakePreDispatchCrashExecutor(), kernel=kernel)
        res2 = await bridge2.execute(
            action="crash_action",
            params={},
            capability_level=1,
            approved=True,
            capability_token=None,
        )
        assert res2["success"] is False
        task2_id = res2["kernel"]["taskId"]
        t2_rows = inspect_sqlite(db_path, "SELECT state, active_lease_id FROM tasks WHERE task_id=?", (task2_id,))
        assert t2_rows[0]["state"] == "FAILED"
        assert t2_rows[0]["active_lease_id"] is None

        l2_rows = inspect_sqlite(db_path, "SELECT released FROM leases WHERE task_id=?", (task2_id,))
        assert l2_rows[0]["released"] == 1
        print("  [*] Case 2 (Pre-dispatch crash) passed: task cleanly FAILED, lease released")

    try:
        asyncio.run(_run_cases())
    finally:
        kernel.close()


def test_suite_5_adversarial_boundary_and_concurrency_attacks(tmp_path: Path):
    """Test Suite 5: Adversarial edge cases, lease spoofing, empty indictment, and OCC concurrency race."""
    print("\n--- [TEST SUITE 5] Adversarial Boundary & Concurrency Attacks ---")
    db_path = str(tmp_path / "ts5_adv.sqlite3")
    kernel = TaskKernel(db_path)
    try:
        # Vector 1: Attempt direct transition(..., "FAILED") from every single known state
        print("  [>] Probing raw transition to FAILED across all known states...")
        for state in sorted(STATES):
            t_id = f"task-state-{state.lower()}"
            kernel.create_task(t_id, "owner-scan", "state scan", max_attempts=3)
            # Force task directly into state via internal helper to test transition() fence
            kernel.conn.execute("UPDATE tasks SET state=? WHERE task_id=?", (state, t_id))
            try:
                kernel.transition(t_id, "FAILED", actor="rogue-attacker")
                assert False, f"VULNERABILITY: transition({t_id}, 'FAILED') from state {state} succeeded!"
            except InvalidTransition as exc:
                assert "forbidden" in str(exc) or "unknown target state" in str(exc)
        print("  [*] All 17 states safely blocked direct transition to FAILED with InvalidTransition")

        # Vector 2: Stolen lease actor spoofing
        t_stolen = "task-stolen-lease"
        kernel.create_task(t_stolen, "owner-stolen", "stolen lease test")
        kernel.transition(t_stolen, "PLANNING")
        kernel.transition(t_stolen, "READY")
        kernel.transition(t_stolen, "QUEUED")
        legit_lease = kernel.claim(t_stolen, "legit-worker")
        kernel.start(t_stolen, legit_lease.lease_id)

        # Attacker tries multiple spoofed actor variants
        spoofed_actors = ["imposter", "legit-worker-2", "LEGIT-WORKER", "attacker", "root", "admin"]
        for bad_actor in spoofed_actors:
            try:
                kernel.commit_failed(
                    task_id=t_stolen,
                    lease_id=legit_lease.lease_id,
                    actor=bad_actor,
                    failure_classification="FATAL",
                    indictment_ref="ref://attack/stolen",
                )
                assert False, f"VULNERABILITY: spoofed actor '{bad_actor}' was accepted!"
            except InvalidTransition as exc:
                assert "does not match lease worker" in str(exc)

        # Attacker tries empty or whitespace actor
        for empty_actor in ["", "   ", "\t"]:
            try:
                kernel.commit_failed(
                    task_id=t_stolen,
                    lease_id=legit_lease.lease_id,
                    actor=empty_actor,
                    failure_classification="FATAL",
                    indictment_ref="ref://attack/stolen",
                )
                assert False, f"VULNERABILITY: empty actor '{empty_actor}' was accepted!"
            except KernelError as exc:
                assert "actor is required" in str(exc)

        # Vector 3: Missing / Whitespace Indictment Reference
        for bad_indictment in ["", "   ", "\t", "\n\r  \t"]:
            try:
                kernel.commit_failed(
                    task_id=t_stolen,
                    lease_id=legit_lease.lease_id,
                    actor="legit-worker",
                    failure_classification="FATAL",
                    indictment_ref=bad_indictment,
                )
                assert False, f"VULNERABILITY: bad indictment '{bad_indictment}' was accepted!"
            except KernelError as exc:
                assert "indictment_ref is required" in str(exc)
        print("  [*] Lease actor spoofing and empty indictment rejected fail-closed")

        # Vector 4: Queue Account Active Underflow Defense
        # When active is already 0, commit_failed() must not cause active < 0
        q_underflow = inspect_sqlite(db_path, "SELECT active FROM queue_accounts WHERE owner='owner-stolen'")
        # Current active is 1. Commit legitimate failure now:
        kernel.commit_failed(
            task_id=t_stolen,
            lease_id=legit_lease.lease_id,
            actor="legit-worker",
            failure_classification="FATAL",
            indictment_ref="ref://legit/fatal",
        )
        q_after1 = inspect_sqlite(db_path, "SELECT active FROM queue_accounts WHERE owner='owner-stolen'")
        assert q_after1[0]["active"] == 0

        # Simulate another task failing under the same owner when active is already 0
        t_underflow = "task-underflow"
        kernel.create_task(t_underflow, "owner-stolen", "underflow test")
        kernel.transition(t_underflow, "PLANNING")
        kernel.transition(t_underflow, "READY")
        kernel.transition(t_underflow, "QUEUED")
        lease_underflow = kernel.claim(t_underflow, "legit-worker")
        kernel.start(t_underflow, lease_underflow.lease_id)
        # Manually force queue_accounts active to 0 to simulate extreme race
        kernel.conn.execute("UPDATE queue_accounts SET active=0 WHERE owner='owner-stolen'")

        kernel.commit_failed(
            task_id=t_underflow,
            lease_id=lease_underflow.lease_id,
            actor="legit-worker",
            failure_classification="FATAL",
            indictment_ref="ref://underflow/fatal",
        )
        q_final = inspect_sqlite(db_path, "SELECT active FROM queue_accounts WHERE owner='owner-stolen'")
        assert q_final[0]["active"] == 0, f"Queue active went negative! {q_final[0]['active']}"
        print("  [*] Queue underflow defense verified: active count cannot go below 0")

        # Vector 5: Concurrency Race (OCC Protection)
        print("  [>] Testing OCC concurrency race on commit_failed()...")
        t_race = "task-race-occ"
        kernel.create_task(t_race, "owner-race", "race test")
        kernel.transition(t_race, "PLANNING")
        kernel.transition(t_race, "READY")
        kernel.transition(t_race, "QUEUED")
        race_lease = kernel.claim(t_race, "race-worker")
        kernel.start(t_race, race_lease.lease_id)

        barrier = threading.Barrier(2)
        results = []

        def race_worker(worker_idx: int):
            # Create a dedicated kernel instance per thread to test real OCC
            k = TaskKernel(db_path)
            k._system_authority = True  # bypass instance-local lease map to test storage-level OCC
            barrier.wait()
            try:
                res = k.commit_failed(
                    task_id=t_race,
                    lease_id=race_lease.lease_id,
                    actor="race-worker",
                    failure_classification="FATAL",
                    indictment_ref=f"ref://race/worker_{worker_idx}",
                )
                results.append(("SUCCESS", worker_idx, res))
            except Exception as exc:
                results.append(("FAILED", worker_idx, exc))
            finally:
                k.close()

        t1 = threading.Thread(target=race_worker, args=(1,))
        t2 = threading.Thread(target=race_worker, args=(2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        successes = [r for r in results if r[0] == "SUCCESS"]
        conflicts = [r for r in results if r[0] == "FAILED"]
        assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"
        assert len(conflicts) == 1, f"Expected exactly 1 conflict, got {len(conflicts)}"
        assert isinstance(conflicts[0][2], (OptimisticLockError, StaleLease)), f"Expected OCC/Lease error, got {type(conflicts[0][2])}"

        # Physical DB verification: exactly 1 TASK_FAILED event recorded
        ev_race = inspect_sqlite(db_path, "SELECT type, payload_json FROM events WHERE task_id=? AND type='TASK_FAILED'", (t_race,))
        assert len(ev_race) == 1
        print(f"  [*] OCC Concurrency race passed: 1 winner, 1 conflict ({type(conflicts[0][2]).__name__}), 1 journal entry")

    finally:
        kernel.close()


def main():
    print("=" * 80)
    print("CHALLENGER 2: EMPIRICAL ADVERSARIAL STRESS HARNESS (GAP-12 REMEDIATION)")
    print("Zero-Trust & Fail-Closed Protocols: FA-08, FA-09, FA-12, FA-13")
    print("=" * 80)

    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)
        test_suite_1_retryable_lifecycle_and_exhaustion(tmp_dir)
        test_suite_2_uncertain_errors_fail_closed_no_blind_retries(tmp_dir)
        test_suite_3_downstream_ask_kernel_adapter_integration(tmp_dir)
        test_suite_4_downstream_task_kernel_bridge_integration(tmp_dir)
        test_suite_5_adversarial_boundary_and_concurrency_attacks(tmp_dir)

    print("\n" + "=" * 80)
    print("VERDICT: ALL 5 ADVERSARIAL TEST SUITES PASSED (100% EMPIRICAL CONFIRMATION)")
    print("  - Retry preservation and exhaustion lifecycle: VERIFIED")
    print("  - Uncertain failure fail-closed routing: VERIFIED")
    print("  - Downstream AskKernelAdapter physical SQLite integration: VERIFIED")
    print("  - Downstream TaskKernelHandsBridge physical SQLite integration: VERIFIED")
    print("  - OCC concurrency race, actor spoofing & underflow protection: VERIFIED")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
