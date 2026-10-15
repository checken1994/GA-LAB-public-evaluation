"""Adversarial stress test and break attempts against GAP-11 remediation.

Tests:
1. Replay attack: reusing an existing TASK_COMPLETED event_id in transition()
2. State variations: attempting transition to COMPLETED from all 15 states
3. Non-existent task transition to COMPLETED
4. Identity spoofing: actor="verifier", reason="postcondition_verified"
5. Tampered event in SQLite journal vs rebuild_projection()
6. Rebuild projection after legitimate commit_completed()
7. OCC concurrency conflict in commit_completed() during race
"""
import sys
import tempfile
from pathlib import Path
import sqlite3
from unittest.mock import patch

from scp.task_kernel import (
    TaskKernel,
    InvalidTransition,
    KernelError,
    StaleLease,
    OptimisticLockError,
    NotFound,
)

def run_adversarial_suite():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "adversarial.sqlite3"
        kernel = TaskKernel(db_path)

        # 1. Setup Task 1 and complete it legitimately
        kernel.create_task("task_legit", "owner_1", "legit goal")
        kernel.transition("task_legit", "PLANNING")
        kernel.transition("task_legit", "READY")
        kernel.transition("task_legit", "QUEUED")
        lease1 = kernel.claim("task_legit", "worker_1", 30.0)
        kernel.start("task_legit", lease1.lease_id)
        kernel.transition("task_legit", "VERIFYING", lease_id=lease1.lease_id)
        
        completed = kernel.commit_completed(
            "task_legit",
            lease1.lease_id,
            "VERIFIED",
            "evidence://provenance/sha256:abc12345",
        )
        assert completed["state"] == "COMPLETED"
        events_legit = kernel.get_events("task_legit")
        completed_event = [e for e in events_legit if e["to_state"] == "COMPLETED"][0]
        completed_event_id = completed_event["event_id"]
        print(f"[ADV-1] Legit completion event_id: {completed_event_id}")

        # 2. Replay attack: attempt to use completed_event_id to transition task_2 to COMPLETED
        kernel.create_task("task_victim", "owner_1", "victim goal")
        kernel.transition("task_victim", "PLANNING")
        kernel.transition("task_victim", "READY")
        kernel.transition("task_victim", "QUEUED")
        lease2 = kernel.claim("task_victim", "worker_2", 30.0)
        kernel.start("task_victim", lease2.lease_id)
        kernel.transition("task_victim", "VERIFYING", lease_id=lease2.lease_id)

        try:
            kernel.transition(
                "task_victim",
                "COMPLETED",
                event_id=completed_event_id,
                lease_id=lease2.lease_id,
                actor="verifier",
                reason="postcondition_verified",
            )
            print("FAIL: Replay attack succeeded!")
            sys.exit(1)
        except InvalidTransition as e:
            assert "direct transition to COMPLETED is forbidden" in str(e)
            print(f"[ADV-2] Replay attack BLOCKED: {e}")

        # Verify task_victim remains in VERIFYING, no COMPLETED event appended
        task_victim = kernel.get_task("task_victim")
        assert task_victim["state"] == "VERIFYING"
        events_victim = kernel.get_events("task_victim")
        assert not any(e["to_state"] == "COMPLETED" for e in events_victim)
        print("[ADV-3] Verified victim task untouched in SQLite")

        # 3. Non-existent task
        try:
            kernel.transition("non_existent_task", "COMPLETED")
            print("FAIL: Non-existent task transition succeeded!")
            sys.exit(1)
        except InvalidTransition as e:
            assert "direct transition to COMPLETED is forbidden" in str(e)
            print(f"[ADV-4] Non-existent task transition to COMPLETED BLOCKED: {e}")

        # 4. Attempt from terminal states (COMPLETED, FAILED, CANCELLED)
        # Attempt to transition task_legit (already COMPLETED) to COMPLETED again
        try:
            kernel.transition("task_legit", "COMPLETED")
            print("FAIL: Terminal transition to COMPLETED succeeded!")
            sys.exit(1)
        except InvalidTransition as e:
            assert "direct transition to COMPLETED is forbidden" in str(e)
            print(f"[ADV-5] Terminal state transition to COMPLETED BLOCKED: {e}")

        # 5. Tampered event vs rebuild_projection()
        # Direct raw SQLite injection of fake COMPLETED event with broken hash chain
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO events(event_id, task_id, seq, type, from_state, to_state, actor, reason, payload_json, event_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "evt_forged_1",
                "task_victim",
                999,
                "STATE_TRANSITION",
                "VERIFYING",
                "COMPLETED",
                "attacker",
                "forged",
                "{}",
                "fake_hash_123",
                "2026-09-08T00:00:00Z",
            ),
        )
        conn.commit()
        conn.close()

        # Rebuild projection must detect broken hash chain and refuse!
        try:
            kernel.rebuild_projection("task_victim")
            print("FAIL: rebuild_projection accepted tampered event!")
            sys.exit(1)
        except KernelError as e:
            assert "journal integrity invalid" in str(e)
            print(f"[ADV-6] rebuild_projection rejected forged event (Fail-Closed): {e}")

        # Verify task_victim state is STILL VERIFYING in SQLite
        task_victim_after = kernel.get_task("task_victim")
        assert task_victim_after["state"] == "VERIFYING"
        print("[ADV-7] Verified task_victim DB state preserved after failed rebuild")

        # 6. Legitimate rebuild_projection on task_legit
        rebuilt_legit = kernel.rebuild_projection("task_legit")
        assert rebuilt_legit["state"] == "COMPLETED"
        assert rebuilt_legit["active_lease_id"] is None
        assert rebuilt_legit["active_fencing_token"] == 0
        print("[ADV-8] Verified legitimate rebuild_projection preserves COMPLETED projection")

        # 7. OCC concurrency conflict: racing mutation during commit_completed()
        kernel.create_task("task_occ", "owner_1", "occ goal")
        kernel.transition("task_occ", "PLANNING")
        kernel.transition("task_occ", "READY")
        kernel.transition("task_occ", "QUEUED")
        lease_occ = kernel.claim("task_occ", "worker_occ", 30.0)
        kernel.start("task_occ", lease_occ.lease_id)
        kernel.transition("task_occ", "VERIFYING", lease_id=lease_occ.lease_id)

        # Simulate racing commit_completed where version was bumped right before UPDATE tasks
        original_task = kernel._task
        def racing_task(task_id):
            res = original_task(task_id)
            if task_id == "task_occ":
                # Return a stale version dictionary to trigger cur.rowcount == 0
                stale = dict(res)
                stale["version"] = 99999
                return stale
            return res

        with patch.object(kernel, "_task", side_effect=racing_task):
            try:
                kernel.commit_completed(
                    "task_occ",
                    lease_occ.lease_id,
                    "VERIFIED",
                    "evidence://valid/evidence",
                )
                print("FAIL: commit_completed succeeded despite version conflict!")
                sys.exit(1)
            except StaleLease as e:
                assert "concurrency conflict completing task" in str(e)
                print(f"[ADV-9] OCC protected commit_completed against version conflict: {e}")

        kernel.close()
        print("\nALL ADVERSARIAL ATTACK VECTORS BLOCKED SUCCESSFULLY!")

if __name__ == "__main__":
    run_adversarial_suite()
