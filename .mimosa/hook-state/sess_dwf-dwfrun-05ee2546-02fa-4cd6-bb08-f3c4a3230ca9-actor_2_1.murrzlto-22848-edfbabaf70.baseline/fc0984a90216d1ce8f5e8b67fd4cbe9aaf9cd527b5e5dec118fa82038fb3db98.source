"""Persistence boundary for :class:`scp.task_kernel.TaskKernel`.

``TaskKernel`` owns task semantics and SQL projections.  This module owns the
database lifecycle: connections, transaction serialization, backend exception
translation, and online backup.  Keeping SQL projections in the kernel is an
intentional incremental boundary; a non-SQL backend would also require a
repository/query contract, not merely a connection adapter.

``TaskKernel(db_path)`` remains backward compatible, while
``TaskKernel(storage=...)`` makes the persistence lifecycle injectable and
testable without exposing SQLite locks or connections to the kernel.
"""
from __future__ import annotations

import contextvars
import logging
import os
import sqlite3
import threading
import time
import weakref
from collections import deque
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)



class StorageIntegrityError(RuntimeError):
    """Backend-neutral uniqueness/integrity conflict."""


@runtime_checkable
class KernelStorage(Protocol):
    """Contract that TaskKernel requires from any persistence engine."""

    def begin(self) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

    def execute(self, sql: str, params: Any = ()) -> Any:
        ...

    def executescript(self, script: str) -> None:
        ...

    def fetchone(self, sql: str, params: Any = ()) -> Any | None:
        ...

    def fetchall(self, sql: str, params: Any = ()) -> list[Any]:
        ...

    @property
    def in_transaction(self) -> bool:
        ...

    def close(self) -> None:
        ...

    def backup_to(self, target: str | Path) -> None:
        ...


class _ConnHandle:
    """Per-context ownership token for one SQLite connection.

    [CONCURRENCY-FIX 2026-09-24] The handle is stored in the ContextVar, so
    the only strong reference chain to it runs through the owning context.
    When the context dies (thread exits, asyncio/task context discarded), the
    handle is garbage-collected and its weakref in ``_handle_refs`` turns
    dead — a *provably* abandoned connection that is safe to close, because
    no live code path can still reach it. This replaces the previous
    heuristic of re-binding any pooled connection whose ``in_transaction``
    was False, which could hand the SAME connection to a second context
    while the first had not yet executed BEGIN (TOCTOU) and produced
    ``DatabaseError: another row available`` / nested-BEGIN corruption under
    load.
    """

    __slots__ = ("conn", "__weakref__")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn


