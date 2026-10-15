"""Persistence DB + migration authority (26-P0.4).

One migration authority for the P0 databases so subsystems never open SQLite
directly or invent their own transaction semantics.

Startup contract (fail-closed):
    open -> PRAGMA foreign_keys=ON -> quick_check
         -> verify applied-migration CHECKSUMS (tampered history => BLOCKED)
         -> apply pending migrations transactionally
         -> READY

A migration is (migration_id, [statements]); its checksum is sha256 over the
statement list. Editing an already-applied migration changes its checksum and
BLOCKS startup - history is never silently rewritten.
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from scp.contracts.time import now_utc_iso


class MigrationError(RuntimeError):
    """Migration checksum mismatch or integrity failure - startup BLOCKED."""


def _checksum(statements: list[str]) -> str:
    canonical = "\n;;\n".join(statements)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class FoundationDB:
    def __init__(self, path: str | Path, migrations: list[tuple[str, list[str]]]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrations = [(mid, list(stmts), _checksum(stmts)) for mid, stmts in migrations]
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._startup()

    def _startup(self) -> None:
        row = self._conn.execute("PRAGMA quick_check").fetchone()
        if not row or row[0] != "ok":
            raise MigrationError(f"integrity check failed for {self.path}: {row}")
        with self._lock:
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                       migration_id TEXT PRIMARY KEY,
                       checksum TEXT NOT NULL,
                       applied_at TEXT NOT NULL)"""
            )
            self._conn.commit()
        applied = {
            r["migration_id"]: r["checksum"]
            for r in self._conn.execute("SELECT migration_id, checksum FROM schema_migrations")
        }
        for mid, statements, checksum in self._migrations:
            if mid in applied:
                if applied[mid] != checksum:
                    raise MigrationError(
                        f"migration {mid!r} checksum mismatch - applied history was "
                        "tampered with; startup BLOCKED (fail closed)"
                    )
                continue
            with self.transaction() as conn:
                for statement in statements:
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO schema_migrations (migration_id, checksum, applied_at) VALUES (?,?,?)",
                    (mid, checksum, now_utc_iso()),
                )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """One atomic unit of work; any exception rolls the whole unit back."""
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
            except BaseException:
                self._conn.rollback()
                raise
            self._conn.commit()

    def execute(self, sql: str, params: tuple | list = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, params)

    def query(self, sql: str, params: tuple | list = ()) -> list[dict]:
        with self._lock:
            return [dict(row) for row in self._conn.execute(sql, params)]

    def applied_migrations(self) -> list[dict]:
        return self.query(
            "SELECT migration_id, checksum, applied_at FROM schema_migrations ORDER BY applied_at"
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
