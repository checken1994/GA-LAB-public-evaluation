"""Chaos tests: PgKernelStorage under real failure injection (Track C1 session 2).

Failure scenarios run against a REAL PostgreSQL (docker postgres:16-alpine),
no mocks:

(a) Backend connection killed (``pg_terminate_backend``) with a write
    transaction in flight -> the in-flight write must be lost (rolled back by
    the server), the killed instance must fail LOUDLY (sqlite3.OperationalError,
    the SQLite-parity error type), and a fresh instance must recover with an
    intact journal hash-chain and no corruption.
(b) PostgreSQL server restart between a claim and the next operation -> the
    stale connection fails with the parity error type, and after boot recovery
    the task is recoverable end-to-end (LEASED -> RECOVERING -> QUEUED ->
    re-claimable by a new worker).
(c) Two OS processes race ``claim_next`` on the same queued task (real
    multiprocessing, real separate connections) -> exactly one lease.
(d) ``backup_to`` -> pg_dump snapshot -> restore into a brand-new database ->
    ``verify_integrity`` + projection match the source.

Infra notes:
- Requires ``SCP_PG_TEST_DSN`` (declared infra-skip when absent — no assertion
  hidden). Unreachable server -> INFRA-SKIP with the original error visible.
- Scenario (b) uses the docker CLI to restart the container named by
  ``SCP_PG_TEST_CONTAINER`` (default ``scp-pg-test`` — the container from the
  docker hint in test_pg_storage_parity.py).
- The host may not ship pg_dump/psql. Scenario (d) still exercises the REAL
  pg_dump binary shipped inside the postgres container through a small
  test-support shim placed on PATH (the product's ``backup_to`` runs its real
  subprocess path; the shim only relocates the pg_dump executable). The
  restore runs the container's real psql against a freshly created database.
- DSN passwords are never printed; failures surface only redacted context.
"""
from __future__ import annotations

import json
import multiprocessing
import os
import re
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg import sql as pg_sql

from scp.kernel_storage_pg import PgKernelStorage
from scp.task_kernel import TaskKernel

PG_DSN_ENV = "SCP_PG_TEST_DSN"
PG_CONTAINER_ENV = "SCP_PG_TEST_CONTAINER"
DEFAULT_CONTAINER = "scp-pg-test"
RESTORE_DB = "scpkernel_chaos_restore"
# Fixed restore-target DDL: pure module-level literals (no dynamic SQL text —
# the database name is a compile-time constant, RESTORE_DB). Pinned at import
# so any drift between the literals and RESTORE_DB fails loudly.
_RESTORE_DB_SQL_DROP = "DROP DATABASE IF EXISTS scpkernel_chaos_restore WITH (FORCE)"
_RESTORE_DB_SQL_CREATE = "CREATE DATABASE scpkernel_chaos_restore"
assert RESTORE_DB in _RESTORE_DB_SQL_DROP and RESTORE_DB in _RESTORE_DB_SQL_CREATE

_TS_KEYS = frozenset(
    {"created_at", "updated_at", "issued_at", "expires_at", "heartbeat_at", "last_dispatch_at"}
)
_DERIVED_HASH_KEYS = frozenset({"event_hash", "prev_event_hash", "payload_hash"})
_TOKEN_RES = (
    (re.compile(r"evt_[0-9a-f]+"), "<evt>"),
    (re.compile(r"lease_[0-9a-f]+"), "<lease>"),
    (re.compile(r"cp_[0-9a-f]+"), "<cp>"),
    (re.compile(r"attempt_[0-9a-f]+"), "<attempt>"),
)


# --------------------------------------------------------------------------- #
# fixtures                                                                    #
# --------------------------------------------------------------------------- #
def _base_dsn() -> str:
    dsn = os.environ.get(PG_DSN_ENV, "").strip()
    if not dsn:
        pytest.skip(
            f"{PG_DSN_ENV} not set — PG chaos needs a real PostgreSQL "
            "(docker run -d --rm --name scp-pg-test -e POSTGRES_PASSWORD=scppg "
            "-e POSTGRES_DB=scpkernel -p 55432:5432 postgres:16-alpine); "
            "declared infra-skip (no assertion hidden)"
        )
    return dsn


