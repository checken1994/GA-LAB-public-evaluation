# SCP CIRCUIT: S24 — LOOKUP fork unit tests (hermetic).
"""T07/S24 — test fork LOOKUP→data-API trong AskKernelAdapter.run_rag.

Phủ design chốt của task S24:
  (a) Fork thành công: answer compose từ data-API, KHÔNG gọi LLM generation
      (handler spy phải không chạy), llm_bypassed_count tăng.
  (b) Fork miss (catalog không có entry / fetch fail / REASONING): fallback
      LLM CÓ reason được log, llm_calls_count tăng.
  (c) Provenance="input_context_only" + evidence data-API được đưa vào CÙNG
      verification path (grounded/judge check nhận thêm bằng chứng).
  (d) Kill switch SCP_T2_ROUTER=0 → handler chạy như cũ.
  (e) Scope v1: RAG ask (có contexts) / replay (ai_answer) KHÔNG fork.

Không mạng: catalog + fetch + wiki + judge đều mock. Không skip/xfail.
"""
from __future__ import annotations

import pytest

from scp.ask_kernel_adapter import AskKernelAdapter

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _no_crosscheck(monkeypatch):
    monkeypatch.setenv("SCP_MULTI_LLM_CROSSCHECK", "0")


@pytest.fixture()
def judge_gate(monkeypatch):
    """Hermetic judge (same pattern as T04 test_ask_kernel_adapter_verify)."""
    import scp.runtime.judge_llm as judge_mod

    state = {"pass": True, "calls": 0}

    async def _fake_judge(question: str, ai_answer: str, context: str = "") -> bool:
        state["calls"] += 1
        return state["pass"]

    monkeypatch.setattr(judge_mod, "_llm_judge_async", _fake_judge)
    return state


class ForkReq:
    def __init__(self, question="What is the capital of France?"):
        self.question = question
        self.ai_answer = ""
        self.contexts = []
        self.retrieved_context = ""
        self.session_id = "sess-s24-test"
        self.source = "api"


FORK_DATA = {
    "text": "Paris is the capital and largest city of France.",
    "api_name": "Wikipedia (en) — France",
    "api_url": "https://en.wikipedia.org/wiki/France",
    "evidence": "Paris is the capital and largest city of France.",
}


@pytest.fixture()
def fork_stats_guard():
    """Stats singleton dùng delta — không reset prod state."""
    from scp.runtime.question_router import route_stats_snapshot

    return route_stats_snapshot()


# ---------------------------------------------------------------------------
# (a) attempt_lookup_fork thành công
# ---------------------------------------------------------------------------
async def test_fork_success_composes_answer_without_generation(monkeypatch, fork_stats_guard):
    from scp.runtime import question_router as qr

    async def _fake_route(question, gateway=None):
        return qr.RouteDecision(qr.LOOKUP, "geography", 0.75, "l0-keyword", "lookup_signal:interrogative_en")

    monkeypatch.setattr(qr, "route_question_async", _fake_route)
    monkeypatch.setattr(qr, "resolve_lookup_data", lambda *a, **k: dict(FORK_DATA))

    result = await qr.attempt_lookup_fork(ForkReq())
    assert result is not None
    assert result["verdict"] == "PASS"
    assert "Paris is the capital" in result["final_answer"]
    assert "Wikipedia (en) — France" in result["final_answer"]
    assert "https://en.wikipedia.org/wiki/France" in result["final_answer"]
    assert result["v98_classification"]["provenance"] == "input_context_only"
    assert result["v98_classification"]["route"] == "lookup_data_api"
    # Evidence = payload thô + provenance suffix (contract S24: evidence đưa
    # vào verification phải chứa TOÀN BỘ phần answer compose từ nó).
    assert result["data_api_evidence"] == (
        FORK_DATA["evidence"] + "\n(Nguồn dữ liệu: Wikipedia (en) — France — https://en.wikipedia.org/wiki/France)"
    )
    after = qr.route_stats_snapshot()
    assert after["llm_bypassed_count"] == fork_stats_guard["llm_bypassed_count"] + 1


