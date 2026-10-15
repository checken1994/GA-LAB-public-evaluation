from __future__ import annotations

import asyncio
import itertools

import pytest


class _Response:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": "ok"}}]}


class _Client:
    def __init__(self) -> None:
        self.calls = 0

    async def post(self, *args, **kwargs):
        self.calls += 1
        return _Response()



def _mock_zero_cost(monkeypatch):
    pass

def _configure_openrouter(monkeypatch, provider_cls) -> None:
    monkeypatch.setattr(provider_cls, "_API_KEYS", ["test-key"], raising=False)
    monkeypatch.setattr(provider_cls, "_key_cycle", itertools.cycle(["test-key"]), raising=False)
    monkeypatch.setattr(provider_cls, "_dynamic_models_loaded", True, raising=False)


def test_deny_blocks_external_provider_before_network(monkeypatch):
    _mock_zero_cost(monkeypatch)
    from scp.llm_gateway.client import OpenRouterProvider

    _configure_openrouter(monkeypatch, OpenRouterProvider)
    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
    provider = OpenRouterProvider(task="chat")
    fake = _Client()
    provider._client = fake

    answer, label = asyncio.run(provider.chat("hello"))

    assert answer is None
    assert label == "none"
    assert fake.calls == 0


def test_allowlist_rejects_unlisted_provider_before_network(monkeypatch):
    _mock_zero_cost(monkeypatch)
    from scp.llm_gateway.client import OpenRouterProvider

    _configure_openrouter(monkeypatch, OpenRouterProvider)
    monkeypatch.setenv("SCP_EGRESS_MODE", "allowlist")
    monkeypatch.setenv("SCP_LLM_EGRESS_ALLOWLIST", "api.openai.com")
    provider = OpenRouterProvider(task="chat")
    fake = _Client()
    provider._client = fake

    answer, label = asyncio.run(provider.chat("hello"))

    assert answer is None
    assert label == "none"
    assert fake.calls == 0


def test_allowlist_permits_exact_https_provider_host(monkeypatch):
    _mock_zero_cost(monkeypatch)
    from scp.llm_gateway.client import OpenRouterProvider

    _configure_openrouter(monkeypatch, OpenRouterProvider)
    monkeypatch.setenv("SCP_EGRESS_MODE", "allowlist")
    monkeypatch.setenv("SCP_LLM_EGRESS_ALLOWLIST", "openrouter.ai")
    provider = OpenRouterProvider(task="chat")
    fake = _Client()
    provider._client = fake

    answer, label = asyncio.run(provider.chat("hello"))

    assert answer == "ok"
    assert label.startswith("openrouter:")
    assert fake.calls == 1


def test_deny_still_allows_loopback_fixture(monkeypatch):
    _mock_zero_cost(monkeypatch)
    from scp.llm_gateway.client import EnvCompatProvider

    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
    monkeypatch.setenv("FIXTURE_KEY", "fixture-key")
    monkeypatch.setenv("FIXTURE_URL", "http://127.0.0.1:8123/v1")
    monkeypatch.setenv("FIXTURE_MODEL", "fixture-model")
    provider = EnvCompatProvider(
        "fixture", "chat", "FIXTURE_KEY", "FIXTURE_URL", "FIXTURE_MODEL"
    )
    fake = _Client()
    provider._client = fake

    answer, label = asyncio.run(provider.chat("hello"))

    assert answer == "ok"
    assert label == "fixture:fixture-model"
    assert fake.calls == 1


@pytest.mark.parametrize("mode", ["deny", "offline", "disabled", "unexpected-mode"])
def test_non_network_modes_fail_closed_for_external_llm(monkeypatch, mode):
    from scp.llm_gateway.client import _llm_egress_allowed

    monkeypatch.setenv("SCP_EGRESS_MODE", mode)
    monkeypatch.setenv("SCP_LLM_EGRESS_ALLOWLIST", "openrouter.ai")

    assert _llm_egress_allowed("https://openrouter.ai/api/v1") is False
    assert _llm_egress_allowed("http://127.0.0.1:8123/v1") is True


def test_allowlist_requires_https_for_external_provider(monkeypatch):
    from scp.llm_gateway.client import _llm_egress_allowed

    monkeypatch.setenv("SCP_EGRESS_MODE", "allowlist")
    monkeypatch.setenv("SCP_LLM_EGRESS_ALLOWLIST", "openrouter.ai")

    assert _llm_egress_allowed("http://openrouter.ai/api/v1") is False
    assert _llm_egress_allowed("https://openrouter.ai/api/v1") is True


def test_free_catalog_obeys_allowlist_before_constructing_network_client(monkeypatch):
    from scp.llm_gateway import free_catalog

    class ForbiddenNetworkClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("catalog constructed network client for an unlisted host")

    monkeypatch.setenv("SCP_EGRESS_MODE", "allowlist")
    monkeypatch.setenv("SCP_LLM_EGRESS_ALLOWLIST", "api.openai.com")
    monkeypatch.setattr(free_catalog.httpx, "Client", ForbiddenNetworkClient)
    monkeypatch.setattr(free_catalog, "_fetched", False)
    monkeypatch.setattr(free_catalog, "_last_ok", None)

    assert free_catalog.refresh_free_catalog(force=True) is False

