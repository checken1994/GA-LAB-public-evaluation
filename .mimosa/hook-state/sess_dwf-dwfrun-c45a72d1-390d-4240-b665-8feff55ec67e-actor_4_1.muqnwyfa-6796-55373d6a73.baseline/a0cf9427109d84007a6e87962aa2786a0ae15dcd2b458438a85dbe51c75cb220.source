"""Unit tests for rebuild_projection OCC (GAP-03) and Transaction Boundary (GAP-04).

Verifies:
1. Normal rebuild_projection increments version by 1 and updates state.
2. Stale expected_version raises OptimisticLockError (GAP-03).
3. Concurrent threads contending on expected_version yields exactly 1 winner (GAP-03).
4. Entire rebuild_projection runs within transaction boundary: rolling back on errors (GAP-04).
5. OptimisticLockError attributes are properly populated (table, entity_id, expected_version).
"""
import multiprocessing
import threading
from pathlib import Path

import pytest

from scp.task_kernel import (
    KernelError,
    NotFound,
    OptimisticLockError,
    TaskKernel,
)


def _setup_task_in_planning(kernel: TaskKernel, task_id: str) -> dict:
    kernel.create_task(task_id, "test-owner", "occ probe goal", "R1")
    return kernel.transition(task_id, "PLANNING", actor="setup")


def _mp_rebuild_worker(db_path: str, task_id: str, base_version: int, result_queue: multiprocessing.Queue):
    """Top-level worker function safe for Windows multiprocessing spawn."""
    try:
        k = TaskKernel(db_path)
        try:
            k.rebuild_projection(task_id, expected_version=base_version)
            result_queue.put("SUCCESS")
        except OptimisticLockError:
            result_queue.put("OCC_ERROR")
        except Exception as e:
            result_queue.put(f"ERROR_{type(e).__name__}: {e}")
        finally:
            k.close()
    except Exception as e:
        result_queue.put(f"INIT_ERROR: {e}")


def test_rebuild_projection_increments_version_with_occ(tmp_path: Path):
    """Happy path: rebuild_projection successfully increments version using OCC."""
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        task_id = "test-rebuild-happy"
        _setup_task_in_planning(kernel, task_id)
        task_before = kernel.get_task(task_id)
        v_before = int(task_before["version"])

        # Rebuild without explicit expected_version
        rebuilt = kernel.rebuild_projection(task_id)
        assert int(rebuilt["version"]) == v_before + 1
        assert rebuilt["state"] == "PLANNING"

        # Rebuild with matching expected_version
        v_current = int(rebuilt["version"])
        rebuilt_again = kernel.rebuild_projection(task_id, expected_version=v_current)
        assert int(rebuilt_again["version"]) == v_current + 1
    finally:
        kernel.close()


def test_rebuild_projection_stale_expected_version_raises_optimistic_lock_error(tmp_path: Path):
    """GAP-03: Stale expected_version must be rejected with OptimisticLockError."""
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        task_id = "test-rebuild-stale"
        _setup_task_in_planning(kernel, task_id)
        t1 = kernel.get_task(task_id)
        stale_version = int(t1["version"])

        # Progress the task: version increments to stale_version + 1
        kernel.transition(task_id, "READY", actor="setup")
        t2 = kernel.get_task(task_id)
        assert int(t2["version"]) > stale_version

        # Attempt rebuild with stale version -> must fail closed
        with pytest.raises(OptimisticLockError) as exc_info:
            kernel.rebuild_projection(task_id, expected_version=stale_version)

        err = exc_info.value
        assert err.table == "tasks"
        assert err.entity_id == task_id
        assert err.expected_version == stale_version
        assert "concurrency conflict rebuilding projection" in str(err)

        # Confirm task state and version were not corrupted by failed rebuild
        t_unchanged = kernel.get_task(task_id)
        assert t_unchanged["version"] == t2["version"]
        assert t_unchanged["state"] == "READY"
    finally:
        kernel.close()


