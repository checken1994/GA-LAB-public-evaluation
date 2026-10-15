#!/usr/bin/env python3
"""Migrate a TaskKernel SQLite database to PostgreSQL (ADOPT-AND-FIX Track C1).

1:1 table copy (control, tasks, events, leases, checkpoints, idempotency,
queue_accounts) in dependency order. The journal is the authoritative source
of truth, so a faithful copy preserves all kernel semantics; the kernel state
machine is NOT re-run — rows are moved as-is.

Safety:
- fail-closed: aborts when the SQLite table/column shape does not match the
  canonical PostgreSQL kernel schema, when BLOB values appear (the kernel
  stores none), or when the post-copy row counts do not match;
- refuses to write into non-empty target tables unless ``--truncate`` is
  given explicitly (no silent overwrite);
- takes the kernel write-slot advisory lock for the duration so a live
  kernel cannot write mid-migration (stop the kernel first anyway);
- DSN secrets are passed via libpq and never echoed (output is redacted);
- ``--dry-run`` reads and reports only — writes nothing.

Usage:
  python scripts/migrate_kernel_sqlite_to_pg.py \
      --sqlite data/kernel.sqlite3 \
      --pg-dsn postgresql://user:pass@host:5432/db \
      [--schema scp_kernel] [--dry-run] [--truncate] [--batch-size 1000]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql as pg_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scp.kernel_storage_pg import KERNEL_TABLES, _WRITE_SLOT_LOCK_KEY  # noqa: E402

# Dependency order: parents before children (logical references only; the
# kernel schema declares no FKs, matching SQLite 1:1).
COPY_ORDER = (
    "control",
    "tasks",
    "events",
    "leases",
    "checkpoints",
    "idempotency",
    "queue_accounts",
)
# Compile-time whitelist (SEC-S4 discipline): only these tables are ever
# touched, and their identifiers enter SQL exclusively through compile-time
# literal statements (constant maps below) or psycopg.sql.Identifier
# (CREATE SCHEMA / INSERT, whose targets are not statically enumerable).
assert set(COPY_ORDER) == KERNEL_TABLES

# Compile-time literal SQL per whitelisted table (no dynamic SQL text: no
# f-strings, no psycopg sql.SQL composition). Keys are pinned to COPY_ORDER so
# any drift fails loudly at import; a lookup of an unknown table raises
# KeyError (fail-closed) instead of building a statement.
_SQLITE_COUNT_SQL: dict[str, str] = {
    "control": 'SELECT COUNT(*) FROM "control"',
    "tasks": 'SELECT COUNT(*) FROM "tasks"',
    "events": 'SELECT COUNT(*) FROM "events"',
    "leases": 'SELECT COUNT(*) FROM "leases"',
    "checkpoints": 'SELECT COUNT(*) FROM "checkpoints"',
    "idempotency": 'SELECT COUNT(*) FROM "idempotency"',
    "queue_accounts": 'SELECT COUNT(*) FROM "queue_accounts"',
}
_PG_COUNT_SQL: dict[str, str] = {
    "control": 'SELECT COUNT(*) FROM "control"',
    "tasks": 'SELECT COUNT(*) FROM "tasks"',
    "events": 'SELECT COUNT(*) FROM "events"',
    "leases": 'SELECT COUNT(*) FROM "leases"',
    "checkpoints": 'SELECT COUNT(*) FROM "checkpoints"',
    "idempotency": 'SELECT COUNT(*) FROM "idempotency"',
    "queue_accounts": 'SELECT COUNT(*) FROM "queue_accounts"',
}
_PG_DELETE_SQL: dict[str, str] = {
    "control": 'DELETE FROM "control"',
    "tasks": 'DELETE FROM "tasks"',
    "events": 'DELETE FROM "events"',
    "leases": 'DELETE FROM "leases"',
    "checkpoints": 'DELETE FROM "checkpoints"',
    "idempotency": 'DELETE FROM "idempotency"',
    "queue_accounts": 'DELETE FROM "queue_accounts"',
}
assert set(_SQLITE_COUNT_SQL) == set(COPY_ORDER)
assert set(_PG_COUNT_SQL) == set(COPY_ORDER)
assert set(_PG_DELETE_SQL) == set(COPY_ORDER)

SCHEMA_SQL_PATH = REPO_ROOT / "scp" / "kernel_storage_pg_schema.sql"


def redact_dsn(dsn: str) -> str:
    try:
        info = psycopg.conninfo.conninfo_to_dict(dsn)
        if info.get("password"):
            info["password"] = "***"
        return psycopg.conninfo.make_conninfo(**info)
    except Exception:
        return "<redacted-dsn>"


def open_sqlite_readonly(path: str) -> sqlite3.Connection:
    src = Path(path)
    if not src.is_file():
        raise SystemExit(f"FAIL: SQLite database not found: {src}")
    uri = f"file:{src.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    # pragma_table_info() as a table-valued function keeps the table name a
    # bound parameter (no dynamic SQL text); rows come back in cid order,
    # identical to PRAGMA table_info, and a missing table yields no rows.
    return [
        row["name"]
        for row in conn.execute(
            "SELECT name FROM pragma_table_info(?) ORDER BY cid", (table,)
        )
    ]


def pg_columns(conn: psycopg.Connection, table: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    ).fetchall()
    return [r[0] if isinstance(r, tuple) else r["column_name"] for r in rows]


def check_blob(row: sqlite3.Row, table: str, idx: int) -> None:
    for key in row.keys():
        if isinstance(row[key], bytes):
            raise SystemExit(
                f"FAIL: BLOB value encountered in {table} row {idx} column '{key}' — "
                "the kernel schema stores no BLOBs; aborting (fail-closed)"
            )


def apply_canonical_schema(conn: psycopg.Connection) -> None:
    """Apply scp/kernel_storage_pg_schema.sql (idempotent CREATE IF NOT EXISTS)."""
    script = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    # strip full-line comments first: the header contains ';' characters
    lines = [ln for ln in script.splitlines() if not ln.strip().startswith("--")]
    for statement in "\n".join(lines).split(";"):
        if statement.strip():
            conn.execute(statement)


def migrate(
    sqlite_path: str,
    pg_dsn: str,
    schema: str | None,
    dry_run: bool,
    truncate: bool,
    batch_size: int,
) -> bool:
    print(f"[1/5] Source SQLite: {Path(sqlite_path).resolve()}")
    print(f"[1/5] Target PG: {redact_dsn(pg_dsn)}" + (f" schema={schema}" if schema else ""))
    src = open_sqlite_readonly(sqlite_path)
    try:
        # source shape check upfront (read-only)
        source_counts: dict[str, int] = {}
        for table in COPY_ORDER:
            cols = sqlite_columns(src, table)
            if not cols:
                raise SystemExit(
                    f"FAIL: table '{table}' missing in source SQLite (fail-closed)"
                )
            # table is a compile-time whitelist entry (COPY_ORDER); the SQL is
            # a per-table literal (_SQLITE_COUNT_SQL), not composed text
            source_counts[table] = src.execute(_SQLITE_COUNT_SQL[table]).fetchone()[0]
        print(f"[2/5] Source row counts: {source_counts}")

        dst = psycopg.connect(pg_dsn, autocommit=False)
        try:
            cur = dst.cursor()
            # Schema resolution. The schema may come from --schema OR from the
            # DSN itself (options='-c search_path=...'). When search_path names
            # a schema that does not exist yet, current_schema() is NULL and
            # unqualified CREATE TABLE fails — resolve and create it (unless
            # dry-run, which must never write).
            if schema is None:
                current = cur.execute("SELECT current_schema()").fetchone()[0]
                if current is None:
                    setting = cur.execute("SELECT current_setting('search_path')").fetchone()[0]
                    first = setting.split(",")[0].strip().strip('"')
                    schema = first if first and first != "$user" else None
                    if schema and dry_run:
                        print(
                            f"[3/5] DRY-RUN: schema '{schema}' (from DSN search_path) does not "
                            "exist yet; it would be created"
                        )
            if schema:
                exists = cur.execute(
                    "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s",
                    (schema,),
                ).fetchone()[0]
                if not exists:
                    if dry_run:
                        print(
                            "[4/5] DRY-RUN: no data written. Would create schema "
                            f"'{schema}' + apply canonical kernel schema + copy:"
                        )
                        for table in COPY_ORDER:
                            print(f"      {table}: {source_counts[table]} rows")
                        dst.rollback()
                        print("[5/5] DRY-RUN complete (no writes performed)")
                        return True
                    cur.execute(
                        pg_sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                            pg_sql.Identifier(schema)
                        )
                    )
                # session-scoped: must survive commits (applies even when the
                # schema pre-existed but DSN options did not set the path)
                cur.execute("SELECT set_config('search_path', %s, false)", (schema,))
            if dry_run:
                dst.rollback()  # dry-run never writes, not even implicitly

            # kernel write-slot (session-level lock: held across commits until
            # unlocked in finally) so a live kernel cannot write mid-migration
            cur.execute("SELECT pg_advisory_lock(%s)", (_WRITE_SLOT_LOCK_KEY,))
            try:
                missing_tables = [t for t in COPY_ORDER if not pg_columns(cur, t)]
                if missing_tables:
                    if dry_run:
                        print(
                            "[3/5] DRY-RUN: target has no kernel schema yet "
                            f"(missing: {missing_tables}); canonical schema would be applied"
                        )
                        print("[4/5] DRY-RUN: would copy:")
                        for table in COPY_ORDER:
                            print(f"      {table}: {source_counts[table]} rows")
                        print("[5/5] DRY-RUN complete (no writes performed)")
                        return True
                    apply_canonical_schema(cur)
                    still_missing = [t for t in COPY_ORDER if not pg_columns(cur, t)]
                    if still_missing:
                        raise SystemExit(
                            f"FAIL: canonical schema application failed for {still_missing}"
                        )
                    # the canonical schema seeds control(id=1) for operational
                    # bootstrap; a migration replaces it with source data in
                    # this same transaction, so drop the seed now
                    cur.execute(_PG_DELETE_SQL["control"])
                    target_counts = {t: 0 for t in COPY_ORDER}
                else:
                    target_counts = {
                        t: cur.execute(_PG_COUNT_SQL[t]).fetchone()[0]
                        for t in COPY_ORDER
                    }
                print(f"[3/5] Target row counts (before): {target_counts}")

                for table in COPY_ORDER:
                    src_cols = sqlite_columns(src, table)
                    dst_cols = pg_columns(cur, table)
                    if src_cols != dst_cols:
                        raise SystemExit(
                            f"FAIL: column mismatch for '{table}': sqlite={src_cols} pg={dst_cols} "
                            "(fail-closed; boot the kernel once on the source DB so ALTERs run, "
                            "or check schema drift)"
                        )

                non_empty = {t: c for t, c in target_counts.items() if c > 0}
                if non_empty and not truncate:
                    if dry_run:
                        print(
                            f"[5/5] DRY-RUN would FAIL: target tables not empty {non_empty} "
                            "and --truncate not given"
                        )
                        return False
                    raise SystemExit(
                        f"FAIL: target tables not empty {non_empty} — use --truncate explicitly "
                        "or choose an empty target (fail-closed, no silent overwrite)"
                    )

                if dry_run:
                    print("[4/5] DRY-RUN: no data written. Would copy:")
                    for table in COPY_ORDER:
                        print(f"      {table}: {source_counts[table]} rows")
                    print("[5/5] DRY-RUN complete (no writes performed)")
                    return True

                if truncate and any(c > 0 for c in target_counts.values()):
                    for table in COPY_ORDER:
                        cur.execute(_PG_DELETE_SQL[table])

                total_copied = 0
                for table in COPY_ORDER:
                    cols = sqlite_columns(src, table)
                    insert_sql = pg_sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                        pg_sql.Identifier(table),
                        pg_sql.SQL(", ").join(pg_sql.Identifier(c) for c in cols),
                        pg_sql.SQL(", ").join([pg_sql.Placeholder()] * len(cols)),
                    )
                    fetched = 0
                    starts = list(range(0, source_counts[table], batch_size)) or [0]
                    for start in starts:
                        rows = src.execute(
                            # table is a compile-time whitelist entry (COPY_ORDER)
                            f'SELECT * FROM "{table}" LIMIT ? OFFSET ?',
                            (batch_size, start),
                        ).fetchall()
                        if not rows:
                            break
                        payload = []
                        for idx, row in enumerate(rows):
                            check_blob(row, table, start + idx)
                            payload.append(tuple(row))
                        cur.executemany(insert_sql, payload)
                        fetched += len(rows)
                    total_copied += fetched
                    print(f"      copied {table}: {fetched}/{source_counts[table]} rows")

                # post-copy verification inside the same transaction
                mismatches = []
                for table in COPY_ORDER:
                    after = cur.execute(_PG_COUNT_SQL[table]).fetchone()[0]
                    if after != source_counts[table]:
                        mismatches.append((table, source_counts[table], after))
                if mismatches:
                    raise SystemExit(
                        f"FAIL: post-copy count mismatch {mismatches} — transaction rolled back"
                    )
                dst.commit()
                print(
                    f"[4/5] Copied {total_copied} rows; count verification: "
                    f"OK for all {len(COPY_ORDER)} tables"
                )
                print("[5/5] Migration committed")
                return True
            finally:
                try:
                    if dst.info.transaction_status == 3:  # INERROR: clear before unlock
                        dst.rollback()
                    cur.execute("SELECT pg_advisory_unlock(%s)", (_WRITE_SLOT_LOCK_KEY,))
                except psycopg.Error:
                    pass  # lock is released when the connection closes anyway
        except SystemExit:
            dst.rollback()
            raise
        except Exception:
            dst.rollback()
            raise
        finally:
            dst.close()
    finally:
        src.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sqlite", required=True, help="path to the source SQLite kernel DB")
    parser.add_argument("--pg-dsn", required=True, help="PostgreSQL DSN (password stays off output)")
    parser.add_argument("--schema", default=None, help="optional PG schema (created if absent)")
    parser.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    parser.add_argument("--truncate", action="store_true", help="DELETE existing target rows first (explicit)")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args(argv)
    try:
        ok = migrate(
            sqlite_path=args.sqlite,
            pg_dsn=args.pg_dsn,
            schema=args.schema,
            dry_run=args.dry_run,
            truncate=args.truncate,
            batch_size=max(1, args.batch_size),
        )
    except SystemExit as exc:
        print(str(exc))
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI boundary: report and fail-closed
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 2
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
