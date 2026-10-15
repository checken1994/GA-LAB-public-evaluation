from __future__ import annotations

import asyncio

from scp.llm_gateway.client import OpenRouterProvider
from scp.security import dos_protection
from scp.security.dos_protection import DoSProtectionEngine


def test_api_rate_limit_has_retry_after_without_model_fallback() -> None:
    engine = DoSProtectionEngine()
    engine.MAX_REQUESTS_PER_MINUTE = 1

    assert engine.check_request("198.51.100.10") is None
    alert = engine.check_request("198.51.100.10")

    assert alert is not None
    assert alert.alert_type == "rate_limit"
    assert alert.action_taken == "block"
    assert alert.status_code == 429
    retry_after = int(alert.recommended_headers["Retry-After"])
    assert 1 <= retry_after <= 60


def test_api_rate_limit_retry_after_caps_at_window(monkeypatch) -> None:
    monkeypatch.setattr(dos_protection.time, "time", lambda: 1000.0)
    engine = DoSProtectionEngine()
    engine.MAX_REQUESTS_PER_MINUTE = 1

    assert engine.check_request("198.51.100.11") is None
    alert = engine.check_request("198.51.100.11")

    assert alert is not None
    assert alert.recommended_headers["Retry-After"] == "60"


def test_openrouter_provider_429_falls_back_to_task_model(monkeypatch) -> None:
    monkeypatch.setenv('OPENROUTER_MODEL', 'openrouter/free-fallback')
    monkeypatch.setenv('OPENROUTER_MODEL_DEFAULT', 'openrouter/free')
    monkeypatch.delenv('SCP_BUDGET_ROUTING', raising=False)
    async def scenario() -> tuple[list[str], str | None, str]:
        provider = OpenRouterProvider(task="default")
        provider._API_KEYS = ["test-key"]
        provider._next_key = lambda: "test-key"  # type: ignore[method-assign]
        calls: list[str] = []
        # print("FREE:", paid_model, "ENV:", os.environ.get("OPENROUTER_MODEL"))

        async def fake_call(model: str, messages: list[dict], api_key: str):
            calls.append(model)
            if model == "openrouter/free-fallback":
                return None, "HTTP 429 (quota/rate-limit)"
            return "fallback answer", None

        provider._call_model = fake_call  # type: ignore[method-assign]
        answer, name = await provider.chat("test")
        return calls, answer, name

    calls, answer, provider_name = asyncio.run(scenario())
    assert calls[:2] == ["openrouter/free-fallback", "openrouter/free"]
    assert answer == "fallback answer"
    assert provider_name == "openrouter:openrouter/free"