def test_rebuild_projection_concurrent_threads_exactly_one_winner(tmp_path: Path):
    """GAP-03: Racing rebuilds on the same version must yield exactly 1 winner and 1 OCC error."""
    db_path = tmp_path / "kernel.sqlite3"
    init_kernel = TaskKernel(db_path)
    task_id = "test-rebuild-race"
    _setup_task_in_planning(init_kernel, task_id)
    base_task = init_kernel.get_task(task_id)
    base_version = int(base_task["version"])
    init_kernel.close()

    results = []
    barrier = threading.Barrier(2)

    def worker_fn(worker_name: str):
        k = TaskKernel(db_path)
        try:
            barrier.wait()
            k.rebuild_projection(task_id, expected_version=base_version)
            results.append((worker_name, "SUCCESS"))
        except OptimisticLockError:
            results.append((worker_name, "OCC_ERROR"))
        except Exception as e:
            results.append((worker_name, f"UNEXPECTED_{type(e).__name__}"))
        finally:
            k.close()

    t1 = threading.Thread(target=worker_fn, args=("Worker-1",))
    t2 = threading.Thread(target=worker_fn, args=("Worker-2",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    statuses = [status for _, status in results]
    assert "SUCCESS" in statuses, f"At least one worker must succeed, got {results}"
    assert "OCC_ERROR" in statuses, f"The losing worker must receive OptimisticLockError, got {results}"
    assert len(statuses) == 2


def test_rebuild_projection_transaction_boundary_rolls_back_on_corrupt_journal(tmp_path: Path):
    """GAP-04: If verify_journal fails, the transaction is cleanly rolled back."""
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        task_id = "test-rebuild-rollback"
        _setup_task_in_planning(kernel, task_id)
        task_before = kernel.get_task(task_id)
        v_before = int(task_before["version"])

        # Corrupt an event in the events table
        kernel.conn.execute(
            "UPDATE events SET event_hash='corrupted_hash' WHERE task_id=? AND seq=1",
            (task_id,),
        )

        with pytest.raises(KernelError) as exc_info:
            kernel.rebuild_projection(task_id)
        assert "journal integrity invalid" in str(exc_info.value)

        # Version must remain unchanged
        task_after = kernel.get_task(task_id)
        assert int(task_after["version"]) == v_before
    finally:
        kernel.close()


def test_rebuild_projection_nonexistent_task_raises_not_found_and_cleans_transaction(tmp_path: Path):
    """rebuild_projection on non-existent task raises NotFound and releases transaction."""
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        with pytest.raises(NotFound):
            kernel.rebuild_projection("non-existent-task-999")

        # Storage must be clean and usable immediately after the exception
        kernel.create_task("subsequent-task", "owner", "valid goal", "R0")
        task = kernel.get_task("subsequent-task")
        assert task["task_id"] == "subsequent-task"
        assert task["state"] == "CREATED"
    finally:
        kernel.close()


def test_rebuild_projection_races_with_transition_exactly_one_winner(tmp_path: Path):
    """Adversarial race: transition() vs rebuild_projection() on identical base version."""
    db_path = tmp_path / "kernel.sqlite3"
    init_kernel = TaskKernel(db_path)
    task_id = "test-race-trans-rebuild"
    _setup_task_in_planning(init_kernel, task_id)
    base_task = init_kernel.get_task(task_id)
    base_version = int(base_task["version"])
    init_kernel.close()

    results = []
    barrier = threading.Barrier(2)

    def transition_worker():
        k = TaskKernel(db_path)
        try:
            barrier.wait(timeout=5)
            k.transition(task_id, "READY", actor="worker-trans", expected_version=base_version)
            results.append(("TRANSITION", "SUCCESS"))
        except OptimisticLockError:
            results.append(("TRANSITION", "OCC_ERROR"))
        except Exception as e:
            results.append(("TRANSITION", f"ERROR_{type(e).__name__}"))
        finally:
            k.close()

    def rebuild_worker():
        k = TaskKernel(db_path)
        try:
            barrier.wait(timeout=5)
            k.rebuild_projection(task_id, expected_version=base_version)
            results.append(("REBUILD", "SUCCESS"))
        except OptimisticLockError:
            results.append(("REBUILD", "OCC_ERROR"))
        except Exception as e:
            results.append(("REBUILD", f"ERROR_{type(e).__name__}"))
        finally:
            k.close()

    t1 = threading.Thread(target=transition_worker)
    t2 = threading.Thread(target=rebuild_worker)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    outcomes = [status for _, status in results]
    assert len(outcomes) == 2, f"Both workers must finish, got {results}"
    assert "SUCCESS" in outcomes, f"Exactly one must succeed, got {results}"
    assert "OCC_ERROR" in outcomes, f"The losing worker must receive OCC_ERROR, got {results}"

    # Final DB check: version must have incremented by exactly 1
    final_kernel = TaskKernel(db_path)
    try:
        final_task = final_kernel.get_task(task_id)
        assert int(final_task["version"]) == base_version + 1
    finally:
        final_kernel.close()


def test_rebuild_projection_high_concurrency_stress_single_winner(tmp_path: Path):
    """Stress test: 10 parallel threads all racing to rebuild the same task version."""
    db_path = tmp_path / "kernel.sqlite3"
    init_kernel = TaskKernel(db_path)
    task_id = "test-stress-rebuild"
    _setup_task_in_planning(init_kernel, task_id)
    base_task = init_kernel.get_task(task_id)
    base_version = int(base_task["version"])
    init_kernel.close()

    num_threads = 10
    results = []
    barrier = threading.Barrier(num_threads)

    def worker_thread(idx: int):
        k = TaskKernel(db_path)
        try:
            barrier.wait(timeout=5)
            k.rebuild_projection(task_id, expected_version=base_version)
            results.append((f"Worker-{idx}", "SUCCESS"))
        except OptimisticLockError:
            results.append((f"Worker-{idx}", "OCC_ERROR"))
        except Exception as e:
            results.append((f"Worker-{idx}", f"ERROR_{type(e).__name__}"))
        finally:
            k.close()

    threads = [threading.Thread(target=worker_thread, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    outcomes = [status for _, status in results]
    assert len(outcomes) == num_threads, f"All {num_threads} threads must record result, got {results}"
    successes = outcomes.count("SUCCESS")
    occ_errors = outcomes.count("OCC_ERROR")
    assert successes == 1, f"Expected exactly 1 winner under high contention, got {successes} (results={results})"
    assert occ_errors == num_threads - 1, f"Expected {num_threads - 1} OCC_ERROR, got {occ_errors}"

    # Final DB check: version must be base_version + 1
    final_kernel = TaskKernel(db_path)
    try:
        final_task = final_kernel.get_task(task_id)
        assert int(final_task["version"]) == base_version + 1
    finally:
        final_kernel.close()


def test_rebuild_projection_transaction_boundary_is_active_during_event_read(tmp_path: Path):
    """GAP-04: Runtime verification that event reading is strictly protected inside active transaction."""
    kernel = TaskKernel(tmp_path / "kernel.sqlite3")
    try:
        task_id = "test-boundary-active"
        _setup_task_in_planning(kernel, task_id)

        orig_get_events = kernel.get_events
        in_tx_observations = []

        def tracked_get_events(tid: str):
            in_tx_observations.append(bool(kernel._storage.in_transaction))
            return orig_get_events(tid)

        kernel.get_events = tracked_get_events
        kernel.rebuild_projection(task_id)

        assert in_tx_observations, "get_events must be invoked during rebuild_projection"
        assert all(in_tx_observations), f"All get_events invocations must occur inside transaction: {in_tx_observations}"
        assert not kernel._storage.in_transaction, "Transaction must be committed and closed after rebuild"
    finally:
        kernel.close()


def test_rebuild_projection_multiprocess_concurrency_single_winner(tmp_path: Path):
    """Multi-process OCC stress: 4 separate OS processes contending on same task version."""
    db_path = str(tmp_path / "kernel_mp.sqlite3")
    init_kernel = TaskKernel(db_path)
    task_id = "test-mp-rebuild"
    _setup_task_in_planning(init_kernel, task_id)
    base_task = init_kernel.get_task(task_id)
    base_version = int(base_task["version"])
    init_kernel.close()

    num_processes = 4
    result_queue = multiprocessing.Queue()
    processes = [
        multiprocessing.Process(
            target=_mp_rebuild_worker,
            args=(db_path, task_id, base_version, result_queue),
        )
        for _ in range(num_processes)
    ]

    for p in processes:
        p.start()
    for p in processes:
        p.join(timeout=15)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get_nowait())

    assert len(results) == num_processes, f"Expected {num_processes} results, got {results}"
    successes = results.count("SUCCESS")
    occ_errors = results.count("OCC_ERROR")
    assert successes == 1, f"Expected exactly 1 SUCCESS across processes, got {successes} (results={results})"
    assert occ_errors == num_processes - 1, f"Expected {num_processes - 1} OCC_ERROR, got {occ_errors}"

    final_kernel = TaskKernel(db_path)
    try:
        final_task = final_kernel.get_task(task_id)
        assert int(final_task["version"]) == base_version + 1
    finally:
        final_kernel.close()


def test_rebuild_projection_lease_lifecycle_and_terminal_states(tmp_path: Path):
    """Verify lease preservation during active states, lease clearing upon release/terminal, and negative version rejection."""
    kernel = TaskKernel(tmp_path / "kernel_lease.sqlite3")
    try:
        task_id = "test-rebuild-lease-lifecycle"
        kernel.create_task(task_id, "owner-lease", "goal", "R1")
        kernel.transition(task_id, "PLANNING", actor="setup")
        kernel.transition(task_id, "READY", actor="setup")
        kernel.transition(task_id, "QUEUED", actor="setup")

        # 1. Claim lease -> LEASED state
        lease = kernel.claim(task_id, "worker-alpha")
        t_leased = kernel.get_task(task_id)
        assert t_leased["state"] == "LEASED"
        assert t_leased["active_lease_id"] == lease.lease_id

        # Rebuild while LEASED: active lease must be preserved
        rebuilt_leased = kernel.rebuild_projection(task_id)
        assert rebuilt_leased["state"] == "LEASED"
        assert rebuilt_leased["active_lease_id"] == lease.lease_id
        assert rebuilt_leased["active_fencing_token"] == lease.fencing_token
        assert int(rebuilt_leased["version"]) == int(t_leased["version"]) + 1

        # 2. Transition to RUNNING: lease preserved
        kernel.transition(task_id, "RUNNING", actor="worker-alpha", lease_id=lease.lease_id)
        t_running = kernel.get_task(task_id)
        assert t_running["state"] == "RUNNING"
        rebuilt_running = kernel.rebuild_projection(task_id)
        assert rebuilt_running["state"] == "RUNNING"
        assert rebuilt_running["active_lease_id"] == lease.lease_id
        assert rebuilt_running["active_fencing_token"] == lease.fencing_token

        # 3. Release lease: active_lease_id and active_fencing_token cleared
        kernel.release(task_id, lease.lease_id)
        rebuilt_released = kernel.rebuild_projection(task_id)
        assert rebuilt_released["active_lease_id"] is None
        assert rebuilt_released["active_fencing_token"] == 0

        # 4. Terminal state CANCELLED: admin cancellation via system authority
        kernel._system_authority = True
        kernel.transition(task_id, "CANCELLED", actor="admin")
        rebuilt_cancelled = kernel.rebuild_projection(task_id)
        assert rebuilt_cancelled["state"] == "CANCELLED"
        assert rebuilt_cancelled["active_lease_id"] is None
        assert rebuilt_cancelled["active_fencing_token"] == 0
        kernel._system_authority = False

        # 5. Negative expected_version: fail closed with OptimisticLockError
        with pytest.raises(OptimisticLockError) as exc_info:
            kernel.rebuild_projection(task_id, expected_version=-1)
        assert exc_info.value.table == "tasks"
        assert exc_info.value.entity_id == task_id
        assert exc_info.value.expected_version == -1
    finally:
        kernel.close()



