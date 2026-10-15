#!/usr/bin/env python3
"""Adversarial stress test harness for Milestone 1 (P0: Concurrency & Persistence).

Tests:
1. ChatMemoryStore:
   - Concurrent appends across 12 threads (1,200 total records).
   - Simultaneous prunes with forced atomic replacement (tempfile + os.replace) across 3 pruner threads.
   - Concurrent readers across 3 reader threads.
   - Verification: 0 WinError 32 / PermissionError, 0 dropped entries, all hashes valid.
2. TraceLedger:
   - Concurrent appends across 16 threads (1,600 total records).
   - Concurrent readers querying get_trace().
   - Verification: Sequence continuity 1..N, unbroken SHA-256 hash chains, 0 errors.
3. db_manager:
   - Concurrent inserts and queries across 16 threads (8 writers, 4 query_all, 4 query_one).
   - Concurrent WAL checkpoints while writers and readers are active.
   - Verification: 0 cursor corruption, 0 transaction errors, 100% row count consistency, PRAGMA integrity_check ok.
"""
from __future__ import annotations

import os
import sys
import time
import json
import uuid
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any

# Ensure project root is in path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scp.core.chat_memory_store import ChatMemoryStore
from scp.trace_ledger import TraceLedger, _hash as trace_hash
from scp.core.db_manager import db_exec, db_query_all, db_query_one, checkpoint_wal, _path_conns


