# SCP CIRCUIT: S24 — Classifier cascade unit tests (hermetic).
"""T07/S24 — test cascade L0→L2 của scp/runtime/question_router.py.

Phủ design chốt của task S24:
  (a) L0 regex intent rules (REASONING ưu tiên trước LOOKUP)
  (b) L0 reuse detect_domain (shard) làm domain hint
  (c) L2 LLM zero-shot: parse LOOKUP/REASONING + fail-safe REASONING
  (d) route_question: L0 quyết định thì L2 KHÔNG được gọi
  (e) Kill switch SCP_T2_ROUTER + SCP_T2_MIN_CONFIDENCE parse fail-safe
  (f) KPI counters: llm_bypassed / llm_calls / fallback_reasons

Không mạng, không skip/xfail.
"""
from __future__ import annotations

import pytest

from scp.runtime.question_router import (
    LOOKUP,
    REASONING,
    RouteDecision,
    classify_l0,
    classify_l2,
    extract_salient_terms,
    route_question,
    route_stats_snapshot,
    t2_fork_enabled,
    t2_min_confidence,
)


# ---------------------------------------------------------------------------
# (a) L0 rules — intent
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "question,expected",
    [
        ("2 + 2 = ?", REASONING),
        ("sqrt(144) bằng bao nhiêu?", REASONING),
        ("Tính 15!", REASONING),
        ("GCD của 48 và 36?", REASONING),
        ("Fibonacci thứ 10?", REASONING),
        ("2 mũ 10 bằng bao nhiêu?", REASONING),
        ("log10 của 1000?", REASONING),
        ("15% của 200?", REASONING),
        ("Trung bình của [2,4,6,8,10]?", REASONING),
        ("Median of [3,1,4,1,5,9,2]?", REASONING),
        ("NOT (TRUE AND FALSE) = ?", REASONING),
        ("Nếu A > B và B > C thì A > C. Đây là tính chất gì?", REASONING),
        ("Viết hàm Python kiểm tra số nguyên tố", REASONING),
        ("write a function that checks primes", REASONING),
        ("What is the capital of France?", LOOKUP),
        ("Thủ đô của Việt Nam là gì?", LOOKUP),
        ("Dân số của Nhật Bản là bao nhiêu?", LOOKUP),
        ("CVE-2021-44228 là lỗ hổng gì?", LOOKUP),
        ("1 km bằng bao nhiêu mét?", LOOKUP),
        ("Bitcoin được tạo ra bởi ai?", LOOKUP),
        ("Thời tiết Hà Nội hôm nay thế nào?", LOOKUP),
        ("Kim loại nào nhẹ nhất?", LOOKUP),
        ("Lục địa lớn nhất?", LOOKUP),
        ("AES là thuật toán gì?", LOOKUP),
        # [S24] arithmetic phải cho phép trừ CÓ khoảng trắng, chặn ID "CVE-2021-44228"
        ("Mã 2021 - 44228 là gì?", REASONING),
    ],
)
def test_l0_intent(question, expected):
    decision = classify_l0(question)
    assert decision is not None, f"L0 must decide: {question!r}"
    assert decision.intent == expected, f"{question!r} → {decision}"


def test_l0_cve_id_is_not_arithmetic():
    """Regression: 'CVE-2021-44228' (digits-dash-digits) không được nuốt vào
    nhánh REASONING arithmetic — phải LOOKUP."""
    decision = classify_l0("CVE-2021-44228 là lỗ hổng gì?")
    assert decision.intent == LOOKUP
    assert decision.reason.startswith("lookup_signal:")


def test_l0_inconclusive_returns_none():
    assert classify_l0("") is None


# ---------------------------------------------------------------------------
# (b) domain hint reuse detect_domain (shard)
# ---------------------------------------------------------------------------
def test_l0_domain_hint_reuses_shard_detect_domain():
    decision = classify_l0("Thủ đô của Việt Nam là gì?")
    assert decision.domain == "geography"  # shard DOMAIN_KEYWORDS: 'thủ đô'
    assert decision.via == "l0-keyword"


def test_l0_domain_hint_falls_back_when_general():
    decision = classify_l0("What is the capital of France?")
    # detect_domain chỉ có keyword tiếng Việt → 'general'; domain vẫn là hint
    # phụ (classify_top1 có thể bắt 'capital of'), intent mới là quyết định.
    assert decision.intent == LOOKUP


# ---------------------------------------------------------------------------
# (c) L2 — mock gateway
# ---------------------------------------------------------------------------
def test_l2_parses_lookup(monkeypatch):
    class SyncGW:
        def __init__(self):
            self.calls = 0

        def chat(self, question, context="", system_prompt="", task="default"):
            self.calls += 1
            return "LOOKUP", "stub:model"

    gw = SyncGW()
    decision = classify_l2("Ai là tổng thống Pháp?", gateway=gw)
    assert decision.intent == LOOKUP
    assert decision.via == "l2-llm"
    assert decision.confidence >= 0.6
    assert gw.calls == 1


