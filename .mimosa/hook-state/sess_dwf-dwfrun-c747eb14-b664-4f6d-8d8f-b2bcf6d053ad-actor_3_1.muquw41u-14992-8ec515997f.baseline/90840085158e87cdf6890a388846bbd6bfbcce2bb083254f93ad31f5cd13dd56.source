"""[B-S1] Wire test: DomainKnowledgeStore → judge verdict + /v100/knowledge/stats.

Audit 52-mảnh @9ec8d6b (commit e0696f5; reports/expert-panel/ARCH-AUDIT-B-knowledge.md
mảnh #1): RealityJudge.domain_knowledge_store trả None cứng (judge.py:111) →
KB nội bộ CHẾT: không consult khi thẩm định, /v100/knowledge/* luôn 503.
Hệ thống "có tri thức nhưng không dùng khi thẩm định".

Contract sau wire (falsifiable — kill được cả regression None-cứng):
  (a) KB có data → judge consult: verdict output evidence["knowledge"] chứa ref,
      knowledge_consult_count tăng, KB ref được inject vào context cascade
      NHƯ evidence bổ trợ (không quyết định thay verifier/Tier-2).
  (b) KB empty / KB lỗi (search raise) / constructor lỗi → verdict KHÔNG ĐỔI,
      KHÔNG raise (fail-closed) — judge chạy như cũ.
  (c) /v100/knowledge/stats: auth chặn như route admin khác (401 sai token,
      deny-by-default); đúng token → 200 với concepts/sources/fresh/stale/
      judge_consults.

Hermetic: không mạng, không LLM thật (stub _llm_judge + SCP_MULTI_LLM_CROSSCHECK=0),
KB seed vào tmp_path — không đụng data/knowledge/ thật.
"""
from __future__ import annotations

import types

import pytest

from scp.knowledge.domain_store import DomainKnowledgeStore
from scp.runtime.judge import RealityJudge

_QUESTION = "what is the boiling point of water"
_ANSWER = "Water boils at 100 degrees Celsius at sea level."
_STORED_Q = "boiling point of water at sea level"
_STORED_A = "100 degrees Celsius"


@pytest.fixture(autouse=True)
def _hermetic_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    """Không LLM thật, không crosscheck, không expert injection (seam giống
    test_judge_sync_crosscheck_alive.py — không mạng trong unit test)."""
    monkeypatch.setenv("SCP_MULTI_LLM_CROSSCHECK", "0")
    monkeypatch.setattr("scp.runtime.judge._llm_judge", lambda q, a, c: True)
    monkeypatch.setattr(
        "scp.data_sources.domain_classifier.classify_top1", lambda _q: "__no_domain__"
    )


def _seed_store(tmp_path) -> DomainKnowledgeStore:
    store = DomainKnowledgeStore(data_dir=str(tmp_path / "kb"))
    store.store(
        question=_STORED_Q,
        answer=_STORED_A,
        domain="general",
        source="wikipedia",
        confidence=0.9,
    )
    return store


def _run_judge(judge: RealityJudge, captured: dict | None = None) -> dict:
    def _fake_llm_judge(question: str, ai_answer: str, context: str):
        if captured is not None:
            captured["context"] = context
        return True

    judge_mod = __import__("scp.runtime.judge", fromlist=["_llm_judge"])
    judge_mod._llm_judge = _fake_llm_judge  # re-stub để capture context
    return judge.judge(question=_QUESTION, ai_answer=_ANSWER, context="")


# ---------------------------------------------------------------------------
# (a) KB có data → consult + ref trong verdict output + counter tăng
# ---------------------------------------------------------------------------

def test_judge_consults_kb_refs_in_verdict_and_counter_increases(monkeypatch, tmp_path):
    captured: dict = {}
    judge = RealityJudge()
    judge._kb_store = _seed_store(tmp_path)
    before = judge.knowledge_consult_count

    verdict = _run_judge(judge, captured)

    # counter tăng — consult thật sự diễn ra
    assert judge.knowledge_consult_count == before + 1
    # verdict output chứa knowledge ref (evidence bổ trợ, không thay verifier)
    kb_refs = verdict["evidence"]["knowledge"]
    assert kb_refs, "verdict output phải chứa KB ref khi KB có data khớp"
    assert any(_STORED_Q == r["question"] for r in kb_refs)
    assert kb_refs[0]["source"] == "wikipedia"
    assert kb_refs[0]["tier"] == 2  # CONSENSUS
    # KB được DÙNG NHƯ BỔ TRỢ evidence: inject vào context cho cascade
    assert "[KNOWLEDGE BASE REF]" in captured["context"]
    assert _STORED_A in captured["context"]
    # verifier/Tier-2 vẫn là người phân định verdict
    assert verdict["verdict"] == "PASS"


