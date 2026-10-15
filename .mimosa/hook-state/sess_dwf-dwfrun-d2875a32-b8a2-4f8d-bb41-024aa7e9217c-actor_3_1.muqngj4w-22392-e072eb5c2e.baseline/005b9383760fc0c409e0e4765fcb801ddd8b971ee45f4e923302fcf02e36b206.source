"""Dual-backend parity: PgKernelStorage vs SQLiteKernelStorage (Track C1).

The SAME deterministic TaskKernel operation sequence (create/transition,
journal append, lease claim + heartbeat + release + fencing, checkpoint,
idempotency claim/complete, kill switch, rebuild, recovery) runs against the
SQLite backend (tmp file) and against a REAL PostgreSQL backend, then the
projections and journal events are compared after normalizing only the
nondeterministic fields (random ids, timestamps). Journal hash-chain validity
is asserted per backend separately because event ids/hashes are random by
design (idempotent event IDs).

Postgres is REAL (no mocks): tests require ``SCP_PG_TEST_DSN``. When the env
var is absent the PG tests skip with an explicit reason — this is a declared
infra-skip, not a skip to hide a failing assertion. When the env var IS set
but the server is unreachable, the test also skips with the connection error
surfaced in the reason (INFRA-SKIP prefix) so the cause is visible in logs.

Unit-level translator tests in this file always run (no Postgres needed).
"""
from __future__ import annotations

import os
import re
import uuid
from typing import Any

import psycopg
import pytest
from psycopg import sql as pg_sql

from scp.kernel_storage import SQLiteKernelStorage, make_storage
from scp.kernel_storage_pg import PgKernelStorage, translate_sqlite_sql
from scp.task_kernel import TaskKernel

PG_DSN_ENV = "SCP_PG_TEST_DSN"
_DOCKER_HINT = (
    "docker run -d --rm --name scp-pg-test -e POSTGRES_PASSWORD=scppg "
    "-e POSTGRES_DB=scpkernel -p 55432:5432 postgres:16-alpine"
)
_SCHEMA_NAME_RE = re.compile(r"scp_parity_[0-9a-f]{10}")


# --------------------------------------------------------------------------- #
# fixtures                                                                    #
# --------------------------------------------------------------------------- #
@pytest.fixture()
def pg_storage() -> Any:
    dsn = os.environ.get(PG_DSN_ENV, "").strip()
    if not dsn:
        pytest.skip(
            f"{PG_DSN_ENV} not set — PG parity needs a real PostgreSQL ({_DOCKER_HINT}); "
            "declared infra-skip (no assertion hidden)"
        )
    schema = f"scp_parity_{uuid.uuid4().hex[:10]}"
    assert _SCHEMA_NAME_RE.fullmatch(schema)
    admin = psycopg.connect(dsn, autocommit=True, connect_timeout=5)
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
        # keyword/value pairs cannot be appended to a URI conninfo; use
        # make_conninfo so the base DSN may be URI or keyword form.
        scoped_dsn = psycopg.conninfo.make_conninfo(
            dsn, options=f"-c search_path={schema}"
        )
        storage = PgKernelStorage(scoped_dsn)
        try:
            yield storage
        finally:
            storage.close()
    finally:
        try:
            admin.execute(
                pg_sql.SQL("DROP SCHEMA {} CASCADE").format(pg_sql.Identifier(schema))
            )
        finally:
            admin.close()


# --------------------------------------------------------------------------- #
# normalization                                                               #
# --------------------------------------------------------------------------- #
_TOKEN_RES = (
    (re.compile(r"evt_[0-9a-f]+"), "<evt>"),
    (re.compile(r"lease_[0-9a-f]+"), "<lease>"),
    (re.compile(r"cp_[0-9a-f]+"), "<cp>"),
    (re.compile(r"attempt_[0-9a-f]+"), "<attempt>"),
)
_TS_KEYS = frozenset(
    {"created_at", "updated_at", "issued_at", "expires_at", "heartbeat_at", "last_dispatch_at"}
)
# Hashes derived from content containing random ids are nondeterministic by
# design; their integrity is enforced separately by the per-backend journal
# hash-chain validation.
_DERIVED_HASH_KEYS = frozenset({"event_hash", "prev_event_hash", "payload_hash"})


