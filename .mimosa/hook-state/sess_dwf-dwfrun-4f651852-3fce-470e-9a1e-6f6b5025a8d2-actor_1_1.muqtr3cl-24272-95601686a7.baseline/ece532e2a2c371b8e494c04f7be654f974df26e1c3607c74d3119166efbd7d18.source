from __future__ import annotations

import pytest

from scp.ask_kernel_adapter import AskKernelAdapter


class DummyReq:
    question = "what color is the sky?"
    contexts = ["sky is blue"]
    retrieved_context = ""
    session_id = "terminal-race"


RAW_RESPONSE = {
    "final_answer": "UNVERIFIED ANSWER MUST NOT ESCAPE",
    "verdict": "PASS",
    "governance_decision": "UPHOLD",
    "confidence": 1.0,
    "trace_id": "trace-terminal-race",
}


def _assert_terminal_fail_closed(adapter, task, result):
    assert result["task"]["state"] == "CANCELLED"
    assert result["verification"]["verdict"] == "INSUFFICIENT"
    assert "task_terminal_before_verification" in result["verification"]["failures"]
    safe = result["safe_response"]
    assert safe["verdict"] == "FAIL"
    assert safe["confidence"] == 0.0
    assert safe["governance_decision"] in {"ESCALATE", "KILL"}
    assert safe["final_answer"].startswith("[SCP: Answer withheld")
    assert "UNVERIFIED ANSWER MUST NOT ESCAPE" not in safe["final_answer"]
    assert adapter.kernel.get_task(task["task_id"])["state"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancelled_task_before_finalize_withholds_unverified_response(tmp_path, monkeypatch):
    adapter = AskKernelAdapter(
        db_path=str(tmp_path / "kernel.sqlite3"),
        trace_path=str(tmp_path / "trace.jsonl"),
    )
    req = DummyReq()
    task = adapter.begin(
        req.question,
        list(req.contexts),
        req.retrieved_context,
        req.session_id,
    )
    adapter.kernel.transition(
        task["task_id"],
        "CANCELLED",
        actor="test",
        reason="simulate kill-switch race while handler was in flight",
    )

    async def forbidden_verify(*args, **kwargs):
        raise AssertionError("terminal task must not enter response verification")

    monkeypatch.setattr(adapter, "verify_response", forbidden_verify)
    result = await adapter.finalize(task, dict(RAW_RESPONSE), req)
    _assert_terminal_fail_closed(adapter, task, result)
    adapter.kernel.close()


@pytest.mark.asyncio
async def test_cancel_between_precheck_and_verifying_transition_fails_closed(tmp_path, monkeypatch):
    adapter = AskKernelAdapter(
        db_path=str(tmp_path / "kernel-race.sqlite3"),
        trace_path=str(tmp_path / "trace-race.jsonl"),
    )
    req = DummyReq()
    task = adapter.begin(
        req.question,
        list(req.contexts),
        req.retrieved_context,
        "terminal-race-toctou",
    )
    real_transition = adapter.kernel.transition
    injected = {"done": False}

    def racing_transition(task_id, new_state, *args, **kwargs):
        if new_state == "VERIFYING" and not injected["done"]:
            injected["done"] = True
            real_transition(
                task_id,
                "CANCELLED",
                actor="test",
                reason="cancel exactly between terminal precheck and VERIFYING transition",
            )
        return real_transition(task_id, new_state, *args, **kwargs)

    async def forbidden_verify(*args, **kwargs):
        raise AssertionError("raced terminal task must not enter response verification")

    monkeypatch.setattr(adapter.kernel, "transition", racing_transition)
    monkeypatch.setattr(adapter, "verify_response", forbidden_verify)

    result = await adapter.finalize(task, dict(RAW_RESPONSE), req)

    assert injected["done"] is True
    _assert_terminal_fail_closed(adapter, task, result)
    adapter.kernel.close()