def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_chat_memory_store_stress(test_dir: Path) -> dict[str, Any]:
    print_banner("TEST 1: ChatMemoryStore Concurrent Append & Simultaneous Prune (Windows Stress)")

    chat_path = test_dir / "chat_stress.jsonl"
    store = ChatMemoryStore(chat_path)

    NUM_APPEND_THREADS = 12
    APPENDS_PER_THREAD = 100
    TOTAL_APPENDS = NUM_APPEND_THREADS * APPENDS_PER_THREAD

    NUM_PRUNE_THREADS = 3
    NUM_READ_THREADS = 3

    # Force pruning threshold to 0 so every single _prune_if_needed() executes
    # tempfile.mkstemp + os.replace on Windows under heavy concurrency
    original_prune = store._prune_if_needed

    prune_count = 0
    prune_lock = threading.Lock()

    def forced_prune(self_store: ChatMemoryStore):
        nonlocal prune_count
        with self_store._file_lock.acquire():
            try:
                if not self_store.path.exists():
                    return
                cutoff = time.time() - self_store.RETENTION_SECONDS
                rows: list[dict[str, Any]] = []
                for line in self_store.path.read_text(encoding="utf-8", errors="replace").splitlines():
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if float(row.get("ts", 0)) >= cutoff:
                        rows.append(row)
                rows = rows[-self_store.MAX_RECORDS :]
                fd, temp_name = tempfile.mkstemp(prefix="chat-stress-", suffix=".jsonl", dir=str(self_store.path.parent))
                try:
                    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                        for row in rows:
                            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temp_name, self_store.path)
                    with prune_lock:
                        prune_count += 1
                finally:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
            except Exception as exc:
                print(f"[ERROR in forced_prune]: {type(exc).__name__}: {exc}")
                raise

    # Patch store to use forced_prune with os.replace on every prune attempt
    store._prune_if_needed = lambda: forced_prune(store)

    appended_entries: list[str] = []
    appended_lock = threading.Lock()
    errors: list[Exception] = []
    stop_background = threading.Event()

    def append_worker(wid: int):
        try:
            # Each worker can use its own instance of ChatMemoryStore pointing to the same file
            w_store = ChatMemoryStore(chat_path)
            w_store._prune_if_needed = lambda: forced_prune(w_store)

            for i in range(APPENDS_PER_THREAD):
                unique_content = f"worker_{wid}_msg_{i}_{uuid.uuid4().hex}"
                ok = w_store.append(
                    session_id="stress_session",
                    role="user",
                    content=unique_content,
                    metadata={"run_id": f"run_{wid}_{i}"},
                )
                if not ok:
                    raise RuntimeError(f"store.append returned False for {unique_content}")
                with appended_lock:
                    appended_entries.append(unique_content)
        except Exception as exc:
            errors.append(exc)
            print(f"[EXCEPTION in append_worker-{wid}]: {type(exc).__name__}: {exc}")

    def prune_worker(pid: int):
        p_store = ChatMemoryStore(chat_path)
        while not stop_background.is_set():
            try:
                forced_prune(p_store)
                time.sleep(0.005)
            except Exception as exc:
                errors.append(exc)
                print(f"[EXCEPTION in prune_worker-{pid}]: {type(exc).__name__}: {exc}")
                break

    def read_worker(rid: int):
        r_store = ChatMemoryStore(chat_path)
        while not stop_background.is_set():
            try:
                records = r_store.load("stress_session", limit=50)
                # Load succeeded, quick yield
                time.sleep(0.005)
            except Exception as exc:
                errors.append(exc)
                print(f"[EXCEPTION in read_worker-{rid}]: {type(exc).__name__}: {exc}")
                break

    print(f"Launching {NUM_APPEND_THREADS} appenders, {NUM_PRUNE_THREADS} pruners, {NUM_READ_THREADS} readers...")
    start_time = time.time()

    prune_threads = [threading.Thread(target=prune_worker, args=(i,), name=f"Pruner-{i}") for i in range(NUM_PRUNE_THREADS)]
    read_threads = [threading.Thread(target=read_worker, args=(i,), name=f"Reader-{i}") for i in range(NUM_READ_THREADS)]
    append_threads = [threading.Thread(target=append_worker, args=(i,), name=f"Appender-{i}") for i in range(NUM_APPEND_THREADS)]

    for t in prune_threads + read_threads:
        t.start()

    for t in append_threads:
        t.start()

    for t in append_threads:
        t.join()

    # Let background pruners and readers run for a moment longer
    time.sleep(0.1)
    stop_background.set()

    for t in prune_threads + read_threads:
        t.join(timeout=5.0)

    duration = time.time() - start_time
    print(f"All threads finished in {duration:.2f}s. Forced atomic prune replacements executed: {prune_count}")

    # Validation: Check errors
    winerror_32_count = sum(1 for e in errors if "WinError 32" in str(e) or getattr(e, "winerror", None) == 32)
    permission_error_count = sum(1 for e in errors if isinstance(e, PermissionError))

    print(f"Total exceptions caught: {len(errors)}")
    print(f"WinError 32 count: {winerror_32_count}")
    print(f"PermissionError count: {permission_error_count}")

    # Validation: Read entire file and verify 0 dropped entries
    persisted_lines = chat_path.read_text(encoding="utf-8").splitlines()
    persisted_contents = set()
    corrupted_lines = 0
    hash_mismatches = 0

    for line in persisted_lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            persisted_contents.add(record.get("content"))
            # Validate hash
            rec_copy = dict(record)
            rec_hash = rec_copy.pop("record_hash", None)
            expected_hash = store._record_hash(rec_copy)
            if rec_hash != expected_hash:
                hash_mismatches += 1
        except Exception:
            corrupted_lines += 1

    expected_set = set(appended_entries)
    missing_entries = expected_set - persisted_contents

    print(f"Appended entries: {len(appended_entries)} (expected {TOTAL_APPENDS})")
    print(f"Persisted unique entries: {len(persisted_contents)}")
    print(f"Missing (dropped) entries: {len(missing_entries)}")
    print(f"Corrupted lines: {corrupted_lines}")
    print(f"Hash mismatches: {hash_mismatches}")

    success = (
        len(errors) == 0
        and winerror_32_count == 0
        and permission_error_count == 0
        and len(missing_entries) == 0
        and corrupted_lines == 0
        and hash_mismatches == 0
        and len(appended_entries) == TOTAL_APPENDS
    )

    result = {
        "success": success,
        "total_appends": TOTAL_APPENDS,
        "persisted_entries": len(persisted_contents),
        "missing_entries": len(missing_entries),
        "prune_replacements": prune_count,
        "winerror_32_count": winerror_32_count,
        "errors_count": len(errors),
        "duration_s": duration,
    }

    if success:
        print(">>> [PASS] ChatMemoryStore stress test PASSED: 0 WinError 32 crashes, 0 dropped entries! <<<")
    else:
        print(">>> [FAIL] ChatMemoryStore stress test FAILED! <<<")

    return result


