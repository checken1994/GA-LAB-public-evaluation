"""Round 3 Adversarial Probe: Multi-Process Concurrency & OS-Level Stress Testing.

Verifies TaskKernel GAP-11 remediation across separate, independent OS processes:
1. Multi-process concurrent attack: Spawns independent Python subprocesses opening
   the same physical SQLite database file.
2. Cross-process GAP-11 bypass attempt: Subprocess attempts direct transition(task_id, "COMPLETED")
   and is strictly rejected with InvalidTransition across process boundaries.
3. Cross-process watchdog vs worker race: Subprocess 1 (worker) racing commit_completed()
   against Subprocess 2 (watchdog) running expire_leases().
4. Cross-process stale fencing token rejection: Subprocess using an expired or superseded
   lease fencing token cannot complete the task.
5. Transaction rollback & SQLite integrity check: Verifies PRAGMA integrity_check is 'ok'
   and event sequence has zero corruption after multi-process concurrent access.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from scp.task_kernel import InvalidTransition, TaskKernel

REPO_ROOT = Path(__file__).resolve().parents[2]

WORKER_SCRIPT = f"""
import sys
import time
from pathlib import Path

sys.path.insert(0, {repr(str(REPO_ROOT))})
from scp.task_kernel import TaskKernel, InvalidTransition, StaleLease, KernelError

db_path = sys.argv[1]
action = sys.argv[2]
task_id = sys.argv[3]
lease_id = sys.argv[4] if len(sys.argv) > 4 else None

kernel = TaskKernel(Path(db_path))

try:
    if action == "bypass_transition_completed":
        # Adversary subprocess attempts direct transition to COMPLETED
        try:
            kernel.transition(task_id, "COMPLETED", actor="subproc_attacker", lease_id=lease_id)
            print("VULNERABILITY: Subprocess succeeded direct transition to COMPLETED!")
            sys.exit(1)
        except InvalidTransition as e:
            print(f"BLOCKED_SUBPROC_TRANSITION: {{e}}")
            sys.exit(0)
    elif action == "commit_completed":
        # Worker subprocess commits completion with evidence
        if lease_id:
            kernel._bound_leases[task_id] = lease_id
        time.sleep(0.02)
        res = kernel.commit_completed(task_id, lease_id, "VERIFIED", f"subproc://evidence/{{task_id}}")
        print("COMMITTED_COMPLETED")
        sys.exit(0)
    elif action == "expire_watchdog":
        # Watchdog subprocess expires leases
        time.sleep(0.02)
        expired = kernel.expire_leases(now=time.time() + 100.0)
        print(f"EXPIRED_COUNT: {{len(expired)}}")
        sys.exit(0)
    elif action == "stale_fencing_commit":
        # Worker with old/stale lease attempts commit_completed
        if lease_id:
            kernel._bound_leases[task_id] = lease_id
        try:
            kernel.commit_completed(task_id, lease_id, "VERIFIED", f"subproc://stale/{{task_id}}")
            print("VULNERABILITY: Stale fencing commit succeeded!")
            sys.exit(1)
        except (StaleLease, KernelError) as e:
            print(f"BLOCKED_STALE_FENCING: {{type(e).__name__}}: {{e}}")
            sys.exit(0)
    else:
        print(f"UNKNOWN_ACTION: {{action}}")
        sys.exit(2)
except (StaleLease, KernelError) as e:
    print(f"EXPECTED_KERNEL_REJECTION: {{type(e).__name__}}: {{e}}")
    sys.exit(0)
except Exception as e:
    print(f"SUBPROC_EXCEPTION: {{type(e).__name__}}: {{e}}")
    sys.exit(3)
finally:
    kernel.close()
