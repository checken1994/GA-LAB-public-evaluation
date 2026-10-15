"""PostgreSQL persistence boundary for :class:`scp.task_kernel.TaskKernel`.

ADOPT-AND-FIX Track C1: ``PgKernelStorage`` implements the same
``KernelStorage`` contract as :class:`scp.kernel_storage.SQLiteKernelStorage`
on PostgreSQL (psycopg 3), keeping TaskKernel semantics unchanged (17 states,
lease/fencing, idempotency, journal hash-chain, UNKNOWN reconcile).

Design notes (parity with the SQLite backend):

- **Write-slot semantics**: SQLite ``BEGIN IMMEDIATE`` grabs the single
  reserved writer lock. The PostgreSQL analogue here is ``BEGIN`` followed by
  a transaction-scoped advisory lock (``pg_advisory_xact_lock``) on a fixed
  kernel-wide key, so kernel write transactions are serialized exactly like
  the SQLite path (read-modify-write windows such as ``_append_event``'s
  seq-max read cannot interleave). The advisory lock is always the first lock
  acquired in every write transaction, so no new deadlocks are introduced.
  OCC guards (``UPDATE ... WHERE version=?`` + ``rowcount``) keep working on
  top of that serialization.
- **Lock timeout / bounded retry**: mirrors ``busy_timeout=10000`` via
  ``lock_timeout`` plus the same 25-attempt bounded retry loop. When the
  write slot cannot be acquired, ``begin()`` raises
  ``sqlite3.OperationalError`` — the same exception type the SQLite path
  raises — so kernel/test error handling is unchanged.
- **Dialect translation**: TaskKernel owns SQL projections written in the
  SQLite dialect (``?``/``:name`` placeholders, ``INSERT OR IGNORE``,
  ``PRAGMA table_info``, ``strftime``). This module translates at the storage
  boundary so the kernel code stays untouched. All translation is
  quote-literal-aware; identifiers/table names never come from parameters
  (PRAGMA table_info targets are whitelist-checked). No f-string SQL.
- **Row objects**: psycopg rows are wrapped in :class:`PgRow`, which supports
  both ``row["col"]`` (dict access, like ``sqlite3.Row``) and ``row[0]``
  (positional access used by ``verify_integrity()``).
- **Integrity translation**: psycopg integrity errors (unique violations,
  ...) are translated to :class:`scp.kernel_storage.StorageIntegrityError`,
  exactly like the SQLite path translates ``sqlite3.IntegrityError``.
- **Per-thread connections**: same design as the SQLite backend (each thread
  gets its own connection, tracked for ``close()``).

Schema: the canonical PostgreSQL DDL is ``scp/kernel_storage_pg_schema.sql``
(1:1 SQLite mapping: TEXT->TEXT, INTEGER->BIGINT, REAL->DOUBLE PRECISION,
timestamps stay TEXT ISO-8601). At runtime the kernel sends its SQLite DDL
through ``executescript()`` and this module translates it with the same
mapping, so both paths converge.
"""
from __future__ import annotations

import contextvars
import hashlib
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import weakref
from collections import deque
from pathlib import Path
from typing import Any

import psycopg
from psycopg import errors as pg_errors

from scp.kernel_storage import StorageIntegrityError

logger = logging.getLogger(__name__)

__all__ = ["PgKernelStorage", "PgRow", "translate_sqlite_sql", "KERNEL_TABLES"]

# Kernel tables declared by TaskKernel._schema() — the whitelist for PRAGMA
# table_info emulation and quick_check (defense-in-depth: identifiers are
# never accepted from SQL parameters).
KERNEL_TABLES = frozenset(
    {"control", "tasks", "events", "leases", "checkpoints", "idempotency", "queue_accounts"}
)

# Fixed advisory-lock key serializing kernel write transactions (the
# PostgreSQL analogue of SQLite's single-writer BEGIN IMMEDIATE slot).
_WRITE_SLOT_LOCK_KEY = int.from_bytes(
    hashlib.sha256(b"scp.taskkernel.write_slot.v1").digest()[:8], "big"
) & 0x7FFFFFFFFFFFFFFF