def test_judge_async_consults_kb_refs_in_verdict_and_counter_increases(monkeypatch, tmp_path):
    import asyncio

    async def _fake_async_llm_judge(question: str, ai_answer: str, context: str):
        return True

    # judge_async import cục bộ `_llm_judge_async` từ judge_llm → patch tại nguồn
    monkeypatch.setattr("scp.runtime.judge_llm._llm_judge_async", _fake_async_llm_judge)
    judge = RealityJudge()
    judge._kb_store = _seed_store(tmp_path)
    before = judge.knowledge_consult_count

    verdict = asyncio.run(
        judge.judge_async(question=_QUESTION, ai_answer=_ANSWER, context="")
    )

    assert judge.knowledge_consult_count == before + 1
    kb_refs = verdict["evidence"]["knowledge"]
    assert kb_refs and kb_refs[0]["question"] == _STORED_Q
    assert verdict["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# (b) KB empty / lỗi → verdict không đổi, không raise (fail-closed)
# ---------------------------------------------------------------------------

def test_judge_kb_empty_verdict_unchanged_no_raise(monkeypatch, tmp_path):
    judge = RealityJudge()
    judge._kb_store = DomainKnowledgeStore(data_dir=str(tmp_path / "empty-kb"))
    before = judge.knowledge_consult_count

    captured: dict = {}
    verdict = _run_judge(judge, captured)

    assert verdict["verdict"] == "PASS"  # như cũ, không đổi
    assert verdict["evidence"]["knowledge"] == []
    assert "[KNOWLEDGE BASE REF]" not in captured.get("context", "")  # không inject rác
    assert judge.knowledge_consult_count == before + 1  # consult vẫn chạy (0 hit)


def test_judge_kb_search_error_fail_closed_no_raise(monkeypatch):
    class _BrokenStore:
        def search(self, *args, **kwargs):
            raise RuntimeError("KB fault injection")

    judge = RealityJudge()
    judge._kb_store = _BrokenStore()

    verdict = _run_judge(judge)  # KHÔNG được raise

    assert verdict["verdict"] == "PASS"  # verdict không đổi so với baseline không-KB
    assert verdict["evidence"]["knowledge"] == []
    assert judge.knowledge_consult_count == 0  # search raise → không đếm là consult thành công


def test_judge_kb_constructor_failure_returns_none_and_judge_still_works(monkeypatch):
    import scp.knowledge.domain_store as ds_module

    def _boom(*args, **kwargs):
        raise RuntimeError("no disk (fault injection)")

    monkeypatch.setattr(ds_module, "DomainKnowledgeStore", _boom)
    judge = RealityJudge()
    # property fail-closed: None + không raise (trước wire: None cứng — như nhau,
    # nhưng giờ đây là nhánh dự phòng có log, không phải trạng thái chết mặc định)
    assert judge.domain_knowledge_store is None

    verdict = _run_judge(judge)
    assert verdict["verdict"] == "PASS"
    assert verdict["evidence"]["knowledge"] == []


def test_judge_property_lazy_constructs_real_store(monkeypatch, tmp_path):
    """Property phải trả store THẬT khi constructor khả dụng — kill regression
    `return None` cứng (audit mảnh #1)."""
    monkeypatch.setattr(
        "scp.knowledge.domain_store.DomainKnowledgeStore",
        lambda *a, **kw: "REAL_STORE_SENTINEL",
    )
    judge = RealityJudge()
    assert judge.domain_knowledge_store == "REAL_STORE_SENTINEL"
    # memoized — lần 2 không construct lại
    assert judge.domain_knowledge_store == "REAL_STORE_SENTINEL"


# ---------------------------------------------------------------------------
# (c) /v100/knowledge/stats — cấu trúc đúng + auth chặn như route khác
# ---------------------------------------------------------------------------

def test_knowledge_stats_endpoint_auth_and_structure(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import scp.security.auth as auth_module
    from scp.api.routes import admin_v100

    judge = RealityJudge()
    judge._kb_store = _seed_store(tmp_path)
    judge.knowledge_consult_count = 7

    monkeypatch.setattr(admin_v100, "get_judge", lambda: judge)
    monkeypatch.setattr(
        auth_module,
        "load_auth_config",
        lambda: types.SimpleNamespace(configured=True, token="scp-test-token-123", password=""),
    )
    monkeypatch.setattr(auth_module, "_auth_failures", {})  # rate-limit state sạch

    app = FastAPI()
    app.include_router(admin_v100.router)
    client = TestClient(app, raise_server_exceptions=False)

    # auth chặn như route admin khác: sai token → 401 (không dev bypass)
    r_bad = client.get(
        "/v100/knowledge/stats", headers={"Authorization": "Bearer wrong-token"}
    )
    assert r_bad.status_code == 401, "sai token phải bị chặn (401)"

    # không token → 401 (deny-by-default)
    r_none = client.get("/v100/knowledge/stats")
    assert r_none.status_code == 401

    # đúng token → 200 + cấu trúc stats đầy đủ
    r = client.get(
        "/v100/knowledge/stats", headers={"Authorization": "Bearer scp-test-token-123"}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    for key in (
        "concepts",
        "total_records",
        "domains",
        "by_domain",
        "sources",
        "fresh_records",
        "stale_records",
        "judge_consults",
    ):
        assert key in data, f"stats thiếu key {key}"
    assert data["concepts"] >= 1
    assert data["sources"].get("wikipedia", 0) >= 1
    assert data["fresh_records"] >= 1
    assert data["stale_records"] == 0  # record mới seed, chưa hết hạn
    assert data["judge_consults"] == 7  # counter từ step 1 (judge consult)


def test_knowledge_stats_endpoint_503_when_store_unavailable(monkeypatch):
    """KB constructor lỗi → property None → endpoint vẫn 503 (fail-closed API)."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import scp.security.auth as auth_module
    from scp.api.routes import admin_v100

    judge = RealityJudge()
    judge._kb_store = None  # mô phỏng constructor đã fail
    monkeypatch.setattr(admin_v100, "get_judge", lambda: judge)
    monkeypatch.setattr(
        auth_module,
        "load_auth_config",
        lambda: types.SimpleNamespace(configured=True, token="scp-test-token-123", password=""),
    )
    monkeypatch.setattr(auth_module, "_auth_failures", {})

    app = FastAPI()
    app.include_router(admin_v100.router)
    client = TestClient(app, raise_server_exceptions=False)

    r = client.get(
        "/v100/knowledge/stats", headers={"Authorization": "Bearer scp-test-token-123"}
    )
    assert r.status_code == 503
