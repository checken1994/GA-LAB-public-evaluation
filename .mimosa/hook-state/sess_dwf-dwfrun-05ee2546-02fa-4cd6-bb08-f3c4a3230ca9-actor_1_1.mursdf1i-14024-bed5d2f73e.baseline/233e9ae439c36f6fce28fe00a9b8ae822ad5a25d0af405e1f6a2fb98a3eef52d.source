"""[W1-c2 2026-10-02] Valid chatbot-lane answers must NOT be wrongly refused
by the lifecycle route or the response verifier ("refuse-block" guard).

Runtime failure being pinned against (audit, same SHA): q05 122.4s / q11 89.4s
were withheld as ``lifecycle_authority_lost`` even though the answer had been
generated correctly — the watchdog expire sweep moved RUNNING->RECOVERING and
finalize's state route discarded a valid chatbot-lane answer. The structural
fixes land in c3 (heartbeat retry) and c4 (TTL knob); THIS commit pins the
delivery contract with a two-layer guard so no later change to the lifecycle
route or the verifier may start refusing valid chatbot-lane answers:

  Layer 1 — LIFECYCLE: the task must finish COMPLETED through the legal
  RUNNING->VERIFYING->COMPLETED path with zero ``lifecycle_authority_lost``
  / ``heartbeat_expired`` events and no HUMAN_REVIEW escalation.
  Layer 2 — VERIFY: with the REAL ``verify_response`` (never monkeypatched
  here), the verdict must be VERIFIED and the delivered response must keep
  the current valid-response shape (final_answer intact, no "[SCP:" withhold
  text, verdict PASS, governance clearance preserved, confidence > 0).

Anti-placebo: the assertions are behavioural (delivered text equals the
generated chatbot text). If lifecycle or verify ever withholds, the delivered
``final_answer`` becomes "[SCP: Answer withheld — ...]" (adapter
_safe_response) and every layer-2 assert fails.

Hermetic: monkeypatch.setenv only (no direct os.environ writes), no network —
the chatbot-lane verifier branch derives judge_pass from the governance
clearance and never calls RealityJudge.
"""
from __future__ import annotations

import asyncio

import pytest

from scp.ask_kernel_adapter import AskKernelAdapter
from scp.runtime.question_router import LANE_CHATBOT, route_question

C2_VERIFIER_SECRET = "w1-c2-unit-test-dummy-secret"

CHATBOT_QUESTION = "chào bạn, bạn tên là gì?"
CHATBOT_ANSWER = "Chào bạn! Mình là SCP, rất vui được trò chuyện cùng bạn."


def _assert_chatbot_lane_question() -> None:
    decision = route_question(CHATBOT_QUESTION)
    assert decision.lane == LANE_CHATBOT, (
        "guard vô nghĩa nếu câu hỏi probe không còn thuộc LANE_CHATBOT "
        f"(lane={decision.lane}, via={decision.via})"
    )


class ChatbotReq:
    question = CHATBOT_QUESTION
    contexts = []  # general chat: no evidence carried
    retrieved_context = ""
    session_id = "w1-c2-chatbot"
    domain = "general"
    domain_override = ""
    rag_enabled = True


def _chatbot_response(governance: str) -> dict:
    """Current valid chatbot-lane response shape (mirrors the _ask_impl
    boundary output: verdict/governance_decision/final_answer/confidence/lane
    plus the judge_evaluated provenance the verifier reads)."""
    return {
        "final_answer": CHATBOT_ANSWER,
        "verdict": "PASS",
        "governance_decision": governance,
        "confidence": 0.9,
        "lane": "LANE_CHATBOT",
        "judge_evaluated": True,
        "evidence": {"judge_evaluated": True, "governance_decision": governance},
        "slm_trace": [{"model": "w1-c2"}],
        "elapsed_ms": 12.5,
        "trace_id": "trace-w1-c2",
    }


def _adapter(tmp_path) -> AskKernelAdapter:
    return AskKernelAdapter(
        db_path=str(tmp_path / "kernel.sqlite3"),
        trace_path=str(tmp_path / "trace.jsonl"),
    )


def _task_id_for_req() -> str:
    return AskKernelAdapter.task_id_for(
        ChatbotReq.question, list(ChatbotReq.contexts), "", ChatbotReq.session_id, None
    )


