"""High-concurrency and stress tests for persistence, ledger, and lock primitives.

Validates:
- ChatMemoryStore multi-threaded concurrent appends (10 threads x 30 records)
- ChatMemoryStore file lock re-entrancy and concurrent write during pruning
- TraceLedger multi-threaded concurrent appends (12 threads x 25 records)
- TraceLedger sequence continuity (1..N) and cryptographic hash chain verification
- TraceLedger backwards tail reader performance and consistency under concurrent writes
- SQLiteKernelStorage connection pool bounds (max_conns) and BEGIN IMMEDIATE concurrency
- db_manager concurrent readers and writers under read/write lock synchronization
- Zero file corruption, zero deadlocks, zero lost records under parallel stress
"""
import concurrent.futures
import contextvars
import json
import logging
import os
import tempfile
import time

from scp.core.chat_memory_store import ChatMemoryStore
from scp.core.db_manager import (
    checkpoint_wal,
    db_exec,
    db_query_all,
    db_query_one,
)
from scp.kernel_storage import SQLiteKernelStorage
from scp.trace_ledger import TraceLedger

logger = logging.getLogger(__name__)


def test_chat_memory_store_high_concurrency_append_and_load(tmp_path):
    store_file = tmp_path / "chat_stress.jsonl"
    store = ChatMemoryStore(store_file)
    session_id = "sess_stress_concurrency"

    append_errors = []
    load_errors = []

    def appender(thread_idx: int):
        for i in range(30):
            ok = store.append(
                session_id=session_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"thread {thread_idx} message {i}",
                metadata={"type": "chat", "run_id": f"run_{thread_idx}_{i}"},
            )
            if not ok:
                append_errors.append(f"append failed: thread {thread_idx} msg {i}")

    def reader():
        for _ in range(15):
            try:
                records = store.load(session_id, limit=50)
                for r in records:
                    assert "role" in r
                    assert "content" in r
            except Exception as exc:
                load_errors.append(exc)
            time.sleep(0.005)

    with concurrent.futures.ThreadPoolExecutor(max_workers=14) as executor:
        appender_futures = [executor.submit(appender, t) for t in range(10)]
        reader_futures = [executor.submit(reader) for _ in range(4)]
        concurrent.futures.wait(appender_futures + reader_futures)

    assert len(append_errors) == 0
    assert len(load_errors) == 0

    lines = store_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 300
    for line in lines:
        record = json.loads(line)
        assert record["session_id"] == session_id
        assert "record_hash" in record


