"""[ZONE-FIX 2026-09-26] Regression — internet_search redirect hops must be
re-gated by the egress policy (PEP on every hop).

BEFORE the fix: httpx.AsyncClient ran with follow_redirects=True and only the
provider URL was gated — a 302 to an off-allowlist host was fetched UN-GATED
(probe-verified: off-allowlist content parsed as search results). AFTER: the
fetch mirrors web_navigator.browse_public (follow_redirects=False + manual
hop loop + enforce_egress_policy per hop).
"""
from __future__ import annotations

import asyncio

import httpx
import pytest


class _RedirectTransport(httpx.MockTransport):
    def __init__(self, seen: list[str]):
        super().__init__(self._handle)
        self._seen = seen

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self._seen.append(str(request.url))
        if request.url.host == "html.duckduckgo.com":
            return httpx.Response(302, headers={"Location": "http://evil.attacker.example/steal?q=leak"})
        return httpx.Response(
            200,
            text='<html><a class="result__a" href="http://evil.attacker.example/loot">EXFILTRATED</a></html>',
        )


def _install_transport(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    real_client = httpx.AsyncClient

    class _PatchedClient(real_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("scp.web_control.internet_search.httpx.AsyncClient", _PatchedClient)


def test_redirect_hop_to_off_allowlist_host_is_denied(monkeypatch):
    monkeypatch.setenv("SCP_EGRESS_MODE", "allowlist")
    monkeypatch.setenv("SCP_EGRESS_ALLOWLIST", "html.duckduckgo.com")

    from scp.web_control.internet_search import InternetSearch

    seen: list[str] = []
    _install_transport(monkeypatch, _RedirectTransport(seen))

    result = asyncio.run(InternetSearch(timeout=5.0).search("probe"))

    off_allowlist_fetched = [u for u in seen if "evil.attacker.example" in u]
    off_allowlist_results = [
        r for r in result.get("results", []) if "evil.attacker.example" in r.get("url", "")
    ]
    denied = any(
        "evil.attacker.example" in e.get("error", "") or "egress" in e.get("error", "").lower()
        for e in result.get("errors", [])
    )
    assert not off_allowlist_fetched, (
        f"redirect hop fetched WITHOUT egress re-gate: {off_allowlist_fetched}"
    )
    assert not off_allowlist_results, "off-allowlist redirect content parsed as results"
    assert denied, "expected an egress denial recorded in errors[] for the redirect hop"


def test_redirect_hop_gate_allows_allowlisted_provider(monkeypatch):
    """The first hop (allowlisted provider) still fetches normally."""
    monkeypatch.setenv("SCP_EGRESS_MODE", "allowlist")
    monkeypatch.setenv("SCP_EGRESS_ALLOWLIST", "html.duckduckgo.com")

    from scp.web_control.internet_search import InternetSearch

    seen: list[str] = []
    _install_transport(monkeypatch, _RedirectTransport(seen))

    asyncio.run(InternetSearch(timeout=5.0).search("probe"))
    assert any(u.startswith("https://html.duckduckgo.com") for u in seen), (
        "allowlisted provider fetch was blocked — over-broad gate"
    )


def test_too_many_redirects_fail_closed(monkeypatch):
    """A redirect loop terminates with Too many redirects instead of hanging."""
    monkeypatch.setenv("SCP_EGRESS_MODE", "allowlist")
    monkeypatch.setenv("SCP_EGRESS_ALLOWLIST", "html.duckduckgo.com")

    from scp.web_control.internet_search import InternetSearch

    class _LoopTransport(httpx.MockTransport):
        def __init__(self):
            super().__init__(self._handle)

        def _handle(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(302, headers={"Location": "https://html.duckduckgo.com/loop"})

    seen: list[str] = []
    _install_transport(monkeypatch, _LoopTransport())

    result = asyncio.run(InternetSearch(timeout=5.0).search("probe"))
    duck_errors = [e for e in result.get("errors", []) if e.get("provider") == "duckduckgo"]
    assert duck_errors, "redirect loop must surface as a provider error"
    assert "Too many redirects" in duck_errors[0].get("error", "")
    assert len([u for u in seen if u.startswith("https://html.duckduckgo.com")]) <= 6
