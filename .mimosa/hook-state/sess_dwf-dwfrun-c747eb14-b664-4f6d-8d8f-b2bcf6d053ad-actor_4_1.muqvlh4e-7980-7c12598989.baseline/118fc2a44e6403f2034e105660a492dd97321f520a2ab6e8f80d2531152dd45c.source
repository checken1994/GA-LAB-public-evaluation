"""P1 kernel regression tests — expert panel B (kernel durability).

Locks in four verified P1 defects so they cannot silently regress:

  1. Bridge replay dedupe: kernel_storage translates the backend UNIQUE
     violation into StorageIntegrityError, so a duplicate create_task must
     produce the durable "replayed" response (never a generic pre-dispatch
     failure, never a second side effect).
  2. auto_reconcile_orphans must respect lease authority: a worker whose
     lease heartbeat/expires_at is still fresh is NOT hijacked even when
     tasks.updated_at is stale; a worker with a dead lease IS reconciled —
     through legal ALLOWED_TRANSITIONS with version increments only.
  3. CHECKPOINT_WRITTEN events carry to_state=NULL: a crash after checkpoint
     rebuilds the projection to the pre-checkpoint legal state instead of
     projecting the checkpoint snapshot state.
  4. Bridge heartbeats the lease across the awaited dispatch, so an action
     running longer than the lease TTL still commits its VERIFIED result.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from scp.hands.hands_executor import HandsExecutor
from scp.hands.task_kernel_bridge import TaskKernelHandsBridge
from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority
from scp.task_kernel import ALLOWED_TRANSITIONS, CheckpointCorrupt, TaskKernel

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _bridge_with_executor(tmp_path: Path) -> tuple[TaskKernelHandsBridge, Path, CapabilityAuthority]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    cap_state = tmp_path / "capability_state.json"
    cap_auth = CapabilityAuthority(cap_state)
    executor = HandsExecutor(
        controller=PCController(working_dir=workspace),
        capability_authority=cap_auth,
        data_dir=tmp_path / "hands_data",
    )
    bridge = TaskKernelHandsBridge(executor, db_path=tmp_path / "kernel.sqlite3")
    return bridge, workspace, cap_auth


def _running_task(
    kernel: TaskKernel, task_id: str, worker_id: str, ttl_seconds: float
):
    kernel.create_task(task_id, "p1-regression", "prove kernel durability fix", "R1")
    for state in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, state, actor="p1-regression", reason="setup")
    lease = kernel.claim(task_id, worker_id, ttl_seconds=ttl_seconds)
    kernel.start(task_id, lease.lease_id)
    return lease


def _age_task_updated_at(kernel: TaskKernel, task_id: str, seconds_ago: float) -> None:
    stale = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    kernel.conn.execute(
        "UPDATE tasks SET updated_at=? WHERE task_id=?", (stale.isoformat(), task_id)
    )


def _age_lease(kernel: TaskKernel, lease_id: str, seconds_ago: float) -> None:
    past = datetime.now(timezone.utc).timestamp() - seconds_ago
    kernel.conn.execute(
        "UPDATE leases SET heartbeat_at=?, expires_at=? WHERE lease_id=?",
        (past, past, lease_id),
    )


def _assert_legal_state_chain(events: list[dict[str, Any]]) -> None:
    chain = [e["to_state"] for e in events if e["to_state"]]
    assert chain, "journal must contain at least one state-bearing event"
    for prev, nxt in zip(chain, chain[1:]):
        assert nxt in ALLOWED_TRANSITIONS.get(prev, set()), (
            f"illegal journal transition {prev}->{nxt}"
        )


# ---------------------------------------------------------------------------
# (a) Bridge duplicate request returns the replayed response
# ---------------------------------------------------------------------------


def test_bridge_duplicate_request_returns_replayed_response(tmp_path):
    bridge, workspace, cap_auth = _bridge_with_executor(tmp_path)
    try:
        target = workspace / "replay_artifact.txt"
        content = "original_state_written_once"
        request_key = f"p1-replay-{uuid.uuid4().hex}"
        token = cap_auth.issue("hands:pc.write_file")
        confirmation_id = bridge.executor.controller.human_store.record_confirmation(
            action="pc.write_file", target=str(target.resolve()), ttl_seconds=60,
        )

        first = asyncio.run(
            bridge.execute(
                action="pc.write_file",
                params={"path": str(target), "content": content, "confirmation_id": confirmation_id},
                capability_level=3,
                approved=True,
                request_key=request_key,
                capability_token=token,
            )
        )
        assert first.get("success") is True, f"first execution failed: {first}"
        task_id = first["kernel"]["taskId"]

        kernel = TaskKernel(str(tmp_path / "kernel.sqlite3"))
        events_before = len(kernel.get_events(task_id))

        replay = asyncio.run(
            bridge.execute(
                action="pc.write_file",
                params={"path": str(target), "content": "MUTATED_BY_REPLAY", "confirmation_id": confirmation_id},
                capability_level=3,
                approved=True,
                request_key=request_key,
                capability_token=token,
            )
        )

        # The exact regression: the replayed response must fire (it was dead
        # code while the bridge caught the wrong exception type).
        assert replay.get("replayed") is True, f"duplicate did not replay: {replay}"
        assert replay.get("success") is False
        assert replay.get("safeToRetry") is False
        assert replay["kernel"]["taskId"] == task_id

        # Dedupe: no new journal events, no second side effect on reality.
        assert len(kernel.get_events(task_id)) == events_before
        assert kernel.get_task(task_id)["state"] == "COMPLETED"
        assert kernel.verify_journal(task_id)["hash_chain_valid"] is True
        assert target.read_text(encoding="utf-8") == content, (
            "replay mutated reality - bridge dedupe is broken"
        )
        kernel.close()
    finally:
        bridge.close()


# ---------------------------------------------------------------------------
# (b) Orphan sweep respects lease authority (fresh heartbeat kept, stale taken)
# ---------------------------------------------------------------------------


def test_orphan_sweep_keeps_fresh_lease_and_reconciles_stale_one(tmp_path):
    kernel = TaskKernel(str(tmp_path / "kernel.sqlite3"))
    try:
        live_lease = _running_task(kernel, "orphan-live", "worker-live", ttl_seconds=300)
        stale_lease = _running_task(kernel, "orphan-stale", "worker-stale", ttl_seconds=60)

        # Live worker heartbeats but changes no state: tasks.updated_at goes
        # stale while leases.expires_at stays fresh (the exact hijack window).
        kernel.heartbeat("orphan-live", live_lease.lease_id, extend_seconds=300)
        _age_task_updated_at(kernel, "orphan-live", seconds_ago=300)

        # Dead worker: heartbeat/expiry and projection are all in the past.
        _age_task_updated_at(kernel, "orphan-stale", seconds_ago=300)
        _age_lease(kernel, stale_lease.lease_id, seconds_ago=120)

        live_version_before = kernel.get_task("orphan-live")["version"]
        live_events_before = len(kernel.get_events("orphan-live"))
        stale_version_before = kernel.get_task("orphan-stale")["version"]

        orphans = kernel.auto_reconcile_orphans(now=datetime.now(timezone.utc).timestamp())

        # The live worker is NOT hijacked (regression: stale updated_at used to
        # be the only signal and dragged RUNNING tasks into UNKNOWN).
        assert "orphan-live" not in orphans, f"live worker hijacked: {orphans}"
        live = kernel.get_task("orphan-live")
        assert live["state"] == "RUNNING"
        assert live["version"] == live_version_before
        assert len(kernel.get_events("orphan-live")) == live_events_before

        # The dead worker IS reconciled, through legal transitions only.
        assert orphans == ["orphan-stale"], f"unexpected orphan set: {orphans}"
        stale = kernel.get_task("orphan-stale")
        assert stale["state"] == "RECONCILING"
        assert stale["version"] >= stale_version_before + 2, (
            "orphan sweep must bump the version per applied transition"
        )
        events = kernel.get_events("orphan-stale")
        _assert_legal_state_chain(events)
        reasons = {e["reason"] for e in events}
        assert {"ORPHAN_TIMEOUT", "AUTO_RECONCILE_INITIATED"} <= reasons
        assert kernel.verify_journal("orphan-stale")["hash_chain_valid"] is True

        # The dead worker's lease authority is revoked by the sweep.
        row = kernel.conn.execute(
            "SELECT released FROM leases WHERE lease_id=?", (stale_lease.lease_id,)
        ).fetchone()
        assert row["released"] == 1

        # The live worker's lease authority is untouched and still usable.
        kernel.heartbeat("orphan-live", live_lease.lease_id, extend_seconds=300)
    finally:
        kernel.close()


# ---------------------------------------------------------------------------
# (c) Crash after checkpoint rebuilds the pre-checkpoint legal state
# ---------------------------------------------------------------------------


def test_checkpoint_event_does_not_poison_rebuild_projection(tmp_path):
    kernel = TaskKernel(str(tmp_path / "kernel.sqlite3"))
    try:
        lease = _running_task(kernel, "cp-crash", "cp-worker", ttl_seconds=300)
        logical_key, claimed = kernel.idempotency_claim(
            "cp-crash", "step-1", "fs.write", "resource-1"
        )
        assert claimed is True

        checkpoint_id = kernel.checkpoint(
            "cp-crash",
            lease.lease_id,
            "step-1",
            "WAITING_TOOL",
            {"planned": "side_effect"},
            0,
            logical_key,
            pre_observation_ref="p1://pre",
        )
        assert checkpoint_id

        # A checkpoint is a snapshot, not a transition: to_state must be NULL.
        cp_events = [
            e for e in kernel.get_events("cp-crash") if e["type"] == "CHECKPOINT_WRITTEN"
        ]
        assert len(cp_events) == 1
        assert cp_events[0]["to_state"] is None, (
            "CHECKPOINT_WRITTEN must not carry a to_state or it poisons rebuild"
        )

        # Crash window: the worker dies right after the checkpoint, before any
        # further transition. Rebuild must project the pre-checkpoint legal
        # state (RUNNING), not the checkpoint snapshot state (WAITING_TOOL).
        repaired = kernel.rebuild_projection("cp-crash")
        assert repaired["state"] == "RUNNING", (
            f"projection poisoned by checkpoint event: {repaired['state']}"
        )
        _assert_legal_state_chain(kernel.get_events("cp-crash"))
        assert kernel.verify_journal("cp-crash")["hash_chain_valid"] is True

        # The repaired state stays usable for a legal follow-up transition.
        kernel.transition("cp-crash", "VERIFYING", actor="p1-test", reason="post_rebuild")
        assert kernel.get_task("cp-crash")["state"] == "VERIFYING"

        # Checkpoint snapshot state itself is still authoritative on the row.
        stored = kernel.get_checkpoint(checkpoint_id)
        assert stored["state"] == "WAITING_TOOL"
    finally:
        kernel.close()


def test_checkpoint_still_rejects_invalid_state(tmp_path):
    kernel = TaskKernel(str(tmp_path / "kernel.sqlite3"))
    try:
        lease = _running_task(kernel, "cp-invalid", "cp-worker", ttl_seconds=300)
        logical_key, claimed = kernel.idempotency_claim(
            "cp-invalid", "step-1", "fs.write", "resource-1"
        )
        assert claimed is True
        with pytest.raises(CheckpointCorrupt):
            kernel.checkpoint(
                "cp-invalid",
                lease.lease_id,
                "step-1",
                "NOT_A_STATE",
                {"planned": "side_effect"},
                0,
                logical_key,
            )
    finally:
        kernel.close()


# ---------------------------------------------------------------------------
# (d) Bridge heartbeats across the awaited dispatch (lease outlives slow action)
# ---------------------------------------------------------------------------


def test_bridge_heartbeat_keeps_lease_alive_across_slow_dispatch(tmp_path):
    bridge, workspace, cap_auth = _bridge_with_executor(tmp_path)
    try:
        # Force lease expiry well below the dispatch duration: without the
        # heartbeat loop the lease dies mid-flight and a VERIFIED result can
        # no longer be committed (fail-closed UNKNOWN instead).
        #
        # [S16 FIX 2026-09-13] CI timing, test parameter only (no product
        # change): with ttl=1.0s the heartbeat interval is ttl/3 = 0.333s and
        # ANY single event-loop scheduling gap over ~1.0s (sqlite writes +
        # loaded CI runners) expires the lease mid-flight -> StaleLease,
        # observed on the windows CI job. ttl=3.0s gives a 1.0s heartbeat
        # interval and 3x headroom; the dispatch stays > 2 full lease TTLs so
        # the "must be heartbeated" assertions below keep their force.
        bridge.lease_ttl_seconds = 3.0

        executor = bridge.executor
        real_execute = executor.execute

        async def slow_execute(action, params, capability_level, approved, dry_run, capability_token=None, **kwargs):
            await asyncio.sleep(7.0)  # > 2 full lease TTLs (2 x 3.0s)
            return await real_execute(action, params, capability_level, approved, dry_run, capability_token=capability_token, **kwargs)

        executor.execute = slow_execute

        # Spy on lease renewal: the dispatch MUST be covered by heartbeats.
        heartbeat_calls: list[str] = []
        real_heartbeat = bridge.kernel.heartbeat

        def spy_heartbeat(task_id, lease_id, extend_seconds=30.0):
            heartbeat_calls.append(lease_id)
            return real_heartbeat(task_id, lease_id, extend_seconds=extend_seconds)

        bridge.kernel.heartbeat = spy_heartbeat

        target = workspace / "slow_artifact.txt"
        content = "written_after_slow_dispatch"
        token = cap_auth.issue("hands:pc.write_file")
        confirmation_id = bridge.executor.controller.human_store.record_confirmation(
            action="pc.write_file", target=str(target.resolve()), ttl_seconds=60,
        )

        result = asyncio.run(
            bridge.execute(
                action="pc.write_file",
                params={"path": str(target), "content": content, "confirmation_id": confirmation_id},
                capability_level=3,
                approved=True,
                request_key=f"p1-slow-{uuid.uuid4().hex}",
                capability_token=token,
            )
        )

        assert result.get("success") is True, f"slow dispatch failed: {result}"
        assert result["kernel"]["state"] == "COMPLETED", result["kernel"]
        assert target.read_text(encoding="utf-8") == content

        # The awaited dispatch was actively covered by lease renewals: without
        # the heartbeat loop a >TTL action loses its lease mid-flight.
        assert len(heartbeat_calls) >= 2, (
            f"dispatch ran longer than the lease TTL but was not heartbeated: {heartbeat_calls}"
        )
        assert len(set(heartbeat_calls)) == 1, "heartbeats crossed leases"

        kernel = TaskKernel(str(tmp_path / "kernel.sqlite3"))
        task = kernel.get_task(result["kernel"]["taskId"])
        assert task["state"] == "COMPLETED"
        assert kernel.verify_journal(task["task_id"])["hash_chain_valid"] is True
        kernel.close()
    finally:
        bridge.close()
