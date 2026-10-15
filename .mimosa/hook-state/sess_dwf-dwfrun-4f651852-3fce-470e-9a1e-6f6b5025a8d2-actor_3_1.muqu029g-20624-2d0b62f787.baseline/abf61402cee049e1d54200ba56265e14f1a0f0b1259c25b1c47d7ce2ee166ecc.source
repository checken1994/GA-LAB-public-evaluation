"""Round 2 Adversarial Probe: Lease Expiration Watchdog racing against commit_completed().

Tests:
1. Passive TTL expiry: commit_completed() called after lease TTL expired before watchdog runs.
2. Active watchdog expiry in VERIFYING: expire_leases() runs first -> task moves to HUMAN_REVIEW -> worker commit_completed() strictly rejected.
3. Active watchdog expiry in RUNNING: expire_leases() runs first -> task moves to RECOVERING -> worker commit_completed() strictly rejected.
4. Explicit lease revocation: release() called -> worker commit_completed() strictly rejected.
5. Fencing token staleness: Lease expired, task re-claimed by worker 2 -> worker 1 commit_completed() strictly rejected.
6. Multithreaded concurrent race: ThreadPool racing expire_leases() vs commit_completed() across multiple tasks.
"""
from __future__ import annotations

import concurrent.futures
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

from scp.task_kernel import (
    TaskKernel,
    InvalidTransition,
    KernelError,
    StaleLease,
    OptimisticLockError,
)


def _setup_task(kernel: TaskKernel, task_id: str, owner: str, target_state: str = "VERIFYING", ttl: float = 30.0):
    kernel.create_task(task_id, owner, f"goal for {task_id}")
    kernel.transition(task_id, "PLANNING")
    kernel.transition(task_id, "READY")
    kernel.transition(task_id, "QUEUED")
    lease = kernel.claim(task_id, f"worker-{task_id}", ttl_seconds=ttl)
    kernel.start(task_id, lease.lease_id)
    if target_state == "VERIFYING":
        kernel.transition(task_id, "VERIFYING", lease_id=lease.lease_id)
    return lease