def test_trace_ledger_stress(test_dir: Path) -> dict[str, Any]:
    print_banner("TEST 2: TraceLedger Concurrent Appends & Hash-Chain Continuity")

    trace_path = test_dir / "trace_stress.jsonl"
    NUM_THREADS = 16
    APPENDS_PER_THREAD = 100
    TOTAL_APPENDS = NUM_THREADS * APPENDS_PER_THREAD

    NUM_READER_THREADS = 4
    stop_readers = threading.Event()
    errors: list[Exception] = []

    def append_worker(wid: int):
        try:
            ledger = TraceLedger(trace_path)
            for i in range(APPENDS_PER_THREAD):
                entry = ledger.append(
                    worker_id=wid,
                    step=i,
                    payload=f"data_{wid}_{i}_{uuid.uuid4().hex[:8]}",
                    secret_token=f"Bearer super_secret_token_{wid}_{i}",
                )
                if not entry or "seq" not in entry:
                    raise RuntimeError(f"Invalid entry returned from append: {entry}")
        except Exception as exc:
            errors.append(exc)
            print(f"[EXCEPTION in trace worker-{wid}]: {type(exc).__name__}: {exc}")

    def reader_worker(rid: int):
        ledger = TraceLedger(trace_path)
        while not stop_readers.is_set():
            try:
                # Intermittently inspect trace entries
                ledger.get_trace(f"non_existent_{rid}")
                time.sleep(0.005)
            except Exception as exc:
                errors.append(exc)
                print(f"[EXCEPTION in trace reader-{rid}]: {type(exc).__name__}: {exc}")
                break

    print(f"Launching {NUM_THREADS} appenders ({TOTAL_APPENDS} entries total) + {NUM_READER_THREADS} concurrent readers...")
    start_time = time.time()

    reader_threads = [threading.Thread(target=reader_worker, args=(i,), name=f"TraceReader-{i}") for i in range(NUM_READER_THREADS)]
    append_threads = [threading.Thread(target=append_worker, args=(i,), name=f"TraceAppender-{i}") for i in range(NUM_THREADS)]

    for t in reader_threads:
        t.start()
    for t in append_threads:
        t.start()

    for t in append_threads:
        t.join()

    stop_readers.set()
    for t in reader_threads:
        t.join(timeout=5.0)

    duration = time.time() - start_time
    print(f"All trace threads completed in {duration:.2f}s")

    # Verify ledger using official verify() method
    test_ledger = TraceLedger(trace_path)
    verify_result = test_ledger.verify()

    entries_count = verify_result.get("entries", 0)
    hash_chain_valid = verify_result.get("hash_chain_valid", False)
    ledger_errors = verify_result.get("errors", [])

    print(f"Total entries in ledger: {entries_count} (expected {TOTAL_APPENDS})")
    print(f"Hash chain valid: {hash_chain_valid}")
    print(f"Ledger verify errors count: {len(ledger_errors)}")

    # Deep adversarial verification: check every line directly
    raw_lines = trace_path.read_text(encoding="utf-8").splitlines()
    seq_numbers = []
    prev_hash = None
    chain_breaks = 0
    hash_corruptions = 0
    unredacted_secrets = 0

    for i, line in enumerate(raw_lines, 1):
        if not line.strip():
            continue
        data = json.loads(line)
        seq = data.get("seq")
        seq_numbers.append(seq)
        if seq != i:
            chain_breaks += 1
        if data.get("prev_hash") != prev_hash:
            chain_breaks += 1
        # Re-hash
        body = {k: v for k, v in data.items() if k != "hash"}
        if trace_hash(body) != data.get("hash"):
            hash_corruptions += 1
        # Secret check
        raw_str = json.dumps(data)
        if "super_secret_token" in raw_str:
            unredacted_secrets += 1
        prev_hash = data.get("hash")

    expected_seq = list(range(1, TOTAL_APPENDS + 1))
    sequence_continuous = (seq_numbers == expected_seq)

    print(f"Sequence continuity 1..{TOTAL_APPENDS}: {sequence_continuous}")
    print(f"Chain breaks: {chain_breaks}")
    print(f"Hash corruptions: {hash_corruptions}")
    print(f"Unredacted secrets leaked: {unredacted_secrets}")

    success = (
        len(errors) == 0
        and entries_count == TOTAL_APPENDS
        and hash_chain_valid is True
        and len(ledger_errors) == 0
        and sequence_continuous
        and chain_breaks == 0
        and hash_corruptions == 0
        and unredacted_secrets == 0
    )

    result = {
        "success": success,
        "total_appends": TOTAL_APPENDS,
        "entries_count": entries_count,
        "hash_chain_valid": hash_chain_valid,
        "sequence_continuous": sequence_continuous,
        "chain_breaks": chain_breaks,
        "hash_corruptions": hash_corruptions,
        "unredacted_secrets": unredacted_secrets,
        "errors_count": len(errors),
        "duration_s": duration,
    }

    if success:
        print(">>> [PASS] TraceLedger stress test PASSED: unbroken sequence 1..N and valid hash chains! <<<")
    else:
        print(">>> [FAIL] TraceLedger stress test FAILED! <<<")

    return result


