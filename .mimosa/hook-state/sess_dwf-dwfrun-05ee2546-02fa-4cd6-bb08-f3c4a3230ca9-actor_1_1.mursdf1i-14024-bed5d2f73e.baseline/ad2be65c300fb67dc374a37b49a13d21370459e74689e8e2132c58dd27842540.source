import pytest


@pytest.fixture(autouse=True)
def _no_crosscheck(monkeypatch):
    monkeypatch.setenv("SCP_MULTI_LLM_CROSSCHECK", "0")
from scp.ask_kernel_adapter import AskKernelAdapter


class DummyReq:
    contexts = ["sky is blue"]
    retrieved_context = ""
    question = "what color is the sky?"


PASSING_RESPONSE = {
    "final_answer": "The sky is blue",
    "verdict": "PASS",
    "governance_decision": "UPHOLD",
    "v98_classification": {"provenance": "input_context_only"},
}


@pytest.fixture()
def judge_gate(monkeypatch):
    """Hermetic semantic judge.

    TẠI SAO mock: verify_response() đi qua RealityJudge → _llm_judge, mà bản
    thật gọi OpenRouter API. Test phụ thuộc mạng/cloud là test non-hermetic
    (đã từng FAIL chỉ vì model cold-start quá 15s). Patch tại
    scp.runtime.judge (nơi judge.py giữ tham chiếu đã import).
    """
    import scp.runtime.judge_llm as judge_mod

    state = {"pass": True, "calls": 0}

    async def _fake_judge(question: str, ai_answer: str, context: str = "") -> bool:
        state["calls"] += 1
        return state["pass"]

    monkeypatch.setattr(judge_mod, "_llm_judge_async", _fake_judge)
    return state


@pytest.mark.asyncio
async def test_rag_ask_with_passing_judge_is_verified(judge_gate):
    adapter = AskKernelAdapter(db_path=":memory:", trace_path="/tmp")
    req = DummyReq()
    task = {"task_id": "test_123"}

    result = await adapter.verify_response(req, dict(PASSING_RESPONSE), task)
    assert result["verdict"] == "VERIFIED"
    assert 0.0 <= result["grounded_ratio"] <= 1.0
    assert result["checked"]["rag_evidence_bound"] is True
    assert judge_gate["calls"] == 1


@pytest.mark.asyncio
async def test_chat_ask_without_contexts_uses_judge_semantics(judge_gate):
    """No request evidence = general-knowledge chat ask: the judge + governance
    pipeline is the verifier; grounding is not applicable (contract 2026-08-29)."""
    adapter = AskKernelAdapter(db_path=":memory:", trace_path="/tmp")
    req = DummyReq()
    req.contexts = []
    task = {"task_id": "test_123"}

    result = await adapter.verify_response(req, dict(PASSING_RESPONSE), task)
    assert result["verdict"] == "VERIFIED"
    assert result["grounded_ratio"] == 0.0
    assert "rag_evidence_bound" not in result["checked"]


@pytest.mark.asyncio
async def test_failing_judge_contradicts_any_ask(judge_gate):
    adapter = AskKernelAdapter(db_path=":memory:", trace_path="/tmp")
    req = DummyReq()
    task = {"task_id": "test_123"}

    judge_gate["pass"] = False
    result = await adapter.verify_response(req, dict(PASSING_RESPONSE), task)
    assert result["verdict"] == "CONTRADICTED"
    assert "judge_pass" in result["failures"]