def _journal_reasons(adapter: AskKernelAdapter, task_id: str) -> list[str]:
    return [
        str(row["reason"])
        for row in adapter.kernel.conn.execute(
            "SELECT reason FROM events WHERE task_id=?", (task_id,)
        ).fetchall()
    ]


def _assert_delivered_shape_unchanged(response: dict, governance: str) -> None:
    """Layer 2 — the delivered response keeps the CURRENT valid shape."""
    assert response["final_answer"] == CHATBOT_ANSWER, (
        f"valid chatbot answer was rewritten (withheld?): {response['final_answer']!r}"
    )
    assert not str(response["final_answer"]).startswith("[SCP:")
    assert response["verdict"] == "PASS"
    assert response["governance_decision"] == governance
    assert float(response["confidence"]) > 0.0


# ---------------------------------------------------------------------------
# Guard layer 1+2 — fast provider, real verify, both chatbot clearances
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("governance", ["UPHOLD", "ALLOW"])
async def test_valid_chatbot_lane_answer_delivered_through_real_verify(
    tmp_path, monkeypatch, governance
):
    """A valid chatbot-lane answer (verdict PASS + governance clearance) must
    be DELIVERED through the real verify_response + finalize, never refused by
    the lifecycle route or the verifier."""
    _assert_chatbot_lane_question()
    monkeypatch.setenv("SCP_VERIFIER_SECRET", C2_VERIFIER_SECRET)
    monkeypatch.delenv("SCP_ASK_LEASE_TTL_SECONDS", raising=False)
    monkeypatch.delenv("SCP_ASK_LEASE_HEARTBEAT", raising=False)
    adapter = _adapter(tmp_path)

    async def fast_provider(req, request):
        return dict(_chatbot_response(governance))

    response = await adapter.run_rag(ChatbotReq(), None, fast_provider)

    task_id = _task_id_for_req()
    task = adapter.kernel.get_task(task_id)

    # Layer 1 — lifecycle did not refuse: legal happy-path terminal state.
    assert task["state"] == "COMPLETED"
    reasons = _journal_reasons(adapter, task_id)
    assert not any("lifecycle_authority_lost" in r for r in reasons), (
        f"lifecycle route withheld a valid chatbot-lane answer: {reasons}"
    )
    assert not any("heartbeat_expired" in r for r in reasons)

    # Layer 2 — verify did not refuse: delivered shape is the valid one.
    _assert_delivered_shape_unchanged(response, governance)
    adapter.kernel.close()


# ---------------------------------------------------------------------------
# Guard layer 1+2 under lease pressure — provider slower than the claim TTL,
# watchdog sweeping mid-flight, REAL verify (no monkeypatch), heartbeat ON.
# The lease survives via renewal, so a valid chatbot-lane answer must still
# be delivered — the q05/q11 shape of refusal must not reproduce here.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_chatbot_lane_answer_survives_lease_pressure_slow_provider(
    tmp_path, monkeypatch
):
    _assert_chatbot_lane_question()
    monkeypatch.setenv("SCP_VERIFIER_SECRET", C2_VERIFIER_SECRET)
    monkeypatch.setenv("SCP_ASK_LEASE_TTL_SECONDS", "2")
    monkeypatch.delenv("SCP_ASK_LEASE_HEARTBEAT", raising=False)
    adapter = _adapter(tmp_path)

    async def slow_provider(req, request):
        await asyncio.sleep(2.6)
        adapter.kernel.expire_leases()  # same call the 30s watchdog makes
        await asyncio.sleep(2.6)
        adapter.kernel.expire_leases()
        return dict(_chatbot_response("UPHOLD"))

    response = await adapter.run_rag(ChatbotReq(), None, slow_provider)

    task_id = _task_id_for_req()
    task = adapter.kernel.get_task(task_id)

    # Layer 1 — lifecycle: COMPLETED, no authority-lost refusal.
    assert task["state"] == "COMPLETED"
    reasons = _journal_reasons(adapter, task_id)
    assert not any("lifecycle_authority_lost" in r for r in reasons), (
        f"lease pressure withheld a valid chatbot-lane answer: {reasons}"
    )
    assert not any(r == "heartbeat_expired" for r in reasons)

    # Layer 2 — verify: real verification VERIFIED, answer text intact.
    _assert_delivered_shape_unchanged(response, "UPHOLD")
    adapter.kernel.close()
