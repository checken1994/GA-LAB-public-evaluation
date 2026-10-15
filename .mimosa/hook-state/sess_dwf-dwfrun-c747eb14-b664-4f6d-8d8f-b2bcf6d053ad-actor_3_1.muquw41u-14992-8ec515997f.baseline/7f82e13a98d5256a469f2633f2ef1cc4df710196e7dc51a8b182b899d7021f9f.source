"""Integration & unit tests for Requirement R1: Global Autonomous State Machine.

Tests prove:
1. Happy path completes end-to-end to COMPLETED with 0 visits to HUMAN_REVIEW.
2. Verification failures fail-closed to RETRY_SCHEDULED or FAILED without entering HUMAN_REVIEW.
3. Asynchronous races to HUMAN_REVIEW are auto-resolved via auto_resolve_human_review -> READY -> COMPLETED.
4. Stale lifecycle results in autonomous mode fail-closed to FAILED instead of HUMAN_REVIEW.
5. Watchdog lease expiry in VERIFYING state transitions to FAILED instead of HUMAN_REVIEW in autonomous mode.
6. Reconcile APPLIED outcome in autonomous mode routes to QUEUED instead of HUMAN_REVIEW.
7. Strict invariants: STATES, ALLOWED_TRANSITIONS, and fail-closed checks remain intact.
"""
from __future__ import annotations

import time

import pytest

from scp.ask_kernel_adapter import AskKernelAdapter
from scp.task_kernel import (
    ALLOWED_TRANSITIONS,
    InvalidTransition,
    TaskKernel,
)

RUN_KEY = "run-autonomous-1"


class DummyReq:
    question = "what is 2 + 2?"
    contexts = ["2 + 2 equals 4"]
    retrieved_context = "2 + 2 equals 4"
    session_id = "s-autonomous-lifecycle"
    domain = "general"
    domain_override = ""
    rag_enabled = True


RAW_RESPONSE = {
    "final_answer": "4",
    "verdict": "PASS",
    "governance_decision": "UPHOLD",
    "confidence": 1.0,
    "trace_id": "trace-auto-1",
}

VERIFIED = {
    "verdict": "VERIFIED",
    "verifier_id": "test-verifier",
    "evidence_ref": "ask://auto/verified",
    "failures": [],
    "checked": {"judge_pass": True},
}

CONTRADICTED = {
    "verdict": "CONTRADICTED",
    "verifier_id": "test-verifier",
    "evidence_ref": "ask://auto/contradicted",
    "failures": ["judge_pass"],
    "checked": {"judge_pass": False},
}


def _autonomous_adapter(tmp_path, autonomous_mode=True):
    return AskKernelAdapter(
        db_path=str(tmp_path / "kernel.sqlite3"),
        trace_path=str(tmp_path / "trace.jsonl"),
        autonomous_mode=autonomous_mode,
    )


def _drive(adapter, task_id, states):
    for state in states:
        adapter.kernel.transition(task_id, state, actor="test-sim", reason=f"auto_drive:{state}")


# ---------------------------------------------------------------------------
# Branch 1: Autonomous Happy Path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_autonomous_happy_path_completes_without_human_review(tmp_path, monkeypatch):
    """Prove that a task under autonomous mode reaches COMPLETED with 0 visits to HUMAN_REVIEW."""
    monkeypatch.setenv("SCP_VERIFIER_SECRET", "autonomous-unit-test-secret")
    adapter = _autonomous_adapter(tmp_path, autonomous_mode=True)
    req = DummyReq()
    task = adapter.begin(
        req.question,
        list(req.contexts),
        req.retrieved_context,
        req.session_id,
    )
    task_id = task["task_id"]

    async def verified(*args, **kwargs):
        return dict(VERIFIED)

    monkeypatch.setattr(adapter, "verify_response", verified)

    result = await adapter.finalize(task, dict(RAW_RESPONSE), req)

    # Assert final task state is COMPLETED
    final = adapter.kernel.get_task(task_id)
    assert final["state"] == "COMPLETED"
    assert result["verification"]["verdict"] == "VERIFIED"

    # Empirical inspection of event journal: zero visits to HUMAN_REVIEW
    events = adapter.kernel.get_events(task_id)
    states_visited = [e["to_state"] for e in events if e.get("to_state")]
    assert "HUMAN_REVIEW" not in states_visited, f"HUMAN_REVIEW was visited: {states_visited}"
    assert states_visited[-1] == "COMPLETED"

    # Verify legal state chain in journal
    for prev, nxt in zip(states_visited, states_visited[1:]):
        assert nxt in ALLOWED_TRANSITIONS.get(prev, set()), f"illegal transition {prev}->{nxt}"

    adapter.kernel.close()