def test_db_manager_stress(test_dir: Path) -> dict[str, Any]:
    print_banner("TEST 3: db_manager Multi-Threaded SQLite Stress (Concurrent Reads/Writes/WAL)")

    db_path = str(test_dir / "stress_db.sqlite")

    # Initialize table
    db_exec(
        """
        CREATE TABLE stress_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER,
            item_seq INTEGER,
            payload TEXT,
            created_at REAL
        )
        """,
        db_path=db_path,
    )

    NUM_WRITERS = 8
    INSERTS_PER_WRITER = 100
    TOTAL_INSERTS = NUM_WRITERS * INSERTS_PER_WRITER

    NUM_QUERY_ALL_THREADS = 4
    NUM_QUERY_ONE_THREADS = 4
    stop_readers = threading.Event()

    errors: list[Exception] = []
    programming_errors = 0
    operational_errors = 0

    def writer_worker(wid: int):
        nonlocal programming_errors, operational_errors
        try:
            for i in range(INSERTS_PER_WRITER):
                payload = f"w_{wid}_item_{i}_{uuid.uuid4().hex}"
                db_exec(
                    "INSERT INTO stress_records (worker_id, item_seq, payload, created_at) VALUES (?, ?, ?, ?)",
                    (wid, i, payload, time.time()),
                    db_path=db_path,
                )
                if i % 25 == 0:
                    time.sleep(0.001)
        except Exception as exc:
            errors.append(exc)
            err_name = type(exc).__name__
            if "ProgrammingError" in err_name:
                programming_errors += 1
            if "OperationalError" in err_name:
                operational_errors += 1
            print(f"[EXCEPTION in DB writer-{wid}]: {err_name}: {exc}")

    def query_all_worker(qid: int):
        nonlocal programming_errors, operational_errors
        while not stop_readers.is_set():
            try:
                rows = db_query_all("SELECT * FROM stress_records ORDER BY id DESC LIMIT 20", db_path=db_path)
                assert isinstance(rows, list)
                time.sleep(0.002)
            except Exception as exc:
                errors.append(exc)
                err_name = type(exc).__name__
                if "ProgrammingError" in err_name:
                    programming_errors += 1
                if "OperationalError" in err_name:
                    operational_errors += 1
                print(f"[EXCEPTION in DB query_all-{qid}]: {err_name}: {exc}")
                break

    def query_one_worker(qid: int):
        nonlocal programming_errors, operational_errors
        while not stop_readers.is_set():
            try:
                row = db_query_one("SELECT COUNT(*) as count, MAX(id) as max_id FROM stress_records", db_path=db_path)
                assert row is not None
                time.sleep(0.002)
            except Exception as exc:
                errors.append(exc)
                err_name = type(exc).__name__
                if "ProgrammingError" in err_name:
                    programming_errors += 1
                if "OperationalError" in err_name:
                    operational_errors += 1
                print(f"[EXCEPTION in DB query_one-{qid}]: {err_name}: {exc}")
                break

    def wal_checkpoint_worker():
        while not stop_readers.is_set():
            try:
                checkpoint_wal()
                time.sleep(0.02)
            except Exception as exc:
                errors.append(exc)
                print(f"[EXCEPTION in wal_checkpoint_worker]: {exc}")
                break

    print(f"Launching {NUM_WRITERS} writers ({TOTAL_INSERTS} inserts), {NUM_QUERY_ALL_THREADS} query_all, {NUM_QUERY_ONE_THREADS} query_one, + 1 WAL checkpoint worker...")
    start_time = time.time()

    writer_threads = [threading.Thread(target=writer_worker, args=(i,), name=f"DBWriter-{i}") for i in range(NUM_WRITERS)]
    qall_threads = [threading.Thread(target=query_all_worker, args=(i,), name=f"DBQAll-{i}") for i in range(NUM_QUERY_ALL_THREADS)]
    qone_threads = [threading.Thread(target=query_one_worker, args=(i,), name=f"DBQOne-{i}") for i in range(NUM_QUERY_ONE_THREADS)]
    wal_thread = threading.Thread(target=wal_checkpoint_worker, name="DBWal")

    for t in qall_threads + qone_threads + [wal_thread]:
        t.start()
    for t in writer_threads:
        t.start()

    for t in writer_threads:
        t.join()

    time.sleep(0.05)
    stop_readers.set()

    for t in qall_threads + qone_threads + [wal_thread]:
        t.join(timeout=5.0)

    duration = time.time() - start_time
    print(f"All DB threads completed in {duration:.2f}s")

    # Verification: Verify total row count
    final_count_row = db_query_one("SELECT COUNT(*) as total_rows FROM stress_records", db_path=db_path)
    final_count = final_count_row.get("total_rows", 0) if final_count_row else 0

    # Verification: SQLite PRAGMA integrity_check
    integrity_rows = db_query_all("PRAGMA integrity_check", db_path=db_path)
    integrity_ok = len(integrity_rows) > 0 and integrity_rows[0].get("integrity_check") == "ok"

    print(f"Total inserted rows in DB: {final_count} (expected {TOTAL_INSERTS})")
    print(f"PRAGMA integrity_check: {integrity_rows}")
    print(f"Cursor / ProgrammingError count: {programming_errors}")
    print(f"Transaction / OperationalError count: {operational_errors}")
    print(f"Total caught exceptions: {len(errors)}")

    # Part 3B: Global default connection (db_path=None)
    print("\n--- Part 3B: Global get_db() default connection concurrency test ---")
    global_table = f"stress_global_{uuid.uuid4().hex[:8]}"
    db_exec(f"CREATE TABLE {global_table} (id INTEGER PRIMARY KEY AUTOINCREMENT, t_id INT, val TEXT)")

    global_errors = []
    def global_writer(wid: int):
        try:
            for i in range(50):
                db_exec(f"INSERT INTO {global_table} (t_id, val) VALUES (?, ?)", (wid, f"val_{i}"))
        except Exception as exc:
            global_errors.append(exc)
            print(f"[EXCEPTION in global_writer-{wid}]: {exc}")

    def global_reader():
        while not stop_global.is_set():
            try:
                db_query_all(f"SELECT * FROM {global_table} LIMIT 10")
                db_query_one(f"SELECT COUNT(*) as c FROM {global_table}")
                time.sleep(0.001)
            except Exception as exc:
                global_errors.append(exc)
                print(f"[EXCEPTION in global_reader]: {exc}")
                break

    stop_global = threading.Event()
    g_writers = [threading.Thread(target=global_writer, args=(i,)) for i in range(8)]
    g_readers = [threading.Thread(target=global_reader) for _ in range(4)]

    for t in g_readers + g_writers:
        t.start()
    for t in g_writers:
        t.join()
    stop_global.set()
    for t in g_readers:
        t.join(timeout=3.0)

    g_count_row = db_query_one(f"SELECT COUNT(*) as c FROM {global_table}")
    g_count = g_count_row.get("c", 0) if g_count_row else 0
    # Clean up global table
    try:
        db_exec(f"DROP TABLE {global_table}")
    except Exception:
        pass

    print(f"Global connection inserts: {g_count} (expected 400), global errors: {len(global_errors)}")

    success = (
        len(errors) == 0
        and programming_errors == 0
        and operational_errors == 0
        and final_count == TOTAL_INSERTS
        and integrity_ok
        and len(global_errors) == 0
        and g_count == 400
    )

    result = {
        "success": success,
        "total_inserts": TOTAL_INSERTS,
        "final_count": final_count,
        "global_inserts": g_count,
        "global_errors": len(global_errors),
        "integrity_ok": integrity_ok,
        "programming_errors": programming_errors,
        "operational_errors": operational_errors,
        "errors_count": len(errors) + len(global_errors),
        "duration_s": duration,
    }

    if success:
        print(">>> [PASS] db_manager stress test PASSED: 0 cursor corruption, 0 transaction errors! <<<")
    else:
        print(">>> [FAIL] db_manager stress test FAILED! <<<")

    return result


