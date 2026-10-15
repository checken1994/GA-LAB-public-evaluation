"""SCP V3.1 Web Navigator.

Browser access is opt-in. Public pages can be fetched directly; logged-in
pages require a user-provided local DevTools session. No credentials are read.
"""
from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urljoin

import httpx

from scp.security.url_safety import enforce_egress_policy  # [EE-G1]

from .browser_session import BrowserSession
from .internet_search import InternetSearch

_WEB_BACKEND_ENV = "SCP_WEB_BACKEND"
_PLAYWRIGHT_BACKEND_NAME = "playwright"
_WEB_BACKEND_ALLOW_INTERNAL_ENV = "SCP_WEB_BACKEND_ALLOW_INTERNAL"


def _playwright_backend_requested() -> bool:
    """Opt-in only for the exact value ``playwright`` (trimmed).

    Unset, empty or any other value keeps the default navigator unchanged.
    """
    return os.environ.get(_WEB_BACKEND_ENV, "").strip() == _PLAYWRIGHT_BACKEND_NAME


def _playwright_allow_internal_requested() -> bool:
    """Explicit local-loopback opt-in for the Playwright backend (default off)."""
    return os.environ.get(_WEB_BACKEND_ALLOW_INTERNAL_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


class WebNavigator:
    def __init__(self, browser: BrowserSession | None = None, search: InternetSearch | None = None) -> None:
        # Opt-in rendered-page backend: only when no explicit browser is
        # injected AND SCP_WEB_BACKEND=playwright. The default path below is
        # unchanged when the variable is unset or has any other value.
        self._playwright_backend: Any = None
        if browser is None and _playwright_backend_requested():
            from .playwright_backend import PlaywrightBackend

            self._playwright_backend = PlaywrightBackend(allow_internal=_playwright_allow_internal_requested())
            self.browser = self._playwright_backend
        else:
            self.browser = browser or BrowserSession()
        self.search_engine = search or InternetSearch()

    async def status(self) -> dict[str, Any]:
        browser_status = await self.browser.status()
        return {"navigator": "online", "browserSession": browser_status, "policy": "public-read or explicit local browser session"}

    async def browse_public(self, url: str, max_chars: int = 100_000) -> dict[str, Any]:
        """Read a public page without bypassing the canonical SSRF policy.

        Redirects are handled explicitly so every destination is validated;
        httpx must not silently follow a redirect into a private network. The
        response body is streamed with a bounded byte budget before decoding.
        """
        # [EE-G1] egress gate trước SSRF validate (cùng thứ tự với
        # safe_urlopen): SCP_EGRESS_MODE=deny chặn public browse trước mọi
        # I/O; EgressDeniedError là ValueError subclass → cùng raise contract.
        enforce_egress_policy(url)
        current_url = self.browser.validate_url(url)
        verify_dns = getattr(self.browser, "_verify_dns_rebinding", BrowserSession._verify_dns_rebinding)
        verify_dns(current_url)
        max_chars = max(1, min(int(max_chars), 1_000_000))
        max_bytes = max_chars * 4
        redirect_statuses = {301, 302, 303, 307, 308}

        async with httpx.AsyncClient(
            follow_redirects=False,
            trust_env=False,
            timeout=20,
            headers={"User-Agent": "SCP-DNA-WebNavigator/3.1"},
        ) as client:
            for _ in range(5):
                # [EE-G1] mỗi redirect hop là một destination mới — re-gate
                # trước khi stream (PEP ngay trước driver, mỗi hop).
                enforce_egress_policy(current_url)
                current_url = self.browser.validate_url(current_url)
                verify_dns(current_url)
                async with client.stream("GET", current_url) as response:
                    if response.status_code in redirect_statuses:
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("Redirect response has no Location header")
                        current_url = urljoin(current_url, location)
                        continue

                    response.raise_for_status()
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > max_bytes:
                        raise ValueError("Response exceeds public browse size limit")

                    chunks: list[bytes] = []
                    total_bytes = 0
                    async for chunk in response.aiter_bytes():
                        total_bytes += len(chunk)
                        if total_bytes > max_bytes:
                            raise ValueError("Response exceeds public browse size limit")
                        chunks.append(chunk)

                    encoding = response.encoding or "utf-8"
                    text = b"".join(chunks).decode(encoding, errors="replace")[:max_chars]
                    final_url = str(response.url)
                    status = response.status_code
                    content_type = response.headers.get("content-type", "")
                    break
            else:
                raise ValueError("Too many redirects")

        return {
            "success": True,
            "url": final_url,
            "status": status,
            "contentType": content_type,
            "text": text,
            "method": "public-http-read",
            "timestamp": time.time(),
        }

    async def search_public(self, query: str, max_results: int = 10) -> dict[str, Any]:
        if self._playwright_backend is not None:
            return await self._playwright_backend.search_public(query, max_results=max_results)
        return await self.search_engine.search(query, max_results=max_results)

    async def browse_logged_in(self, url: str) -> dict[str, Any]:
        return await self.browser.navigate_and_read(url)

    async def browse(self, url: str, use_logged_in_browser: bool = False) -> dict[str, Any]:
        if self._playwright_backend is not None:
            return await self._playwright_backend.browse(url)
        if use_logged_in_browser:
            return await self.browse_logged_in(url)
        return await self.browse_public(url)
