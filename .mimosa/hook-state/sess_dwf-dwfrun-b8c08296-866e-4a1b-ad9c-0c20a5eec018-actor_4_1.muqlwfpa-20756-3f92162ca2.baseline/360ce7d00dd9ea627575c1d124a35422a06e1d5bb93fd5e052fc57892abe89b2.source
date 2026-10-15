# SCP CIRCUIT: S24 — Goldset measurement TRƯỚC KHI WIRE (FA-01).
"""T07/S24 — đo accuracy intent của question router trên goldset thật.

Goldset: scp/benchmark/iso_comprehensive.jsonl — 143 questions (ISO benchmark
spec, scp/benchmark/ISO_BENCHMARK_SPEC.md §2.1). Machine-readable JSONL,
mỗi dòng có id/category/question.

NHÃN INTENT (nguồn nhãn: mapping category→intent, ghi rõ ở đây — không phải
nhãn tay từng câu):
  REASONING: math, logic, statistics — cần tính toán/suy luận đa bước,
    không có data API nào trả lời trực tiếp được.
  LOOKUP: geography, biology, chemistry, physics, history, astronomy,
    medical, technology, weather, finance, cybersecurity, conversion —
    câu hỏi sự thật / real-time / quy đổi, có thể trả lời từ data source.

HERMETIC: L2 (LLM) bị mock về fail-safe REASONING — test đo đúng phần L0
quyết định được, không đụng mạng. Số accuracy thật được assert >= 0.7
(ngưỡng design chốt của task S24; FA-01: đo TRƯỚC khi wire /ask).
Không skip/xfail (kỷ luật test SCP).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scp.runtime.question_router import (
    REASONING,
    RouteDecision,
    route_question,
)

GOLDSET_PATH = (
    Path(__file__).resolve().parents[2] / "scp" / "benchmark" / "iso_comprehensive.jsonl"
)
REASONING_CATEGORIES = frozenset({"math", "logic", "statistics"})
MIN_INTENT_ACCURACY = 0.7


@pytest.fixture()
def l2_failsafe(monkeypatch):
    """L2 luôn fail-safe REASONING (hermetic): mọi câu L0 không quyết định
    được được tính là REASONING — chống điểm giả từ L2 thật."""
    def _fake_l2(question, gateway=None):
        return RouteDecision(REASONING, "general", 0.5, "l2-failsafe", "mocked-failsafe")

    monkeypatch.setattr("scp.runtime.question_router.classify_l2", _fake_l2)


def _load_goldset() -> list[dict]:
    assert GOLDSET_PATH.exists(), f"goldset missing: {GOLDSET_PATH}"
    rows = []
    for line in GOLDSET_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    assert len(rows) == 143, f"expected 143 goldset questions, got {len(rows)}"
    return rows


def test_goldset_intent_accuracy_at_least_0_7(l2_failsafe):
    """FA-01 gate: accuracy intent >= 0.7 trên 143 câu goldset thật."""
    rows = _load_goldset()
    errors = []
    for row in rows:
        expected = REASONING if row["category"] in REASONING_CATEGORIES else "LOOKUP"
        decision = route_question(row["question"])
        if decision.intent != expected:
            errors.append(
                {
                    "id": row["id"],
                    "category": row["category"],
                    "expected": expected,
                    "got": decision.intent,
                    "via": decision.via,
                    "question": row["question"][:80],
                }
            )
    accuracy = (len(rows) - len(errors)) / len(rows)
    # In ra để evidence/log test runner giữ số thật.
    print(f"\n[S24] goldset intent accuracy = {accuracy:.4f} ({len(rows) - len(errors)}/{len(rows)}), errors={len(errors)}")
    for err in errors[:10]:
        print(f"[S24] MISS {err['id']} ({err['category']}): expected={err['expected']} got={err['got']} via={err['via']} :: {err['question']}")
    assert accuracy >= MIN_INTENT_ACCURACY, (
        f"[S24 FA-01] intent accuracy {accuracy:.4f} < {MIN_INTENT_ACCURACY} "
        f"({len(errors)} misrouted: {errors[:5]})"
    )


def test_goldset_owner_directive_questions_route_correctly(l2_failsafe):
    """2 câu đại diện directive: LOOKUP rõ vs REASONING rõ (runtime proof)."""
    lookup_decision = route_question("What is the capital of France?")
    assert lookup_decision.intent == "LOOKUP"
    assert lookup_decision.confidence >= 0.6
    reasoning_decision = route_question("Viết hàm Python kiểm tra số nguyên tố")
    assert reasoning_decision.intent == REASONING


def test_goldset_label_mapping_is_complete():
    """Mapping category→intent phải phủ hết 15 categories của goldset."""
    rows = _load_goldset()
    categories = {row["category"] for row in rows}
    assert len(categories) == 15
    assert categories == (REASONING_CATEGORIES | (categories - REASONING_CATEGORIES))
    assert not (REASONING_CATEGORIES & (categories - REASONING_CATEGORIES))
