"""Opt-in Playwright browser backend for the SCP web navigator.

Activated only when ``SCP_WEB_BACKEND=playwright`` (see
``web_navigator.WebNavigator``). When the variable is unset, empty or has any
other value the default navigator behavior is unchanged.

Safety contract (scp-web-orchestration-safety):

- Read-only navigation: no form filling, no clicking, no submit, no typing.
  Only fixed, constant extraction expressions are evaluated against the page;
  no untrusted string is ever interpolated into an expression.
- Hard navigation timeout, independent of the page load state (the backend
  never waits for network idle), enforced by the Playwright navigation timeout
  plus an outer asyncio deadline. Both fail closed.
- Bounded text extraction: visible inner text only, trimmed and size-capped,
  so hidden (not rendered) honeypot nodes never reach the caller.
- Every URL must pass the same egress rules as the default navigator:
  http/https scheme allowlist, no embedded credentials, no ``..`` path
  traversal segments, and the canonical SSRF validation from
  ``scp.security.url_safety``. Loopback/private targets additionally require
  the explicit ``allow_internal`` opt-in (same convention as
  ``url_safety.safe_urlopen``).
- State independence: every call runs in a fresh ephemeral browser profile and
  the browser process is always closed, including on failure or timeout.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any
from urllib.parse import quote_plus, unquote, urlparse

from scp.security.url_safety import enforce_egress_policy
from scp.security.url_safety import validate_url as validate_safe_url

logger = logging.getLogger(__name__)

BACKEND_ENV = "SCP_WEB_BACKEND"
BACKEND_ALLOW_INTERNAL_ENV = "SCP_WEB_BACKEND_ALLOW_INTERNAL"
PLAYWRIGHT_BACKEND_NAME = "playwright"
PLAYWRIGHT_TIMEOUT_ENV = "SCP_WEB_PLAYWRIGHT_TIMEOUT_SECONDS"

DEFAULT_TIMEOUT_SECONDS = 20.0
MIN_TIMEOUT_SECONDS = 1.0
MAX_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_CHARS = 100_000
MAX_CHARS_LIMIT = 1_000_000

# Fixed extraction expressions. Constants only — never interpolate untrusted
# data into these (DOM injection guard).
_VISIBLE_TEXT_EXPRESSION = "() => document.body ? document.body.innerText : ''"
_SEARCH_RESULTS_EXPRESSION = (
    "() => Array.from(document.querySelectorAll('div.result, div.web-result'))"
    ".map(r => { const a = r.querySelector('a.result__a');"
    " const s = r.querySelector('.result__snippet');"
    " return {href: a ? a.href : '', text: a ? a.innerText : '',"
    " snippet: s ? s.innerText : ''}; })"
)


def playwright_backend_requested() -> bool:
    """Return True only for the exact opt-in value ``playwright``.

    Unset, empty or any other value keeps the default navigator unchanged.
    """
    return os.environ.get(BACKEND_ENV, "").strip() == PLAYWRIGHT_BACKEND_NAME


def playwright_allow_internal_requested() -> bool:
    """Explicit local-loopback opt-in for the Playwright backend (default off)."""
    return os.environ.get(BACKEND_ALLOW_INTERNAL_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _import_sync_playwright() -> Any:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(
            "SCP_WEB_BACKEND=playwright requested but the playwright package is "
            "not importable. Install the optional dependency "
            "(scp/requirements-optional-web.txt) and run "
            "'python -m playwright install chromium' before enabling the backend."
        ) from exc
    return sync_playwright


def _clamp_timeout_seconds(value: float | None) -> float:
    if value is None:
        raw = os.environ.get(PLAYWRIGHT_TIMEOUT_ENV, "")
        try:
            value = float(raw) if raw.strip() else DEFAULT_TIMEOUT_SECONDS
        except ValueError:
            value = DEFAULT_TIMEOUT_SECONDS
    return max(MIN_TIMEOUT_SECONDS, min(MAX_TIMEOUT_SECONDS, float(value)))


class PlaywrightNavigationTimeout(TimeoutError):
    """The Playwright hard navigation timeout fired (distinct from the outer deadline)."""


import atexit
import threading


class PlaywrightBackend:
    """Read-only rendered-page backend exposed through the navigator interface.

    The Playwright sync API is used inside worker threads via
    ``asyncio.to_thread`` (the navigator is async). A fresh headless Chromium
    instance with an ephemeral profile is launched per call and always closed,
    which keeps Playwright objects single-threaded and profiles isolated.
    """
    _active_drivers: set[Any] = set()
    _drivers_lock = threading.Lock()

    @classmethod
    def _register_driver(cls, driver: Any) -> None:
        with cls._drivers_lock:
            cls._active_drivers.add(driver)

    @classmethod
    def _unregister_driver(cls, driver: Any) -> None:
        with cls._drivers_lock:
            cls._active_drivers.discard(driver)

    @classmethod
    def _cleanup_all(cls) -> None:
        with cls._drivers_lock:
            for d in list(cls._active_drivers):
                try:
                    d.stop()
                except Exception as exc:
                    logger.debug("Failed to stop playwright driver during cleanup: %s", exc, exc_info=True)
            cls._active_drivers.clear()

    def __init__(
        self,
        allow_internal: bool = False,
        timeout_seconds: float | None = None,
        headless: bool = True,
    ) -> None:
        self.allow_internal = bool(allow_internal)
        self.timeout_seconds = _clamp_timeout_seconds(timeout_seconds)
        self.headless = bool(headless)

    # ------------------------------------------------------------------
    # URL safety (same egress rules as the default navigator)
    # ------------------------------------------------------------------
    def validate_url(self, url: str) -> str:
        clean_url = url.strip() if isinstance(url, str) else ""
        parsed = urlparse(clean_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Only public http/https URLs are allowed")
        if parsed.username or parsed.password:
            raise ValueError("URLs containing credentials are not allowed")
        # Reject traversal segments in both the raw and the percent-decoded
        # path: a browser resolves ``..`` (and ``..%2f``) before requesting.
        for candidate_path in (parsed.path, unquote(parsed.path)):
            segments = [segment for segment in candidate_path.split("/") if segment != ""]
            if ".." in segments:
                raise ValueError("URL path traversal segments are not allowed")
        validate_safe_url(clean_url, allow_internal=self.allow_internal)
        if not self.allow_internal:
            enforce_egress_policy(clean_url, extra_allowed_hosts=frozenset(["example.com"]))
        return clean_url

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self) -> dict[str, Any]:
        """Declare the backend ready. Browsers are launched per call."""
        _import_sync_playwright()
        return {"backend": PLAYWRIGHT_BACKEND_NAME, "running": True}

    async def stop(self) -> dict[str, Any]:
        """No persistent browser is held; per-call instances are already closed."""
        return {"backend": PLAYWRIGHT_BACKEND_NAME, "running": False}

    async def __aenter__(self) -> PlaywrightBackend:
        await self.start()
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Browsing
    # ------------------------------------------------------------------
    async def browse(self, url: str, max_chars: int = DEFAULT_MAX_CHARS) -> dict[str, Any]:
        """Read a page in a fresh ephemeral Chromium and return bounded evidence."""
        clean_url = self.validate_url(url)
        capped_chars = max(1, min(int(max_chars), MAX_CHARS_LIMIT))
        outer_deadline = self.timeout_seconds + 5.0
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._browse_sync, clean_url, capped_chars),
                timeout=outer_deadline,
            )
        except PlaywrightNavigationTimeout:
            raise
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Playwright browse exceeded the outer hard deadline ({outer_deadline:.0f}s); fail-closed"
            ) from None

    async def navigate_and_read(self, url: str, target: Any = None) -> dict[str, Any]:
        """BrowserSession-compatible shape for ``WebNavigator.browse_logged_in``."""
        result = await self.browse(url)
        return {
            "success": result["success"],
            "url": result["url"],
            "title": result["title"],
            "text": result["text_content"],
            "method": result["method"],
            "timestamp": result["timestamp"],
        }

    async def search_public(self, query: str, max_results: int = 10) -> dict[str, Any]:
        """Public search through the rendered page; no form fill, no submit.

        Navigates directly to the HTML search endpoint (GET semantics) and
        extracts visible result anchors. Fails closed: on navigation failure a
        ``success: False`` result is returned, never a silent fallback.
        """
        clean_query = str(query or "").strip()
        if not clean_query:
            return {"success": False, "error": "Search query is empty", "results": []}
        max_results = max(1, min(int(max_results), 20))
        target_url = f"https://html.duckduckgo.com/html/?q={quote_plus(clean_query)}"
        try:
            # One ephemeral browser per search: validate, navigate (GET
            # semantics — no form fill, no submit) and extract visible rows.
            clean_url = self.validate_url(target_url)
            raw_rows = await asyncio.wait_for(
                asyncio.to_thread(self._search_rows_sync, clean_url),
                timeout=self.timeout_seconds + 5.0,
            )
        except (ValueError, RuntimeError, TimeoutError) as exc:
            return {
                "success": False,
                "query": clean_query,
                "results": [],
                "providersTried": ["duckduckgo-playwright"],
                "errors": [{"provider": "duckduckgo-playwright", "error": str(exc)}],
                "untrustedData": True,
                "method": "playwright-search",
                "timestamp": time.time(),
            }
        results: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in raw_rows:
            url = self._clean_result_url(str(row.get("href", "")))
            if not url or url in seen:
                continue
            seen.add(url)
            results.append(
                {
                    "title": " ".join(str(row.get("text", "")).split()),
                    "url": url,
                    "snippet": " ".join(str(row.get("snippet", "")).split())[:500],
                    "provider": "duckduckgo-playwright",
                }
            )
            if len(results) >= max_results:
                break
        return {
            "success": bool(results),
            "query": clean_query,
            "results": results,
            "providersTried": ["duckduckgo-playwright"],
            "errors": [],
            "untrustedData": True,
            "method": "playwright-search",
            "timestamp": time.time(),
        }

    # ------------------------------------------------------------------
    # BrowserSession-compatible surface (fail-closed for unsupported power)
    # ------------------------------------------------------------------
    async def status(self) -> dict[str, Any]:
        return {
            "available": True,
            "backend": PLAYWRIGHT_BACKEND_NAME,
            "browser": "chromium",
            "headless": self.headless,
            "timeoutSeconds": self.timeout_seconds,
            "allowInternal": self.allow_internal,
            "policy": "read-only rendered text, hard timeout, per-call ephemeral profile",
        }

    async def targets(self) -> list[dict[str, Any]]:
        """No shared DevTools session exists for this backend."""
        return []

    def type_and_submit(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "PlaywrightBackend is read-only: automatic form filling and submit "
            "are disabled by the web orchestration safety policy"
        )

    def open_visible(self, url: str) -> dict[str, Any]:
        raise NotImplementedError("PlaywrightBackend does not open visible browser windows")

    def cdp_command(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("PlaywrightBackend does not expose raw CDP commands")

    def evaluate(self, expression: str, target: Any = None, **kwargs: Any) -> None:
        """Fail loud: arbitrary JS execution stays BrowserSession-only.

        The read-only Playwright backend never runs caller-controlled
        JavaScript against a page (anti-honeypot / DOM injection guard,
        scp-web-orchestration-safety). Hands actions that need CDP
        ``Runtime.evaluate`` (``web.dom_snapshot``, ``web.wait_for_text``)
        must use the default BrowserSession backend. The signature mirrors
        ``BrowserSession.evaluate(expression, target)`` (target also accepted
        positionally) so hands-executor call sites raise this
        ``NotImplementedError`` instead of a ``TypeError``.
        """
        raise NotImplementedError(
            "PlaywrightBackend is read-only: evaluate() is not supported "
            "(anti-honeypot: no arbitrary JS execution). Use BrowserSession "
            "backend for CDP evaluate."
        )

    # ------------------------------------------------------------------
    # Sync internals (run on worker threads)
    # ------------------------------------------------------------------
    def _browse_sync(self, url: str, max_chars: int) -> dict[str, Any]:
        sync_playwright = _import_sync_playwright()
        timeout_ms = int(self.timeout_seconds * 1000)
        driver = sync_playwright().start()
        self._register_driver(driver)
        try:
            browser = driver.chromium.launch(headless=self.headless)
            try:
                context = browser.new_context()
                try:
                    page = context.new_page()
                    response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    title = page.title()
                    raw_text = page.evaluate(_VISIBLE_TEXT_EXPRESSION) or ""
                    text_content = str(raw_text).strip()[:max_chars]
                    status_code = int(response.status) if response is not None else 0
                finally:
                    context.close()
            finally:
                browser.close()
        except Exception as exc:
            raise self._translate_playwright_error(exc) from exc
        finally:
            driver.stop()
            self._unregister_driver(driver)
        return {
            "success": True,
            "url": url,
            "title": title,
            "text_content": text_content,
            "text": text_content,
            "status": status_code,
            "method": "playwright-ephemeral",
            "timestamp": time.time(),
        }

    def _search_rows_sync(self, url: str) -> list[dict[str, Any]]:
        sync_playwright = _import_sync_playwright()
        timeout_ms = int(self.timeout_seconds * 1000)
        driver = sync_playwright().start()
        self._register_driver(driver)
        try:
            browser = driver.chromium.launch(headless=self.headless)
            try:
                context = browser.new_context()
                try:
                    page = context.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    rows = page.evaluate(_SEARCH_RESULTS_EXPRESSION) or []
                finally:
                    context.close()
            finally:
                browser.close()
        except Exception as exc:
            raise self._translate_playwright_error(exc) from exc
        finally:
            driver.stop()
            self._unregister_driver(driver)
        return list(rows)

    @staticmethod
    def _clean_result_url(value: str) -> str:
        value = (value or "").strip()
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        return value

    @staticmethod
    def _translate_playwright_error(exc: Exception) -> Exception:
        name = type(exc).__name__
        message = str(exc).split("\n", 1)[0][:300]
        if "Timeout" in name or "timeout" in message.lower():
            return PlaywrightNavigationTimeout(
                f"Playwright navigation exceeded the hard timeout; fail-closed ({message})"
            )
        return RuntimeError(f"Playwright navigation failed: {name}: {message}")

atexit.register(PlaywrightBackend._cleanup_all)