def _norm(obj: Any) -> Any:
    """Normalize nondeterministic fields for cross-backend comparison."""
    import dataclasses

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        obj = dataclasses.asdict(obj)
    if isinstance(obj, str):
        # Backend vendor wording for integrity violations differs
        # (sqlite 'UNIQUE constraint failed: t.c' vs PG 'duplicate key value
        # violates unique constraint ...'); the kernel contract is the
        # StorageIntegrityError type + fail-closed rollback, not vendor text.
        if obj.startswith("StorageIntegrityError:"):
            obj = "StorageIntegrityError: <integrity-violation>"
        else:
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


def _rows(kernel: TaskKernel, sql: str, params: tuple[Any, ...] = ()) -> list[dict]:
    return [dict(r) for r in kernel.conn.fetchall(sql, params)]


def _projection(kernel: TaskKernel) -> dict[str, Any]:
    import json

    events = []
    for row in _rows(kernel, "SELECT * FROM events ORDER BY task_id, seq"):
        row = dict(row)
        if row.get("payload_json"):
            # payload hashes derived from random-id content are normalized via
            # the dict branch of _norm; re-serialize with the kernel's format.
            payload = _norm(json.loads(row["payload_json"]))
            row["payload_json"] = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        events.append(row)
    return {
        "control": _rows(kernel, "SELECT * FROM control ORDER BY id"),
        "tasks": _rows(kernel, "SELECT * FROM tasks ORDER BY task_id"),
        "events": events,
        "leases": _rows(kernel, "SELECT * FROM leases ORDER BY task_id, fencing_token"),
        "checkpoints": _rows(kernel, "SELECT * FROM checkpoints ORDER BY task_id, attempt_id, step_id"),
        "idempotency": _rows(kernel, "SELECT * FROM idempotency ORDER BY logical_key"),
        "queue_accounts": _rows(kernel, "SELECT * FROM queue_accounts ORDER BY owner"),
    }


