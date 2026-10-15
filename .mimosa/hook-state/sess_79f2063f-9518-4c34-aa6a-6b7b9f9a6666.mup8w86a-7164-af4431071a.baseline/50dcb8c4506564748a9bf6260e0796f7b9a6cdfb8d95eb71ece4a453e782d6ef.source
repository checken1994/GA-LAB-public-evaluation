"""[PG-F1-FIX / PG-F2-FIX] Local regression tests (no real PostgreSQL needed).

Covers two confirmed defects in ``scp.kernel_storage_pg.PgKernelStorage``:

F1 (CRITICAL): ``begin/commit/rollback/in_transaction`` read-write
``self._conn_local.txn`` but ``_conn_local`` was never initialized in
``__init__`` -> ``AttributeError`` on every write-slot operation.

F2 (P1): ``_get_conn`` could hand an IDLE connection that still belonged to a
*living* context to a second context (TOCTOU; same bug class already fixed for
the SQLite backend via per-context ownership + weakrefs).

psycopg is mocked at the ``connect`` boundary only; all assertions exercise
the real ``PgKernelStorage`` code paths (attribute existence, txn flag
lifecycle, per-context connection ownership, dead-context reuse).
"""
from __future__ import annotations

import gc
import sqlite3
import threading
from typing import Any

import pytest

import scp.kernel_storage_pg as kspg
from scp.kernel_storage_pg import PgKernelStorage

DSN = "postgresql://scp:secret@127.0.0.1:55432/scpkernel"


class _FakeInfo:
    def __init__(self) -> None:
        self.transaction_status = 0  # 0 == IDLE (psycopg TransactionStatus)


class _FakeCursor:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    def execute(self, sql: str, params: Any = ()) -> _FakeCursor:
        return self

    def fetchone(self) -> None:
        return None

    def fetchall(self) -> list[Any]:
        return []


class _FakeConn:
    def __init__(self) -> None:
        self.closed = False
        self.info = _FakeInfo()
        self.execute_log: list[str] = []

    def execute(self, sql: str, params: Any = ()) -> _FakeCursor:
        self.execute_log.append(sql)
        return _FakeCursor(self)

    def commit(self) -> None:
        self.info.transaction_status = 0

    def rollback(self) -> None:
        self.info.transaction_status = 0

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)

    def close(self) -> None:
        self.closed = True


@pytest.fixture()
def fake_connect(monkeypatch: pytest.MonkeyPatch) -> list[_FakeConn]:
    made: list[_FakeConn] = []
    lock = threading.Lock()

    def _connect(dsn: str, **kwargs: Any) -> _FakeConn:
        conn = _FakeConn()
        with lock:
            made.append(conn)
        return conn

    monkeypatch.setattr(kspg.psycopg, "connect", _connect)
    return made


# --------------------------------------------------------------------------- #
# F1: _conn_local must exist and the txn flag must follow the full lifecycle  #
# --------------------------------------------------------------------------- #
def test_f1_conn_local_initialized_after_init(fake_connect: list[_FakeConn]) -> None:
    storage = PgKernelStorage(DSN)
    assert hasattr(storage, "_conn_local")  # pre-fix: attribute missing
    assert isinstance(storage._conn_local, threading.local)
    assert storage.in_transaction is False


def test_f1_txn_flag_full_lifecycle(fake_connect: list[_FakeConn]) -> None:
    storage = PgKernelStorage(DSN)
    conn = storage._get_conn()

    assert storage.in_transaction is False
    with pytest.raises(sqlite3.OperationalError):
        storage.commit()  # no active transaction (pre-fix: AttributeError)

    storage.begin()  # pre-fix: AttributeError
    assert storage.in_transaction is True
    assert any(sql.strip().upper() == "BEGIN" for sql in conn.execute_log)
    assert any("pg_advisory_xact_lock" in sql for sql in conn.execute_log)

    storage.commit()
    assert storage.in_transaction is False

    storage.begin()
    assert storage.in_transaction is True
    storage.rollback()
    assert storage.in_transaction is False


# --------------------------------------------------------------------------- #
# F2: per-context ownership — no two LIVING contexts share one connection     #
# --------------------------------------------------------------------------- #
def test_f2_no_two_live_contexts_share_one_connection(
    fake_connect: list[_FakeConn],
) -> None:
    storage = PgKernelStorage(DSN, max_conns=32)
    main_conn = storage._get_conn()  # owned by the living test context

    n = 8
    barrier = threading.Barrier(n + 1)
    results: dict[int, _FakeConn] = {}
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker(i: int) -> None:
        try:
            barrier.wait(timeout=10)
            conn = storage._get_conn()
            with lock:
                results[i] = conn
        except BaseException as exc:
            errors.append(exc)
        finally:
            barrier.wait(timeout=10)

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(n)]
    for t in threads:
        t.start()
    barrier.wait(timeout=10)  # release all binds at the same instant
    barrier.wait(timeout=10)  # all binds finished while ALL contexts alive
    for t in threads:
        t.join(timeout=10)

    assert not errors, errors
    assert len(results) == n
    conns = list(results.values())
    # Strict invariant: 8 distinct connections — none shared between two
    # living contexts, and none of them is the connection still owned by the
    # living main context.
    assert len({id(c) for c in conns}) == n  # pre-fix: all threads got main_conn
    assert all(c is not main_conn for c in conns)
    assert len(fake_connect) == 1 + n  # no sharing == no connection shortage


def test_f2_dead_context_connection_is_reusable(fake_connect: list[_FakeConn]) -> None:
    storage = PgKernelStorage(DSN, max_conns=32)
    storage._get_conn()  # main context owns connection #1

    holder: list[_FakeConn] = []

    t = threading.Thread(target=lambda: holder.append(storage._get_conn()), daemon=True)
    t.start()
    t.join(timeout=10)
    gc.collect()  # ensure the dead thread's context/handle is collected

    made_after_first_bind = len(fake_connect)
    got: list[_FakeConn] = []

    t2 = threading.Thread(target=lambda: got.append(storage._get_conn()), daemon=True)
    t2.start()
    t2.join(timeout=10)

    assert len(got) == 1
    # The abandoned (dead-owner) IDLE connection must be reused, not replaced.
    assert got[0] is holder[0]
    assert len(fake_connect) == made_after_first_bind  # no new connection created


def test_f2_live_owned_connection_never_recycled_at_cap(
    fake_connect: list[_FakeConn],
) -> None:
    storage = PgKernelStorage(DSN, max_conns=2)
    main_conn = storage._get_conn()  # context A (main, alive)

    other: list[_FakeConn] = []
    t = threading.Thread(target=lambda: other.append(storage._get_conn()), daemon=True)
    t.start()
    t.join(timeout=10)
    gc.collect()
    abandoned = other[0]
    assert abandoned is not main_conn
    assert len(fake_connect) == 2  # pool now at cap

    # New bind at cap: the abandoned connection is reused; the LIVE-owned
    # main connection is never handed out and never closed.
    t2 = threading.Thread(target=lambda: other.append(storage._get_conn()), daemon=True)
    t2.start()
    t2.join(timeout=10)
    rebound = other[1]

    assert rebound is abandoned  # dead-owner conn reused
    assert not abandoned.closed
    assert len(fake_connect) == 2  # no extra connection needed
    assert storage._get_conn() is main_conn  # main context keeps its own conn
    assert not main_conn.closed