@pytest.fixture()
def pg_dsn() -> str:
    """Schema-scoped DSN; each test gets an isolated schema, dropped after.

    Teardown reconnects because chaos scenarios (a)/(b) deliberately kill or
    restart the server, which would invalidate the schema-creation connection.
    """
    base = _base_dsn()
    schema = f"scp_chaos_{uuid.uuid4().hex[:10]}"
    assert re.fullmatch(r"scp_chaos_[0-9a-f]{10}", schema)
    admin = psycopg.connect(base, autocommit=True, connect_timeout=5)
    try:
        try:
            # schema name is a self-generated, regex-pinned identifier; it
            # reaches SQL only through psycopg.sql.Identifier (sanctioned
            # dynamic-identifier path, same shape as the C1 migration script)
            admin.execute(
                pg_sql.SQL("CREATE SCHEMA {}").format(pg_sql.Identifier(schema))
            )
        except psycopg.OperationalError as exc:
            pytest.skip(f"INFRA-SKIP: PostgreSQL unreachable ({exc})")
        scoped = psycopg.conninfo.make_conninfo(base, options=f"-c search_path={schema}")
        yield scoped
    finally:
        try:
            admin.close()
        except psycopg.Error:
            pass
        deadline = time.time() + 90.0
        while True:
            try:
                dropper = psycopg.connect(base, autocommit=True, connect_timeout=3)
                try:
                    dropper.execute(
                        pg_sql.SQL("DROP SCHEMA {} CASCADE").format(
                            pg_sql.Identifier(schema)
                        )
                    )
                finally:
                    dropper.close()
                break
            except psycopg.Error:
                if time.time() >= deadline:
                    raise RuntimeError(
                        "could not reconnect to PostgreSQL to drop the chaos schema"
                    )
                time.sleep(1.0)


@pytest.fixture()
def pg_admin():
    base = _base_dsn()
    admin = psycopg.connect(base, autocommit=True, connect_timeout=5)
    try:
        yield admin
    finally:
        admin.close()


def _new_kernel(scoped_dsn: str) -> TaskKernel:
    return TaskKernel(storage=PgKernelStorage(scoped_dsn))


def _wait_pg_ready(base_dsn: str, timeout_s: float = 120.0) -> None:
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            conn = psycopg.connect(base_dsn, connect_timeout=3)
            conn.execute("SELECT 1")
            conn.close()
            return
        except psycopg.Error as exc:
            last_exc = exc
            time.sleep(1.0)
    pytest.fail(f"PostgreSQL did not come back after restart (infra failure; redacted DSN): {type(last_exc).__name__}")


def _queued_task(kernel: TaskKernel, task_id: str, owner: str, risk: str = "R1") -> None:
    kernel.create_task(task_id, owner, f"chaos goal {task_id}", risk_tier=risk)
    for state in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, state)


def _journal_chains_valid(kernel: TaskKernel) -> list[str]:
    invalid = []
    for row in kernel.conn.fetchall("SELECT DISTINCT task_id FROM events"):
        result = kernel.verify_journal(row["task_id"])
        if not result["hash_chain_valid"]:
            invalid.append(row["task_id"])
    return invalid


def _norm(obj: Any) -> Any:
    if isinstance(obj, str):
        for rx, rep in _TOKEN_RES:
            obj = rx.sub(rep, obj)
        return obj
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in _TS_KEYS:
                out[k] = "<ts>"
            elif k in _DERIVED_HASH_KEYS:
                out[k] = "<hash>"
            else:
                out[k] = _norm(v)
        return {k: out[k] for k in sorted(out)}
    if isinstance(obj, (list, tuple)):
        return [_norm(v) for v in obj]
    return obj


# --------------------------------------------------------------------------- #
# (a) kill backend connection mid-transaction                                  #
# --------------------------------------------------------------------------- #
def test_pg_chaos_kill_backend_mid_transaction_no_corruption(pg_dsn: str, pg_admin) -> None:
    k = _new_kernel(pg_dsn)
    try:
        _queued_task(k, "chaos-kill-a", "kill-owner")
        pre_version = k.get_task("chaos-kill-a")["version"]

        # Open the kernel write slot and stage an UNCOMMITTED mutation.
        k.conn.begin()
        k.conn.execute(
            "UPDATE tasks SET version=version+1 WHERE task_id='chaos-kill-a'"
        )

        # Chaos: terminate the storage backend process (pool terminate analogue).
        # Only this test's connections exist for the harness, so excluding the
        # admin connection itself is sufficient targeting.
        terminated = pg_admin.execute(
            "SELECT pg_terminate_backend(pid) AS terminated FROM pg_stat_activity "
            "WHERE datname = current_database() AND pid <> pg_backend_pid()"
        ).fetchall()
        assert len(terminated) >= 1, "expected at least one backend to terminate"

        # The killed instance must fail LOUDLY, not silently succeed.
        with pytest.raises(sqlite3.OperationalError):
            k.conn.execute("SELECT 1")
        with pytest.raises(sqlite3.OperationalError):
            k.conn.commit()
    finally:
        k.close()  # must tolerate dead connections during teardown

    # Recovery on a fresh instance: in-flight write lost, nothing corrupt.
    k2 = _new_kernel(pg_dsn)
    try:
        task = k2.get_task("chaos-kill-a")
        assert task["version"] == pre_version, "uncommitted write must be rolled back"
        assert task["state"] == "QUEUED"

        integrity = k2.verify_integrity()
        assert integrity["quick_check"] == "ok"
        assert integrity["invalid_chains"] == []
        assert _journal_chains_valid(k2) == []

        report = k2.recover_on_boot()
        assert report["corrupted"] == []
    finally:
        k2.close()