class SQLiteKernelStorage:
    """SQLite implementation of :class:`KernelStorage`.

    - WAL mode: allows concurrent readers alongside writers.
    - ContextVar-safe connection management: avoids transaction collisions in asyncio.
    - Per-context connection ownership: every live context owns exactly one
      connection for its lifetime and connections are never re-bound across
      live contexts (SQLite transactions and pending statements are
      per-connection; sharing corrupted transactions under load). Dead
      contexts' connections are provably abandoned via weakref handles and
      are retired; a soft capacity cap bounds forgotten churn.
    - BEGIN IMMEDIATE with retry: prevents write-write deadlocks.
    - All connections tracked in _all_conns for clean shutdown via close().
    """

    def __init__(self, db_path: str | Path, max_conns: int = 16) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._max_conns = max_conns
        self._conn_ctx: contextvars.ContextVar[_ConnHandle | None] = contextvars.ContextVar(
            f"sqlite_kernel_conn_{id(self)}", default=None
        )
        self._all_conns: deque[sqlite3.Connection] = deque()
        self._conn_guard = threading.Lock()
        # conn id -> weakref to the owning context's _ConnHandle.
        self._handle_refs: dict[int, weakref.ref] = {}
        c = self._get_conn()
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=10000")

    def _is_open(self, conn: sqlite3.Connection) -> bool:
        try:
            _ = conn.total_changes
            return True
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            return False

    def _make_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path, timeout=10, isolation_level=None, check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _get_conn(self) -> sqlite3.Connection:
        handle = self._conn_ctx.get()
        if handle is not None and self._is_open(handle.conn):
            return handle.conn

        with self._conn_guard:
            # Re-check inside the guard: another thread may have closed or
            # replaced connections while we waited for the lock.
            handle = self._conn_ctx.get()
            if handle is not None and self._is_open(handle.conn):
                return handle.conn

            # Prune closed connections and connections whose owning context
            # died (weakref handle dead => provably unreachable => safe to
            # close, even mid-transaction: no live code path can reach them).
            open_conns: deque[sqlite3.Connection] = deque()
            for candidate in self._all_conns:
                ref = self._handle_refs.get(id(candidate))
                owner_alive = ref is not None and ref() is not None
                if not owner_alive:
                    self._handle_refs.pop(id(candidate), None)
                    try:
                        candidate.close()
                    except sqlite3.Error:
                        logger.debug('SQLiteKernelStorage._get_conn: prune close failed', exc_info=True)
                    continue
                if not self._is_open(candidate):
                    self._handle_refs.pop(id(candidate), None)
                    continue
                open_conns.append(candidate)
            self._all_conns = open_conns

            # [CONCURRENCY-FIX 2026-09-24] NEVER hand a connection that another
            # live context may still be using to a new context. The previous
            # "reuse idle connection" step re-bound a pooled connection whenever
            # ``in_transaction`` was False, but ``in_transaction`` is only set
            # by the first write statement: a context that had just been handed
            # the same connection but had not yet executed BEGIN (TOCTOU between
            # bind and BEGIN IMMEDIATE), or that was between ``execute(SELECT)``
            # and ``fetchone()`` on an autocommit read, still tested as "idle".
            # Two contexts then shared one SQLite connection and interleaved
            # statements/transactions, which SQLite reports as
            # ``DatabaseError: another row available`` /
            # ``no more rows available`` / ``cannot start a transaction within
            # a transaction`` and, worst case, produced incomplete journal
            # chains when one context's COMMIT/ROLLBACK closed the other's
            # half-finished transaction. Per-context ownership restores the
            # invariant documented in TaskKernel (CHAIN-AUDIT FIX 2026-08-29):
            # one connection per thread/context for its whole lifetime.
            conn = self._make_connection()
            self._all_conns.append(conn)
            handle = _ConnHandle(conn)
            self._handle_refs[id(conn)] = weakref.ref(handle)
            self._conn_ctx.set(handle)

            if len(self._all_conns) > self._max_conns:
                self._retire_abandoned(conn)
            return conn

    def _retire_abandoned(self, protected: sqlite3.Connection) -> None:
        """Retire connections over the soft cap, but only provably dead ones.

        [CONCURRENCY-FIX 2026-09-24] A connection whose owning context may
        still use it is NEVER closed: sqlite3 ``Connection.close()`` is not
        thread-safe against concurrent statement execution, and force-closing
        a connection mid-transaction rolls back another context's in-flight
        transaction (the corruption mechanism behind soak
        ``DatabaseError: another row available`` and broken journal chains).
        A connection is retired only when its owning context is provably gone
        (weakref to the per-context ``_ConnHandle`` is dead) — no live code
        path can still reach it, so closing it is safe regardless of its
        transaction state. Live contexts are kept even past the soft cap,
        bounded by live contexts, never by correctness.
        """
        excess = len(self._all_conns) - self._max_conns
        kept: deque[sqlite3.Connection] = deque()
        for candidate in list(self._all_conns):
            if excess <= 0 or candidate is protected:
                kept.append(candidate)
                continue
            ref = self._handle_refs.get(id(candidate))
            if ref is not None and ref() is not None:
                kept.append(candidate)
                continue
            self._handle_refs.pop(id(candidate), None)
            excess -= 1
            try:
                candidate.close()
            except sqlite3.Error:
                logger.debug('SQLiteKernelStorage._retire_abandoned: close failed', exc_info=True)
        self._all_conns = kept

    def begin(self) -> None:
        """Acquire write lock + BEGIN IMMEDIATE (bounded retry on SQLITE_BUSY / locked)."""
        last_error: Exception | None = None
        for attempt in range(25):
            try:
                self._get_conn().execute("BEGIN IMMEDIATE")
                return
            except sqlite3.OperationalError as exc:
                err_msg = str(exc).lower()
                if "locked" not in err_msg and "busy" not in err_msg:
                    raise
                last_error = exc
                time.sleep(0.05 * min(attempt + 1, 4))
        raise last_error if last_error else RuntimeError("begin failed")

    def commit(self) -> None:
        self._get_conn().execute("COMMIT")

    def rollback(self) -> None:
        conn = self._get_conn()
        if conn.in_transaction:
            conn.execute("ROLLBACK")

    def execute(self, sql: str, params: Any = ()) -> Any:
        try:
            return self._get_conn().execute(sql, params)
        except sqlite3.IntegrityError as exc:
            raise StorageIntegrityError(str(exc)) from exc

    def executescript(self, script: str) -> None:
        """Run a SQL script (e.g. the kernel schema) on this context's connection.

        Fail-closed and bounded: with WAL + ``busy_timeout=10000`` each write
        statement waits at most ~10s for the write slot, then raises
        ``OperationalError: database is locked``. Stress probe (2026-10-01,
        local Windows): a connection holding an eternal ``BEGIN IMMEDIATE``
        makes a competing schema script raise after ~11s; a live WAL reader
        does not block it (0.00s); abandoned per-context connections do not
        block it either. A schema script is ~10 statements, so the worst
        SQLite-lock window is ~100s, not minutes. Long multi-minute stalls
        observed inside a full-suite run at this line were NOT reproduced in
        isolation and are attributed to system-level I/O contention (see the
        anomaly note in ``tests/T04_kernel/test_gap13_state_machine_boundaries.py``).
        """
        self._get_conn().executescript(script)

    def fetchone(self, sql: str, params: Any = ()) -> Any | None:
        return self._get_conn().execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: Any = ()) -> list[Any]:
        return self._get_conn().execute(sql, params).fetchall()

    @property
    def in_transaction(self) -> bool:
        return bool(self._get_conn().in_transaction)

    def close(self) -> None:
        with self._conn_guard:
            for conn in list(self._all_conns):
                try:
                    conn.close()
                except sqlite3.Error:
                    logger.debug('SQLiteKernelStorage.close: sqlite3.Error ignored', exc_info=True)
            self._all_conns.clear()
            self._handle_refs.clear()
            self._conn_ctx.set(None)

    def backup_to(self, target: str | Path) -> None:
        """Use SQLite's online backup API so WAL writers may remain active."""
        destination = sqlite3.connect(str(target))
        try:
            self._get_conn().backup(destination)
        finally:
            destination.close()