def test_l2_parses_reasoning(monkeypatch):
    class SyncGW:
        def chat(self, question, context="", system_prompt="", task="default"):
            return "REASONING", "stub:model"

    decision = classify_l2("So sánh hai kiến trúc", gateway=SyncGW())
    assert decision.intent == REASONING
    assert decision.via == "l2-llm"


def test_l2_unparseable_is_failsafe_reasoning():
    class SyncGW:
        def chat(self, question, context="", system_prompt="", task="default"):
            return "xin lỗi tôi không hiểu", "stub:model"

    decision = classify_l2("câu hỏi lạ lùng", gateway=SyncGW())
    assert decision.intent == REASONING
    assert decision.via == "l2-failsafe"
    assert decision.confidence < 0.6


def test_l2_gateway_exception_is_failsafe():
    class BoomGW:
        def chat(self, question, context="", system_prompt="", task="default"):
            raise RuntimeError("gateway down")

    decision = classify_l2("câu hỏi bất kỳ", gateway=BoomGW())
    assert decision.intent == REASONING
    assert decision.via == "l2-failsafe"
    snap = route_stats_snapshot()
    assert snap["classifier_llm_failures"] >= 1


# ---------------------------------------------------------------------------
# (d) route_question — L0 quyết định thì L2 không chạy
# ---------------------------------------------------------------------------
def test_route_question_l0_hit_skips_llm():
    class SpyGW:
        def chat(self, *args, **kwargs):
            raise AssertionError("L2 must not be called when L0 decides")

    decision = route_question("What is the capital of France?", gateway=SpyGW())
    assert decision.intent == LOOKUP
    assert decision.via.startswith("l0-")


# ---------------------------------------------------------------------------
# (e) env kill switch + threshold
# ---------------------------------------------------------------------------
def test_t2_fork_enabled_default_and_kill_switch(monkeypatch):
    monkeypatch.delenv("SCP_T2_ROUTER", raising=False)
    assert t2_fork_enabled() is True
    for value in ("0", "false", "off", "no"):
        monkeypatch.setenv("SCP_T2_ROUTER", value)
        assert t2_fork_enabled() is False
    monkeypatch.setenv("SCP_T2_ROUTER", "1")
    assert t2_fork_enabled() is True


def test_t2_min_confidence_parse_failsafe(monkeypatch):
    monkeypatch.delenv("SCP_T2_MIN_CONFIDENCE", raising=False)
    assert t2_min_confidence() == 0.6
    monkeypatch.setenv("SCP_T2_MIN_CONFIDENCE", "0.8")
    assert t2_min_confidence() == 0.8
    for bad in ("abc", "", "-1", "1.5"):
        monkeypatch.setenv("SCP_T2_MIN_CONFIDENCE", bad)
        assert t2_min_confidence() == 0.6


# ---------------------------------------------------------------------------
# (f) KPI counters
# ---------------------------------------------------------------------------
def test_kpi_counters_count_real_deltas():
    before = route_stats_snapshot()
    decision = RouteDecision(LOOKUP, "geography", 0.75, "l0-keyword", "test")
    from scp.runtime.question_router import _stats

    _stats.record_route(decision)
    _stats.record_bypass()
    _stats.record_llm_call()
    _stats.record_fallback("no_matching_catalog_entry")
    _stats.record_fetch(True)
    after = route_stats_snapshot()
    assert after["llm_bypassed_count"] == before["llm_bypassed_count"] + 1
    assert after["llm_calls_count"] == before["llm_calls_count"] + 1
    assert after["route_counts"]["l0-keyword:LOOKUP"] == before["route_counts"].get("l0-keyword:LOOKUP", 0) + 1
    assert after["fallback_reasons"]["no_matching_catalog_entry"] == before["fallback_reasons"].get("no_matching_catalog_entry", 0) + 1
    assert after["lookup_fetch_ok"] == before["lookup_fetch_ok"] + 1
    assert 0.0 <= after["bypass_ratio"] <= 1.0


# ---------------------------------------------------------------------------
# salient terms
# ---------------------------------------------------------------------------
def test_extract_salient_terms_strips_interrogatives():
    terms = extract_salient_terms("What is the capital of France?")
    assert "capital" in terms and "france" in terms
    assert "what" not in terms and "the" not in terms


def test_extract_salient_terms_vietnamese():
    terms = extract_salient_terms("Thủ đô của Việt Nam là gì?")
    assert "thủ" in terms and "việt" in terms