def run_probe() -> None:
    print("[PROBE R2] Starting Lease Expiration Watchdog vs commit_completed() Adversarial Probe...")
    tmp_dir = tempfile.mkdtemp(prefix="probe_gap11_r2_")
    kernel = None
    conn = None
    thread_kernels = []
    try:
        db_path = Path(tmp_dir) / "r2_watchdog_race.sqlite3"
        kernel = TaskKernel(db_path)

        # ---------------------------------------------------------------------
        # Attack 1: Passive TTL expiry before watchdog runs
        # ---------------------------------------------------------------------
        print("\n--- Attack 1: Passive TTL expiry before watchdog runs ---")
        lease1 = _setup_task(kernel, "task-passive-1", "owner-1", "VERIFYING", ttl=0.05)
        time.sleep(0.1)  # wait for lease TTL to pass
        
        attack1_blocked = False
        try:
            kernel.commit_completed(
                "task-passive-1",
                lease1.lease_id,
                "VERIFIED",
                "evidence://passive-expiry-test",
            )
        except StaleLease as e:
            attack1_blocked = True
            print(f"[R2-1] Passive TTL expiry commit_completed() BLOCKED with StaleLease: {e}")
        except Exception as e:
            print(f"FAIL: Unexpected exception for Attack 1: {type(e).__name__}: {e}")

        assert attack1_blocked, "Attack 1 FAILED: commit_completed succeeded after lease TTL expired!"

        # Inspect SQLite directly
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        task1 = conn.execute("SELECT * FROM tasks WHERE task_id='task-passive-1'").fetchone()
        assert task1["state"] == "VERIFYING", f"Expected VERIFYING, got {task1['state']}"
        events1 = conn.execute("SELECT * FROM events WHERE task_id='task-passive-1'").fetchall()
        assert not any(e["to_state"] == "COMPLETED" for e in events1), "COMPLETED event recorded unexpectedly!"
        print("[R2-1] SQLite verified: state remains VERIFYING, zero COMPLETED events in journal.")

        # ---------------------------------------------------------------------
        # Attack 2: Active watchdog expiry in VERIFYING (task -> HUMAN_REVIEW)
        # ---------------------------------------------------------------------
        print("\n--- Attack 2: Active watchdog expiry in VERIFYING (HUMAN_REVIEW) ---")
        lease2 = _setup_task(kernel, "task-watchdog-v", "owner-1", "VERIFYING", ttl=1.0)
        # Trigger watchdog with simulated now or future time
        expired = kernel.expire_leases(now=time.time() + 10.0)
        assert lease2.lease_id in expired, "Watchdog failed to expire lease2"

        # Check DB state immediately after watchdog
        task2_mid = conn.execute("SELECT * FROM tasks WHERE task_id='task-watchdog-v'").fetchone()
        assert task2_mid["state"] == "HUMAN_REVIEW", f"Expected HUMAN_REVIEW, got {task2_mid['state']}"
        assert task2_mid["active_lease_id"] is None
        assert task2_mid["active_fencing_token"] == 0
        lease2_row = conn.execute("SELECT * FROM leases WHERE lease_id=?", (lease2.lease_id,)).fetchone()
        assert lease2_row["released"] == 1
        print(f"[R2-2] Watchdog expired lease; task transitioned to HUMAN_REVIEW, lease released=1")

        # Worker attempts commit_completed() with the expired lease
        attack2_blocked = False
        try:
            kernel.commit_completed(
                "task-watchdog-v",
                lease2.lease_id,
                "VERIFIED",
                "evidence://stale-worker-commit",
            )
        except (StaleLease, OptimisticLockError, InvalidTransition) as e:
            attack2_blocked = True
            print(f"[R2-2] Stale worker commit_completed() BLOCKED fail-closed: {type(e).__name__}: {e}")
        except Exception as e:
            print(f"FAIL: Unexpected exception for Attack 2: {type(e).__name__}: {e}")

        assert attack2_blocked, "Attack 2 FAILED: commit_completed succeeded after watchdog expired lease!"

        # Inspect SQLite DB state
        task2_final = conn.execute("SELECT * FROM tasks WHERE task_id='task-watchdog-v'").fetchone()
        assert task2_final["state"] == "HUMAN_REVIEW", f"Expected HUMAN_REVIEW, got {task2_final['state']}"
        assert task2_final["version"] == task2_mid["version"], "Version bumped unexpectedly after failed commit!"
        events2 = conn.execute("SELECT * FROM events WHERE task_id='task-watchdog-v'").fetchall()
        assert not any(e["to_state"] == "COMPLETED" for e in events2)
        print("[R2-2] SQLite verified: state remains HUMAN_REVIEW, version untouched, zero COMPLETED events.")

        # ---------------------------------------------------------------------
        # Attack 3: Active watchdog expiry in RUNNING (task -> RECOVERING)
        # ---------------------------------------------------------------------
        print("\n--- Attack 3: Active watchdog expiry in RUNNING (RECOVERING) ---")
        lease3 = _setup_task(kernel, "task-watchdog-r", "owner-1", "RUNNING", ttl=1.0)
        expired3 = kernel.expire_leases(now=time.time() + 10.0)
        assert lease3.lease_id in expired3

        task3_mid = conn.execute("SELECT * FROM tasks WHERE task_id='task-watchdog-r'").fetchone()
        assert task3_mid["state"] == "RECOVERING", f"Expected RECOVERING, got {task3_mid['state']}"
        print(f"[R2-3] Watchdog expired running lease; task transitioned to RECOVERING")

        attack3_blocked = False
        try:
            kernel.commit_completed(
                "task-watchdog-r",
                lease3.lease_id,
                "VERIFIED",
                "evidence://running-expired-commit",
            )
        except (StaleLease, OptimisticLockError, InvalidTransition) as e:
            attack3_blocked = True
            print(f"[R2-3] Stale commit_completed() on RECOVERING task BLOCKED: {type(e).__name__}: {e}")

        assert attack3_blocked, "Attack 3 FAILED: commit_completed succeeded on RECOVERING task!"
        task3_final = conn.execute("SELECT * FROM tasks WHERE task_id='task-watchdog-r'").fetchone()
        assert task3_final["state"] == "RECOVERING"
        print("[R2-3] SQLite verified: state remains RECOVERING.")

        # ---------------------------------------------------------------------
        # Attack 4: Explicit lease revocation / release() before commit
        # ---------------------------------------------------------------------
        print("\n--- Attack 4: Explicit lease release() before commit ---")
        lease4 = _setup_task(kernel, "task-revoked-1", "owner-1", "VERIFYING", ttl=60.0)
        kernel.release("task-revoked-1", lease4.lease_id)
        lease4_row = conn.execute("SELECT * FROM leases WHERE lease_id=?", (lease4.lease_id,)).fetchone()
        assert lease4_row["released"] == 1
        print(f"[R2-4] Lease explicitly released via kernel.release()")

        attack4_blocked = False
        try:
            kernel.commit_completed(
                "task-revoked-1",
                lease4.lease_id,
                "VERIFIED",
                "evidence://released-lease-commit",
            )
        except (StaleLease, OptimisticLockError) as e:
            attack4_blocked = True
            print(f"[R2-4] Revoked lease commit_completed() BLOCKED: {type(e).__name__}: {e}")

        assert attack4_blocked, "Attack 4 FAILED: commit_completed succeeded with released lease!"
        task4_final = conn.execute("SELECT * FROM tasks WHERE task_id='task-revoked-1'").fetchone()
        assert task4_final["state"] == "VERIFYING"
        print("[R2-4] SQLite verified: task state intact in VERIFYING, lease released=1.")

        # ---------------------------------------------------------------------
        # Attack 5: Fencing token staleness after task re-claim
        # ---------------------------------------------------------------------
        print("\n--- Attack 5: Fencing token staleness after task re-claim ---")
        lease5_w1 = _setup_task(kernel, "task-fence-1", "owner-1", "RUNNING", ttl=1.0)
        # Expire worker 1's lease
        kernel.expire_leases(now=time.time() + 10.0)
        # Transition task RECOVERING -> QUEUED
        kernel.transition("task-fence-1", "QUEUED")
        # Worker 2 claims task with higher fencing token
        lease5_w2 = kernel.claim("task-fence-1", "worker-2", ttl_seconds=60.0)
        assert lease5_w2.fencing_token > lease5_w1.fencing_token
        kernel.start("task-fence-1", lease5_w2.lease_id)
        kernel.transition("task-fence-1", "VERIFYING", lease_id=lease5_w2.lease_id)
        print(f"[R2-5] Task re-claimed by worker 2 with fencing token {lease5_w2.fencing_token} (w1 token: {lease5_w1.fencing_token})")

        # Stale worker 1 attempts commit_completed()
        attack5_blocked = False
        try:
            kernel.commit_completed(
                "task-fence-1",
                lease5_w1.lease_id,
                "VERIFIED",
                "evidence://stale-fencing-token",
            )
        except (StaleLease, OptimisticLockError) as e:
            attack5_blocked = True
            print(f"[R2-5] Stale fencing token commit_completed() BLOCKED: {type(e).__name__}: {e}")

        assert attack5_blocked, "Attack 5 FAILED: worker 1 with stale fencing token succeeded commit_completed!"
        task5 = conn.execute("SELECT * FROM tasks WHERE task_id='task-fence-1'").fetchone()
        assert task5["active_lease_id"] == lease5_w2.lease_id
        assert task5["active_fencing_token"] == lease5_w2.fencing_token
        print("[R2-5] SQLite verified: worker 2's active lease and fencing token preserved.")

        # ---------------------------------------------------------------------
        # Attack 6: Multithreaded concurrent race: Watchdog vs Worker
        # ---------------------------------------------------------------------
        print("\n--- Attack 6: Multithreaded concurrent race (10 tasks, 20 threads) ---")
        num_tasks = 10
        race_tasks = []
        for i in range(num_tasks):
            tid = f"task-race-{i}"
            # Short TTL so watchdog and worker race closely
            l = _setup_task(kernel, tid, "owner-race", "VERIFYING", ttl=0.08)
            race_tasks.append((tid, l.lease_id))

        results = {}

        def watchdog_worker(tid, lid):
            k = None
            try:
                time.sleep(0.04)
                k = TaskKernel(db_path)
                thread_kernels.append(k)
                exp = k.expire_leases(now=time.time() + 0.1)
                return ("watchdog", tid, lid in exp)
            except Exception as e:
                return ("watchdog_err", tid, str(e))

        def completion_worker(tid, lid):
            k = None
            try:
                time.sleep(0.04)
                k = TaskKernel(db_path)
                thread_kernels.append(k)
                k._bound_leases[tid] = lid  # bind lease to thread instance
                res = k.commit_completed(
                    tid,
                    lid,
                    "VERIFIED",
                    f"evidence://race-{tid}",
                )
                return ("commit_ok", tid, res["state"])
            except (StaleLease, OptimisticLockError, InvalidTransition) as e:
                return ("commit_blocked", tid, type(e).__name__)
            except Exception as e:
                return ("commit_err", tid, str(e))

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for tid, lid in race_tasks:
                futures.append(executor.submit(watchdog_worker, tid, lid))
                futures.append(executor.submit(completion_worker, tid, lid))
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                results.setdefault(res[1], []).append(res)

        # Inspect all race outcomes in SQLite
        completed_count = 0
        human_review_count = 0
        for tid, lid in race_tasks:
            row = conn.execute("SELECT * FROM tasks WHERE task_id=?", (tid,)).fetchone()
            state = row["state"]
            events = conn.execute("SELECT type, from_state, to_state FROM events WHERE task_id=? ORDER BY seq", (tid,)).fetchall()
            event_types = [e["type"] for e in events]
            
            # Every task MUST be either COMPLETED (worker won) or HUMAN_REVIEW (watchdog won)
            assert state in {"COMPLETED", "HUMAN_REVIEW"}, f"Task {tid} in unexpected state: {state}"
            if state == "COMPLETED":
                completed_count += 1
                assert "TASK_COMPLETED" in event_types
                assert event_types[-1] == "TASK_COMPLETED"
            elif state == "HUMAN_REVIEW":
                human_review_count += 1
                assert "LEASE_EXPIRED" in event_types
                assert "TASK_COMPLETED" not in event_types

        print(f"[R2-6] Concurrent race completed: {completed_count} won by commit, {human_review_count} won by watchdog.")
        print(f"[R2-6] 100% of tasks cleanly resolved without state corruption or bypass.")

        # Database PRAGMA integrity_check
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        assert integrity == "ok", f"SQLite integrity check failed: {integrity}"
        print("[R2-6] SQLite PRAGMA integrity_check: ok")

    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        if kernel:
            try:
                kernel.close()
            except Exception:
                pass
        for tk in thread_kernels:
            try:
                tk.close()
            except Exception:
                pass
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\nALL R2 LEASE EXPIRATION WATCHDOG RACE ADVERSARIAL CHECKS PASSED!\n")


if __name__ == "__main__":
    run_probe()
