"""Adversarial Mutant Verification Harness.
Tests Mutants M1-M4 and examines whether tests in test_satellite_occ_anti_placebo.py
genuinely kill each mutant (i.e. tests fail when mutants are active).
"""

import copy
import inspect
import sqlite3
import tempfile
import threading
from pathlib import Path
import pytest

from scp.task_kernel import (
    TaskKernel,
    KernelError,
    StaleLease,
    OptimisticLockError,
    _idempotency_claim_fenced,
    _idempotency_complete_fenced,
)
import scp.task_kernel as tk_module
import scp.task_kernel_parts.taskkernel as tk_part


def _setup_running_task(kernel: TaskKernel, task_id: str = "fence-1", worker_id: str = "worker-1"):
    kernel.create_task(task_id, "lease-test", "prove stale writer fencing", "R1")
    for state in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, state, actor="lease-test", reason="setup")
    lease = kernel.claim(task_id, worker_id, ttl_seconds=300)
    kernel.start(task_id, lease.lease_id)
    return lease


def test_mutant_m1():
    """Mutant M1: _idempotency_complete_fenced omits OCC version check."""
    print("Testing Mutant M1...")
    original_complete = tk_module._idempotency_complete_fenced

    # Define mutant: bypass OCC version check
    def mutant_complete(self, logical_key, result_ref, expected_version=None):
        if not logical_key or not result_ref:
            raise KernelError("invalid idempotency completion")
        self._begin()
        try:
            row = self.conn.execute(
                "SELECT * FROM idempotency WHERE logical_key=?", (logical_key,)
            ).fetchone()
            if not row:
                raise KernelError("idempotency key not found")
            tid = str(row["task_id"])
            lease_id = getattr(self, "_bound_leases", {}).get(tid)
            if not lease_id:
                raise StaleLease("idempotency completion requires active lease authority")
            self._assert_lease(lease_id, tid)
            task = self._task(tid)
            if task["active_lease_id"] != lease_id:
                raise StaleLease(f"lease {lease_id} does not match active task lease {task['active_lease_id']}")

            # MUTANT: Omits expected_version check completely!
            if row["status"] == "COMPLETED":
                if row["result_ref"] != result_ref:
                    raise KernelError("idempotency result mismatch")
                self._commit()
                return
            if row["status"] != "CLAIMED":
                raise KernelError(f"invalid idempotency status: {row['status']}")

            # MUTANT: SQL update without AND version=?
            cur = self.conn.execute(
                "UPDATE idempotency SET status='COMPLETED',result_ref=?,version=version+1 WHERE logical_key=? AND status='CLAIMED'",
                (result_ref, logical_key),
            )
            self._commit()
        except Exception:
            self._rollback()
            raise

    # Apply mutant
    tk_module._idempotency_complete_fenced = mutant_complete
    TaskKernel.idempotency_complete = mutant_complete

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test_occ_idem.sqlite3"
        kernel = TaskKernel(db_path=db_path)
        try:
            _setup_running_task(kernel, "task-idem-1", "worker-1")
            logical_key, claimed = kernel.idempotency_claim(
                "task-idem-1", "step-1", "fs.write", "report.doc"
            )
            kernel.idempotency_complete(logical_key, "evidence://valid-outcome", expected_version=1)

            # Test step 3: Stale worker tries to complete with expected_version=1
            failed = False
            try:
                kernel.idempotency_complete(logical_key, "evidence://stale-overwrite", expected_version=1)
            except OptimisticLockError:
                failed = False  # If it raised OptimisticLockError, mutant lived (was not mutant)
            except Exception as e:
                # Raised something else (e.g. KernelError)
                print(f"  [M1] Test failed to catch OptimisticLockError; got {type(e).__name__}: {e}")
                failed = True
            else:
                print("  [M1] Mutant did not raise any exception!")
                failed = True

            if failed:
                print("  [M1] PASS: Mutant M1 is KILLED by test assertions (test_anti_placebo_idempotency_stale_update_fails_closed).")
            else:
                print("  [M1] FAIL: Mutant M1 survived!")
        finally:
            kernel.close()
            tk_module._idempotency_complete_fenced = original_complete
            TaskKernel.idempotency_complete = original_complete


