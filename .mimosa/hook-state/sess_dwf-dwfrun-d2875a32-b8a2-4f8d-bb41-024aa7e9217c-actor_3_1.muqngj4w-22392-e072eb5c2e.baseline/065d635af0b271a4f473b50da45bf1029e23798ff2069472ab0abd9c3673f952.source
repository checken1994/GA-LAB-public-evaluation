#!/usr/bin/env python3
"""
tools/probes/probe_gap03_04_blind_overwrite.py
FA-09 Exploit Mandate: Probe demonstrating GAP-03 (Blind Version Increment)
and GAP-04 (rebuild_projection Transaction Boundary) in TaskKernel.

GAP-03: Blind Version Increment (CRITICAL)
  `UPDATE tasks SET state=?,version=version+1,... WHERE task_id=?`
  lacks `AND version=?`. Any concurrent rebuild or stale rebuild blindly
  increments the version and clobbers state without detecting optimistic lock conflict.

GAP-04: rebuild_projection Transaction Boundary (HIGH)
  `verify_journal()` and `get_events()` run outside `self._begin()`,
  allowing stale reads to be committed into projection.

Probe Behavior:
  - Buggy Code: OCC invariant is violated (stale update succeeds without OptimisticLockError,
    or SQL query lacks AND version=?). -> Exits 1 (RED).
  - Fixed Code: OptimisticLockError is raised on stale rebuild, SQL query enforces OCC,
    and entire method is within transaction boundary. -> Exits 0 (GREEN).
"""
import inspect
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scp.task_kernel import (
    TaskKernel,
    OptimisticLockError,
    KernelError,
)


def print_banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_gap03_stale_expected_version_reproduction(db_path: str) -> None:
    """
    Subtest 1: Reproduce GAP-03 using expected_version OCC invariant.
    If a caller requests a rebuild with an expected_version, but the task has
    already progressed to a higher version, rebuild_projection MUST raise
    OptimisticLockError.
    On BUGGY code: rebuild_projection ignores version or blindly updates,
    causing state overwrite and version jumping without raising OptimisticLockError.
    """
    print("\n[PROBE SUBTEST 1] Testing stale version OCC rejection...")
    kernel = TaskKernel(db_path)
    try:
        task_id = "probe-task-gap03-1"
        kernel.create_task(task_id, "owner-probe", "probe goal", "R1")
        # Task created: version = 1, state = CREATED
        t1 = kernel.get_task(task_id)
        v1 = int(t1["version"])
        print(f"  Task created: id={task_id}, version={v1}, state={t1['state']}")

        # Legitimate state transition: CREATED -> PLANNING
        kernel.transition(task_id, "PLANNING", actor="worker-probe")
        t2 = kernel.get_task(task_id)
        v2 = int(t2["version"])
        print(f"  Task transitioned: version={v2}, state={t2['state']}")
        assert v2 > v1, "Version should have incremented on transition"

        # Now simulate a stale worker attempting rebuild_projection with stale expected_version=v1
        print(f"  Attempting rebuild_projection with stale expected_version={v1} (current={v2})...")
        try:
            kernel.rebuild_projection(task_id, expected_version=v1)
        except OptimisticLockError as exc:
            print(f"  [PASS] OptimisticLockError correctly raised: {exc}")
            return
        except TypeError as exc:
            # Buggy code does not even accept expected_version
            print(f"  [FAIL] rebuild_projection does not accept expected_version: {exc}")
            raise AssertionError(
                "GAP-03 VULNERABILITY CONFIRMED: rebuild_projection does not support "
                "or enforce expected_version OCC check!"
            ) from exc

        # If it returned without error:
        t_after = kernel.get_task(task_id)
        raise AssertionError(
            f"GAP-03 VULNERABILITY CONFIRMED: rebuild_projection succeeded with stale version {v1}! "
            f"Blind overwrite occurred: version jumped to {t_after['version']}!"
        )
    finally:
        kernel.close()