# --------------------------------------------------------------------------- #
# deterministic parity sequence                                               #
# --------------------------------------------------------------------------- #
def run_parity_sequence(make_kernel: Any) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    ctx: dict[str, Any] = {}

    def record(name: str, fn: Any) -> None:
        try:
            records.append({"step": name, "outcome": "ok", "value": _norm(fn())})
        except Exception as exc:  # errors are part of the contract; recorded
            records.append(
                {"step": name, "outcome": "err", "value": _norm(f"{type(exc).__name__}: {exc}")}
            )

    k = make_kernel()   # setup/authority instance
    k2 = make_kernel()  # worker instance (owns bound leases)
    k3 = make_kernel()  # fresh instance (no bound lease authority)

    record("create-a", lambda: k.create_task("task-a", "owner-A", "goal A", risk_tier="R1", deadline_ms=60000, max_attempts=3, priority=3))
    record("create-b", lambda: k.create_task("task-b", "owner-B", "goal B", risk_tier="R0", deadline_ms=120000, max_attempts=3, priority=5))
    record("create-c", lambda: k.create_task("task-c", "owner-C", "goal C", risk_tier="R2", deadline_ms=90000, max_attempts=2, priority=1))
    record("flow-a", lambda: [k.transition("task-a", s) for s in ("PLANNING", "READY", "QUEUED")])
    record("flow-b", lambda: [k.transition("task-b", s) for s in ("PLANNING", "READY", "QUEUED")])
    record("flow-c", lambda: k.transition("task-c", "PLANNING"))
    record("create-a-duplicate", lambda: k.create_task("task-a", "owner-A", "duplicate id"))
    record("occ-stale-version-c", lambda: k.transition("task-c", "READY", expected_version=999))
    record("direct-completed-forbidden", lambda: k.transition("task-c", "COMPLETED"))

    def claim_w1():
        lease = k2.claim_next("worker-1", ttl_seconds=120.0)
        ctx["lease_a"] = lease
        return None if lease is None else {"task_id": lease.task_id, "fencing_token": lease.fencing_token, "worker_id": lease.worker_id}

    record("claim-w1", claim_w1)
    record("start-a", lambda: k2.start("task-a", ctx["lease_a"].lease_id))
    record(
        "checkpoint-a",
        lambda: k2.checkpoint(
            "task-a",
            ctx["lease_a"].lease_id,
            "step-1",
            "RUNNING",
            {"action": "click", "target": "#submit"},
            capability_epoch=1,
            idempotency_key="idem-a",
            pre_observation_ref="obs://pre-1",
            post_observation_ref="obs://post-1",
            tool_result={"ok": True},
            verifier_verdict="VERIFIED",
        ),
    )

    def idem_claim():
        logical_key, claimed = k2.idempotency_claim("task-a", "step-1", "browser.click", "res://btn-1")
        ctx["logical_key"] = logical_key
        return {"claimed": claimed}

    record("idempotency-claim-a", idem_claim)
    record("idempotency-claim-replay-a", idem_claim)
    record("idempotency-complete-a", lambda: k2.idempotency_complete(ctx["logical_key"], "evidence://out-1"))
    record("verify-a", lambda: k2.transition("task-a", "VERIFYING", lease_id=ctx["lease_a"].lease_id))
    record(
        "complete-a",
        lambda: k2.commit_completed("task-a", ctx["lease_a"].lease_id, verifier_verdict="VERIFIED", evidence_ref="evidence://out-1"),
    )
    record("heartbeat-after-completion", lambda: k2.heartbeat("task-a", ctx["lease_a"].lease_id, extend_seconds=30.0))

    def claim_w2():
        lease = k2.claim_next("worker-2", ttl_seconds=120.0)
        ctx["lease_b"] = lease
        return None if lease is None else {"task_id": lease.task_id, "fencing_token": lease.fencing_token, "worker_id": lease.worker_id}

    record("claim-w2", claim_w2)
    record("heartbeat-b", lambda: k2.heartbeat("task-b", ctx["lease_b"].lease_id, extend_seconds=60.0))
    record("heartbeat-unknown-lease", lambda: k2.heartbeat("task-b", "lease_" + "0" * 24, extend_seconds=60.0))
    record("release-b", lambda: k2.release("task-b", ctx["lease_b"].lease_id))
    record("heartbeat-after-release", lambda: k2.heartbeat("task-b", ctx["lease_b"].lease_id, extend_seconds=60.0))

    record("kill-switch-on", lambda: k.set_global_kill(True))
    record("claim-while-killed", lambda: k3.claim_next("worker-3", ttl_seconds=30.0))
    record("kill-switch-off", lambda: k.set_global_kill(False))
    record("kill-task-c", lambda: k.set_task_kill("task-c"))
    record("kill-task-c-again", lambda: k.set_task_kill("task-c"))

    record("rebuild-a", lambda: k.rebuild_projection("task-a"))
    record("journal-a-valid", lambda: k.verify_journal("task-a"))
    record("recover-on-boot", lambda: k.recover_on_boot())
    record("verify-integrity", lambda: k.verify_integrity())

    k.close()
    k2.close()
    k3.close()
    return {"records": records, "projection": _norm(_projection(make_kernel()))}


def _journal_chain_valid(kernel: TaskKernel) -> list[str]:
    invalid = []
    for row in kernel.conn.fetchall("SELECT DISTINCT task_id FROM events"):
        result = kernel.verify_journal(row["task_id"])
        if not result["hash_chain_valid"]:
            invalid.append(row["task_id"])
    return invalid