_BEGIN_RETRIES = 25  # mirrors SQLiteKernelStorage.begin()
_MASK_RE = re.compile("\x00([0-9]+)\x00")
_NAMED_PARAM_RE = re.compile(r"(?<![A-Za-z0-9_:]):([A-Za-z_][A-Za-z0-9_]*)")
_STRFTIME_EPOCH_RE = re.compile(r"strftime\s*\(\s*'%s'\s*,\s*([A-Za-z_][\w.]*)\s*\)", re.I)
_INSERT_OR_IGNORE_RE = re.compile(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", re.I)
_DDL_PREFIX_RE = re.compile(r"\s*(CREATE|ALTER|DROP)\b", re.I)
_INSERT_INTO_RE = re.compile(r"\bINSERT\s+INTO\s+(?P<tbl>[A-Za-z_][\w]*)", re.I)
_DO_UPDATE_SET_RE = re.compile(r"\bDO\s+UPDATE\s+SET\s+(?P<sets>.+)$", re.I | re.S)


def _split_top_level(text: str) -> list[str]:
    """Split on commas at parenthesis depth 0 (literal-free masked text)."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def _qualify_upsert_columns(masked: str) -> str:
    """Qualify unqualified column refs in ``ON CONFLICT DO UPDATE SET`` RHS.

    PostgreSQL rejects ``SET active=active+1`` inside DO UPDATE SET (the bare
    ``active`` is ambiguous between target table and ``excluded``); SQLite
    resolves it to the target table. Rewrite RHS ``col`` -> ``<table>.col``
    (skipping already-qualified refs) so the kernel's upsert SQL keeps its
    exact semantics.
    """
    if not re.search(r"\bON\s+CONFLICT\b", masked, re.I):
        return masked
    m_set = _DO_UPDATE_SET_RE.search(masked)
    m_ins = _INSERT_INTO_RE.search(masked)
    if not m_set or not m_ins:
        return masked
    table = m_ins.group("tbl")
    prefix = masked[: m_set.start("sets")]
    assignments = _split_top_level(m_set.group("sets"))
    rewritten: list[str] = []
    for assignment in assignments:
        lhs, eq, rhs = assignment.partition("=")
        if eq:
            col = lhs.strip()
            if re.fullmatch(r"[A-Za-z_][\w]*", col):
                pattern = rf"(?<![\w.]){re.escape(col)}(?![\w])"
                rhs = re.sub(pattern, f"{table}.{col}", rhs)
            rewritten.append(f"{lhs}={rhs}")
        else:
            rewritten.append(assignment)
    return prefix + ",".join(rewritten)


class PgRow(dict):
    """Row supporting both ``row['col']`` and ``row[0]`` (sqlite3.Row parity)."""

    def __init__(self, keys: list[str], values: tuple[Any, ...]) -> None:
        super().__init__(zip(keys, values))
        self._values = tuple(values)

    def __getitem__(self, key: Any) -> Any:  # type: ignore[override]
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


def _pg_row_factory(cursor: psycopg.Cursor) -> Any:
    """psycopg row factory producing :class:`PgRow`."""
    description = cursor.description
    if description is None:
        return lambda values: None
    names = [col.name for col in description]

    def make_row(values: tuple[Any, ...]) -> PgRow:
        return PgRow(names, values)

    return make_row


def _mask_literals(sql: str) -> tuple[str, list[str]]:
    """Replace '...' / "..." literals with \x00<idx>\x00 sentinels.

    Keeps placeholders and keywords inside literals untouched by later
    transforms; handles '' escaping inside single-quoted strings.
    """
    out: list[str] = []
    literals: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            else:
                j = n
            literals.append(sql[i:j])
            out.append(f"\x00{len(literals) - 1}\x00")
            i = j
        elif ch == '"':
            j = sql.find('"', i + 1)
            j = n if j == -1 else j + 1
            literals.append(sql[i:j])
            out.append(f"\x00{len(literals) - 1}\x00")
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out), literals


def _unmask_literals(sql: str, literals: list[str]) -> str:
    return _MASK_RE.sub(lambda m: literals[int(m.group(1))], sql)


def translate_sqlite_sql(sql: str) -> str:
    """Translate one SQLite-dialect statement into PostgreSQL dialect.

    Raises ``sqlite3.OperationalError`` (fail-closed) on constructs the
    kernel does not actually use, instead of silently mis-executing them.
    """
    # 1) strftime('%s', col) -> epoch extraction (text ISO timestamps, same
    #    as SQLite parsing the TEXT ISO value).
    translated = _STRFTIME_EPOCH_RE.sub(
        r"FLOOR(EXTRACT(EPOCH FROM (\1)::timestamptz))", sql
    )
    masked, literals = _mask_literals(translated)
    # 2) Fail-closed on strftime formats we do not translate.
    if re.search(r"strftime\s*\(", masked, re.I):
        raise sqlite3.OperationalError(
            "PgKernelStorage: unsupported SQLite strftime format in SQL"
        )
    # 3) INSERT OR IGNORE -> ON CONFLICT DO NOTHING.
    if _INSERT_OR_IGNORE_RE.search(masked):
        masked = _INSERT_OR_IGNORE_RE.sub("INSERT INTO", masked, count=1)
        masked = masked.rstrip() + " ON CONFLICT DO NOTHING"
    if re.search(r"\bINSERT\s+OR\s+REPLACE\b", masked, re.I):
        raise sqlite3.OperationalError(
            "PgKernelStorage: INSERT OR REPLACE is not supported; use ON CONFLICT"
        )
    # 3b) Qualify DO UPDATE SET column refs (PG ambiguity vs SQLite).
    masked = _qualify_upsert_columns(masked)
    # 4) DDL type mapping (SQLite INTEGER is signed 64-bit -> BIGINT).
    if _DDL_PREFIX_RE.match(masked):
        masked = re.sub(r"\bINTEGER\b", "BIGINT", masked, flags=re.I)
        masked = re.sub(r"\bREAL\b", "DOUBLE PRECISION", masked, flags=re.I)
        masked = re.sub(r"\bBLOB\b", "BYTEA", masked, flags=re.I)
    # 5) Placeholders: ? -> %s and :name -> %(name)s (outside literals).
    masked = masked.replace("?", "%s")
    masked = _NAMED_PARAM_RE.sub(r"%(\1)s", masked)
    return _unmask_literals(masked, literals)


class _PragmaResult:
    """Minimal cursor-like result for emulated PRAGMA statements."""

    def __init__(self, rows: list[PgRow]) -> None:
        self._rows = list(rows)
        self.rowcount = -1

    def fetchone(self) -> PgRow | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[PgRow]:
        return list(self._rows)


class _PgConnHandle:
    """Per-context ownership token for one PostgreSQL connection. [PG-F2-FIX]

    Stored in ``_conn_ctx`` so the only strong reference chain to it runs
    through the owning context (thread / asyncio task). When that context
    dies, the handle is garbage-collected and its weakref in
    ``PgKernelStorage._conn_owner`` turns dead — a *provably* abandoned
    connection that is safe to reuse or close. This closes the TOCTOU where
    ``_get_conn`` handed an IDLE connection that still belonged to a living
    context to a second context (same bug class fixed for the SQLite backend
    in ``kernel_storage.py`` via ``_ConnHandle`` + weakrefs).
    """

    __slots__ = ("conn", "__weakref__")

    def __init__(self, conn: Any) -> None:
        self.conn = conn


class PgKernelStorage:
    """Per-thread-connection PostgreSQL storage implementing KernelStorage.

    Contract parity with :class:`scp.kernel_storage.SQLiteKernelStorage`:
    begin/commit/rollback write slot, execute/executescript/fetchone/fetchall,
    ``in_transaction``, ``close()`` and ``backup_to()`` (via pg_dump;
    fail-closed when pg_dump is unavailable).
    """

    def __init__(self, dsn: str, *, lock_timeout_ms: int = 10000, max_conns: int = 16) -> None:
        self.dsn = str(dsn)
        self.lock_timeout_ms = int(lock_timeout_ms)
        self.db_path = self._redacted_dsn()  # sqlite-parity attribute (no secrets)
        self._max_conns = max_conns
        self._conn_ctx: contextvars.ContextVar[_PgConnHandle | None] = contextvars.ContextVar(
            f"pg_kernel_conn_{id(self)}", default=None
        )
        # [PG-F1-FIX] Per-thread transaction-flag storage. begin()/commit()/
        # rollback()/in_transaction read-write ``self._conn_local.txn``, but
        # this attribute was never initialized, so every write-slot call
        # raised AttributeError (same correct pattern as event_bus_pg).
        self._conn_local = threading.local()
        self._all_conns: deque[Any] = deque()
        self._conn_guard = threading.Lock()
        # [PG-F2-FIX] Per-context connection ownership: id(conn) -> weakref to
        # the owner handle held in the owning context's _conn_ctx. When the
        # context dies the weakref dies and the connection becomes reusable —
        # the same invariant as SQLiteKernelStorage (_ConnHandle + weakref).
        self._conn_owner: dict[int, weakref.ref] = {}
        self._get_conn()  # warm + validate the connection eagerly

    # ------------------------------------------------------------------ #
    # connection lifecycle                                                #
    # ------------------------------------------------------------------ #
    def _is_open(self, conn: Any) -> bool:
        try:
            return not conn.closed
        except Exception:
            logger.debug("_is_open ignored", exc_info=True)
            return False

    def _redacted_dsn(self) -> str:
        try:
            info = psycopg.conninfo.conninfo_to_dict(self.dsn)
            if info.get("password"):
                info["password"] = "***"
            return psycopg.conninfo.make_conninfo(**info)
        except Exception:
            logger.debug("_redacted_dsn ignored", exc_info=True)
            return "<redacted-dsn>"

    def _make_connection(self) -> Any:
        conn = psycopg.connect(self.dsn, autocommit=True, row_factory=_pg_row_factory)
        # busy_timeout parity: lock_timeout applies to every per-thread
        # connection (write-slot acquisition), parameterized via set_config.
        conn.execute(
            "SELECT set_config('lock_timeout', %s, false)", (f"{self.lock_timeout_ms}ms",)
        )
        return conn

    def _get_conn(self) -> Any:
        # [PG-F2-FIX] Per-context ownership: a connection bound to a LIVING
        # context is never handed to another context (TOCTOU fix; same
        # invariant as SQLiteKernelStorage._get_conn/_retire_abandoned).
        handle = self._conn_ctx.get()
        if handle is not None and self._is_open(handle.conn):
            return handle.conn

        with self._conn_guard:
            # Re-check under the guard: check-then-act must be atomic against
            # concurrent binds racing on the same context.
            handle = self._conn_ctx.get()
            if handle is not None and self._is_open(handle.conn):
                return handle.conn

            # Prune closed connections (and their ownership entries).
            open_conns = [c for c in self._all_conns if self._is_open(c)]
            if len(open_conns) != len(self._all_conns):
                closed_ids = {id(c) for c in self._all_conns} - {id(c) for c in open_conns}
                for cid in closed_ids:
                    self._conn_owner.pop(cid, None)
            self._all_conns = deque(open_conns)

            # Reuse an IDLE connection that NO LIVING context owns.
            for candidate in self._all_conns:
                ref = self._conn_owner.get(id(candidate))
                if ref is not None and ref() is not None:
                    continue  # owned by a living context — never share it
                status = candidate.info.transaction_status
                if status == 0:  # IDLE
                    new_handle = _PgConnHandle(candidate)
                    self._conn_owner[id(candidate)] = weakref.ref(new_handle)
                    self._conn_ctx.set(new_handle)
                    return candidate

            # Bounded creation: at capacity, recycle only PROVABLY abandoned
            # connections (owner weakref dead). A connection whose owning
            # context may still use it is never closed; live contexts may
            # temporarily exceed the soft cap (correctness first — mirrors
            # SQLiteKernelStorage._retire_abandoned).
            if len(self._all_conns) >= self._max_conns:
                kept: deque[Any] = deque()
                retired = False
                for conn in self._all_conns:
                    if not retired:
                        ref = self._conn_owner.get(id(conn))
                        if ref is not None and ref() is not None:
                            kept.append(conn)  # living owner — keep
                            continue
                        self._conn_owner.pop(id(conn), None)
                        retired = True
                        try:
                            conn.close()
                        except Exception as exc:
                            logger.debug(f"_get_conn ignored: {exc}", exc_info=True)
                        continue
                    kept.append(conn)
                self._all_conns = kept

            new_conn = self._make_connection()
            self._all_conns.append(new_conn)
            new_handle = _PgConnHandle(new_conn)
            self._conn_owner[id(new_conn)] = weakref.ref(new_handle)
            self._conn_ctx.set(new_handle)
            return new_conn

    def _abort_if_open(self, conn: Any) -> None:
        status = conn.info.transaction_status
        # 2 = INTRANS, 3 = INERROR
        if status in (2, 3):
            conn.rollback()

    # ------------------------------------------------------------------ #
    # write slot (BEGIN IMMEDIATE analogue)                               #
    # ------------------------------------------------------------------ #
    def begin(self) -> None:
        """Acquire the kernel write slot: BEGIN + transaction advisory lock.

        Bounded retry on lock timeout; on exhaustion raises
        ``sqlite3.OperationalError`` (same exception type as the SQLite path).
        """
        conn = self._get_conn()
        last_error: Exception | None = None
        for attempt in range(_BEGIN_RETRIES):
            try:
                conn.execute("BEGIN")
                conn.execute("SELECT pg_advisory_xact_lock(%s)", (_WRITE_SLOT_LOCK_KEY,))
                self._conn_local.txn = True
                return
            except psycopg.OperationalError as exc:
                msg = str(exc).lower()
                transient = (
                    isinstance(exc, pg_errors.LockNotAvailable)
                    or "lock" in msg
                    or "timeout" in msg
                    or "busy" in msg
                )
                self._abort_if_open(conn)
                if not transient:
                    raise sqlite3.OperationalError(str(exc)) from exc
                last_error = exc
                time.sleep(0.05 * min(attempt + 1, 4))
        self._conn_local.txn = False
        raise sqlite3.OperationalError(
            f"database is locked (pg write-slot lock timeout after {_BEGIN_RETRIES} attempts): {last_error}"
        )

    def commit(self) -> None:
        if not getattr(self._conn_local, "txn", False):
            raise sqlite3.OperationalError("cannot commit - no transaction is active")
        conn = self._get_conn()
        try:
            conn.commit()
        except psycopg.OperationalError as exc:
            raise sqlite3.OperationalError(str(exc)) from exc
        self._conn_local.txn = False

    def rollback(self) -> None:
        if getattr(self._conn_local, "txn", False):
            conn = self._get_conn()
            conn.rollback()
            self._conn_local.txn = False

    @property
    def in_transaction(self) -> bool:
        return bool(getattr(self._conn_local, "txn", False))

    # ------------------------------------------------------------------ #
    # query primitives                                                    #
    # ------------------------------------------------------------------ #
    def execute(self, sql: str, params: Any = ()) -> Any:
        pragma = self._maybe_pragma(sql)
        if pragma is not None:
            return pragma
        conn = self._get_conn()
        translated = translate_sqlite_sql(sql)
        try:
            return conn.cursor().execute(translated, params)
        except pg_errors.IntegrityError as exc:
            raise StorageIntegrityError(str(exc)) from exc
        except (pg_errors.OperationalError, pg_errors.ProgrammingError) as exc:
            raise sqlite3.OperationalError(str(exc)) from exc

    def executescript(self, script: str) -> None:
        """Translate and run a DDL script statement-by-statement."""
        conn = self._get_conn()
        for raw_statement in script.split(";"):
            statement = raw_statement.strip()
            if not statement:
                continue
            translated = translate_sqlite_sql(statement)
            try:
                conn.execute(translated)
            except pg_errors.IntegrityError as exc:
                raise StorageIntegrityError(str(exc)) from exc
            except (pg_errors.OperationalError, pg_errors.ProgrammingError) as exc:
                raise sqlite3.OperationalError(str(exc)) from exc

    def fetchone(self, sql: str, params: Any = ()) -> Any | None:
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: Any = ()) -> list[Any]:
        return self.execute(sql, params).fetchall()

    # ------------------------------------------------------------------ #
    # PRAGMA emulation (fail-closed)                                      #
    # ------------------------------------------------------------------ #
    def _maybe_pragma(self, sql: str) -> _PragmaResult | None:
        stripped = sql.strip()
        match = re.match(r"^PRAGMA\s+(?P<body>.+)$", stripped, re.I)
        if not match:
            return None
        body = match.group("body").strip().rstrip(";").strip()
        table_info = re.match(r'^table_info\(\s*(?P<tbl>"?[A-Za-z_][\w]*"?)\s*\)$', body, re.I)
        if table_info:
            return self._pragma_table_info(table_info.group("tbl").strip('"'))
        if re.match(r"^quick_check$", body, re.I):
            return self._pragma_quick_check()
        raise sqlite3.OperationalError(
            f"PgKernelStorage: unsupported PRAGMA '{stripped}' (fail-closed)"
        )

    def _pragma_table_info(self, table: str) -> _PragmaResult:
        if table not in KERNEL_TABLES:
            raise sqlite3.OperationalError(
                f"PgKernelStorage: table '{table}' is not in the kernel schema whitelist"
            )
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT a.attnum AS cid,
                       a.attname AS name,
                       format_type(a.atttypid, a.atttypmod) AS type,
                       a.attnotnull::int AS notnull,
                       pg_get_expr(d.adbin, d.adrelid) AS dflt_value,
                       COALESCE(EXISTS (
                           SELECT 1 FROM pg_index i
                           WHERE i.indrelid = a.attrelid AND i.indisprimary
                             AND a.attnum = ANY (i.indkey)
                       )::int, 0) AS pk
                FROM pg_attribute a
                LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                WHERE a.attrelid = (%s)::regclass
                  AND a.attnum > 0 AND NOT a.attisdropped
                ORDER BY a.attnum
                """,
                (table,),
            ).fetchall()
        except pg_errors.UndefinedTable:
            # SQLite parity: PRAGMA table_info on a missing table yields no rows.
            rows = []
        return _PragmaResult(list(rows))

    def _pragma_quick_check(self) -> _PragmaResult:
        """Structural integrity check: every kernel table must exist.

        Content integrity (journal hash-chain) is verified separately by
        TaskKernel.verify_integrity(), which stays backend-neutral.
        """
        conn = self._get_conn()
        present = {
            row["table_name"]
            for row in conn.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = current_schema() AND table_name = ANY(%s)
                """,
                (sorted(KERNEL_TABLES),),
            ).fetchall()
        }
        missing = sorted(KERNEL_TABLES - present)
        if missing:
            value = "missing table(s): " + ", ".join(missing)
        else:
            value = "ok"
        return _PragmaResult([PgRow(["quick_check"], (value,))])

    # ------------------------------------------------------------------ #
    # shutdown + backup                                                   #
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        with self._conn_guard:
            for conn in list(self._all_conns):
                try:
                    conn.close()
                except psycopg.Error:
                    logger.debug("PgKernelStorage.close: psycopg.Error ignored", exc_info=True)
            self._all_conns.clear()
            self._conn_owner.clear()  # [PG-F2-FIX] drop ownership registry
            self._conn_ctx.set(None)

    def backup_to(self, target: str | Path) -> None:
        """Transactionally consistent snapshot via ``pg_dump`` (plain format).

        Fail-closed: raises ``RuntimeError`` when pg_dump is unavailable or
        the dump fails — no partial/fake snapshot is written. The dump file
        contains SQL statements (restore with psql), not a SQLite database.
        """
        target_path = Path(target)
        pg_dump = shutil.which("pg_dump")
        if not pg_dump:
            raise RuntimeError(
                "PgKernelStorage.backup_to requires pg_dump on PATH "
                "(Track C1 session 1 scope); no snapshot written (fail-closed)"
            )
        info = psycopg.conninfo.conninfo_to_dict(self.dsn)
        env = os.environ.copy()
        password = info.get("password")
        if password:
            env["PGPASSWORD"] = password  # keep secrets off argv
        cmd = [pg_dump, "--format=plain", "--file", str(target_path)]
        if info.get("host"):
            cmd += ["--host", str(info["host"])]
        if info.get("port"):
            cmd += ["--port", str(info["port"])]
        if info.get("user"):
            cmd += ["--user", str(info["user"])]
        if info.get("dbname"):
            cmd += ["--dbname", str(info["dbname"])]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed (rc={result.returncode}): {result.stderr[-500:]}")