def make_storage(db_path: str | Path, backend: str | None = None) -> KernelStorage:
    """Create the storage backend for a given path.

    Backend resolution order:
      1. explicit ``backend`` argument;
      2. ``SCP_KERNEL_BACKEND`` env (canonical switch; ``postgres`` requires
         ``SCP_KERNEL_PG_DSN`` and returns :class:`PgKernelStorage`);
      3. ``SCP_STORAGE_BACKEND`` env (legacy switch; keeps its fail-closed
         sqlite-only contract — ``postgres`` there still raises
         ``NotImplementedError`` so no deployment silently flips engines);
      4. default ``sqlite``.

    WARNING: SQLite is a Single Point of Failure (SPOF) in distributed deployments.
    It does not support cross-node replication or active-active clustering.
    For high availability or multi-node production setups, a distributed storage backend is required.
    """

    def _unsupported(name: str) -> NotImplementedError:
        return NotImplementedError(
            f"Unsupported storage backend '{name}'. Only 'sqlite' is currently supported. "
            "For distributed deployments, inject a custom Storage instance into TaskKernel."
        )

    def _postgres() -> KernelStorage:
        dsn = os.environ.get("SCP_KERNEL_PG_DSN", "").strip()
        if not dsn:
            raise RuntimeError(
                "SCP_KERNEL_BACKEND=postgres requires SCP_KERNEL_PG_DSN to be set "
                "(fail-closed: refusing to fall back to SQLite)."
            )
        from scp.kernel_storage_pg import PgKernelStorage

        return PgKernelStorage(dsn)

    if backend is not None:
        backend = str(backend).strip().lower()
        if backend in ("sqlite", ""):
            return SQLiteKernelStorage(db_path)
        if backend == "postgres":
            return _postgres()
        raise _unsupported(backend)

    kernel_env = os.environ.get("SCP_KERNEL_BACKEND", "").strip().lower()
    if kernel_env:
        if kernel_env == "sqlite":
            return SQLiteKernelStorage(db_path)
        if kernel_env == "postgres":
            return _postgres()
        raise _unsupported(kernel_env)

    legacy_env = os.environ.get("SCP_STORAGE_BACKEND", "sqlite")
    if legacy_env.strip().lower() in ("sqlite", ""):
        return SQLiteKernelStorage(db_path)
    raise _unsupported(legacy_env.strip())