# --------------------------------------------------------------------------- #
# parity tests (real PostgreSQL, skip = declared infra-skip)                  #
# --------------------------------------------------------------------------- #
def test_pg_parity_full_sequence(pg_storage: PgKernelStorage, tmp_path: Any) -> None:
    dsn = pg_storage.dsn

    def make_sqlite() -> TaskKernel:
        return TaskKernel(storage=SQLiteKernelStorage(tmp_path / "kernel.sqlite3"))

    def make_pg() -> TaskKernel:
        return TaskKernel(storage=PgKernelStorage(dsn))

    sqlite_result = run_parity_sequence(make_sqlite)
    pg_result = run_parity_sequence(make_pg)

    assert sqlite_result == pg_result, "SQLite/PG projections or step records diverged"

    # semantic sanity: the sequence actually exercised the kernel
    outcomes = {r["step"]: r["outcome"] for r in sqlite_result["records"]}
    assert outcomes["claim-w1"] == "ok"
    assert outcomes["complete-a"] == "ok"
    assert outcomes["idempotency-claim-a"] == "ok"
    assert outcomes["kill-switch-on"] == "ok"
    task_a = next(t for t in pg_result["projection"]["tasks"] if t["task_id"] == "task-a")
    assert task_a["state"] == "COMPLETED"

    # journal hash chain independently valid on each backend (ids are random)
    k_sql = make_sqlite()
    try:
        assert _journal_chain_valid(k_sql) == []
    finally:
        k_sql.close()
    k_pg = make_pg()
    try:
        assert _journal_chain_valid(k_pg) == []
    finally:
        k_pg.close()


def test_pg_parity_occ_conflict_across_instances(pg_storage: PgKernelStorage, tmp_path: Any) -> None:
    dsn = pg_storage.dsn
    for make_storage_backend, path in (
        (SQLiteKernelStorage, tmp_path / "occ.sqlite3"),
        (lambda p: PgKernelStorage(dsn), None),
    ):
        a = make_storage_backend(path)
        b = make_storage_backend(path)
        try:
            a.executescript(
                "CREATE TABLE IF NOT EXISTS counters "
                "(id TEXT PRIMARY KEY, val INTEGER, version INTEGER DEFAULT 1)"
            )
            a.execute("DELETE FROM counters WHERE id='c1'")
            a.execute("INSERT INTO counters (id, val, version) VALUES ('c1', 0, 1)")
            a.begin()
            a.execute("UPDATE counters SET val=val+10, version=version+1 WHERE id='c1' AND version=1")
            a.commit()
            b.begin()
            cur = b.execute(
                "UPDATE counters SET val=val+20, version=version+1 WHERE id='c1' AND version=1"
            )
            assert cur.rowcount == 0  # stale version must not win, on either backend
            b.rollback()
            row = a.fetchone("SELECT val, version FROM counters WHERE id='c1'")
            assert (row["val"], row["version"]) == (10, 2)
        finally:
            a.close()
            b.close()


