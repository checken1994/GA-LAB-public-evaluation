"""E2E optimistic-lock race probe against a TaskKernel SQLite database.

[A11 H-01 fix 2026-10-01] This probe used to DELETE/INSERT directly inside
``data/ask_task_kernel.sqlite3`` — the LIVE deployment database. That is a
destructive operation on production state (R3 destructive), so the default
behavior is now:

1. Copy the source DB (plus -wal/-shm sidecars, checkpointed into the copy)
   into a fresh temp directory and run the race on the COPY — zero writes to
   the repository ``data/`` tree.
2. Writing to the live DB is only possible with the explicit flag
   ``--i-know-this-is-live``, which must be typed by the operator. Without it
   the probe refuses to touch repo ``data/`` (fail-closed).
"""

import argparse
import shutil
import sqlite3
import sys
import tempfile
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from scp.task_kernel import TaskKernel, OptimisticLockError

LIVE_FLAG = "--i-know-this-is-live"


def _copy_db_snapshot(src: Path, dest_dir: Path) -> Path:
    """Copy a SQLite DB file into dest_dir, folding WAL/SHM sidecars in.

    Copying a live WAL-mode database file byte-for-byte can lose committed
    transactions still sitting in the -wal file, so we open the source
    read-only and use SQLite's backup API to produce a consistent snapshot.
    """
    dest = dest_dir / src.name
    src_conn = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True)
    try:
        dest_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()
    return dest


def run_real_db_test(live: bool = False) -> None:
    src_db = PROJECT_ROOT / 'data' / 'ask_task_kernel.sqlite3'
    if not src_db.exists():
        print(f"FAILED: Real DB not found at {src_db}")
        sys.exit(1)

    if live:
        db_path = src_db
        print(f"WARNING: LIVE mode explicitly requested — writing to {db_path}")
    else:
        temp_dir = Path(tempfile.mkdtemp(prefix="scp_e2e_db_probe_"))
        db_path = _copy_db_snapshot(src_db, temp_dir)
        print(f"SUCCESS: Copied DB snapshot to temp: {db_path} (source untouched)")

    print(f"SUCCESS: Connected to database: {db_path}")
    kernel = TaskKernel(str(db_path))

    task_id = 'e2e-live-race-test'
    try:
        # Kernel connections run with isolation_level=None (autocommit, per
        # kernel_storage.py:132) — the old explicit kernel._commit() after DML
        # raised "cannot commit - no transaction is active" on current kernels.
        kernel.conn.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))
        kernel.conn.execute("DELETE FROM events WHERE task_id=?", (task_id,))

        kernel.create_task(task_id, 'admin', 'E2E Race Test', 'R0')
        kernel.transition(task_id, 'PLANNING', actor='system')

        base_task = kernel.get_task(task_id)
        base_version = int(base_task['version'])
        print(f"SUCCESS: Created task in DB: id={task_id}, version={base_version}, state={base_task['state']}")

        results = []
        barrier = threading.Barrier(2)

        def worker_thread(name: str) -> None:
            k = TaskKernel(str(db_path))
            try:
                barrier.wait(timeout=5)
                k.rebuild_projection(task_id, expected_version=base_version)
                results.append((name, "SUCCESS"))
            except OptimisticLockError:
                results.append((name, "OCC_ERROR (BLOCKED BY FIX!)"))
            except Exception as e:
                results.append((name, f"ERROR: {e}"))
            finally:
                k.close()

        print("WARNING: Launching 2 concurrent hackers into the TaskKernel...")
        t1 = threading.Thread(target=worker_thread, args=("Hacker_A",))
        t2 = threading.Thread(target=worker_thread, args=("Hacker_B",))
        t1.start(); t2.start()
        t1.join(); t2.join()

        print(f"RESULTS: {results}")

    finally:
        kernel.close()
        if not live:
            try:
                shutil.rmtree(db_path.parent, ignore_errors=True)
            except Exception:
                pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="TaskKernel optimistic-lock race probe (temp-DB by default)")
    parser.add_argument(
        "--" + LIVE_FLAG.lstrip('-').replace('-', '_'),
        dest="i_know_this_is_live",
        action="store_true",
        help="Explicitly write to the LIVE data/ask_task_kernel.sqlite3 (destructive). Default: run on a temp copy.",
    )
    args = parser.parse_args()
    run_real_db_test(live=args.i_know_this_is_live)
