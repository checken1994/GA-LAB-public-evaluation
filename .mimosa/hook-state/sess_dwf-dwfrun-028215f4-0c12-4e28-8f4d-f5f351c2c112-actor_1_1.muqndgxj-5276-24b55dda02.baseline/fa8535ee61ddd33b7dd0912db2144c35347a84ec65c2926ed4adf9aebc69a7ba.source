"""S19 regression tests — live-benchmark PRODUCT bugs 2026-09-13.

Bug 1: /ask finalize assumed the task was still RUNNING. A boot-replay /
watchdog-reconciled task sits in RECONCILING (or RECOVERING/UNKNOWN/
HUMAN_REVIEW after a lease-expiry sweep), and the unconditional
``transition(VERIFYING)`` raised InvalidTransition -> HTTP 500. The W2
witness report (reports/witness/WITNESS-REPORT-W2-2026-09-11.md, bug 1)
recorded the same family: ``InvalidTransition: HUMAN_REVIEW->HUMAN_REVIEW``
on a double escalation.

Bug 2: the durable ask identity was ``request_id or f"{session}|{hash}"``.
A client idempotency key REPLACED the question/evidence hash entirely, so
one reused key mapped every different question onto the first ask's task
and all later requests died with ``KernelError: stable logical ask already
exists`` — the endpoint locked after the first question (benchmark seed-42
re-run / seed-7 timeout, 2026-09-13).

Design decision under test (documented in
reports/expert-panel/S19-ask-kernel-fixes.md): option (b) — finalize
routes by current state; ALLOWED_TRANSITIONS stays strict (a stale attempt
whose lease was revoked by fencing must NOT gain a RECONCILING->VERIFYING
auto-complete edge), and HUMAN_REVIEW escalation is an idempotent
no-op/skip, never a raise.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from scp.ask_kernel_adapter import AskKernelAdapter
from scp.task_kernel import ALLOWED_TRANSITIONS, KernelError, StaleLease

RUN_KEY = "run-1"


class DummyReq:
    question = "what color is the sky?"
    contexts = ["sky is blue"]
    retrieved_context = ""
    session_id = "s19-lifecycle"
    domain = "general"
    domain_override = ""
    rag_enabled = True


OTHER_REQ = SimpleNamespace(
    question="What is 12*8?",
    contexts=[],
    retrieved_context="",
    session_id=None,
    domain="general",
    domain_override="",
    rag_enabled=False,
)

RAW_RESPONSE = {
    "final_answer": "UNVERIFIED ANSWER MUST NOT ESCAPE",
    "verdict": "PASS",
    "governance_decision": "UPHOLD",
    "confidence": 1.0,
    "trace_id": "trace-s19",
}

CONTRADICTED = {
    "verdict": "CONTRADICTED",
    "verifier_id": "test-verifier",
    "evidence_ref": "ask://s19/contradicted",
    "failures": ["judge_pass"],
    "checked": {"judge_pass": False},
}

VERIFIED = {
    "verdict": "VERIFIED",
    "verifier_id": "test-verifier",
    "evidence_ref": "ask://s19/verified",
    "failures": [],
    "checked": {"judge_pass": True},
}


def _adapter(tmp_path):
    return AskKernelAdapter(
        db_path=str(tmp_path / "kernel.sqlite3"),
        trace_path=str(tmp_path / "trace.jsonl"),
    )


def _begin(adapter, req=DummyReq, request=None):
    return adapter.begin(
        req.question,
        list(req.contexts or []),
        req.retrieved_context or "",
        req.session_id,
        request=request,
    )


def _drive(adapter, task_id, states):
    """Move a task through states the same way boot-recovery /
    auto_reconcile_orphans / lease expiry do (legal edges only)."""
    for state in states:
        adapter.kernel.transition(task_id, state, actor="test-sim", reason=f"s19_drive:{state}")


def _keyed_request(key=RUN_KEY):
    return SimpleNamespace(headers={"X-SCP-Idempotency-Key": key})


async def _forbidden_verify(*args, **kwargs):
    raise AssertionError("lifecycle-race finalize must not run response verification")


def _assert_withheld(result):
    safe = result["safe_response"]
    assert safe["verdict"] == "FAIL"
    assert safe["confidence"] == 0.0
    assert str(safe["final_answer"]).startswith("[SCP: Answer withheld")
    assert "UNVERIFIED ANSWER MUST NOT ESCAPE" not in str(safe["final_answer"])


# ---------------------------------------------------------------------------
# Bug 1 — finalize must route by current state, never 500
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_finalize_from_reconciling_returns_withheld_result_not_500(tmp_path, monkeypatch):
    """Runtime stacktrace 2026-09-13: InvalidTransition RECONCILING->VERIFYING
    at ask_kernel_adapter.finalize. A reconciled task's response must be
    intercepted fail-closed (withheld, escalated), not crash the request."""
    adapter = _adapter(tmp_path)
    req = DummyReq()
    task = _begin(adapter, req)
    assert adapter.kernel.get_task(task["task_id"])["state"] == "RUNNING"
    # watchdog/boot-replay path: RUNNING -> RECOVERING -> RECONCILING
    _drive(adapter, task["task_id"], ("RECOVERING", "RECONCILING"))
    monkeypatch.setattr(adapter, "verify_response", _forbidden_verify)

    result = await adapter.finalize(task, dict(RAW_RESPONSE), req)

    assert result["verification"]["verdict"] == "INSUFFICIENT"
    assert result["verification"]["failures"] == ["lifecycle_authority_lost:RECONCILING"]
    final = adapter.kernel.get_task(task["task_id"])
    assert final["state"] == "HUMAN_REVIEW", "RECONCILING must escalate via the legal edge"
    _assert_withheld(result)
    adapter.kernel.close()


@pytest.mark.asyncio
async def test_finalize_from_human_review_never_raises(tmp_path, monkeypatch):
    """W2 witness bug 1: a task already sitting in HUMAN_REVIEW (boot
    recovery moved RUNNING/VERIFYING there, or lease sweep VERIFYING->
    HUMAN_REVIEW) must not crash finalize a second time."""
    adapter = _adapter(tmp_path)
    req = DummyReq()
    task = _begin(adapter, req)
    _drive(adapter, task["task_id"], ("HUMAN_REVIEW",))
    monkeypatch.setattr(adapter, "verify_response", _forbidden_verify)

    result = await adapter.finalize(task, dict(RAW_RESPONSE), req)

    assert result["verification"]["verdict"] == "INSUFFICIENT"
    assert result["verification"]["failures"] == ["lifecycle_authority_lost:HUMAN_REVIEW"]
    assert adapter.kernel.get_task(task["task_id"])["state"] == "HUMAN_REVIEW"
    _assert_withheld(result)
    adapter.kernel.close()


@pytest.mark.asyncio
async def test_double_escalation_is_idempotent_noop_not_raise(tmp_path, monkeypatch):
    """W2 exact crash: finalize escalated a task that had ALREADY entered
    HUMAN_REVIEW mid-verification (lease-expiry race). The second
    escalation must be a no-op with a log, never InvalidTransition."""
    adapter = _adapter(tmp_path)
    req = DummyReq()
    task = _begin(adapter, req)

    async def racing_verify(*args, **kwargs):
        # Simulates expire_leases sweeping VERIFYING -> HUMAN_REVIEW while
        # the (slow) judge runs.
        adapter.kernel.transition(
            task["task_id"], "HUMAN_REVIEW", actor="test-sim", reason="lease_expired_sweep_race"
        )
        return dict(CONTRADICTED)

    monkeypatch.setattr(adapter, "verify_response", racing_verify)

    result = await adapter.finalize(task, dict(RAW_RESPONSE), req)

    assert result["verification"]["verdict"] == "CONTRADICTED"
    assert adapter.kernel.get_task(task["task_id"])["state"] == "HUMAN_REVIEW"
    _assert_withheld(result)
    adapter.kernel.close()


@pytest.mark.asyncio
async def test_verified_commit_racing_stale_lease_does_not_500(tmp_path, monkeypatch):
    """Same family: a verified answer whose lease died mid-verification must
    not 500 nor complete via a stale lease; route to lifecycle-race
    escalation instead."""
    monkeypatch.setenv("SCP_VERIFIER_SECRET", "s19-unit-test-dummy-secret")
    adapter = _adapter(tmp_path)
    req = DummyReq()
    task = _begin(adapter, req)

    async def verified(*args, **kwargs):
        return dict(VERIFIED)

    def stale_commit(*args, **kwargs):
        raise StaleLease("lease expired during verification")

    monkeypatch.setattr(adapter, "verify_response", verified)
    monkeypatch.setattr(adapter.kernel, "commit_verification_result", stale_commit)

    result = await adapter.finalize(task, dict(RAW_RESPONSE), req)

    assert result["verification"]["verdict"] == "INSUFFICIENT"
    assert result["verification"]["failures"] == ["commit_raced_lease_or_state"]
    assert adapter.kernel.get_task(task["task_id"])["state"] == "HUMAN_REVIEW"
    _assert_withheld(result)
    adapter.kernel.close()


@pytest.mark.asyncio
async def test_normal_running_finalize_path_is_unchanged(tmp_path, monkeypatch):
    """Anti-placebo: the happy path still verifies, signs a receipt and
    commits to COMPLETED — the lifecycle routing must not have broken
    normal completion."""
    monkeypatch.setenv("SCP_VERIFIER_SECRET", "s19-unit-test-dummy-secret")
    adapter = _adapter(tmp_path)
    req = DummyReq()
    task = _begin(adapter, req)

    async def verified(*args, **kwargs):
        return dict(VERIFIED)

    monkeypatch.setattr(adapter, "verify_response", verified)

    result = await adapter.finalize(task, dict(RAW_RESPONSE), req)

    assert result["verification"]["verdict"] == "VERIFIED"
    assert adapter.kernel.get_task(task["task_id"])["state"] == "COMPLETED"
    assert result["safe_response"]["final_answer"] == "UNVERIFIED ANSWER MUST NOT ESCAPE"
    adapter.kernel.close()


def test_transition_table_stays_strict_reconciling_and_human_review():
    """The fix deliberately did NOT add RECONCILING->VERIFYING nor a
    HUMAN_REVIEW self-edge: recovery contract says a reconciled/escalated
    task exits to HUMAN_REVIEW and never auto-completes from a revoked
    attempt. Pin that so nobody 'fixes' bug 1 by widening the map."""
    assert "VERIFYING" not in ALLOWED_TRANSITIONS["RECONCILING"]
    assert "HUMAN_REVIEW" not in ALLOWED_TRANSITIONS["HUMAN_REVIEW"]
    assert "HUMAN_REVIEW" in ALLOWED_TRANSITIONS["RECONCILING"]
    assert "HUMAN_REVIEW" in ALLOWED_TRANSITIONS["UNKNOWN"]
    assert "HUMAN_REVIEW" in ALLOWED_TRANSITIONS["RECOVERING"]


# ---------------------------------------------------------------------------
# Bug 2 — durable identity must discriminate per question
# ---------------------------------------------------------------------------


def test_task_id_for_always_includes_question_hash():
    keyed_q1 = AskKernelAdapter.task_id_for("Q1", [], "", None, RUN_KEY)
    keyed_q2 = AskKernelAdapter.task_id_for("What is 12*8?", [], "", None, RUN_KEY)
    same_again = AskKernelAdapter.task_id_for("Q1", [], "", None, RUN_KEY)
    sessioned = AskKernelAdapter.task_id_for("Q1", [], "", "s1", None)
    assert keyed_q1 != keyed_q2, "same idempotency key must NOT collapse different questions"
    assert keyed_q1 == same_again, "same key + same body must still dedupe transport retries"
    assert keyed_q1 != sessioned


def test_same_key_different_questions_do_not_collide(tmp_path):
    """Runtime proof 2026-09-13: second question ("What is 12*8?") died with
    'stable logical ask already exists' under a reused key. Both must run."""
    adapter = _adapter(tmp_path)
    t1 = _begin(adapter, DummyReq, request=_keyed_request())
    t2 = _begin(adapter, OTHER_REQ, request=_keyed_request())
    assert t1["task_id"] != t2["task_id"]
    assert adapter.kernel.get_task(t1["task_id"])["state"] == "RUNNING"
    assert adapter.kernel.get_task(t2["task_id"])["state"] == "RUNNING"
    assert adapter.kernel.in_flight_count() == 2
    adapter.kernel.close()


def test_same_key_same_question_transport_retry_still_deduped(tmp_path):
    """Idempotency must survive: one in-flight duplicate under the same key
    is a transport retry and is still refused fail-closed."""
    adapter = _adapter(tmp_path)
    _begin(adapter, DummyReq, request=_keyed_request())
    with pytest.raises(KernelError, match="stable logical ask already exists"):
        _begin(adapter, DummyReq, request=_keyed_request())
    assert adapter.kernel.in_flight_count() == 1
    adapter.kernel.close()


def test_same_session_same_question_still_deduped(tmp_path):
    adapter = _adapter(tmp_path)
    _begin(adapter, DummyReq)
    with pytest.raises(KernelError, match="stable logical ask already exists"):
        _begin(adapter, DummyReq)
    adapter.kernel.close()


def test_different_questions_same_session_both_run(tmp_path):
    adapter = _adapter(tmp_path)
    t1 = _begin(adapter, DummyReq)
    t2 = _begin(adapter, OTHER_REQ)
    assert t1["task_id"] != t2["task_id"]
    adapter.kernel.close()


def test_reask_after_decision_runs_fresh_uniquified_task(tmp_path):
    """Seed re-run behaviour: once the first ask REACHED A DECISION
    (HUMAN_REVIEW here), an identical request must execute again as a new
    durable ask instead of being blocked forever."""
    adapter = _adapter(tmp_path)
    t1 = _begin(adapter, DummyReq)
    _drive(adapter, t1["task_id"], ("HUMAN_REVIEW",))
    t2 = _begin(adapter, DummyReq)
    assert t2["task_id"] != t1["task_id"]
    assert t2["task_id"].startswith(t1["task_id"].split("-")[0])
    assert adapter.kernel.get_task(t1["task_id"])["state"] == "HUMAN_REVIEW"
    assert adapter.kernel.get_task(t2["task_id"])["state"] == "RUNNING"
    adapter.kernel.close()