def test_pg_factory_make_storage_env_backend(pg_storage: PgKernelStorage, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    base = os.environ[PG_DSN_ENV]
    monkeypatch.setenv("SCP_KERNEL_BACKEND", "postgres")
    monkeypatch.setenv("SCP_KERNEL_PG_DSN", base)
    monkeypatch.delenv("SCP_STORAGE_BACKEND", raising=False)
    storage = make_storage(tmp_path / "ignored.sqlite3")
    try:
        assert isinstance(storage, PgKernelStorage)
    finally:
        storage.close()


def test_pg_factory_make_storage_backend_param(pg_storage: PgKernelStorage, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCP_KERNEL_PG_DSN", os.environ[PG_DSN_ENV])
    storage = make_storage(tmp_path / "ignored.sqlite3", backend="postgres")
    try:
        assert isinstance(storage, PgKernelStorage)
    finally:
        storage.close()


def test_pg_factory_param_wins_over_env(pg_storage: PgKernelStorage, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCP_KERNEL_BACKEND", "postgres")
    monkeypatch.setenv("SCP_KERNEL_PG_DSN", os.environ[PG_DSN_ENV])
    storage = make_storage(tmp_path / "kept-sqlite.sqlite3", backend="sqlite")
    try:
        assert isinstance(storage, SQLiteKernelStorage)
    finally:
        storage.close()


def test_pg_factory_missing_dsn_fails_closed(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCP_KERNEL_BACKEND", "postgres")
    monkeypatch.delenv("SCP_KERNEL_PG_DSN", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        make_storage(tmp_path / "x.sqlite3")
    assert "SCP_KERNEL_PG_DSN" in str(exc_info.value)


def test_pg_factory_legacy_env_postgres_still_unsupported(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy SCP_STORAGE_BACKEND keeps its fail-closed sqlite-only contract."""
    monkeypatch.setenv("SCP_STORAGE_BACKEND", "postgres")
    monkeypatch.delenv("SCP_KERNEL_BACKEND", raising=False)
    with pytest.raises(NotImplementedError):
        make_storage(tmp_path / "x.sqlite3")


# --------------------------------------------------------------------------- #
# translator unit tests (backend-free, always run)                            #
# --------------------------------------------------------------------------- #
def test_translate_placeholders() -> None:
    out = translate_sqlite_sql(
        "INSERT INTO tasks(task_id,owner,goal) VALUES (?,?,?) "
        "WHERE goal='a?b:c' AND tag=:owner"
    )
    assert "VALUES (%s,%s,%s)" in out
    assert "tag=%(owner)s" in out
    assert "'a?b:c'" in out  # literals untouched
    assert "'a%sb' " not in out


def test_translate_insert_or_ignore() -> None:
    out = translate_sqlite_sql("INSERT OR IGNORE INTO control(id) VALUES(1)")
    assert out == "INSERT INTO control(id) VALUES(1) ON CONFLICT DO NOTHING"


def test_translate_upsert_qualifies_ambiguous_columns() -> None:
    out = translate_sqlite_sql(
        "INSERT INTO queue_accounts(owner,active,dispatch_count,last_dispatch_at) "
        "VALUES (?,?,?,?) ON CONFLICT(owner) DO UPDATE SET "
        "active=active+1,dispatch_count=dispatch_count+1,last_dispatch_at=excluded.last_dispatch_at"
    )
    assert "active=queue_accounts.active+1" in out
    assert "dispatch_count=queue_accounts.dispatch_count+1" in out
    assert "last_dispatch_at=excluded.last_dispatch_at" in out  # excluded stays


def test_translate_strftime_epoch() -> None:
    out = translate_sqlite_sql(
        "SELECT task_id FROM tasks WHERE CAST(strftime('%s', updated_at) AS INTEGER) < ?"
    )
    assert "FLOOR(EXTRACT(EPOCH FROM (updated_at)::timestamptz))" in out
    assert "strftime" not in out.lower()
    assert out.endswith("< %s")


def test_translate_ddl_type_mapping() -> None:
    out = translate_sqlite_sql(
        "CREATE TABLE IF NOT EXISTS leases (lease_id TEXT PRIMARY KEY, issued_at REAL NOT NULL, fencing_token INTEGER NOT NULL)"
    )
    assert "issued_at DOUBLE PRECISION NOT NULL" in out
    assert "fencing_token BIGINT NOT NULL" in out
    assert "lease_id TEXT PRIMARY KEY" in out


def test_translate_ddm_not_type_mapped() -> None:
    out = translate_sqlite_sql("UPDATE tasks SET state=? WHERE task_id=?")
    assert "INTEGER" not in out and "%s" in out


def test_translate_fail_closed_on_insert_or_replace() -> None:
    import sqlite3 as _sqlite3

    with pytest.raises(_sqlite3.OperationalError):
        translate_sqlite_sql("INSERT OR REPLACE INTO tasks(task_id) VALUES (?)")


def test_pragma_emulation_and_fail_closed(pg_storage: PgKernelStorage) -> None:
    import sqlite3 as _sqlite3

    from scp.task_kernel import TaskKernel

    # unsupported PRAGMA must fail-closed, never silently pass
    with pytest.raises(_sqlite3.OperationalError):
        pg_storage.execute("PRAGMA journal_mode=WAL")
    # non-kernel tables are whitelist-rejected
    with pytest.raises(_sqlite3.OperationalError):
        pg_storage.execute("PRAGMA table_info(pg_catalog)")
    # SQLite parity: table_info of a missing table yields no rows, no error
    assert pg_storage.fetchall("PRAGMA table_info(tasks)") == []
    # after the kernel schema is created the real columns are visible
    kernel = TaskKernel(storage=pg_storage)
    try:
        cols = pg_storage.fetchall("PRAGMA table_info(tasks)")
        names = {row["name"] for row in cols}
        assert {"task_id", "owner", "state", "version", "priority"} <= names
        quick = pg_storage.fetchone("PRAGMA quick_check")
        assert quick[0] == "ok"
        assert quick["quick_check"] == "ok"
    finally:
        kernel.close()