# --------------------------------------------------------------------------- #
# (b) PostgreSQL server restart between claim and next operation               #
# --------------------------------------------------------------------------- #
def test_pg_chaos_server_restart_between_claim_lock_type_and_recovery(pg_dsn: str) -> None:
    base = _base_dsn()
    container = os.environ.get(PG_CONTAINER_ENV, DEFAULT_CONTAINER).strip()

    k1 = _new_kernel(pg_dsn)
    try:
        _queued_task(k1, "chaos-restart-t", "restart-owner")
        lease = k1.claim_next("worker-pre-restart", ttl_seconds=120.0)
        assert lease is not None and lease.task_id == "chaos-restart-t"

        # Chaos: restart the PostgreSQL server under the live lease.
        proc = subprocess.run(
            ["docker", "restart", container],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            pytest.fail(
                "INFRA-FAIL: docker restart of the PG test container failed "
                f"(rc={proc.returncode}): {proc.stderr[-300:]}"
            )

        # The stale instance's operations raise the SQLite-parity error type —
        # the kernel contract for a dead backend is sqlite3.OperationalError
        # (same type the SQLite backend raises for 'database is locked').
        # NOTE: this must happen BEFORE close(): the storage re-creates a
        # healthy per-thread connection once the server is back, and the
        # kernel correctly refuses via lease authority (StaleLease) instead.
        with pytest.raises(sqlite3.OperationalError):
            k1.heartbeat("chaos-restart-t", lease.lease_id, extend_seconds=5.0)
    finally:
        k1.close()  # tolerate dead connections

    _wait_pg_ready(base)

    # Post-restart recovery: boot replay must recover the leased task and the
    # task must be recoverable end-to-end (re-claimable by a new worker).
    k2 = _new_kernel(pg_dsn)
    try:
        report = k2.recover_on_boot()
        assert report["corrupted"] == []
        recovered = {entry["task_id"]: entry for entry in report["recovered"]}
        assert recovered["chaos-restart-t"]["to"] == "RECOVERING"

        task = k2.get_task("chaos-restart-t")
        assert task["state"] == "RECOVERING"
        assert task["active_lease_id"] is None

        k2.transition("chaos-restart-t", "QUEUED", actor="chaos-recovery")
        lease2 = k2.claim_next("worker-post-restart", ttl_seconds=30.0)
        assert lease2 is not None and lease2.task_id == "chaos-restart-t"
        assert lease2.lease_id != lease.lease_id

        assert _journal_chains_valid(k2) == []
        integrity = k2.verify_integrity()
        assert integrity["quick_check"] == "ok"
        assert integrity["invalid_chains"] == []
    finally:
        k2.close()


# --------------------------------------------------------------------------- #
# (c) two OS processes race claim_next -> exactly one lease                    #
# --------------------------------------------------------------------------- #
def _claim_child(
    scoped_dsn: str, worker_id: str, start_file: str, result_file: str
) -> None:
    """Child process body: wait for the start signal, then race the claim.

    Runs in a spawned interpreter that re-imports this module; must stay
    import-safe (no side effects at module import — see bottom of file).
    """
    result: dict[str, Any]
    try:
        while not Path(start_file).exists():
            time.sleep(0.02)
        kernel = TaskKernel(storage=PgKernelStorage(scoped_dsn))
        try:
            lease = kernel.claim_next(worker_id, ttl_seconds=30.0)
            result = {
                "got": lease is not None,
                "task_id": lease.task_id if lease else None,
                "lease_id": lease.lease_id if lease else None,
                "fencing_token": lease.fencing_token if lease else None,
                "worker_id": worker_id,
            }
        finally:
            kernel.close()
    except Exception as exc:  # surfaced to the parent, never swallowed
        result = {"got": False, "worker_id": worker_id, "error": f"{type(exc).__name__}: {exc}"}
    Path(result_file).write_text(json.dumps(result), encoding="utf-8")


def test_pg_chaos_two_process_claim_race_single_lease(pg_dsn: str, tmp_path: Path) -> None:
    k = _new_kernel(pg_dsn)
    try:
        _queued_task(k, "chaos-race-1", "race-owner")
    finally:
        k.close()

    ctx = multiprocessing.get_context("spawn")
    start_file = tmp_path / "race_start"
    procs = []
    result_files = []
    for i in range(2):
        result_file = tmp_path / f"race_result_{i}.json"
        p = ctx.Process(
            target=_claim_child,
            args=(pg_dsn, f"race-worker-{i}", str(start_file), str(result_file)),
        )
        p.start()
        procs.append(p)
        result_files.append(result_file)

    start_file.write_text("go", encoding="utf-8")
    try:
        for p in procs:
            p.join(timeout=180)
    finally:
        for p in procs:
            if p.is_alive():
                p.terminate()
    assert all(p.exitcode == 0 for p in procs), "claim child processes crashed"

    results = [json.loads(f.read_text(encoding="utf-8")) for f in result_files]
    winners = [r for r in results if r.get("got")]
    losers = [r for r in results if not r.get("got")]
    assert len(winners) == 1, f"exactly one lease expected, got {len(winners)}"
    assert len(losers) == 1
    # A loser must be a clean 'no eligible task', never a storage error.
    assert "error" not in losers[0], losers[0]

    winner = winners[0]
    assert winner["task_id"] == "chaos-race-1"
    assert winner["worker_id"] in {"race-worker-0", "race-worker-1"}

    # Persistence agrees: exactly one unreleased lease, one LEASE_GRANTED event.
    k2 = _new_kernel(pg_dsn)
    try:
        task = k2.get_task("chaos-race-1")
        assert task["state"] == "LEASED"
        assert task["active_lease_id"] == winner["lease_id"]
        lease_rows = k2.conn.fetchall(
            "SELECT lease_id, released FROM leases WHERE task_id='chaos-race-1'"
        )
        assert len(lease_rows) == 1
        granted = k2.conn.fetchall(
            "SELECT seq FROM events WHERE task_id='chaos-race-1' AND type='LEASE_GRANTED'"
        )
        assert len(granted) == 1
        assert _journal_chains_valid(k2) == []
    finally:
        k2.close()


# --------------------------------------------------------------------------- #
# (d) backup_to -> pg_dump -> restore into a new DB -> integrity + projection  #
# --------------------------------------------------------------------------- #
_PG_DUMP_SHIM = '''"""Test-support shim: proxy pg_dump to the postgres container binary.

The host may not ship pg_dump; the product's PgKernelStorage.backup_to only
requires a pg_dump executable on PATH. This shim runs the REAL pg_dump binary
inside the test's postgres container and writes the plain-format SQL dump to
the requested host path. Fail-closed: non-zero exit when pg_dump fails.
"""
import os
import subprocess
import sys
from pathlib import Path


def main(argv):
    args = argv[1:]
    container = os.environ.get("SCP_PG_TEST_CONTAINER", "scp-pg-test").strip() or "scp-pg-test"
    outfile = None
    rest = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--file":
            outfile = args[i + 1]
            i += 2
            continue
        if arg in ("--host", "--port"):
            # Inside the container the server is reached via its local socket;
            # host-side address/port mapping is irrelevant to the dump itself.
            i += 2
            continue
        rest.append(arg)
        i += 1
    cmd = ["docker", "exec"]
    if os.environ.get("PGPASSWORD"):
        cmd += ["-e", "PGPASSWORD=" + os.environ["PGPASSWORD"]]
    cmd += [container, "pg_dump", *rest]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.buffer.write(proc.stderr[-800:])
        return proc.returncode
    if outfile is None:
        sys.stdout.buffer.write(proc.stdout)
    else:
        Path(outfile).write_bytes(proc.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
'''

_PG_DUMP_CMD = '''@echo off
python "%~dp0pg_dump_shim.py" %*
'''


@pytest.fixture()
def pg_dump_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Put a container-proxy pg_dump on PATH (real binary, test-support shim)."""
    shim_dir = tmp_path / "pg_shim"
    shim_dir.mkdir()
    (shim_dir / "pg_dump_shim.py").write_text(_PG_DUMP_SHIM, encoding="utf-8")
    (shim_dir / "pg_dump.cmd").write_text(_PG_DUMP_CMD, encoding="utf-8")
    monkeypatch.setenv("PATH", str(shim_dir) + os.pathsep + os.environ.get("PATH", ""))


def test_pg_chaos_backup_to_pg_dump_restore_round_trip(
    pg_dsn: str, pg_admin, pg_dump_on_path: None, tmp_path: Path
) -> None:
    k = _new_kernel(pg_dsn)
    try:
        # Distinctive source state: one COMPLETED task via the real lifecycle,
        # one QUEUED task, and the global kill switch ON (control row state).
        _queued_task(k, "chaos-bk-done", "bk-owner", risk="R2")
        lease = k.claim_next("bk-worker", ttl_seconds=60.0)
        assert lease is not None and lease.task_id == "chaos-bk-done"
        k.start("chaos-bk-done", lease.lease_id)
        k.transition("chaos-bk-done", "VERIFYING", lease_id=lease.lease_id)
        k.commit_completed(
            "chaos-bk-done",
            lease.lease_id,
            verifier_verdict="VERIFIED",
            evidence_ref="evidence://chaos-bk-out",
        )
        _queued_task(k, "chaos-bk-queued", "bk-owner-2")
        k.set_global_kill(True, actor="chaos-operator")

        source_snapshot = {
            "tasks": _norm(k.conn.fetchall("SELECT * FROM tasks ORDER BY task_id")),
            "control": _norm(k.conn.fetchall("SELECT * FROM control ORDER BY id")),
            "event_counts": {
                r["task_id"]: int(r["n"])
                for r in k.conn.fetchall(
                    "SELECT task_id, COUNT(*) AS n FROM events GROUP BY task_id ORDER BY task_id"
                )
            },
        }

        dump_path = tmp_path / "chaos_dump.sql"
        k.conn.backup_to(dump_path)

        # A real plain-format SQL dump landed on the host.
        assert dump_path.stat().st_size > 0
        dump_text = dump_path.read_text(encoding="utf-8", errors="replace")
        assert "CREATE TABLE" in dump_text
        assert "PostgreSQL database dump" in dump_text
    finally:
        k.close()

    try:
        # Fresh target database (fail loud on restore errors).
        pg_admin.execute(_RESTORE_DB_SQL_DROP)
        pg_admin.execute(_RESTORE_DB_SQL_CREATE)
        with open(dump_path, "rb") as dump_fh:
            proc = subprocess.run(
                ["docker", "exec", "-i",
                 os.environ.get(PG_CONTAINER_ENV, DEFAULT_CONTAINER).strip(),
                 "psql", "-U", "postgres", "-d", RESTORE_DB, "-v", "ON_ERROR_STOP=1", "-q"],
                stdin=dump_fh,
                capture_output=True,
                timeout=120,
            )
        assert proc.returncode == 0, (
            "psql restore failed (rc=%s): %s" % (proc.returncode, proc.stderr[-500:].decode("utf-8", "replace"))
        )

        # Open the kernel on the restored database (same schema name).
        info = psycopg.conninfo.conninfo_to_dict(pg_dsn)
        info["dbname"] = RESTORE_DB
        restored_dsn = psycopg.conninfo.make_conninfo(**info)
        kr = _new_kernel(restored_dsn)
        try:
            integrity = kr.verify_integrity()
            assert integrity["quick_check"] == "ok"
            assert integrity["invalid_chains"] == []
            assert _journal_chains_valid(kr) == []

            restored_snapshot = {
                "tasks": _norm(kr.conn.fetchall("SELECT * FROM tasks ORDER BY task_id")),
                "control": _norm(kr.conn.fetchall("SELECT * FROM control ORDER BY id")),
                "event_counts": {
                    r["task_id"]: int(r["n"])
                    for r in kr.conn.fetchall(
                        "SELECT task_id, COUNT(*) AS n FROM events GROUP BY task_id ORDER BY task_id"
                    )
                },
            }
            assert restored_snapshot == source_snapshot, "restored projection diverged"

            # Semantic sanity: the restored kernel is operational, not a husk.
            assert kr.get_task("chaos-bk-done")["state"] == "COMPLETED"
            assert kr.get_task("chaos-bk-queued")["state"] == "QUEUED"
            control = kr.conn.fetchone("SELECT global_kill FROM control WHERE id=1")
            assert int(control["global_kill"]) == 1
        finally:
            kr.close()
    finally:
        pg_admin.execute(_RESTORE_DB_SQL_DROP)
