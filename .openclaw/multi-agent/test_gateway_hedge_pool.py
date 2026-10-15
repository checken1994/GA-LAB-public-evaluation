"""[Agent3-GatewaySentinel R2] Regression: gateway-level hedge cap must apply
when a provider chain contains providers with NO API keys configured.

Contract under test (scp/llm_gateway/client.py, LLMGateway.chat):
  * the rotation pool is built from ENABLED providers only
    (`enabled = [p for p in chain if p.enabled]`);
  * with a single enabled provider, a slow-but-successful primary must still
    return its answer (hedge off / single-provider sequential semantics);
  * an all-disabled chain fails closed with (None, "none").

This pins the pool-construction invariant that the hedge race depends on:
providers without credentials must never enter the race (old-code risk was
rotating into a disabled provider whose enabled=False guard returns
(None, "none") immediately, wasting the hedge fire on a no-op).

Env hygiene: Phase 1.1 rule 5. Network: none (chain fully monkeypatched).
"""
from __future__ import annotations

import asyncio
import time

import pytest

from scp.llm_gateway.client import EnvCompatProvider, LLMGateway


class _SlowFakeProvider:
    PROVIDER_NAME = "slowfake"

    def __init__(self, delay: float, answer: str):
        self._delay = delay
        self._answer = answer
        self.enabled = True
        self._breaker = type("_B", (), {"is_open": lambda self: False})()

    async def chat(self, question, context="", system_prompt="", prioritize_free=False):
        await asyncio.sleep(self._delay)
        return self._answer, f"{self.PROVIDER_NAME}:model"


class _DeadProvider:
    """A provider with no keys configured: enabled=False by contract."""

    PROVIDER_NAME = "deadfake"

    def __init__(self):
        self.enabled = False
        self._breaker = type("_B", (), {"is_open": lambda self: False})()

    async def chat(self, *args, **kwargs):  # pragma: no cover — must never run
        raise AssertionError("disabled provider must never be called")


def _gateway_with(monkeypatch, providers) -> LLMGateway:
    for name in ("SCP_LLM_HEDGE", "SCP_LLM_ATTEMPT_TIMEOUT_SECONDS", "SCP_LLM_HEDGE_MAX_SECONDS"):
        monkeypatch.delenv(name, raising=False)
    gateway = LLMGateway()
    monkeypatch.setattr(gateway, "_provider_chain", lambda _task: providers, raising=False)
    return gateway


def test_disabled_providers_excluded_from_rotation_pool(monkeypatch):
    """Chain [dead, slow-ok] → rotation must use only the enabled provider."""
    dead = _DeadProvider()
    slow = _SlowFakeProvider(delay=0.05, answer="ok")
    gateway = _gateway_with(monkeypatch, [dead, slow])

    t0 = time.monotonic()
    answer, label = asyncio.run(gateway.chat("q", task="chat"))
    elapsed = time.monotonic() - t0

    assert answer == "ok"
    assert label == "slowfake:model"
    assert elapsed < 5.0


def test_all_disabled_chain_fails_closed(monkeypatch):
    gateway = _gateway_with(monkeypatch, [_DeadProvider(), _DeadProvider()])
    answer, label = asyncio.run(gateway.chat("q", task="chat"))
    assert answer is None
    assert label == "none"


def test_env_compat_provider_without_key_is_disabled():
    """EnvCompatProvider contract: no key → enabled False (pool invariant)."""
    provider = EnvCompatProvider(
        "envtest", "default", "AGENT3_TEST_KEY_ENV", "AGENT3_TEST_BASE_ENV", "AGENT3_TEST_MODEL_ENV",
        default_base_url="https://openrouter.ai/api/v1",
    )
    assert provider.enabled is False
    assert provider._key_count() == 0