def test_gap03_concurrent_clobber_reproduction(db_path: str) -> None:
    """
    Subtest 2: Reproduce GAP-03 concurrent race condition with real parallel threads.
    Two threads race to rebuild projection based on the same base version.
    Only one must succeed; the other must fail with OptimisticLockError.
    On BUGGY code: both succeed (or fail due to lack of expected_version support),
    violating OCC invariants.
    """
    print("\n[PROBE SUBTEST 2] Testing concurrent rebuild OCC enforcement with parallel threads...")
    kernel = TaskKernel(db_path)
    try:
        task_id = "probe-task-gap03-2"
        kernel.create_task(task_id, "owner-probe", "probe goal", "R1")
        kernel.transition(task_id, "PLANNING", actor="worker-probe")
        t_base = kernel.get_task(task_id)
        base_version = int(t_base["version"])
        print(f"  Base task version: {base_version}")
    finally:
        kernel.close()

    results = []
    barrier = threading.Barrier(2)

    def worker_thread(name: str) -> None:
        k = TaskKernel(db_path)
        try:
            barrier.wait(timeout=5)
            k.rebuild_projection(task_id, expected_version=base_version)
            results.append((name, "SUCCESS"))
        except OptimisticLockError:
            results.append((name, "OCC_ERROR"))
        except TypeError as exc:
            results.append((name, f"TYPE_ERROR: {exc}"))
        except Exception as exc:
            results.append((name, f"ERROR: {type(exc).__name__}: {exc}"))
        finally:
            k.close()

    t1 = threading.Thread(target=worker_thread, args=("Worker-A",))
    t2 = threading.Thread(target=worker_thread, args=("Worker-B",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    print(f"  Parallel results: {results}")
    for name, status in results:
        if status.startswith("TYPE_ERROR"):
            raise AssertionError(f"GAP-03 VULNERABILITY CONFIRMED: {status}")

    outcomes = [res[1] for res in results]
    if outcomes.count("SUCCESS") > 1:
        raise AssertionError(
            f"GAP-03 VULNERABILITY CONFIRMED: Both concurrent workers succeeded! "
            f"Blind overwrite occurred on version {base_version}: outcomes={outcomes}"
        )

    if "SUCCESS" not in outcomes:
        raise AssertionError(f"Neither worker succeeded: outcomes={outcomes}")

    if "OCC_ERROR" not in outcomes:
        raise AssertionError(
            f"GAP-03 VULNERABILITY CONFIRMED: Losing worker was not rejected with OptimisticLockError! "
            f"outcomes={outcomes}"
        )

    print("  [PASS] Concurrency race resolved correctly: exactly 1 SUCCESS and 1 OCC_ERROR")


def test_gap04_transaction_boundary_and_sql_structure() -> None:
    """
    Subtest 3: Verify GAP-04 transaction boundary and SQL OCC clause.
    Inspects TaskKernel.rebuild_projection implementation to ensure:
    1. `UPDATE tasks ... WHERE task_id=? AND version=?` is present (GAP-03).
    2. `self._begin()` wraps the entire method, specifically before `verify_journal`
       and `get_events` (GAP-04).
    """
    print("\n[PROBE SUBTEST 3] Inspecting SQL and Transaction Boundary...")
    from scp.task_kernel_parts.taskkernel import TaskKernel as InternalTaskKernel

    source = inspect.getsource(InternalTaskKernel.rebuild_projection)
    lines = [line.strip() for line in source.splitlines()]

    # Check 1: SQL must have AND version=?
    has_occ_sql = any("WHERE task_id=? AND version=?" in line for line in lines)
    if not has_occ_sql:
        raise AssertionError(
            "GAP-03 VULNERABILITY CONFIRMED: rebuild_projection SQL lacks 'WHERE task_id=? AND version=?'"
        )
    print("  [PASS] SQL contains 'WHERE task_id=? AND version=?'")

    # Check 2: Transaction boundary must wrap verify_journal and get_events
    begin_idx = -1
    verify_idx = -1
    get_events_idx = -1
    for i, line in enumerate(lines):
        if "self._begin()" in line and begin_idx == -1:
            begin_idx = i
        if "self.verify_journal(" in line and verify_idx == -1:
            verify_idx = i
        if "self.get_events(" in line and get_events_idx == -1:
            get_events_idx = i

    if begin_idx == -1:
        raise AssertionError("GAP-04 VULNERABILITY: self._begin() not found in rebuild_projection")

    if verify_idx != -1 and begin_idx > verify_idx:
        raise AssertionError(
            f"GAP-04 VULNERABILITY CONFIRMED: verify_journal (line {verify_idx}) runs OUTSIDE "
            f"transaction boundary (self._begin() at line {begin_idx})!"
        )

    if get_events_idx != -1 and begin_idx > get_events_idx:
        raise AssertionError(
            f"GAP-04 VULNERABILITY CONFIRMED: get_events (line {get_events_idx}) runs OUTSIDE "
            f"transaction boundary (self._begin() at line {begin_idx})!"
        )

    print("  [PASS] Transaction boundary wraps verify_journal and get_events")


def test_gap04_runtime_transaction_rollback(db_path: str) -> None:
    """
    Subtest 4: Runtime verification of GAP-04 transaction rollback and active boundary.
    Verifies that:
    1. verify_journal and get_events execute strictly INSIDE the active transaction boundary
       (self._storage.in_transaction is True).
       On BUGGY code: get_events runs before self._begin(), so in_transaction is False -> FAILS RED.
    2. When journal integrity verification fails, the transaction is cleanly rolled back:
       - Tasks table projection is completely untouched.
       - Connection transaction slot is released (in_transaction is False).
       - Subsequent operations succeed cleanly without lock exhaustion.
    """
    print("\n[PROBE SUBTEST 4] Testing runtime transaction boundary and rollback...")
    kernel = TaskKernel(db_path)
    try:
        task_id = "probe-task-gap04-rollback"
        kernel.create_task(task_id, "owner-probe", "probe rollback goal", "R1")
        kernel.transition(task_id, "PLANNING", actor="worker-probe")
        t_before = kernel.get_task(task_id)
        v_before = int(t_before["version"])

        # Dynamically hook get_events to track transaction state
        orig_get_events = kernel.get_events
        observed_in_tx = []

        def tracked_get_events(tid: str):
            observed_in_tx.append(bool(kernel._storage.in_transaction))
            return orig_get_events(tid)

        kernel.get_events = tracked_get_events

        # Corrupt event hash directly in DB
        kernel.conn.execute(
            "UPDATE events SET event_hash='tampered_hash' WHERE task_id=? AND seq=1",
            (task_id,),
        )

        try:
            kernel.rebuild_projection(task_id)
            raise AssertionError("GAP-04 VULNERABILITY: rebuild_projection succeeded on corrupt journal!")
        except KernelError as exc:
            if "journal integrity invalid" not in str(exc):
                raise AssertionError(f"Unexpected KernelError message: {exc}")
            print(f"  [PASS] KernelError properly raised: {exc}")

        # Invariant 1: get_events must have run inside transaction
        if not observed_in_tx:
            raise AssertionError("GAP-04 VULNERABILITY: get_events was never called during rebuild!")
        if not all(observed_in_tx):
            raise AssertionError(
                f"GAP-04 VULNERABILITY CONFIRMED: get_events executed outside active "
                f"transaction boundary! Observations: {observed_in_tx}"
            )
        print(f"  [PASS] get_events executed inside active transaction: {observed_in_tx}")

        # Invariant 2: Transaction rolled back (storage not in transaction)
        if kernel._storage.in_transaction:
            raise AssertionError("GAP-04 VULNERABILITY: storage remained in transaction after error (lock leaked)!")

        # Invariant 3: Projection must remain intact with unchanged version
        t_after = kernel.get_task(task_id)
        if int(t_after["version"]) != v_before:
            raise AssertionError(
                f"GAP-04 VULNERABILITY: version changed from {v_before} to {t_after['version']} despite error!"
            )
        print("  [PASS] Task projection untouched and transaction cleanly rolled back")

        # Invariant 4: Storage connection remains clean for subsequent transactions
        kernel.create_task("probe-after-rollback", "owner", "post rollback test", "R0")
        t_sub = kernel.get_task("probe-after-rollback")
        assert t_sub["state"] == "CREATED"
        print("  [PASS] Storage connection healthy and reusable for subsequent transactions")
    finally:
        kernel.close()


def main() -> int:
    print_banner("FA-09 EXPLOIT MANDATE PROBE: GAP-03 + GAP-04")
    temp_dir = tempfile.mkdtemp(prefix="probe_gap03_04_")
    db_path = os.path.join(temp_dir, "probe_kernel.sqlite3")

    try:
        test_gap03_stale_expected_version_reproduction(db_path)
        test_gap03_concurrent_clobber_reproduction(db_path)
        test_gap04_transaction_boundary_and_sql_structure()
        test_gap04_runtime_transaction_rollback(db_path)
        print("\n" + "=" * 70)
        print("  ALL OCC AND TRANSACTION INVARIANTS SATISFIED (GREEN)")
        print("=" * 70)
        return 0
    except AssertionError as e:
        print("\n" + "=" * 70)
        print(f"  PROBE FAILED (RED): {e}")
        print("=" * 70)
        return 1
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 2
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
