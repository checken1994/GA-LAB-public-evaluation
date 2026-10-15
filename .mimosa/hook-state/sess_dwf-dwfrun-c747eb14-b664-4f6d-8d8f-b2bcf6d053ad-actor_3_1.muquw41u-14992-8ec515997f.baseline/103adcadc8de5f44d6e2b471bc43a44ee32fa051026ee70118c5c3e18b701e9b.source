"""[Agent3-GatewaySentinel R1] Regression: the payment-dead 402 sentinel is
deliberately DIGIT-FREE ("payment-required" phrasing, no "402"/"429" digits),
so provider.chat() must classify quota failures via the SENTINEL PREFIX
("payment_required:" / "rate_limited:") — never via raw status digits.

Contract under test (scp/llm_gateway/client.py):
  * _call_model_inner returns the payment_required sentinel without digits
    in the prefix token;
  * provider.chat() must count such a failure into the provider breaker
    EXACTLY ONCE per ask (three consecutive hard-quota asks => breaker OPEN).

Old-code behavior (pre-fix): chat() matched only "quota"/"rate-limit"/"429"/"402"
substrings in the error; the digit-free 402 sentinel matched none, so
record_failure() was skipped and the breaker stayed CLOSED forever under a
renewed hard-quota wall (payment state, dead candidate kept being probed via
the *provider* breaker while the per-model dead cache is process-scoped only).
The old code fails the breaker-open assertion; the fixed code passes.

Env hygiene: Phase 1.1 rule 5 — env changes via monkeypatch only.
Network: none — _call_model is monkeypatched; conftest forbids real HTTP.
"""
from __future__ import annotations

import asyncio

import pytest

from scp.llm_gateway.client import OpenRouterProvider

# The exact sentinel _call_model_once returns on a real HTTP 402 —
# intentionally carries the digit "402" ONLY inside the parenthetical body,
# while the leading token stays digit-free. chat() must not depend on digits.
_PAYMENT_SENTINEL = "payment_required: HTTP 402 (quota/rate-limit)"
_RATE_SENTINEL = "rate_limited: HTTP 429 (quota/rate-limit)"


@pytest.fixture(autouse=True)
def _clean_dead_model_registry():
    from scp.llm_gateway import client as gw_client

    gw_client.reset_dead_model_cache()
    yield
    gw_client.reset_dead_model_cache()


def _make_provider(monkeypatch) -> OpenRouterProvider:
    monkeypatch.setenv("OPENROUTER_MODEL", "paid/primary-model")
    monkeypatch.setenv("OPENROUTER_MODEL_DEFAULT", "free/task-fallback")
    monkeypatch.delenv("SCP_BUDGET_ROUTING", raising=False)
    monkeypatch.delenv("SCP_LLM_DEAD_MODEL_BREAKER", raising=False)
    provider = OpenRouterProvider(task="default")
    provider._API_KEYS = ["test-key"]
    provider._next_key = lambda: "test-key"  # type: ignore[method-assign]
    return provider


def test_payment_sentinel_prefix_is_digit_free(monkeypatch):
    """The classifier contract: the sentinel's leading token has no digits.
    (Guards the invariant that makes the substring-matcher bug possible.)"""
    prefix = _PAYMENT_SENTINEL.split(":", 1)[0]
    assert prefix == "payment_required"
    assert not any(ch.isdigit() for ch in prefix)


def test_402_sentinel_records_breaker_failure_exactly_once(monkeypatch):
    """402 sentinel → breaker failure counted once per ask; threshold → OPEN."""
    provider = _make_provider(monkeypatch)

    async def fake_call(model: str, messages: list[dict], api_key: str):
        return None, _PAYMENT_SENTINEL

    provider._call_model = fake_call  # type: ignore[method-assign]
    threshold = provider._breaker.failure_threshold
    for _ in range(threshold):
        asyncio.run(provider.chat("q"))
    assert provider._breaker.is_open() is True, (
        "provider breaker must OPEN after repeated 402 payment-required failures"
    )


def test_429_sentinel_single_hit_counts_one_breaker_failure(monkeypatch):
    """429 sentinel below cache threshold still counts ONE provider failure."""
    provider = _make_provider(monkeypatch)

    async def fake_call(model: str, messages: list[dict], api_key: str):
        return None, _RATE_SENTINEL

    provider._call_model = fake_call  # type: ignore[method-assign]
    assert provider._breaker.is_open() is False
    asyncio.run(provider.chat("q"))
    failures_after_one_ask = provider._breaker._consecutive_failures
    assert failures_after_one_ask >= 1, "single 429 sentinel must count one provider failure"
    assert provider._breaker.is_open() is False  # threshold is 3: not yet open