# ---------------------------------------------------------------------------
# Branch 2 & 3: Autonomous Verification Failures
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_autonomous_verification_failed_retries_when_attempts_remain(tmp_path, monkeypatch):
    """When verification fails in autonomous mode with attempts < max_attempts, routes to RETRY_SCHEDULED, NOT HUMAN_REVIEW."""
    adapter = _autonomous_adapter(tmp_path, autonomous_mode=True)
    req = DummyReq()
    task = adapter.begin(
        req.question,
        list(req.contexts),
        req.retrieved_context,
        req.session_id,
    )
    task_id = task["task_id"]

    async def contradicted(*args, **kwargs):
        return dict(CONTRADICTED)

    monkeypatch.setattr(adapter, "verify_response", contradicted)

    await adapter.finalize(task, dict(RAW_RESPONSE), req)

    final = adapter.kernel.get_task(task_id)
    assert final["state"] == "RETRY_SCHEDULED"

    events = adapter.kernel.get_events(task_id)
    states_visited = [e["to_state"] for e in events if e.get("to_state")]
    assert "HUMAN_REVIEW" not in states_visited
    assert "RETRY_SCHEDULED" in states_visited

    adapter.kernel.close()


@pytest.mark.asyncio
async def test_autonomous_verification_failed_terminal_when_attempts_exhausted(tmp_path, monkeypatch):
    """When verification fails in autonomous mode with attempts >= max_attempts, routes to FAILED, NOT HUMAN_REVIEW."""
    adapter = _autonomous_adapter(tmp_path, autonomous_mode=True)
    req = DummyReq()
    task = adapter.begin(
        req.question,
        list(req.contexts),
        req.retrieved_context,
        req.session_id,
    )
    task_id = task["task_id"]

    # Manually exhaust attempts
    adapter.kernel.conn.execute("UPDATE tasks SET attempts=3, max_attempts=3 WHERE task_id=?", (task_id,))

    async def contradicted(*args, **kwargs):
        return dict(CONTRADICTED)

    monkeypatch.setattr(adapter, "verify_response", contradicted)

    await adapter.finalize(task, dict(RAW_RESPONSE), req)

    final = adapter.kernel.get_task(task_id)
    assert final["state"] == "FAILED"

    events = adapter.kernel.get_events(task_id)
    states_visited = [e["to_state"] for e in events if e.get("to_state")]
    assert "HUMAN_REVIEW" not in states_visited
    assert states_visited[-1] == "FAILED"

    adapter.kernel.close()


# ---------------------------------------------------------------------------
# Branch 4: Race to HUMAN_REVIEW Auto-Resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_autonomous_race_to_human_review_auto_resolves_and_completes(tmp_path, monkeypatch):
    """Simulate a race where watchdog swept the task into HUMAN_REVIEW during verification;
    in autonomous mode, finalize auto-resolves HUMAN_REVIEW -> READY and advances to COMPLETED."""
    monkeypatch.setenv("SCP_VERIFIER_SECRET", "autonomous-unit-test-secret")
    adapter = _autonomous_adapter(tmp_path, autonomous_mode=True)
    req = DummyReq()
    task = adapter.begin(
        req.question,
        list(req.contexts),
        req.retrieved_context,
        req.session_id,
    )
    task_id = task["task_id"]

    async def racing_verified(*args, **kwargs):
        # Swept to HUMAN_REVIEW concurrently while verification judge was running
        adapter.kernel.transition(
            task_id, "HUMAN_REVIEW", actor="test-sim", reason="concurrent_sweep_to_human_review"
        )
        return dict(VERIFIED)

    monkeypatch.setattr(adapter, "verify_response", racing_verified)

    await adapter.finalize(task, dict(RAW_RESPONSE), req)

    final = adapter.kernel.get_task(task_id)
    assert final["state"] == "COMPLETED"

    events = adapter.kernel.get_events(task_id)
    event_types = [e["type"] for e in events]
    assert "AUTONOMOUS_HUMAN_REVIEW_RESOLVED" in event_types
    assert "TASK_COMPLETED" in event_types

    adapter.kernel.close()


# ---------------------------------------------------------------------------
# Branch 5: Stale Lifecycle Fails Closed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_autonomous_stale_lifecycle_fails_closed_not_human_review(tmp_path, monkeypatch):
    """When a task sits in RECONCILING in autonomous mode, stale lifecycle fails-closed to FAILED, not HUMAN_REVIEW."""
    adapter = _autonomous_adapter(tmp_path, autonomous_mode=True)
    req = DummyReq()
    task = adapter.begin(
        req.question,
        list(req.contexts),
        req.retrieved_context,
        req.session_id,
    )
    task_id = task["task_id"]
    _drive(adapter, task_id, ("RECOVERING", "RECONCILING"))

    async def _forbidden(*args, **kwargs):
        raise AssertionError("should not run verify")

    monkeypatch.setattr(adapter, "verify_response", _forbidden)

    result = await adapter.finalize(task, dict(RAW_RESPONSE), req)

    final = adapter.kernel.get_task(task_id)
    assert final["state"] == "FAILED"
    assert result["verification"]["verdict"] == "INSUFFICIENT"
    assert "UNVERIFIED ANSWER MUST NOT ESCAPE" not in str(result["safe_response"]["final_answer"])

    adapter.kernel.close()


# ---------------------------------------------------------------------------
# Branch 6: Watchdog Expiry in VERIFYING Fails Closed
# ---------------------------------------------------------------------------