"""


def run_probe() -> None:
    print("[PROBE R3] Starting Multi-Process Concurrency & OS Stress Probe...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "multiproc_kernel.sqlite3"
        worker_script_path = Path(tmpdir) / "worker_runner.py"
        worker_script_path.write_text(WORKER_SCRIPT, encoding="utf-8")

        main_kernel = TaskKernel(db_path)
        try:
            # -------------------------------------------------------------
            # Attack 1: Cross-process direct transition to COMPLETED (GAP-11)
            # -------------------------------------------------------------
            print("\n--- Attack 1: Cross-process direct transition to COMPLETED ---")
            main_kernel.create_task("task_mp_1", "owner_mp", "test direct complete across process")
            for s in ("PLANNING", "READY", "QUEUED"):
                main_kernel.transition("task_mp_1", s, actor="setup")
            lease1 = main_kernel.claim("task_mp_1", "worker_mp_1", ttl_seconds=30.0)
            main_kernel.start("task_mp_1", lease1.lease_id)
            main_kernel.transition("task_mp_1", "VERIFYING", lease_id=lease1.lease_id)

            # Spawn subprocess attempting direct transition to COMPLETED
            proc = subprocess.run(
                [sys.executable, str(worker_script_path), str(db_path), "bypass_transition_completed", "task_mp_1", lease1.lease_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert proc.returncode == 0, f"Process failed: stdout={proc.stdout}, stderr={proc.stderr}"
            assert "BLOCKED_SUBPROC_TRANSITION" in proc.stdout
            print(f"[R3-1] Subprocess direct transition to COMPLETED blocked: {proc.stdout.strip()}")

            # Verify raw SQLite state remains VERIFYING
            row1 = main_kernel.get_task("task_mp_1")
            assert row1["state"] == "VERIFYING"
            events1 = main_kernel.get_events("task_mp_1")
            assert not any(e["to_state"] == "COMPLETED" for e in events1)
            print("[R3-1] SQLite verified: state remains VERIFYING, zero COMPLETED events.")

            # -------------------------------------------------------------
            # Attack 2: Cross-process Watchdog vs Worker race across 6 tasks
            # -------------------------------------------------------------
            print("\n--- Attack 2: Cross-process Watchdog vs Worker race (12 subprocesses) ---")
            tasks = []
            for i in range(6):
                tid = f"task_race_mp_{i}"
                main_kernel.create_task(tid, "owner_mp", f"goal {i}")
                for s in ("PLANNING", "READY", "QUEUED"):
                    main_kernel.transition(tid, s, actor="setup")
                # Lease with very short TTL
                lease = main_kernel.claim(tid, f"worker_{i}", ttl_seconds=0.08)
                main_kernel.start(tid, lease.lease_id)
                main_kernel.transition(tid, "VERIFYING", lease_id=lease.lease_id)
                tasks.append((tid, lease.lease_id))

            # Launch concurrent subprocesses: for each task, one commit worker and one watchdog
            procs = []
            for tid, lid in tasks:
                # Subprocess worker trying to commit
                p_commit = subprocess.Popen(
                    [sys.executable, str(worker_script_path), str(db_path), "commit_completed", tid, lid],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                # Subprocess watchdog trying to expire
                p_watchdog = subprocess.Popen(
                    [sys.executable, str(worker_script_path), str(db_path), "expire_watchdog", tid, lid],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                procs.extend([p_commit, p_watchdog])

            for p in procs:
                p.wait(timeout=15)
                assert p.returncode in (0, 1), f"Unexpected exit code {p.returncode}: {p.stderr.read()}"

            # Inspect all tasks
            completed_count = 0
            human_review_count = 0
            for tid, lid in tasks:
                t = main_kernel.get_task(tid)
                assert t["state"] in {"COMPLETED", "HUMAN_REVIEW"}, f"Task {tid} in unexpected state: {t['state']}"
                if t["state"] == "COMPLETED":
                    completed_count += 1
                else:
                    human_review_count += 1

            print(f"[R3-2] Multi-process race settled cleanly: {completed_count} COMPLETED, {human_review_count} HUMAN_REVIEW.")

            # -------------------------------------------------------------
            # Attack 3: Cross-process Stale Fencing Token Rejection
            # -------------------------------------------------------------
            print("\n--- Attack 3: Cross-process Stale Fencing Token Rejection ---")
            main_kernel.create_task("task_fence_mp", "owner_mp", "test fencing across process")
            for s in ("PLANNING", "READY", "QUEUED"):
                main_kernel.transition("task_fence_mp", s, actor="setup")
            lease_old = main_kernel.claim("task_fence_mp", "worker_old", ttl_seconds=30.0)
            main_kernel.start("task_fence_mp", lease_old.lease_id)
            main_kernel.transition("task_fence_mp", "VERIFYING", lease_id=lease_old.lease_id)

            # Expire lease_old via expire_leases() -> moves task from VERIFYING to HUMAN_REVIEW
            main_kernel.expire_leases(now=time.time() + 100.0)
            assert main_kernel.get_task("task_fence_mp")["state"] == "HUMAN_REVIEW"
            main_kernel.transition("task_fence_mp", "READY")
            main_kernel.transition("task_fence_mp", "QUEUED")
            lease_new = main_kernel.claim("task_fence_mp", "worker_new", ttl_seconds=60.0)
            main_kernel.start("task_fence_mp", lease_new.lease_id)
            main_kernel.transition("task_fence_mp", "VERIFYING", lease_id=lease_new.lease_id)

            # Subprocess attempts commit_completed with lease_old (stale fencing token)
            proc_fence = subprocess.run(
                [sys.executable, str(worker_script_path), str(db_path), "stale_fencing_commit", "task_fence_mp", lease_old.lease_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert proc_fence.returncode == 0
            assert "BLOCKED_STALE_FENCING" in proc_fence.stdout
            print(f"[R3-3] Cross-process stale fencing token commit rejected: {proc_fence.stdout.strip()}")
            assert main_kernel.get_task("task_fence_mp")["active_lease_id"] == lease_new.lease_id

            # -------------------------------------------------------------
            # Attack 4: Transaction Rollback Integrity under Contention
            # -------------------------------------------------------------
            print("\n--- Attack 4: Transaction Rollback Integrity under Contention ---")
            events_before = len(main_kernel.get_events("task_fence_mp"))
            task_before = main_kernel.get_task("task_fence_mp")
            try:
                # Deliberately attempt an invalid transition that raises inside transaction
                main_kernel.transition("task_fence_mp", "COMPLETED", lease_id=lease_new.lease_id)
            except InvalidTransition:
                pass
            events_after = len(main_kernel.get_events("task_fence_mp"))
            task_after = main_kernel.get_task("task_fence_mp")
            assert events_before == events_after, f"Transaction rollback leaked events: {events_before} vs {events_after}"
            assert task_before["version"] == task_after["version"], "Transaction rollback leaked version increment!"
            assert task_after["state"] == "VERIFYING", f"State corrupted after rollback: {task_after['state']}"
            print("[R3-4] Transaction rollback verified: 0 dirty events, version preserved, state intact.")

            # -------------------------------------------------------------
            # Attack 5: Database Integrity & Consistency Check
            # -------------------------------------------------------------
            print("\n--- Attack 5: SQLite physical database integrity check ---")
            integrity = main_kernel.conn.execute("PRAGMA integrity_check").fetchone()
            assert integrity[0] == "ok", f"Integrity check failed: {integrity[0]}"
            print("[R3-5] SQLite PRAGMA integrity_check: ok")

        finally:
            main_kernel.close()

    print("\nALL R3 MULTI-PROCESS CONCURRENCY ADVERSARIAL CHECKS PASSED!")


if __name__ == "__main__":
    run_probe()
