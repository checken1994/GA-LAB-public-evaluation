import asyncio
import itertools

import pytest

from scp.llm_gateway.client import LLMGateway, OpenRouterProvider


@pytest.fixture
def configured_openrouter(monkeypatch):
    # Synthetic non-secret values only; no network call is made.
    monkeypatch.setattr(OpenRouterProvider, "_API_KEYS", ["test-key-a", "test-key-b"])
    monkeypatch.setattr(
        OpenRouterProvider,
        "_key_cycle",
        itertools.cycle(["test-key-a", "test-key-b"]),
    )


def test_openrouter_429_moves_from_paid_to_task_free(configured_openrouter) -> None:
    async def scenario() -> tuple[str | None, str, list[str]]:
        provider = OpenRouterProvider(task="default")
        provider.model = "paid-model"
        provider.free_fallback = "free-model"
        calls: list[str] = []

        async def fake_call(model, messages, api_key):
            calls.append(model)
            if model == "paid-model":
                return None, "HTTP 429 (quota/rate-limit)"
            return "fallback answer", None

        provider._call_model = fake_call  # type: ignore[method-assign]
        answer, returned_provider = await provider.chat("question")
        return answer, returned_provider, calls

    answer, returned_provider, calls = asyncio.run(scenario())
    assert answer == "fallback answer"
    assert returned_provider == "openrouter:free-model"
    assert calls == ["paid-model", "paid-model", "free-model"]


def test_openrouter_402_moves_to_auto_router_when_task_free_fails(
    configured_openrouter,
) -> None:
    async def scenario() -> tuple[str | None, str, list[str]]:
        provider = OpenRouterProvider(task="default")
        provider.model = "paid-model"
        provider.free_fallback = "free-model"
        calls: list[str] = []

        async def fake_call(model, messages, api_key):
            calls.append(model)
            if model == "paid-model":
                return None, "HTTP 402 (quota/rate-limit)"
            if model == "free-model":
                return None, "HTTP 500"
            return "router answer", None

        provider._call_model = fake_call  # type: ignore[method-assign]
        answer, returned_provider = await provider.chat("question")
        return answer, returned_provider, calls

    answer, returned_provider, calls = asyncio.run(scenario())
    assert answer == "router answer"
    assert returned_provider == "openrouter:openrouter/free"
    assert calls == ["paid-model", "paid-model", "free-model", "openrouter/free"]


def test_openrouter_disabled_or_exhausted_returns_none(
    configured_openrouter,
) -> None:
    async def scenario() -> tuple[tuple[str | None, str], tuple[str | None, str]]:
        disabled = OpenRouterProvider(task="default")
        disabled._API_KEYS = []
        disabled._key_cycle = None
        disabled_result = await disabled.chat("question")

        exhausted = OpenRouterProvider(task="default")
        exhausted.model = "paid-model"
        exhausted.free_fallback = "free-model"

        async def fail(model, messages, api_key):
            return None, "timeout"

        exhausted._call_model = fail  # type: ignore[method-assign]
        exhausted_result = await exhausted.chat("question")
        return disabled_result, exhausted_result

    disabled_result, exhausted_result = asyncio.run(scenario())
    assert disabled_result == (None, "none")
    assert exhausted_result == (None, "none")


def test_openrouter_unproven_free_candidates_are_explicitly_blocked(
    configured_openrouter,
) -> None:
    """[DEPRECATION] zero_cost_guard/zero_cost_runtime have been architecturally
    deprecated.  This test now verifies that when the Gateway has no model
    assigned (no free list match), it returns (None, ...) without calling any
    provider — the egress-guarded routing is the surviving enforcement layer."""

    calls: list[str] = []

    async def fake_call(model, messages, api_key):
        calls.append(model)
        return None, "should not reach"

    async def scenario() -> tuple[str | None, str]:
        provider = OpenRouterProvider(task="default")
        # Simulate no model available (empty free list match)
        provider.model = None
        provider.free_fallback = None
        provider._call_model = fake_call  # type: ignore[method-assign]
        return await provider.chat("question")

    result = asyncio.run(scenario())
    assert result[0] is None, "Gateway must return None answer when no model is available"
    assert calls == [], "Provider _call_model must not be called when model is None"


def test_gateway_returns_none_when_all_providers_fail(monkeypatch) -> None:
    """[FAILOVER] Tất cả provider trong chuỗi đều fail → (None, "none") fail-closed."""
    class FailingProvider:
        PROVIDER_NAME = "synthetic"  # contract mới: mọi provider phải tự định danh
        enabled = True
        model = "synthetic"
        from scp.llm_gateway.client import CircuitBreaker as _CB
        _breaker = _CB()  # contract: provider phải có breaker để gateway sắp thứ tự sức khỏe

        async def chat(self, question, context, system_prompt, prioritize_free=False):
            return None, "none"

        def stats(self):
            return {"enabled": True, "model": self.model}

    gateway = LLMGateway()
    gateway.openrouter_default = FailingProvider()
    gateway.groq_default = FailingProvider()
    gateway.openrouter = gateway.openrouter_default
    monkeypatch.setenv("SCP_LLM_PROVIDER_MODE", "auto")

    answer, provider = asyncio.run(gateway.chat("question", task="default"))
    assert answer is None
    assert provider == "none"
    assert gateway.stats()["failures"] == 1


def test_gateway_propagates_budget_free_priority(monkeypatch) -> None:
    """Budget routing must reach the provider instead of becoming dead state."""
    from scp.core import budget_engine

    class RecordingProvider:
        PROVIDER_NAME = "recording"
        enabled = True
        model = "recording"
        from scp.llm_gateway.client import CircuitBreaker as _CB
        _breaker = _CB()

        def __init__(self) -> None:
            self.prioritize_free = None

        async def chat(self, question, context, system_prompt, prioritize_free=False):
            self.prioritize_free = prioritize_free
            return "answer", "recording:free"

    provider = RecordingProvider()
    gateway = LLMGateway()
    monkeypatch.setenv("SCP_BUDGET_ROUTING", "1")
    monkeypatch.setattr(budget_engine, "order_tiers", lambda *_args: ["free", "free-fallback"])
    monkeypatch.setattr(gateway, "_provider_chain", lambda _task: [provider])

    answer, label = asyncio.run(gateway.chat("question", task="default"))

    assert (answer, label) == ("answer", "recording:free")
    assert provider.prioritize_free is True