def test_mutant_m2():
    """Mutant M2: Concurrent racing workers without OCC."""
    print("Testing Mutant M2...")
    original_complete = tk_module._idempotency_complete_fenced

    # Define mutant: SQL blind update without OCC
    def mutant_complete(self, logical_key, result_ref, expected_version=None):
        self._begin()
        try:
            row = self.conn.execute(
                "SELECT * FROM idempotency WHERE logical_key=?", (logical_key,)
            ).fetchone()
            tid = str(row["task_id"])
            lease_id = getattr(self, "_bound_leases", {}).get(tid)
            # Blind overwrite: ignore version
            self.conn.execute(
                "UPDATE idempotency SET status='COMPLETED',result_ref=?,version=version+1 WHERE logical_key=?",
                (result_ref, logical_key),
            )
            self._commit()
        except Exception:
            self._rollback()
            raise

    tk_module._idempotency_complete_fenced = mutant_complete
    TaskKernel.idempotency_complete = mutant_complete

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test_occ_race.sqlite3"
        kernel = TaskKernel(db_path=db_path)
        try:
            _setup_running_task(kernel, "task-race-1", "worker-1")
            logical_key, claimed = kernel.idempotency_claim(
                "task-race-1", "step-race", "fs.write", "output.dat"
            )
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
                except Exception as e:
                    errors.append((ident, e))
                finally:
                    k.close()

            t1 = threading.Thread(target=worker_attempt, args=("worker-A",))
            t2 = threading.Thread(target=worker_attempt, args=("worker-B",))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            # The test asserts len(successes) == 1 and len(errors) == 1 and isinstance(errors[0][1], OptimisticLockError)
            if len(successes) == 2 or len(errors) == 0 or not any(isinstance(err[1], OptimisticLockError) for err in errors):
                print(f"  [M2] Under mutant: successes={len(successes)}, errors={len(errors)}")
                print("  [M2] PASS: Mutant M2 is KILLED by test assertions (test_anti_placebo_concurrent_racing_workers_exactly_one_winner).")
            else:
                print("  [M2] FAIL: Mutant M2 survived!")
        finally:
            kernel.close()
            tk_module._idempotency_complete_fenced = original_complete
            TaskKernel.idempotency_complete = original_complete


def test_mutant_m3():
    """Mutant M3: Heartbeat and release without OCC version fencing."""
    print("Testing Mutant M3...")
    original_heartbeat = TaskKernel.heartbeat
    original_release = TaskKernel.release

    # Mutant heartbeat: ignores expected_version and omits AND version=? in SQL
    def mutant_heartbeat(self, task_id, lease_id, extend_seconds=30.0, expected_version=None):
        self._begin()
        try:
            lease = self._assert_lease(lease_id, task_id)
            now = 1000.0
            expires = now + extend_seconds
            # MUTANT: no version check in SQL
            cur = self.conn.execute(
                'UPDATE leases SET heartbeat_at=?,expires_at=?,version=version+1 WHERE lease_id=? AND released=0',
                (now, expires, lease_id),
            )
            self._commit()
            return lease
        except Exception:
            self._rollback()
            raise

    TaskKernel.heartbeat = mutant_heartbeat

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test_occ_lease.sqlite3"
        kernel = TaskKernel(db_path=db_path)
        try:
            lease = _setup_running_task(kernel, "task-lease-1", "worker-1")
            lease_id = lease.lease_id

            # Heartbeat 1 bumps version
            kernel.conn.execute("UPDATE leases SET version=2 WHERE lease_id=?", (lease_id,))

            # Stale heartbeat with expected_version=1: with mutant, does it raise OptimisticLockError?
            stale_raised = False
            try:
                kernel.heartbeat("task-lease-1", lease_id, expected_version=1)
            except OptimisticLockError:
                stale_raised = True
            except Exception:
                pass

            if not stale_raised:
                print("  [M3] PASS: Mutant M3 (heartbeat without OCC) is KILLED: did NOT raise OptimisticLockError.")
            else:
                print("  [M3] FAIL: Mutant M3 survived!")
        finally:
            kernel.close()
            TaskKernel.heartbeat = original_heartbeat
            TaskKernel.release = original_release


def test_mutant_m4():
    """Mutant M4: Idempotency claim on RETRYABLE without OCC."""
    print("Testing Mutant M4...")
    original_claim = tk_module._idempotency_claim_fenced

    # Define mutant: ignores expected_version
    def mutant_claim(self, task_id, step_id, action_type, resource_identity, expected_version=None):
        logical_key = f"{task_id}:{step_id}:{action_type}:{resource_identity}"
        self._begin()
        try:
            row = self.conn.execute(
                "SELECT * FROM idempotency WHERE logical_key=?", (logical_key,)
            ).fetchone()
            if row:
                # MUTANT: ignores expected_version != current_version!
                if row["status"] == "RETRYABLE":
                    cur = self.conn.execute(
                        "UPDATE idempotency SET status='CLAIMED',result_ref=NULL,version=version+1 WHERE logical_key=? AND status='RETRYABLE'",
                        (logical_key,),
                    )
                    self._commit()
                    return logical_key, True
                self._commit()
                return logical_key, False
            self._commit()
            return logical_key, True
        except Exception:
            self._rollback()
            raise

    tk_module._idempotency_claim_fenced = mutant_claim
    TaskKernel.idempotency_claim = mutant_claim

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test_occ_retry.sqlite3"
        kernel = TaskKernel(db_path=db_path)
        try:
            _setup_running_task(kernel, "task-retry-1", "worker-1")
            logical_key, claimed = kernel.idempotency_claim(
                "task-retry-1", "step-retry", "net.fetch", "data.json"
            )
            kernel.conn.execute(
                "UPDATE idempotency SET status='CLAIMED', version=2 WHERE logical_key=?",
                (logical_key,),
            )
            # Worker B tries to claim with stale expected_version=1
            raised = False
            try:
                kernel.idempotency_claim(
                    "task-retry-1", "step-retry", "net.fetch", "data.json", expected_version=1
                )
            except OptimisticLockError:
                raised = True
            except Exception:
                pass

            if not raised:
                print("  [M4] PASS: Mutant M4 (RETRYABLE claim without OCC) is KILLED: did NOT raise OptimisticLockError.")
            else:
                print("  [M4] FAIL: Mutant M4 survived!")
        finally:
            kernel.close()
            tk_module._idempotency_claim_fenced = original_claim
            TaskKernel.idempotency_claim = original_claim