def test_chat_memory_store_concurrent_append_under_prune_pressure(tmp_path, monkeypatch):
    store_file = tmp_path / "chat_prune_pressure.jsonl"
    store = ChatMemoryStore(store_file)

    def aggressive_prune(self):
        with self._file_lock.acquire():
            try:
                if not self.path.exists() or self.path.stat().st_size < 300:
                    return
                rows = []
                for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
                    try:
                        rows.append(json.loads(line))
                    except Exception as exc:
                        logger.debug("json parse error in prune: %s", exc)
                if len(rows) > 15:
                    rows = rows[-15:]
                fd, temp_name = tempfile.mkstemp(prefix="chat-prune-", suffix=".jsonl", dir=str(self.path.parent))
                try:
                    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                        for row in rows:
                            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temp_name, self.path)
                finally:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
            except (OSError, TypeError, ValueError) as exc:
                logger.debug("chat_memory_store: aggressive prune non-fatal: %s", exc)

    monkeypatch.setattr(ChatMemoryStore, "_prune_if_needed", aggressive_prune)

    errors = []

    def worker(worker_idx: int):
        for i in range(20):
            ok = store.append(
                session_id=f"sess_prune_{worker_idx}",
                role="user",
                content=f"stress message {i} with payload data to exceed size threshold",
                metadata={"type": "prune_test"},
            )
            if not ok:
                errors.append(f"worker {worker_idx} failed on append {i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, w) for w in range(8)]
        concurrent.futures.wait(futures)

    assert len(errors) == 0
    assert store_file.exists()

    for line in store_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            assert "content" in row


def test_trace_ledger_high_concurrency_hash_chain_integrity(tmp_path):
    ledger_file = tmp_path / "traces_stress.jsonl"
    ledger = TraceLedger(ledger_file)

    def worker(thread_id: int):
        for i in range(25):
            ledger.append(
                action="test_action",
                thread_id=thread_id,
                iteration=i,
                data=f"entry_{thread_id}_{i}",
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(worker, t) for t in range(12)]
        concurrent.futures.wait(futures)

    result = ledger.verify()
    assert result["hash_chain_valid"] is True
    assert result["entries"] == 300
    assert len(result["errors"]) == 0

    lines = ledger_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 300
    seqs = [json.loads(line)["seq"] for line in lines]
    assert seqs == list(range(1, 301))


def test_trace_ledger_tail_reader_accuracy_under_concurrent_writes(tmp_path):
    ledger_file = tmp_path / "traces_tail.jsonl"
    ledger = TraceLedger(ledger_file)

    tail_read_errors = []

    def writer(t_idx: int):
        for i in range(15):
            ledger.append(source=f"writer_{t_idx}", msg=f"val_{i}")
            time.sleep(0.002)

    def tail_reader():
        for _ in range(25):
            seq, h = ledger._read_tail()
            if seq > 0 and h is None:
                tail_read_errors.append("hash is None when seq > 0")
            time.sleep(0.003)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        writer_futures = [executor.submit(writer, w) for w in range(4)]
        reader_futures = [executor.submit(tail_reader) for _ in range(2)]
        concurrent.futures.wait(writer_futures + reader_futures)

    assert len(tail_read_errors) == 0
    final_seq, final_hash = ledger._read_tail()
    assert final_seq == 60
    assert final_hash is not None


def test_sqlite_kernel_storage_connection_pool_bounds_and_concurrency(tmp_path):
    db_file = tmp_path / "pool_bound_test.db"
    storage = SQLiteKernelStorage(db_file, max_conns=8)
    try:
        storage.executescript(
            "CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, tid INTEGER, item INTEGER);"
        )

        # Phase 1 (original contract): connections allocated by discarded
        # contexts are provably abandoned (the per-context weakref handle is
        # dead once the Context is garbage-collected) and must be retired, so
        # the pool stays within capacity without unbounded growth.
        for i in range(16):
            def alloc_discarded():
                c = storage._get_conn()
                c.execute("BEGIN")
                return c
            contextvars.Context().run(alloc_discarded)  # context discarded immediately

        # Pool capacity strictly enforced for abandoned churn
        with storage._conn_guard:
            assert len(storage._all_conns) <= 8

        # Phase 2 (CONCURRENCY-FIX 2026-09-24, stricter contract): LIVE
        # contexts holding open transactions are never force-closed and never
        # share a connection. The previous implementation force-closed the
        # oldest pooled connection once capacity was reached — silently
        # rolling back another context's in-flight transaction, which is the
        # corruption mechanism behind soak DatabaseErrors like
        # 'another row available' and broken journal hash chains.
        live_contexts = []
        active_conns = []
        for i in range(16):
            ctx = contextvars.Context()

            def alloc_live():
                c = storage._get_conn()
                c.execute("BEGIN")
                return c
            c = ctx.run(alloc_live)
            live_contexts.append(ctx)  # keep the owning context alive
            active_conns.append(c)

        # Every live context owns a DISTINCT connection (no cross-context
        # sharing: SQLite transactions/pending statements are per-connection).
        assert len({id(c) for c in active_conns}) == 16
        # No live connection was force-closed behind its owner's back:
        # in_transaction must remain readable and True on all of them.
        assert all(c.in_transaction for c in active_conns)

        # Roll back remaining active connections
        for c in active_conns:
            try:
                if c.in_transaction:
                    c.execute("ROLLBACK")
            except Exception as exc:
                logger.debug("cleanup rollback: %s", exc)
    finally:
        storage.close()


def test_sqlite_kernel_storage_busy_timeout_retry_under_write_contention(tmp_path):
    db_file = tmp_path / "busy_retry_test.db"
    init_s = SQLiteKernelStorage(db_file)
    init_s.executescript(
        "CREATE TABLE IF NOT EXISTS counters (key TEXT PRIMARY KEY, val INTEGER);"
    )
    init_s.execute("INSERT INTO counters VALUES ('global', 0);")
    init_s.close()

    errors = []

    def worker(worker_id: int):
        s_worker = SQLiteKernelStorage(db_file)
        try:
            for _ in range(10):
                try:
                    s_worker.begin()
                    row = s_worker.fetchone("SELECT val FROM counters WHERE key='global'")
                    new_val = row["val"] + 1
                    s_worker.execute("UPDATE counters SET val=? WHERE key='global'", (new_val,))
                    s_worker.commit()
                except Exception as exc:
                    errors.append(exc)
                    try:
                        s_worker.rollback()
                    except Exception as rb_exc:
                        logger.debug("rollback: %s", rb_exc)
        finally:
            s_worker.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker, i) for i in range(4)]
        concurrent.futures.wait(futures)

    assert len(errors) == 0

    verify_s = SQLiteKernelStorage(db_file)
    try:
        final_row = verify_s.fetchone("SELECT val FROM counters WHERE key='global'")
        assert final_row["val"] == 40
    finally:
        verify_s.close()


def test_db_manager_concurrent_readers_writers_under_lock(tmp_path):
    db_file = tmp_path / "dbm_concurrency.db"
    db_path_str = str(db_file)

    db_exec("CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, val INTEGER);", db_path=db_path_str)

    errors = []

    def writer(tid: int):
        for i in range(15):
            try:
                db_exec("INSERT INTO metrics (val) VALUES (?);", (tid * 100 + i,), db_path=db_path_str)
            except Exception as exc:
                errors.append(exc)

    def reader():
        for _ in range(20):
            try:
                rows = db_query_all("SELECT * FROM metrics ORDER BY id DESC LIMIT 5;", db_path=db_path_str)
                assert isinstance(rows, list)
                one = db_query_one("SELECT COUNT(*) as total FROM metrics;", db_path=db_path_str)
                assert one is not None
            except Exception as exc:
                errors.append(exc)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        writer_futures = [executor.submit(writer, w) for w in range(4)]
        reader_futures = [executor.submit(reader) for _ in range(8)]
        concurrent.futures.wait(writer_futures + reader_futures)

    assert len(errors) == 0
    total_row = db_query_one("SELECT COUNT(*) as total FROM metrics;", db_path=db_path_str)
    assert total_row["total"] == 60


def test_db_manager_checkpoint_wal_under_concurrency(tmp_path):
    checkpoint_errors = []

    def reader():
        for _ in range(15):
            try:
                db_query_all("SELECT 1;")
            except Exception as exc:
                checkpoint_errors.append(exc)
            time.sleep(0.005)

    def checkpointer():
        for _ in range(5):
            try:
                checkpoint_wal()
            except Exception as exc:
                checkpoint_errors.append(exc)
            time.sleep(0.01)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        r_futs = [executor.submit(reader) for _ in range(4)]
        cp_futs = [executor.submit(checkpointer) for _ in range(2)]
        concurrent.futures.wait(r_futs + cp_futs)

    assert len(checkpoint_errors) == 0
