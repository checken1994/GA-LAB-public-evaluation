"""S20 regression tests — lease renew primitive + /ask heartbeat (long-LLM availability).

Runtime evidence 2026-09-13 (bench_final_seed99.json + GA.md B11): the /ask
kernel lease was claimed with a fixed 60s TTL while free-tier provider latency
measures 30-260s (mean 85.6s). The lease expired under a LIVING worker, the
watchdog moved the task out of the happy path, and S19's fail-closed
state-route discarded a real, correct answer (2/10 asks died this way on
seed 99). The fix is a fencing-checked expiry-only renewal (kernel
``renew_lease``) driven by an asyncio heartbeat inside ``run_rag`` — NOT a
bigger TTL (that only delays genuine crash detection).

FA-01: every assertion below is behavioural (expiry moved, state untouched,
stale holder refused, lifecycle outcome) — no smoke-only checks.
Anti-placebo control (test c): with the heartbeat kill-switch off, the OLD
lifecycle_authority_lost failure MUST reproduce against the same slow
provider, proving tests b/d actually exercise the bug, not pass vacuously.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from scp.ask_kernel_adapter import (
    DEFAULT_ASK_LEASE_TTL_SECONDS,
    AskKernelAdapter,
    ask_lease_heartbeat_enabled,
    ask_lease_ttl_seconds,
)
from scp.task_kernel import TaskKernel

S20_VERIFIER_SECRET = "s20-unit-test-dummy-secret"


class SlowReq:
    question = "what is 17*23?"
    contexts = ["17 times 23 is 391"]
    retrieved_context = ""
    session_id = "s20-heartbeat"
    domain = "general"
    domain_override = ""
    rag_enabled = True


RAW_RESPONSE = {
    "final_answer": "391",
    "verdict": "PASS",
    "governance_decision": "UPHOLD",
    "confidence": 0.95,
    "trace_id": "trace-s20",
}

VERIFIED = {
    "verdict": "VERIFIED",
    "verifier_id": "test-verifier",
    "evidence_ref": "ask://s20/verified",
    "failures": [],
    "checked": {"judge_pass": True},
}


def _adapter(tmp_path):
    return AskKernelAdapter(
        db_path=str(tmp_path / "kernel.sqlite3"),
        trace_path=str(tmp_path / "trace.jsonl"),
    )


def _lease_row(kernel, lease_id):
    row = kernel.conn.execute("SELECT * FROM leases WHERE lease_id=?", (lease_id,)).fetchone()
    return dict(row)


def _task_row(kernel, task_id):
    row = kernel.conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
    return dict(row)


def _queued_kernel(tmp_path, task_id="t-s20"):
    kernel = TaskKernel(str(tmp_path / "k-s20.sqlite3"))
    kernel.create_task(task_id, "s20-owner", "lease heartbeat")
    for state in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, state, actor="test-s20", reason="s20_setup")
    return kernel


# ---------------------------------------------------------------------------
# (a) renew_lease primitive semantics — fencing, expiry-only, no resurrection
# ---------------------------------------------------------------------------


def test_renew_with_current_token_extends_expiry_only(tmp_path):
    kernel = _queued_kernel(tmp_path)
    # [FLAKE-FIX 2026-09-24] TTL 1.0s: claim->start->renew spans multiple fsync'd
    # transactions plus the 0.25s sleep; 0.4s left ~150ms of margin and could
    # fail closed on a loaded CI runner before renew_lease() runs. The test
    # semantics (renew within TTL succeeds, expiry-only) are unchanged.
    lease = kernel.claim("t-s20", "worker-a", ttl_seconds=1.0)
    kernel.start("t-s20", lease.lease_id)
    before = _lease_row(kernel, lease.lease_id)
    task_before = _task_row(kernel, "t-s20")
    time.sleep(0.25)

    assert kernel.renew_lease("t-s20", lease.lease_id, lease.fencing_token, ttl_seconds=5.0) is True

    after = _lease_row(kernel, lease.lease_id)
    assert after["expires_at"] > before["expires_at"] + 4.0
    assert after["heartbeat_at"] >= before["heartbeat_at"]
    # expiry-only: state machine untouched, task version NOT bumped
    task_after = _task_row(kernel, "t-s20")
    assert task_after["state"] == task_before["state"] == "RUNNING"
    assert task_after["version"] == task_before["version"]
    assert task_after["active_lease_id"] == lease.lease_id
    kernel.close()


def test_renew_with_wrong_fencing_token_is_refused(tmp_path):
    kernel = _queued_kernel(tmp_path)
    lease = kernel.claim("t-s20", "worker-a", ttl_seconds=30.0)
    kernel.start("t-s20", lease.lease_id)
    before = _lease_row(kernel, lease.lease_id)

    assert kernel.renew_lease("t-s20", lease.lease_id, lease.fencing_token + 1) is False
    assert kernel.renew_lease("t-s20", lease.lease_id, lease.fencing_token - 1) is False
    assert kernel.renew_lease("t-s20", lease.lease_id, "not-an-int") is False
    assert kernel.renew_lease("other-task", lease.lease_id, lease.fencing_token) is False
    assert kernel.renew_lease("t-s20", "lease_missing", lease.fencing_token) is False
    assert _lease_row(kernel, lease.lease_id)["expires_at"] == before["expires_at"]
    kernel.close()


def test_renew_by_old_attempt_holder_after_reclaim_is_refused(tmp_path):
    """The zombie case the fence exists for: an expired+swept attempt must not
    keep renewing its lease once a newer attempt holds authority."""
    kernel = _queued_kernel(tmp_path)
    old = kernel.claim("t-s20", "worker-slow", ttl_seconds=1.0)
    kernel.start("t-s20", old.lease_id)
    # watchdog sweeps the expired lease: RUNNING -> RECOVERING, lease released
    expired = kernel.expire_leases(now=time.time() + 1000.0)
    assert old.lease_id in expired
    kernel.transition("t-s20", "QUEUED", actor="test-s20", reason="s20_requeue")
    fresh = kernel.claim("t-s20", "worker-new", ttl_seconds=30.0)
    assert fresh.fencing_token > old.fencing_token

    assert kernel.renew_lease("t-s20", old.lease_id, old.fencing_token) is False
    # presenting a foreign (higher) token against the old row also fails
    assert kernel.renew_lease("t-s20", old.lease_id, fresh.fencing_token) is False
    # and the fresh attempt's lease renews fine with its own token
    assert kernel.renew_lease("t-s20", fresh.lease_id, fresh.fencing_token, ttl_seconds=30.0) is True
    kernel.close()


def test_renew_on_released_or_expired_lease_returns_false_no_resurrect(tmp_path):
    kernel = _queued_kernel(tmp_path, "t-rel")
    lease = kernel.claim("t-rel", "worker-a", ttl_seconds=30.0)
    kernel.start("t-rel", lease.lease_id)
    kernel.release("t-rel", lease.lease_id)
    assert kernel.renew_lease("t-rel", lease.lease_id, lease.fencing_token) is False
    kernel.close()

    kernel2 = _queued_kernel(tmp_path, "t-exp")
    l2 = kernel2.claim("t-exp", "worker-b", ttl_seconds=0.3)
    kernel2.start("t-exp", l2.lease_id)
    time.sleep(0.45)  # lease wall-clock expired; watchdog has NOT run yet
    assert kernel2.renew_lease("t-exp", l2.lease_id, l2.fencing_token) is False
    # renew must not sweep or resurrect either — the lease row stays exactly
    # as the expired-but-unreaped watchdog found it (release is the sweep's job)
    row = _lease_row(kernel2, l2.lease_id)
    assert row["released"] == 0
    assert _task_row(kernel2, "t-exp")["state"] == "RUNNING"
    kernel2.close()


def test_renew_allowed_in_verifying_but_not_after_release_by_terminal(tmp_path):
    kernel = _queued_kernel(tmp_path, "t-vf")
    lease = kernel.claim("t-vf", "worker-a", ttl_seconds=30.0)
    kernel.start("t-vf", lease.lease_id)
    kernel.transition("t-vf", "VERIFYING", actor="test-s20", reason="s20_setup")
    assert kernel.renew_lease("t-vf", lease.lease_id, lease.fencing_token) is True
    # a HUMAN_REVIEW escalation releases the lease; renew must refuse after
    kernel.transition("t-vf", "HUMAN_REVIEW", actor="test-s20", reason="s20_setup")
    assert kernel.renew_lease("t-vf", lease.lease_id, lease.fencing_token) is False
    assert _task_row(kernel, "t-vf")["state"] == "HUMAN_REVIEW"
    kernel.close()


# ---------------------------------------------------------------------------
# (b)+(c) E2E: slow provider vs lease expiry, heartbeat ON vs kill-switch OFF
# ---------------------------------------------------------------------------


async def _run_slow_provider(adapter, monkeypatch, heartbeat_on):
    """TTL 2s, provider 5.2s, watchdog sweeps at 2.6s and 5.2s.

    Deterministic by wall-clock margin, not thread sleeps inside kernel."""
    monkeypatch.setenv("SCP_ASK_LEASE_TTL_SECONDS", "2")
    monkeypatch.setenv("SCP_VERIFIER_SECRET", S20_VERIFIER_SECRET)
    if heartbeat_on:
        monkeypatch.delenv("SCP_ASK_LEASE_HEARTBEAT", raising=False)
    else:
        monkeypatch.setenv("SCP_ASK_LEASE_HEARTBEAT", "0")

    async def slow_provider(req, request):
        await asyncio.sleep(2.6)
        adapter.kernel.expire_leases()  # same call the 30s watchdog makes
        await asyncio.sleep(2.6)
        adapter.kernel.expire_leases()
        return dict(RAW_RESPONSE)

    async def verified(*args, **kwargs):
        return dict(VERIFIED)

    monkeypatch.setattr(adapter, "verify_response", verified)
    response = await adapter.run_rag(SlowReq(), None, slow_provider)
    task_id = AskKernelAdapter.task_id_for(
        SlowReq.question, list(SlowReq.contexts), "", SlowReq.session_id, None
    )
    return response, adapter.kernel.get_task(task_id)


@pytest.mark.asyncio
async def test_heartbeat_on_slow_provider_finalizes_completed(tmp_path, monkeypatch):
    """The S20 fix: provider slower than TTL, watchdog sweeping mid-flight,
    yet the answer survives — COMPLETED, VERIFIED, no lifecycle_authority_lost."""
    adapter = _adapter(tmp_path)
    response, final = await _run_slow_provider(adapter, monkeypatch, heartbeat_on=True)

    assert final["state"] == "COMPLETED"
    assert response["final_answer"] == "391"
    assert response["verdict"] == "PASS"
    reasons = [
        row["reason"]
        for row in adapter.kernel.conn.execute(
            "SELECT reason FROM events WHERE task_id=?", (final["task_id"],)
        ).fetchall()
    ]
    assert not any("lifecycle_authority_lost" in str(r) for r in reasons)
    assert not any("lease_expired" in str(r).lower() for r in reasons)
    adapter.kernel.close()


@pytest.mark.asyncio
async def test_heartbeat_off_control_reproduces_old_bug(tmp_path, monkeypatch):
    """Anti-placebo control: identical scenario, heartbeat kill-switch OFF.
    The lease MUST expire and the S19 fail-closed route MUST discard the
    correct answer with lifecycle_authority_lost -> HUMAN_REVIEW. If this
    test ever goes green, the bug is not actually being exercised above."""
    adapter = _adapter(tmp_path)
    response, final = await _run_slow_provider(adapter, monkeypatch, heartbeat_on=False)

    assert final["state"] == "HUMAN_REVIEW"
    assert str(response["final_answer"]).startswith("[SCP: Answer withheld")
    assert "391" not in str(response["final_answer"])
    assert response["verdict"] == "FAIL"
    reasons = [
        str(row["reason"])
        for row in adapter.kernel.conn.execute(
            "SELECT reason FROM events WHERE task_id=?", (final["task_id"],)
        ).fetchall()
    ]
    assert any(r.startswith("lifecycle_authority_lost:") for r in reasons), (
        "old lease-expiry death must reproduce with the heartbeat disabled"
    )
    assert any(r == "heartbeat_expired" for r in reasons)  # watchdog swept the dead TTL
    adapter.kernel.close()


# ---------------------------------------------------------------------------
# (d) heartbeat must not leak: provider exception -> renew stops
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_exception_stops_heartbeat_no_renew_after_release(tmp_path, monkeypatch):
    monkeypatch.setenv("SCP_ASK_LEASE_TTL_SECONDS", "2")
    monkeypatch.delenv("SCP_ASK_LEASE_HEARTBEAT", raising=False)
    adapter = _adapter(tmp_path)

    observed_released: list[int] = []
    original_renew = adapter.kernel.renew_lease

    def spy(task_id, lease_id, fencing_token, ttl_seconds=None):
        row = adapter.kernel.conn.execute(
            "SELECT released FROM leases WHERE lease_id=?", (lease_id,)
        ).fetchone()
        observed_released.append(int(row["released"]) if row else 1)
        return original_renew(task_id, lease_id, fencing_token, ttl_seconds=ttl_seconds)

    monkeypatch.setattr(adapter.kernel, "renew_lease", spy)

    async def exploding_provider(req, request):
        await asyncio.sleep(2.5)  # past one TTL: heartbeat must have ticked
        raise RuntimeError("provider boom")

    with pytest.raises(RuntimeError, match="provider boom"):
        await adapter.run_rag(SlowReq(), None, exploding_provider)

    assert len(observed_released) >= 1, "heartbeat must have renewed while provider slept"
    # At most ONE call may observe a released lease (the stop-race tail); the
    # loop must never keep renewing a lease that has already been revoked.
    assert all(flag == 0 for flag in observed_released[:-1])
    count_at_return = len(observed_released)
    await asyncio.sleep(1.6)  # > 3x the 0.67s heartbeat interval
    assert len(observed_released) == count_at_return, "heartbeat task leaked past run_rag"
    adapter.kernel.close()


# ---------------------------------------------------------------------------
# (e) TTL / kill-switch env parsing: bad values must never crash or mean 0
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["abc", "", "0", "-5", "  ", "6.5"])
def test_bad_ttl_env_falls_back_to_default(monkeypatch, raw):
    monkeypatch.setenv("SCP_ASK_LEASE_TTL_SECONDS", raw)
    assert ask_lease_ttl_seconds() == DEFAULT_ASK_LEASE_TTL_SECONDS == 60


def test_ttl_env_unset_is_default_and_valid_value_applied(monkeypatch):
    monkeypatch.delenv("SCP_ASK_LEASE_TTL_SECONDS", raising=False)
    assert ask_lease_ttl_seconds() == 60
    monkeypatch.setenv("SCP_ASK_LEASE_TTL_SECONDS", "45")
    assert ask_lease_ttl_seconds() == 45
    monkeypatch.setenv("SCP_ASK_LEASE_TTL_SECONDS", " 30 ")
    assert ask_lease_ttl_seconds() == 30


@pytest.mark.parametrize("raw", ["0", "false", "OFF", "no"])
def test_heartbeat_kill_switch_values(monkeypatch, raw):
    monkeypatch.setenv("SCP_ASK_LEASE_HEARTBEAT", raw)
    assert ask_lease_heartbeat_enabled() is False


@pytest.mark.parametrize("raw", ["", "1", "true", "anything"])
def test_heartbeat_defaults_to_enabled(monkeypatch, raw):
    monkeypatch.setenv("SCP_ASK_LEASE_HEARTBEAT", raw)
    assert ask_lease_heartbeat_enabled() is True
    monkeypatch.delenv("SCP_ASK_LEASE_HEARTBEAT", raising=False)
    assert ask_lease_heartbeat_enabled() is True
