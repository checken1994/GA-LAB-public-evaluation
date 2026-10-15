import asyncio

from scp.llm_gateway.client import EnvCompatProvider, LLMGateway, OpenRouterProvider


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = ""):
        self.status_code = status_code
        self._text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(f"HTTP {self.status_code}", request=None, response=None)

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._text}}]}

    @property
    def text(self):
        return self._text


class FakeClient:
    def __init__(self, script: list):
        self.script = list(script)
        self.calls = 0
        self.models: list[str] = []

    async def post(self, url, json=None, headers=None, **kwargs):
        self.calls += 1
        self.models.append(str((json or {}).get("model", "unknown")))
        item = self.script.pop(0) if self.script else self.script[-1]
        if isinstance(item, Exception):
            raise item
        return item

def _keyed(monkeypatch, provider):
    import itertools
    target = provider if isinstance(provider, type) else type(provider)
    monkeypatch.setattr(target, "_API_KEYS", ["test-key"], raising=False)
    monkeypatch.setattr(target, "_key_cycle", itertools.cycle(["test-key"]), raising=False)

def test_breaker_open_skips_dead_provider_without_network_call(monkeypatch):
    gateway = LLMGateway()
    _keyed(monkeypatch, OpenRouterProvider)
    dead = FakeClient([])
    gateway.openrouter_chat._client = dead
    for _ in range(3):
        gateway.openrouter_chat._breaker.record_failure()
    assert gateway.openrouter_chat._breaker.is_open() is True
    answer, label = asyncio.run(gateway.chat("q", task="chat"))
    assert answer is None
    assert label == "none"
    assert dead.calls == 0

def test_env_extra_provider_sits_in_chain(monkeypatch):
    monkeypatch.setenv("SCP_LLM_FALLBACK_PROVIDERS", "deepseek:DEEPSEEK_API_KEY:DEEPSEEK_BASE_URL:DEEPSEEK_MODEL")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key-123456")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    monkeypatch.setenv("SCP_EGRESS_MODE", "allowlist")
    monkeypatch.setenv("SCP_LLM_EGRESS_ALLOWLIST", "openrouter.ai,api.deepseek.com")
    gateway = LLMGateway()
    _keyed(monkeypatch, OpenRouterProvider)
    chain = gateway._provider_chain("chat")
    names = [p.PROVIDER_NAME for p in chain]
    assert names == ["openrouter", "deepseek"]
    gateway.openrouter_chat._client = FakeClient([FakeResponse(429)])
    deepseek_provider = next(p for p in gateway._extra_providers["chat"] if p.PROVIDER_NAME == "deepseek")
    deepseek_provider._client = FakeClient([FakeResponse(200, "deepseek answers")])
    answer, label = asyncio.run(gateway.chat("q", task="chat"))
    assert answer == "deepseek answers"
    assert label.startswith("deepseek:")

def test_deny_egress_blocks_env_provider_before_injected_transport(monkeypatch):
    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key-123456")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    provider = EnvCompatProvider("deepseek", "chat", "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL")
    transport = FakeClient([FakeResponse(200, "must-not-be-used")])
    provider._client = transport
    answer, label = asyncio.run(provider.chat("q"))
    assert answer is None and label == "none"
    assert transport.calls == 0

def test_all_providers_down_fails_closed(monkeypatch):
    monkeypatch.setenv("SCP_EGRESS_MODE", "allowlist")
    monkeypatch.setenv("SCP_LLM_EGRESS_ALLOWLIST", "openrouter.ai")
    gateway = LLMGateway()
    _keyed(monkeypatch, OpenRouterProvider)
    dead = FakeClient([FakeResponse(429), FakeResponse(429)])
    gateway.openrouter_chat._client = dead
    answer, label = asyncio.run(gateway.chat("q", task="chat"))
    assert answer is None and label == "none"
    assert gateway._stats["failures"] == 1

def test_env_compat_placeholder_key_is_disabled(monkeypatch):
    monkeypatch.setenv("FAKE_KEY", "changeme")
    EnvCompatProvider("fake", "chat", "FAKE_KEY", "FAKE_URL", "FAKE_MODEL")
    monkeypatch.setenv("FAKE_URL", "https://api.fake.ai/v1")
    monkeypatch.setenv("FAKE_MODEL", "fake-1")
    provider2 = EnvCompatProvider("fake", "chat", "FAKE_KEY", "FAKE_URL", "FAKE_MODEL")
    assert provider2.enabled is False

def test_free_catalog_respects_deny_egress_without_network(monkeypatch):
    from scp.llm_gateway import free_catalog
    class ForbiddenNetworkClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("network client constructed while SCP_EGRESS_MODE=deny")
    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
    monkeypatch.setattr(free_catalog.httpx, "Client", ForbiddenNetworkClient)
    monkeypatch.setattr(free_catalog, "_fetched", False)
    monkeypatch.setattr(free_catalog, "_last_ok", None)
    assert free_catalog.refresh_free_catalog(force=True) is False
