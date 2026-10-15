"""End-to-end migration test: synthetic SQLite kernel DB -> real PostgreSQL.

Runs scripts/migrate_kernel_sqlite_to_pg.py as a subprocess against a
synthetic TaskKernel SQLite database and a REAL PostgreSQL (docker). The
migration must be atomic, verify row counts per table, refuse to overwrite a
non-empty target without --truncate, and treat --dry-run as read-only.

Postgres is REAL (no mocks): requires ``SCP_PG_TEST_DSN``; absent -> declared
infra-skip with explicit reason.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import sql as pg_sql

from scp.kernel_storage_pg import KERNEL_TABLES
from scp.task_kernel import TaskKernel

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATE_SCRIPT = REPO_ROOT / "scripts" / "migrate_kernel_sqlite_to_pg.py"
PG_DSN_ENV = "SCP_PG_TEST_DSN"

# Per-table compile-time literal COUNT statements for the kernel tables (no
# dynamic SQL text: table identifiers reach SQL only through this literal map,
# same safe pattern as the migration script's _SQLITE_COUNT_SQL/_PG_COUNT_SQL).
# Pinned to KERNEL_TABLES so drift fails loudly at import; an unknown table
# raises KeyError (fail-closed) instead of building a statement.
_COUNT_SQL_BY_TABLE: dict[str, str] = {
    "checkpoints": 'SELECT COUNT(*) FROM "checkpoints"',
    "control": 'SELECT COUNT(*) FROM "control"',
    "events": 'SELECT COUNT(*) FROM "events"',
    "idempotency": 'SELECT COUNT(*) FROM "idempotency"',
    "leases": 'SELECT COUNT(*) FROM "leases"',
    "queue_accounts": 'SELECT COUNT(*) FROM "queue_accounts"',
    "tasks": 'SELECT COUNT(*) FROM "tasks"',
}
assert set(_COUNT_SQL_BY_TABLE) == set(KERNEL_TABLES)


@pytest.fixture()
def pg_admin_dsn() -> str:
    dsn = os.environ.get(PG_DSN_ENV, "").strip()
    if not dsn:
        pytest.skip(
            f"{PG_DSN_ENV} not set — migration test needs a real PostgreSQL "
            "(docker run -d --rm --name scp-pg-test -e POSTGRES_PASSWORD=scppg "
            "-e POSTGRES_DB=scpkernel -p 55432:5432 postgres:16-alpine); "
            "declared infra-skip (no assertion hidden)"
        )
    return dsn


def _build_synthetic_sqlite(path: Path) -> dict[str, int]:
    """Create a realistic kernel DB via the real kernel (includes ALTERed columns)."""
    kernel = TaskKernel(path)
    kernel.create_task("mig-a", "owner-A", "migrate me A", risk_tier="R1", priority=3)
    kernel.create_task("mig-b", "owner-B", "migrate me B", risk_tier="R0", priority=5)
    kernel.create_task("mig-c", "owner-C", "migrate me C", risk_tier="R2", priority=1)
    for tid in ("mig-a", "mig-b"):
        for state in ("PLANNING", "READY", "QUEUED"):
            kernel.transition(tid, state)
    lease = kernel.claim_next("worker-mig", ttl_seconds=300.0)
    assert lease is not None and lease.task_id == "mig-a"
    kernel.start("mig-a", lease.lease_id)
    kernel.set_global_kill(True)
    kernel.set_global_kill(False)
    kernel.set_task_kill("mig-c")
    kernel.close()
    # snapshot per-table counts via a read-only connection
    import sqlite3

    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return {
            t: conn.execute(_COUNT_SQL_BY_TABLE[t]).fetchone()[0]
            for t in sorted(KERNEL_TABLES)
        }
    finally:
        conn.close()


def _run_migrate(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MIGRATE_SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def _pg_table_counts(dsn: str, schema: str) -> dict[str, int]:
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('search_path', %s, false)", (schema,))
            return {
                t: cur.execute(_COUNT_SQL_BY_TABLE[t]).fetchone()[0]
                for t in sorted(KERNEL_TABLES)
            }


def _schema_exists(dsn: str, schema: str) -> bool:
    with psycopg.connect(dsn, autocommit=True) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s",
            (schema,),
        ).fetchone()
        return (row[0] if isinstance(row, tuple) else row["count"]) > 0


def test_migrate_sqlite_to_pg_end_to_end(pg_admin_dsn: str, tmp_path: Path) -> None:
    schema = f"scp_mig_{uuid.uuid4().hex[:10]}"
    assert schema.startswith("scp_mig_") and schema.isidentifier()
    sqlite_db = tmp_path / "kernel.sqlite3"
    expected = _build_synthetic_sqlite(sqlite_db)
    target_dsn = psycopg.conninfo.make_conninfo(
        pg_admin_dsn, options=f"-c search_path={schema}"
    )

    # 1) dry-run on empty target: reports plan, writes NOTHING
    result = _run_migrate(
        ["--sqlite", str(sqlite_db), "--pg-dsn", str(target_dsn), "--dry-run"]
    )
    assert result.returncode == 0, result.stderr[-800:]
    assert "DRY-RUN complete (no writes performed)" in result.stdout
    assert not _schema_exists(pg_admin_dsn, schema), "dry-run must not create anything"

    # 2) real migration
    result = _run_migrate(["--sqlite", str(sqlite_db), "--pg-dsn", str(target_dsn)])
    assert result.returncode == 0, result.stderr[-800:]
    assert "count verification: OK" in result.stdout
    assert _pg_table_counts(pg_admin_dsn, schema) == expected

    # 3) re-run without --truncate must fail-closed (no silent overwrite)
    result = _run_migrate(["--sqlite", str(sqlite_db), "--pg-dsn", str(target_dsn)])
    assert result.returncode == 2
    assert "not empty" in result.stdout
    assert _pg_table_counts(pg_admin_dsn, schema) == expected, "failed run must not change data"

    # 4) re-run WITH --truncate is idempotent
    result = _run_migrate(
        ["--sqlite", str(sqlite_db), "--pg-dsn", str(target_dsn), "--truncate"]
    )
    assert result.returncode == 0, result.stderr[-800:]
    assert _pg_table_counts(pg_admin_dsn, schema) == expected

    # 5) migrated kernel semantics intact: open PG kernel, verify journal chains
    from scp.kernel_storage_pg import PgKernelStorage

    k = TaskKernel(storage=PgKernelStorage(target_dsn))
    try:
        assert k.get_task("mig-a")["state"] == "RUNNING"  # claimed + started pre-migration
        assert k.get_task("mig-c")["state"] == "CANCELLED"
        report = k.recover_on_boot()
        assert report["corrupted"] == [], "journal hash chain must survive migration"
        integrity = k.verify_integrity()
        assert integrity["quick_check"] == "ok"
        assert integrity["invalid_chains"] == []
        assert integrity["tasks"] == 4  # 3 tasks + the __global__ kill-switch journal
    finally:
        k.close()

    # cleanup
    with psycopg.connect(pg_admin_dsn, autocommit=True) as conn:
        # schema name is self-generated (regex-pinned in the test); it reaches
        # SQL only through psycopg.sql.Identifier
        conn.execute(
            pg_sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                pg_sql.Identifier(schema)  # self-generated name
            )
        )


def test_migrate_missing_source_fails_closed(pg_admin_dsn: str, tmp_path: Path) -> None:
    result = _run_migrate(
        [
            "--sqlite",
            str(tmp_path / "missing.sqlite3"),
            "--pg-dsn",
            pg_admin_dsn,
        ]
    )
    assert result.returncode == 2
    assert "FAIL" in result.stdout
