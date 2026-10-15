"""Boot-on-Pg runtime: full TaskKernel lifecycle on a real PostgreSQL backend.

Track C1 session 2 (D3): the TaskKernel API itself (not just the storage
layer) drives a complete task lifecycle against PgKernelStorage:

  create -> PLANNING -> READY -> QUEUED -> claim (LEASED) -> start (RUNNING)
  -> idempotency claim -> pre-dispatch checkpoint -> heartbeat
  -> VERIFYING -> signed VerifierReceipt -> commit_verification_result
  -> COMPLETED

followed by verify_integrity + journal hash-chain validation, projection
rebuild, and a clean boot recovery report. A second test covers the crashed
worker path: a kernel instance dies mid-RUNNING, boot recovery sends the task
to HUMAN_REVIEW, and an operator loops it back to QUEUED where a new worker
claims and completes it.

Requires ``SCP_PG_TEST_DSN`` (declared infra-skip when absent; INFRA-SKIP with
the original error when unreachable). DSN passwords are never printed.
"""
from __future__ import annotations

import os
import re
import time
import uuid

import psycopg
import pytest
from psycopg import sql as pg_sql

from scp.core.verifier_receipt import VerifierReceipt, sign_verifier_receipt
from scp.kernel_storage_pg import PgKernelStorage
from scp.task_kernel import TaskKernel

PG_DSN_ENV = "SCP_PG_TEST_DSN"


@pytest.fixture()
def pg_dsn() -> str:
    base = os.environ.get(PG_DSN_ENV, "").strip()
    if not base:
        pytest.skip(
            f"{PG_DSN_ENV} not set — boot-on-Pg runtime needs a real PostgreSQL "
            "(docker run -d --rm --name scp-pg-test -e POSTGRES_PASSWORD=scppg "
            "-e POSTGRES_DB=scpkernel -p 55432:5432 postgres:16-alpine); "
            "declared infra-skip (no assertion hidden)"
        )
    schema = f"scp_boot_{uuid.uuid4().hex[:10]}"
    assert re.fullmatch(r"scp_boot_[0-9a-f]{10}", schema)
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
        yield psycopg.conninfo.make_conninfo(base, options=f"-c search_path={schema}")
    finally:
        try:
            admin.execute(
                pg_sql.SQL("DROP SCHEMA {} CASCADE").format(pg_sql.Identifier(schema))
            )
        finally:
            admin.close()


def _journal_chains_valid(kernel: TaskKernel) -> list[str]:
    invalid = []
    for row in kernel.conn.fetchall("SELECT DISTINCT task_id FROM events"):
        result = kernel.verify_journal(row["task_id"])
        if not result["hash_chain_valid"]:
            invalid.append(row["task_id"])
    return invalid


def test_pg_boot_full_lifecycle_commit_verification_result(pg_dsn: str) -> None:
    kernel = TaskKernel(storage=PgKernelStorage(pg_dsn))
    try:
        # --- create + plan ---------------------------------------------------
        kernel.create_task(
            "boot-pg-1",
            "boot-owner",
            "full lifecycle on postgres",
            risk_tier="R1",
            input_hash="deadbeef" * 8,
        )
        assert kernel.get_task("boot-pg-1")["state"] == "CREATED"
        for state in ("PLANNING", "READY", "QUEUED"):
            kernel.transition("boot-pg-1", state, actor="boot-probe", reason="runtime_probe")

        # --- claim + lease ---------------------------------------------------
        lease = kernel.claim_next("boot-worker", ttl_seconds=60.0)
        assert lease is not None and lease.task_id == "boot-pg-1"
        assert kernel.get_task("boot-pg-1")["state"] == "LEASED"
        assert kernel.get_task("boot-pg-1")["active_lease_id"] == lease.lease_id
        assert lease.fencing_token >= 1
        kernel.start("boot-pg-1", lease.lease_id)
        assert kernel.get_task("boot-pg-1")["state"] == "RUNNING"

        # --- idempotency + pre-dispatch checkpoint ---------------------------
        logical_key, claimed = kernel.idempotency_claim(
            "boot-pg-1", "step-1", "browser.click", "res://submit-btn"
        )
        assert claimed is True
        checkpoint_id = kernel.checkpoint(
            "boot-pg-1",
            lease.lease_id,
            "step-1",
            "WAITING_TOOL",
            {"action": "click", "target": "#submit"},
            capability_epoch=1,
            idempotency_key=logical_key,
            pre_observation_ref="obs://boot-pg-1/pre",
        )
        assert checkpoint_id.startswith("cp_")
        restored = kernel.get_checkpoint(checkpoint_id)
        assert restored["task_id"] == "boot-pg-1"
        assert restored["step_id"] == "step-1"
        assert restored["state"] == "WAITING_TOOL"

        # --- heartbeat while dispatch is in flight ---------------------------
        kernel.heartbeat("boot-pg-1", lease.lease_id, extend_seconds=60.0)

        # --- verify + commit with an independently signed receipt ------------
        kernel.transition(
            "boot-pg-1", "VERIFYING", actor="boot-probe", reason="result_observed"
        )
        evidence_ref = "evidence://boot-pg-1/result"
        kernel.idempotency_complete(logical_key, evidence_ref)
        receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id="boot-pg-1",
                verifier_id="boot-probe-verifier-v1",
                verdict="VERIFIED",
                evidence_ref=evidence_ref,
                issued_at=time.time(),
            )
        )
        final_task = kernel.commit_verification_result(
            "boot-pg-1", lease.lease_id, receipt
        )
        assert final_task["state"] == "COMPLETED"

        # --- postconditions ---------------------------------------------------
        task = kernel.get_task("boot-pg-1")
        assert task["state"] == "COMPLETED"
        assert task["active_lease_id"] is None
        assert task["active_fencing_token"] == 0

        events = kernel.get_events("boot-pg-1")
        types = [e["type"] for e in events]
        assert "LEASE_GRANTED" in types
        assert "TASK_COMPLETED" in types
        seqs = [int(e["seq"]) for e in events]
        assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)

        journal = kernel.verify_journal("boot-pg-1")
        assert journal["hash_chain_valid"] is True, journal

        integrity = kernel.verify_integrity()
        assert integrity["quick_check"] == "ok"
        assert integrity["invalid_chains"] == []

        rebuilt = kernel.rebuild_projection("boot-pg-1")
        assert rebuilt["state"] == "COMPLETED"

        report = kernel.recover_on_boot()
        assert report["corrupted"] == []
        assert all(entry["task_id"] != "boot-pg-1" for entry in report["recovered"])

        # Idempotency replay across a fresh instance must be a no-op.
        fresh = TaskKernel(storage=PgKernelStorage(pg_dsn))
        try:
            _, replayed = fresh.idempotency_claim(
                "boot-pg-1", "step-1", "browser.click", "res://submit-btn"
            )
            assert replayed is False
        finally:
            fresh.close()
    finally:
        kernel.close()