def main():
    print_banner("STARTING ADVERSARIAL STRESS TEST SUITE (MILISTONE 1 / P0)")
    overall_start = time.time()

    temp_dir = Path(tempfile.mkdtemp(prefix="scp_challenger_p0_"))
    print(f"Working temporary directory: {temp_dir}")

    results = {}
    try:
        results["chat_memory_store"] = test_chat_memory_store_stress(temp_dir)
        results["trace_ledger"] = test_trace_ledger_stress(temp_dir)
        results["db_manager"] = test_db_manager_stress(temp_dir)
    finally:
        try:
            # Clean up connections in db_manager so files can be deleted on Windows
            for p, conn in list(_path_conns.items()):
                if str(temp_dir) in p:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    _path_conns.pop(p, None)
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"Cleanup warning: {e}")

    overall_duration = time.time() - overall_start
    print_banner("SUMMARY OF ADVERSARIAL STRESS TEST RESULTS")

    all_passed = all(r.get("success", False) for r in results.values())
    for name, res in results.items():
        status = "PASSED" if res.get("success") else "FAILED"
        print(f"  [{status}] {name}: duration={res.get('duration_s', 0):.2f}s, errors={res.get('errors_count', 0)}")

    print(f"\nTotal duration: {overall_duration:.2f}s")
    if all_passed:
        print("\n>>> OVERALL VERDICT: APPROVE (All stress tests passed with 0 crashes, 0 corruptions, 0 data loss) <<<\n")
        return 0
    else:
        print("\n>>> OVERALL VERDICT: REQUEST_CHANGES (Failures detected under concurrency) <<<\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
