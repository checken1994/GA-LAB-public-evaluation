"""P1: Chaos Recovery Test (Cổng F/C).
Simulates a random crash and verifies task kernel can reconcile and resume.
Replaces legacy placebo 'assert True' with actual process termination,
state reconciliation, lease recovery, and hash-chain verification.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from scp.task_kernel import TaskKernel

CHILD_WORKER_SCRIPT = r"""
import sys, time
sys.path.insert(0, r"{root}")
from scp.task_kernel import TaskKernel

kernel = TaskKernel(r"{db}")
kernel.create_task("chaos-worker-task-1", "chaos-operator", "perform critical file write", "R1", deadline_ms=600000)
kernel.transition("chaos-worker-task-1", "PLANNING", actor="chaos-sim", reason="planning started")
kernel.transition("chaos-worker-task-1", "READY", actor="chaos-sim", reason="ready for execution")
kernel.transition("chaos-worker-task-1", "QUEUED", actor="chaos-sim", reason="queued in broker")
lease = kernel.claim("chaos-worker-task-1", "worker-node-alpha", ttl_seconds=300)
kernel.start("chaos-worker-task-1", lease.lease_id)
kernel.idempotency_claim("chaos-worker-task-1", "step-1", "fs.write", "report.dat")
print("CHILD_RUNNING_READY", flush=True)
time.sleep(120)  # Parent terminates process here to simulate sudden crash
"""


def test_chaos_recovery():
    """Simulate a sudden unhandled worker crash mid-flight, boot new kernel,

    and verify journal replay, task state recovery to HUMAN_REVIEW, and hash-chain preservation.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "chaos_test.sqlite3")
        repo_root = str(Path(__file__).resolve().parents[2])
        
        # 1. Spawn child worker process
        proc = subprocess.Popen(
            [sys.executable, "-X", "utf8", "-c", CHILD_WORKER_SCRIPT.format(root=repo_root, db=db_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
        try:
            line = proc.stdout.readline()
            assert "CHILD_RUNNING_READY" in line, f"Child worker did not reach RUNNING: {line}"
            # 2. Inject hard chaos crash: kill process while actively RUNNING
            proc.kill()
            proc.wait(timeout=15)
        finally:
            if proc.poll() is None:
                proc.kill()

        # 3. Boot new TaskKernel instance against crashed database
        kernel = TaskKernel(db_path)
        try:
            # Validate task state immediately after death
            crashed_task = kernel.get_task("chaos-worker-task-1")
            assert crashed_task["state"] == "RUNNING", "State machine must preserve RUNNING state at crash point"

            # 4. Perform boot recovery
            report = kernel.recover_on_boot()
            assert not report["corrupted"], f"Journal corrupted during recovery: {report['corrupted']}"
            assert any(
                r["task_id"] == "chaos-worker-task-1" and r["to"] == "HUMAN_REVIEW"
                for r in report["recovered"]
            ), f"Task was not recovered to HUMAN_REVIEW: {report}"

            # 5. Verify task is safely recovered and lease released
            recovered_task = kernel.get_task("chaos-worker-task-1")
            assert recovered_task["state"] == "HUMAN_REVIEW"
            assert recovered_task["active_lease_id"] is None
            assert recovered_task["active_fencing_token"] == 0

            # 6. Verify cryptographic journal integrity
            journal = kernel.verify_journal("chaos-worker-task-1")
            assert journal["hash_chain_valid"] is True, f"Hash chain violated: {journal['errors']}"
            assert journal["event_count"] >= 6
        finally:
            kernel.close()


def test_chaos_lease_expiration_recovery():
    """Verify TaskKernel recovers tasks whose worker leases expire."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "lease_chaos.sqlite3")
        kernel = TaskKernel(db_path)
        try:
            kernel.create_task("lease-task-1", "operator", "subtask", "R0")
            kernel.transition("lease-task-1", "PLANNING", actor="op", reason="plan")
            kernel.transition("lease-task-1", "READY", actor="op", reason="ready")
            kernel.transition("lease-task-1", "QUEUED", actor="op", reason="queue")
            
            # [FLAKE-FIX 2026-09-24] ttl=0.01 forced kernel.start() to fit in a
            # 10ms window; on a slow disk start() fails closed with StaleLease
            # before the sweep. Setup now uses a safe TTL and expiry is driven
            # by the watchdog's synthetic clock (same pattern as the T04
            # watchdog tests), so the sweep is deterministic, not wall-clock.
            lease = kernel.claim("lease-task-1", "worker-beta", ttl_seconds=1.0)
            kernel.start("lease-task-1", lease.lease_id)
            time.sleep(0.05)

            # Watchdog sweeps expired leases (synthetic now: lease is expired)
            expired = kernel.expire_leases(now=time.time() + 1000.0)
            assert lease.lease_id in expired
            
            # Task transitions to RECOVERING
            task = kernel.get_task("lease-task-1")
            assert task["state"] == "RECOVERING"
            
            journal = kernel.verify_journal("lease-task-1")
            assert journal["hash_chain_valid"] is True
        finally:
            kernel.close()


def test_chaos_corrupted_journal_fails_closed():
    """Verify corrupted journal events cause fail-closed boot recovery without tampering."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "corrupted_chaos.sqlite3")
        kernel = TaskKernel(db_path)
        try:
            kernel.create_task("tampered-task-1", "operator", "goal", "R0")
            kernel.transition("tampered-task-1", "PLANNING", actor="op", reason="plan")
            
            # Tamper event in raw SQL behind the kernel's back
            kernel.conn.begin()
            kernel.conn.execute("UPDATE events SET reason='illicit_tamper' WHERE task_id='tampered-task-1' AND seq=1")
            kernel.conn.commit()
            
            report = kernel.recover_on_boot()
            assert any(c["task_id"] == "tampered-task-1" for c in report["corrupted"])
            # State must remain untouched (fail-closed)
            assert kernel.get_task("tampered-task-1")["state"] == "PLANNING"
        finally:
            kernel.close()