async def test_fork_success_skips_handler_in_run_rag(monkeypatch, judge_gate, tmp_path):
    """Integration: run_rag với fork OK — handler (generation) KHÔNG chạy,
    answer vẫn đi qua finalize/verify (VERIFIED)."""
    from scp.runtime import question_router as qr

    async def _fake_fork(req):
        return {
            "verdict": "PASS",
            "final_answer": "Paris is the capital and largest city of France.\n\n(Nguồn dữ liệu: Wikipedia (en) — France — https://en.wikipedia.org/wiki/France)",
            "confidence": 0.75,
            "domain": "geography",
            "governance_decision": "UPHOLD",
            "reasoning": "[S24 lookup via l0-keyword]",
            "v98_classification": {"provenance": "input_context_only", "route": "lookup_data_api"},
            "data_api_evidence": "Paris is the capital and largest city of France.\n(Nguồn dữ liệu: Wikipedia (en) — France — https://en.wikipedia.org/wiki/France)",
            "slm_responses": [],
            "slm_trace": [],
            "elapsed_ms": 12.0,
            "session_id": "sess-s24",
            "run_id": "run-lookup-test",
            "trace_id": "trace-lookup-test",
            "run_status": "COMPLETED",
            "ledger_status": "COMMITTED",
        }

    monkeypatch.setattr(qr, "attempt_lookup_fork", _fake_fork)
    monkeypatch.setenv("SCP_T2_ROUTER", "1")

    called = {"handler": 0}

    async def handler(req, request):
        called["handler"] += 1
        raise AssertionError("generation handler must NOT run when fork answers")

    # [S24] trace_path PHẢI thư mục thật tồn tại (Windows '/tmp' → PermissionError
    # → begin fail → kernel blocked response — bug test, không phải product).
    trace_file = tmp_path / "trace.jsonl"
    trace_file.parent.mkdir(parents=True, exist_ok=True)
    adapter = AskKernelAdapter(db_path=":memory:", trace_path=str(trace_file))
    req = ForkReq()
    response = await adapter.run_rag(req, request=None, handler=handler)
    assert called["handler"] == 0
    assert response["verdict"] == "PASS"
    assert "Paris" in response["final_answer"]
    assert response["v98_classification"]["provenance"] == "input_context_only"


# ---------------------------------------------------------------------------
# (b) Fork miss → fallback LLM có reason
# ---------------------------------------------------------------------------
async def test_fork_miss_no_catalog_entry_falls_back_with_reason(monkeypatch, fork_stats_guard):
    from scp.runtime import question_router as qr

    async def _fake_route(question, gateway=None):
        return qr.RouteDecision(qr.LOOKUP, "finance", 0.75, "l0-keyword", "lookup_signal:finance_fact")

    monkeypatch.setattr(qr, "route_question_async", _fake_route)
    monkeypatch.setattr(qr, "resolve_lookup_data", lambda *a, **k: None)

    result = await qr.attempt_lookup_fork(ForkReq("Tỷ giá EUR/USD hôm nay?"))
    assert result is None
    after = qr.route_stats_snapshot()
    assert after["llm_calls_count"] == fork_stats_guard["llm_calls_count"] + 1


async def test_fork_reasoning_question_goes_to_llm(monkeypatch, fork_stats_guard):
    from scp.runtime import question_router as qr

    async def _fake_route(question, gateway=None):
        return qr.RouteDecision(qr.REASONING, "general", 0.9, "l0-keyword", "reasoning_signal:code_generation")

    monkeypatch.setattr(qr, "route_question_async", _fake_route)
    result = await qr.attempt_lookup_fork(ForkReq("Viết hàm Python kiểm tra số nguyên tố"))
    assert result is None
    after = qr.route_stats_snapshot()
    assert after["llm_calls_count"] == fork_stats_guard["llm_calls_count"] + 1


async def test_fork_low_confidence_does_not_fork(monkeypatch, fork_stats_guard):
    from scp.runtime import question_router as qr

    async def _fake_route(question, gateway=None):
        return qr.RouteDecision(qr.LOOKUP, "general", 0.5, "l2-llm", "llm:stub")

    monkeypatch.setattr(qr, "route_question_async", _fake_route)
    result = await qr.attempt_lookup_fork(ForkReq())
    assert result is None