def test_pg_boot_crashed_worker_recovery_reclaim_complete(pg_dsn: str) -> None:
    # Worker instance claims and starts, then dies without completing.
    dead = TaskKernel(storage=PgKernelStorage(pg_dsn))
    dead.create_task("boot-pg-2", "boot-owner-2", "crash recovery on postgres", risk_tier="R1")
    for state in ("PLANNING", "READY", "QUEUED"):
        dead.transition("boot-pg-2", state, actor="boot-probe", reason="runtime_probe")
    lease = dead.claim_next("dead-worker", ttl_seconds=120.0)
    assert lease is not None
    dead.start("boot-pg-2", lease.lease_id)
    dead.close()  # worker death: no release, no completion

    # Fresh boot: journal replay must move RUNNING -> HUMAN_REVIEW, release
    # the orphan lease and keep the journal intact.
    kernel = TaskKernel(storage=PgKernelStorage(pg_dsn))
    try:
        report = kernel.recover_on_boot()
        assert report["corrupted"] == []
        recovered = {entry["task_id"]: entry for entry in report["recovered"]}
        assert recovered["boot-pg-2"]["from"] == "RUNNING"
        assert recovered["boot-pg-2"]["to"] == "HUMAN_REVIEW"

        task = kernel.get_task("boot-pg-2")
        assert task["state"] == "HUMAN_REVIEW"
        assert task["active_lease_id"] is None

        orphan_leases = kernel.conn.fetchall(
            "SELECT released FROM leases WHERE lease_id=:lid", {"lid": lease.lease_id}
        )
        assert int(orphan_leases[0]["released"]) == 1

        assert _journal_chains_valid(kernel) == []

        # Operator loop: HUMAN_REVIEW -> READY -> QUEUED, then a new worker
        # claims and completes the very same task.
        kernel.transition("boot-pg-2", "READY", actor="operator", reason="human_review_ok")
        kernel.transition("boot-pg-2", "QUEUED", actor="operator", reason="human_review_ok")
        lease2 = kernel.claim_next("recovery-worker", ttl_seconds=60.0)
        assert lease2 is not None and lease2.task_id == "boot-pg-2"
        assert lease2.fencing_token > lease.fencing_token, "fencing must advance"
        kernel.start("boot-pg-2", lease2.lease_id)
        kernel.transition("boot-pg-2", "VERIFYING", actor="boot-probe", reason="result_observed")
        receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id="boot-pg-2",
                verifier_id="boot-probe-verifier-v1",
                verdict="VERIFIED",
                evidence_ref="evidence://boot-pg-2/result",
                issued_at=time.time(),
            )
        )
        final_task = kernel.commit_verification_result("boot-pg-2", lease2.lease_id, receipt)
        assert final_task["state"] == "COMPLETED"

        assert kernel.verify_integrity()["invalid_chains"] == []
        assert _journal_chains_valid(kernel) == []
    finally:
        kernel.close()