def test_autonomous_expire_leases_verifying_fails_closed(tmp_path):
    """In autonomous mode, expire_leases for a VERIFYING task moves it to FAILED, not HUMAN_REVIEW."""
    kernel = TaskKernel(db_path=str(tmp_path / "kernel.sqlite3"), autonomous_mode=True)
    kernel.create_task("task-exp-verif", "test-owner", "test goal")
    kernel.transition("task-exp-verif", "PLANNING")
    kernel.transition("task-exp-verif", "READY")
    kernel.transition("task-exp-verif", "QUEUED")
    lease = kernel.claim("task-exp-verif", worker_id="w1", ttl_seconds=1.0)
    kernel.transition("task-exp-verif", "RUNNING", lease_id=lease.lease_id)
    kernel.transition("task-exp-verif", "VERIFYING", lease_id=lease.lease_id)

    assert kernel.get_task("task-exp-verif")["state"] == "VERIFYING"

    # Expire leases in the future
    expired = kernel.expire_leases(now=time.time() + 100.0)
    assert lease.lease_id in expired

    final = kernel.get_task("task-exp-verif")
    assert final["state"] == "FAILED"
    assert final["error"] == "verification_lease_expired"

    events = kernel.get_events("task-exp-verif")
    last_event = events[-1]
    assert last_event["type"] == "LEASE_EXPIRED"
    assert last_event["to_state"] == "FAILED"

    kernel.close()


# ---------------------------------------------------------------------------
# Branch 7: Reconcile APPLIED Routes to QUEUED
# ---------------------------------------------------------------------------


def test_autonomous_reconcile_applied_routes_to_queued(tmp_path):
    """In autonomous mode, reconcile_unknown with outcome APPLIED routes to QUEUED, not HUMAN_REVIEW."""
    kernel = TaskKernel(db_path=str(tmp_path / "kernel.sqlite3"), autonomous_mode=True)
    kernel.create_task("task-rec-auto", "test-owner", "test goal")
    kernel.transition("task-rec-auto", "PLANNING")
    kernel.transition("task-rec-auto", "READY")
    kernel.transition("task-rec-auto", "QUEUED")
    lease = kernel.claim("task-rec-auto", worker_id="w1", ttl_seconds=30.0)
    kernel.transition("task-rec-auto", "RUNNING", lease_id=lease.lease_id)

    # Claim idempotency and record action dispatched
    idem_key, claimed = kernel.idempotency_claim("task-rec-auto", "step-1", "http.post", "https://api.test/charge")
    assert claimed is True
    disp = kernel.record_action_dispatched(
        "task-rec-auto",
        lease.lease_id,
        "step-1",
        {"action": "charge"},
        1,
        idem_key,
        "provider-req-1",
    )
    cp_id = disp["checkpoint_id"]
    kernel.enter_reconciling("task-rec-auto", cp_id)

    assert kernel.get_task("task-rec-auto")["state"] == "RECONCILING"

    # Reconcile outcome APPLIED
    kernel.reconcile_unknown(
        "task-rec-auto",
        cp_id,
        outcome="APPLIED",
        evidence_ref="evidence://reconciled/applied",
        verifier_id="test-reconcile-verifier",
    )

    final = kernel.get_task("task-rec-auto")
    assert final["state"] == "QUEUED"

    events = kernel.get_events("task-rec-auto")
    last_event = events[-1]
    assert last_event["type"] == "RECONCILE_APPLIED_AUTONOMOUS"
    assert last_event["to_state"] == "QUEUED"

    kernel.close()


# ---------------------------------------------------------------------------
# Branch 8: auto_resolve_human_review Precondition Guard
# ---------------------------------------------------------------------------


def test_auto_resolve_human_review_invalid_state_raises(tmp_path):
    """auto_resolve_human_review must fail-closed if called on a task not in HUMAN_REVIEW."""
    kernel = TaskKernel(db_path=str(tmp_path / "kernel.sqlite3"), autonomous_mode=True)
    kernel.create_task("task-guard-1", "test-owner", "test goal")
    kernel.transition("task-guard-1", "PLANNING")

    with pytest.raises(InvalidTransition) as exc_info:
        kernel.auto_resolve_human_review("task-guard-1")
    assert "expected HUMAN_REVIEW" in str(exc_info.value)

    kernel.close()


def test_autonomous_mode_activation_via_environment_variable(tmp_path, monkeypatch):
    """Setting SCP_AUTONOMOUS_MODE=1 in environment activates autonomous mode by default."""
    monkeypatch.setenv("SCP_AUTONOMOUS_MODE", "1")
    kernel = TaskKernel(db_path=str(tmp_path / "k.sqlite3"))
    assert kernel.autonomous_mode is True
    kernel.close()

    adapter = AskKernelAdapter(
        db_path=str(tmp_path / "k2.sqlite3"),
        trace_path=str(tmp_path / "trace.jsonl"),
    )
    assert adapter.autonomous_mode is True
    assert adapter.kernel.autonomous_mode is True
    adapter.kernel.close()

    kernel.close()