async def test_fork_disabled_by_kill_switch_handler_runs(monkeypatch, judge_gate, tmp_path):
    from scp.runtime import question_router as qr

    async def _boom(req):
        raise AssertionError("fork must not run when SCP_T2_ROUTER=0")

    monkeypatch.setattr(qr, "attempt_lookup_fork", _boom)
    monkeypatch.setenv("SCP_T2_ROUTER", "0")

    handler_called = {"n": 0}

    async def handler(req, request):
        handler_called["n"] += 1
        return {
            "verdict": "PASS",
            "final_answer": "generated by llm",
            "confidence": 0.8,
            "domain": "general",
            "governance_decision": "UPHOLD",
            "v98_classification": {"provenance": "input_context_only"},
        }

    # [S24] trace_path PHẢI thư mục thật tồn tại (Windows '/tmp' → PermissionError
    # → begin fail → kernel blocked response — bug test, không phải product).
    trace_file = tmp_path / "trace.jsonl"
    trace_file.parent.mkdir(parents=True, exist_ok=True)
    adapter = AskKernelAdapter(db_path=":memory:", trace_path=str(trace_file))
    response = await adapter.run_rag(ForkReq(), request=None, handler=handler)
    assert handler_called["n"] == 1
    assert response["final_answer"] == "generated by llm"


async def test_fork_scope_excludes_rag_and_replay(monkeypatch, fork_stats_guard):
    from scp.runtime import question_router as qr

    async def _boom(req):
        raise AssertionError("fork must not run for RAG/replay asks")

    monkeypatch.setattr(qr, "route_question_async", _boom)

    rag_req = ForkReq()
    rag_req.contexts = ["some evidence"]
    assert await qr.attempt_lookup_fork(rag_req) is None

    replay_req = ForkReq()
    replay_req.ai_answer = "precomputed answer"
    assert await qr.attempt_lookup_fork(replay_req) is None


# ---------------------------------------------------------------------------
# Data path: catalog search → fetch (mock transport) → compose
# ---------------------------------------------------------------------------
async def test_resolve_lookup_data_uses_catalog_entry(monkeypatch):
    from scp.runtime import question_router as qr

    class StubCatalog:
        def search(self, query="", category=None, auth=None, limit=25):
            # Salient terms của câu hỏi: ["capital", "france"] → query "capital france"
            if "capital" in query and auth == "No":
                return [
                    {
                        "name": "SomeGeoAPI",
                        "url": "https://api.example-geo.test/capital",
                        "description": "capital data",
                        "auth": "No",
                        "category": "Geocoding",
                    }
                ]
            return []

    import scp.data_sources.free_api_catalog as cat_mod

    monkeypatch.setattr(cat_mod, "get_catalog", lambda data_dir="data": StubCatalog())
    monkeypatch.setattr(qr, "_host_allowed", lambda url: True)
    monkeypatch.setattr(qr, "_wiki_lookup", lambda question, terms: None)  # hermetic guard
    monkeypatch.setattr(
        qr,
        "_fetch_url_text",
        lambda url, timeout=6.0, max_bytes=262144: '{"fact": "Paris is the capital of France and its largest city."}',
    )

    result = qr.resolve_lookup_data("What is the capital of France?", domain="geography")
    assert result is not None
    assert result["api_name"] == "SomeGeoAPI"
    assert result["api_url"] == "https://api.example-geo.test/capital"
    assert "Paris is the capital" in result["text"]
    snap = qr.route_stats_snapshot()
    assert snap["lookup_fetch_ok"] >= 1