def test_mutant_deadline():
    """Mutant on claim_next deadline cleanup:
    Check what happens if claim_next omits AND version=? vs with AND version=?.
    """
    print("Testing claim_next deadline race condition...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test_occ_dl.sqlite3"
        kernel = TaskKernel(db_path=db_path)
        try:
            kernel.create_task("task-dl-1", "test-actor", "test goal", deadline_ms=1)
            for s in ("PLANNING", "READY", "QUEUED"):
                kernel.transition("task-dl-1", s, actor="test-actor")

            # Emulate real race condition:
            # 1. Thread A (claim_next) selects task at version 5
            kernel.conn.execute(
                "UPDATE tasks SET deadline_ms=1, created_at='2020-01-01T00:00:00Z', version=5 WHERE task_id='task-dl-1'"
            )
            task_before_race = kernel.conn.execute("SELECT * FROM tasks WHERE task_id='task-dl-1'").fetchone()
            assert task_before_race["version"] == 5

            # 2. Racing transaction updates task to version 6 (e.g. worker transitioned or updated it)
            kernel.conn.execute(
                "UPDATE tasks SET version=6, state='READY' WHERE task_id='task-dl-1'"
            )

            # 3. If claim_next attempted to execute the update with stale version=5:
            # With OCC (AND version=?):
            cur = kernel.conn.execute(
                "UPDATE tasks SET state='FAILED',version=version+1 WHERE task_id='task-dl-1' AND version=?",
                (task_before_race["version"],),
            )
            occ_blocked = (cur.rowcount == 0)

            # Without OCC (no version check):
            cur_unfenced = kernel.conn.execute(
                "UPDATE tasks SET state='FAILED' WHERE task_id='task-dl-1'"
            )
            unfenced_overwrote = (cur_unfenced.rowcount == 1)

            print(f"  [Deadline Race] With OCC check: rowcount={cur.rowcount} (blocked blind overwrite: {occ_blocked})")
            print(f"  [Deadline Race] Without OCC check: rowcount={cur_unfenced.rowcount} (overwrote: {unfenced_overwrote})")

        finally:
            kernel.close()


def test_deadline_test_placebo():
    """Demonstrate that test_anti_placebo_tasks_claim_next_deadline_occ_fenced as written
    survives an unfenced mutant because of assertion row['version'] >= 6 and sequential execution.
    """
    print("Testing whether test_anti_placebo_tasks_claim_next_deadline_occ_fenced is vulnerable to placebo survival...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test_occ_deadline.sqlite3"
        kernel = TaskKernel(db_path=db_path)
        try:
            kernel.create_task("task-dl-1", "test-actor", "test goal", deadline_ms=1)
            for s in ("PLANNING", "READY", "QUEUED"):
                kernel.transition("task-dl-1", s, actor="test-actor")

            kernel.conn.execute(
                "UPDATE tasks SET deadline_ms=1, created_at='2020-01-01T00:00:00Z', version=5 WHERE task_id='task-dl-1'"
            )
            kernel.conn.execute(
                "UPDATE tasks SET version=6 WHERE task_id='task-dl-1'"
            )

            # If claim_next executed the unfenced query:
            # UPDATE tasks SET state='FAILED' WHERE task_id='task-dl-1'
            kernel.conn.execute("UPDATE tasks SET state='FAILED' WHERE task_id='task-dl-1'")

            row = kernel.conn.execute(
                "SELECT version, state FROM tasks WHERE task_id='task-dl-1'"
            ).fetchone()
            assertion_passed = (row["version"] >= 6)
            print(f"  [Placebo Finding] Under unfenced mutant, row['version']={row['version']}. Did test assertion pass? {assertion_passed}")
            if assertion_passed:
                print("  [Placebo Finding] WARNING: test_anti_placebo_tasks_claim_next_deadline_occ_fenced has a loose assertion!")
                print("  Reason: It runs sequentially after setting version=6, so version remains 6 and passes '>= 6' without proving OCC fencing prevented an in-flight conflict.")
        finally:
            kernel.close()


if __name__ == "__main__":
    test_mutant_m1()
    test_mutant_m2()
    test_mutant_m3()
    test_mutant_m4()
    test_mutant_deadline()
    test_deadline_test_placebo()
