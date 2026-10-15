"""[A2] Contract: multi-LLM crosscheck phải CHẠY THẬT trong sync judge().

Audit claim (CONFIRMED trước fix): RealityJudge.judge() gọi
`cross_verify(question, ai_answer, context)` — hàm async — KHÔNG await →
nhận coroutine → `cross["final"]` raise TypeError → except nuốt im lặng →
fallback `_llm_judge` single cascade. Hệ quả: crosscheck 2 provider ĐÔI khi
bị gặp trong sync path; mọi sync verdict chỉ đến từ 1 model.

Contract sau fix:
- Crosscheck enabled (mặc định) → sync judge() chạy crossverify thật qua
  2 provider family độc lập (injected gateway seam — thiết kế sẵn của
  cross_verify để test không cần mạng).
- Agree PASS → verdict PASS; disagree → UNKNOWN + failures có
  "multi_llm_disagreement" (fail-closed, escalate cho người).
- Crosscheck raise → log WARNING rồi mới fallback single cascade (không
  nuốt im lặng).
- `_run_crosscheck_sync` phải chạy được cả khi gọi từ thread đang có event
  loop (bridge worker thread) lẫn thread thường (asyncio.run trực tiếp).
"""

from __future__ import annotations

import asyncio
import logging

import pytest

from scp.runtime.judge import RealityJudge, _run_crosscheck_sync


class _FixtureProvider:
    """Provider stub theo seam đã có của test_multi_llm_crosscheck.py —
    không gọi mạng, chỉ trả verdict cố định."""

    def __init__(self, name: str, answer: str):
        self.PROVIDER_NAME = name
        self.answer = answer
        self.calls = 0
        self.enabled = True

    async def chat(self, question: str, context: str = "", system_prompt: str = "", **_kw):
        self.calls += 1
        return self.answer, f"{self.PROVIDER_NAME}:local-model"


class _FixtureGateway:
    def __init__(self, providers):
        self.providers = list(providers)

    def provider_candidates(self, task: str):
        assert task == "judge"
        return list(self.providers)


@pytest.fixture(autouse=True)
def _crosscheck_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCP_MULTI_LLM_CROSSCHECK", "1")


@pytest.fixture(autouse=True)
def _no_expert_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fault-injection seam: classify về domain không có expert để path
    expert injection (có thể chạm mạng) không chạy trong unit test này."""
    monkeypatch.setattr(
        "scp.data_sources.domain_classifier.classify_top1", lambda _q: "__no_domain__"
    )


_QUESTION = "What does the supplied context say?"
_ANSWER = "The supplied context says the answer is yes."
_CONTEXT = "The supplied context says the answer is yes. Additional supporting evidence."


def _patch_gateway(monkeypatch: pytest.MonkeyPatch, gateway) -> None:
    monkeypatch.setattr("scp.llm_gateway.get_gateway", lambda: gateway)


def test_sync_judge_runs_crosscheck_when_providers_agree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[A2 pin] Trước fix: crosscheck chết → verdict UNKNOWN (TypeError →
    fallback single cascade không có gateway → None → escalate).
    Sau fix: 2 family agree PASS → verdict PASS thật từ crosscheck."""
    gateway = _FixtureGateway(
        [_FixtureProvider("family_a", "PASS"), _FixtureProvider("family_b", "PASS")]
    )
    _patch_gateway(monkeypatch, gateway)

    verdict = RealityJudge().judge(question=_QUESTION, ai_answer=_ANSWER, context=_CONTEXT)

    assert verdict["verdict"] == "PASS"
    assert "multi_llm_disagreement" not in verdict["failures"]
    assert "semantic_judge_fail" not in verdict["failures"]
    assert verdict["cross_model_agreement"] is True


def test_sync_judge_disagreement_fails_closed_with_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2 family disagree → final=None → UNKNOWN + marker
    'multi_llm_disagreement' trong failures (không tự chọn bên nào)."""
    gateway = _FixtureGateway(
        [_FixtureProvider("family_a", "PASS"), _FixtureProvider("family_b", "FAIL")]
    )
    _patch_gateway(monkeypatch, gateway)

    verdict = RealityJudge().judge(question=_QUESTION, ai_answer=_ANSWER, context=_CONTEXT)

    assert verdict["verdict"] == "UNKNOWN"
    assert "multi_llm_disagreement" in verdict["failures"]
    assert "semantic_judge_unavailable" in verdict["failures"]


def test_sync_judge_crosscheck_failure_logs_then_falls_back(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Crosscheck raise (gateway lỗi) → WARNING được log → fallback single
    cascade chạy (fault-injection seam ghi nhận) → KHÔNG nuốt im lặng."""
    def _broken_gateway():
        raise RuntimeError("gateway unavailable (fault injection)")

    monkeypatch.setattr("scp.llm_gateway.get_gateway", _broken_gateway)
    fallback_calls: list[tuple[str, str, str]] = []

    def _fake_single_cascade(question: str, ai_answer: str, context: str):
        fallback_calls.append((question, ai_answer, context))
        return True  # single cascade quyết định PASS

    monkeypatch.setattr("scp.runtime.judge._llm_judge", _fake_single_cascade)

    with caplog.at_level(logging.WARNING, logger="scp.judge"):
        verdict = RealityJudge().judge(question=_QUESTION, ai_answer=_ANSWER, context=_CONTEXT)

    assert verdict["verdict"] in ("DEGRADED", "UNCERTAIN")  # [SEC-R2-01] fallback không còn là PASS
    assert verdict["confidence"] < 0.50  # [SEC-R2-01] confidence bị clamp < 0.50
    assert verdict["evidence"]["governance_decision"] == "DEGRADED"
    assert verdict["cross_model_agreement"] is False
    assert verdict["degraded"] is True
    assert fallback_calls == [(_QUESTION, _ANSWER, _CONTEXT)]  # fallback chạy thật
    assert any("crosscheck failed" in rec.message for rec in caplog.records)  # không im lặng



def test_run_crosscheck_sync_works_inside_running_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bridge thread: gọi _run_crosscheck_sync từ thread đang chạy event loop
    vẫn chạy crosscheck thật (không raise 'cannot be called from a running
    event loop', không rơi vào fallback)."""
    gateway = _FixtureGateway(
        [_FixtureProvider("family_a", "PASS"), _FixtureProvider("family_b", "PASS")]
    )
    _patch_gateway(monkeypatch, gateway)

    async def _call_inside_loop():
        # Gọi ĐỒNG BỘ trong coroutine → thread hiện tại đang có loop running
        return _run_crosscheck_sync(_QUESTION, _ANSWER, "evidence says yes")

    cross = asyncio.run(_call_inside_loop())
    assert cross["consensus"] == "agree"
    assert cross["final"] == "PASS"


def test_run_crosscheck_sync_missing_providers_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gateway không có 2 family độc lập → final=None (fail-closed), không
    bao giờ tự phát minh consensus từ 1 provider."""
    gateway = _FixtureGateway([_FixtureProvider("family_a", "PASS")])
    _patch_gateway(monkeypatch, gateway)

    cross = _run_crosscheck_sync(_QUESTION, _ANSWER, "evidence says yes")
    assert cross["consensus"] == "missing_distinct_providers"
    assert cross["final"] is None