async def test_resolve_lookup_data_blocked_host_falls_back(monkeypatch):
    from scp.runtime import question_router as qr

    class StubCatalog:
        def search(self, query="", category=None, auth=None, limit=25):
            return [
                {
                    "name": "BlockedAPI",
                    "url": "https://blocked-host.test/api",
                    "description": "capital data",
                    "auth": "No",
                    "category": "Geocoding",
                }
            ]

    import scp.data_sources.free_api_catalog as cat_mod

    monkeypatch.setattr(cat_mod, "get_catalog", lambda data_dir="data": StubCatalog())
    monkeypatch.setattr(qr, "_host_allowed", lambda url: False)
    monkeypatch.setattr(qr, "_wiki_lookup", lambda question, terms: None)

    result = qr.resolve_lookup_data("What is the capital of France?", domain="finance")
    assert result is None
    snap = qr.route_stats_snapshot()
    assert any(k.startswith("egress_blocked:") for k in snap["fallback_reasons"])


async def test_resolve_lookup_data_wiki_provider_for_knowledge_domain(monkeypatch):
    """Nhánh provider encyclopedic: catalog có entry Wikipedia (auth=No) →
    canonical wikipedia_client trả data (mock) → compose."""
    from scp.runtime import question_router as qr

    class StubCatalog:
        def search(self, query="", category=None, auth=None, limit=25):
            return []

    import scp.data_sources.free_api_catalog as cat_mod

    monkeypatch.setattr(cat_mod, "get_catalog", lambda data_dir="data": StubCatalog())
    monkeypatch.setattr(
        qr,
        "_wiki_lookup",
        lambda question, terms: {
            "text": "Paris is the capital and largest city of France.",
            "api_name": "Wikipedia (en) — France",
            "api_url": "https://en.wikipedia.org/wiki/France",
            "evidence": "Paris is the capital and largest city of France.",
        },
    )

    result = qr.resolve_lookup_data("What is the capital of France?", domain="geography")
    assert result is not None
    assert "en.wikipedia.org" in result["api_url"]
    assert result["api_name"].startswith("Wikipedia")


# ---------------------------------------------------------------------------
# (c) Provenance/evidence — cùng verification path
# ---------------------------------------------------------------------------
async def test_verify_response_includes_fork_evidence_and_verifies(judge_gate):
    adapter = AskKernelAdapter(db_path=":memory:", trace_path="/tmp")
    req = ForkReq()
    fork_response = {
        "verdict": "PASS",
        "final_answer": "Paris is the capital and largest city of France.\n\n(Nguồn dữ liệu: Wikipedia (en) — France — https://en.wikipedia.org/wiki/France)",
        "confidence": 0.75,
        "domain": "geography",
        "governance_decision": "UPHOLD",
        "v98_classification": {"provenance": "input_context_only", "route": "lookup_data_api"},
        # [S24] evidence PHẢI chứa cả provenance suffix — đúng cách production
        # compose (tier1 grounding đếm cả từ trong dòng provenance).
        "data_api_evidence": "Paris is the capital and largest city of France.\n(Nguồn dữ liệu: Wikipedia (en) — France — https://en.wikipedia.org/wiki/France)",
    }
    result = await adapter.verify_response(req, fork_response, {"task_id": "t_s24"})
    assert result["verdict"] == "VERIFIED"
    # Evidence data-API đã vào grounding context (THÊM bằng chứng).
    assert result["evidence_context_count"] == 1
    assert result["grounded_ratio"] > 0.5
    assert result["checked"]["provenance_compatible"] is True
    assert result["checked"]["rag_evidence_bound"] is True


async def test_fork_answer_with_failing_judge_is_withheld(judge_gate):
    """Fork KHÔNG được miễn verification: judge FAIL → withheld như mọi ask."""
    adapter = AskKernelAdapter(db_path=":memory:", trace_path="/tmp")
    judge_gate["pass"] = False
    fork_response = {
        "verdict": "PASS",
        "final_answer": "Paris is the capital and largest city of France.",
        "confidence": 0.75,
        "domain": "geography",
        "governance_decision": "UPHOLD",
        "v98_classification": {"provenance": "input_context_only", "route": "lookup_data_api"},
        "data_api_evidence": "Paris is the capital and largest city of France.",
    }
    result = await adapter.verify_response(ForkReq(), fork_response, {"task_id": "t_s24"})
    assert result["verdict"] == "CONTRADICTED"
    assert "judge_pass" in result["failures"]
