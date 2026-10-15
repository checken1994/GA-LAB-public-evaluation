"""Public Internet search for SCP.

This module performs retrieval only. Search results are untrusted data and are
never treated as executable instructions or as executable instructions.
"""
from __future__ import annotations

import base64
import logging
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

import httpx

from scp.security.url_safety import enforce_egress_policy  # [EE-G1]

logger = logging.getLogger(__name__)


class _SearchParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self.stack: list[tuple[str, str]] = []
        self.current: dict[str, str] | None = None
        self.capture: str | None = None
        self.buffer: list[str] = []

    def _commit(self) -> None:
        """Finalize the result under construction, if it has a title."""
        if self.current is not None and self.current.get("title"):
            self.results.append(self.current)
        self.current = None
        self.capture = None
        self.buffer = []

    @staticmethod
    def _classes(attrs: list[tuple[str, str | None]]) -> str:
        return (dict(attrs).get("class") or "").lower()

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: value or "" for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = self._classes(attrs)
        values = self._attrs(attrs)
        self.stack.append((tag, classes))
        is_ddg_title = "result__a" in classes
        is_bing_title = tag == "a" and any("b_algo" in parent_classes for _, parent_classes in self.stack[:-1])
        if is_ddg_title or is_bing_title:
            # [SEARCH-FIX 2026-10-01] A new result anchor starts: commit the
            # previous result first so a snippet arriving after its title
            # anchor is not lost.
            self._commit()
            provider = "duckduckgo" if is_ddg_title else "bing"
            self.current = {"title": "", "url": values.get("href", ""), "snippet": "", "provider": provider}
            self.capture = "title"
            self.buffer = []
        elif self.current and ("result__snippet" in classes or (tag == "p" and any("b_algo" in c for _, c in self.stack))):
            # [SEARCH-FIX 2026-10-01] Snippets for BOTH providers arrive AFTER
            # the title anchor closes: DDG uses <a class="result__snippet">,
            # Bing uses <p> inside li.b_algo. Results are therefore committed
            # lazily (next result anchor / end of document), not on </a>.
            self.capture = "snippet"
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture and self.stack and self.stack[-1][0] == tag:
            text = " ".join("".join(self.buffer).split())
            if self.current is not None:
                self.current[self.capture] = text
            self.capture = None
            self.buffer = []
        if self.stack:
            self.stack.pop()
        # [SEARCH-FIX 2026-10-01] No commit on </a>: both providers place the
        # snippet after the title anchor, so committing here produced empty
        # snippets. Commit happens on the next result anchor or in close().

    def close(self) -> None:
        super().close()
        self._commit()


class InternetSearch:
    """Search public web indexes without requiring an AI login or API key."""

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout
        self.user_agent = "SCP-DNA-InternetSearch/3.2"

    @staticmethod
    def _clean_url(value: str) -> str:
        value = (value or "").strip()
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        return value

    @staticmethod
    def _unwrap_url(value: str) -> str:
        """[SEARCH-FIX 2026-10-01] Resolve provider redirect wrappers to the
        real destination URL; otherwise return the (scheme-normalized) input.

        Both engines served results through first-party redirectors:
          - DuckDuckGo: ``//duckduckgo.com/l/?uddg=<urlencoded-real>&rut=...``
            (protocol-relative, so ``_clean_url`` silently dropped EVERY DDG
            result — the fetched page parsed fine but all URLs were empty).
          - Bing: ``https://www.bing.com/ck/a?...&u=a1<base64url-real>``.

        Unwrapping is display-only hygiene: targets stay untrusted data and
        are never fetched by this module (browse_public re-validates on
        navigation). If a wrapper is recognized but the target cannot be
        extracted, return "" (fail closed) rather than surfacing a tracking
        URL as if it were the source.
        """
        value = (value or "").strip()
        if value.startswith("//"):
            value = "https:" + value
        try:
            parsed = urlparse(value)
            host = (parsed.hostname or "").lower()
            path = parsed.path or ""
        except ValueError:
            return value
        if host in {"duckduckgo.com", "www.duckduckgo.com"} and path.startswith("/l/"):
            return parse_qs(parsed.query).get("uddg", [""])[0]
        if host in {"bing.com", "www.bing.com"} and path.startswith("/ck/"):
            target = parse_qs(parsed.query).get("u", [""])[0]
            if not target.startswith("a1"):
                return ""
            raw = target[2:]
            try:
                return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", "replace")
            except (ValueError, UnicodeDecodeError):
                return ""
        return value

    @staticmethod
    def _dedupe(results: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        seen: set[str] = set()
        output: list[dict[str, Any]] = []
        for item in results:
            url = item.get("url", "")
            if not url or url in seen:
                continue
            item["url"] = url
            seen.add(url)
            output.append(item)
            if len(output) >= limit:
                break
        return output

    def _parse(self, html: str, provider: str, limit: int) -> list[dict[str, Any]]:
        parser = _SearchParser()
        parser.feed(html)
        parser.close()
        results: list[dict[str, Any]] = []
        for item in parser.results:
            if item.get("provider") != provider:
                continue
            # [SEARCH-FIX 2026-10-01] unwrap the engine redirect wrapper first,
            # then validate scheme/host — order matters: DDG wrapper URLs are
            # protocol-relative and were previously dropped wholesale.
            item["url"] = self._clean_url(self._unwrap_url(item.get("url", "")))
            if item["url"]:
                results.append(item)
        return self._dedupe(results, limit)

    async def search(self, query: str, max_results: int = 10) -> dict[str, Any]:
        query = query.strip()
        if not query:
            return {"success": False, "error": "Search query is empty", "results": []}
        max_results = max(1, min(int(max_results), 20))
        headers = {"User-Agent": self.user_agent, "Accept-Language": "vi,en;q=0.8"}
        errors: list[dict[str, str]] = []
        all_results: list[dict[str, Any]] = []
        async with httpx.AsyncClient(follow_redirects=False, timeout=self.timeout, headers=headers) as client:
            providers = [
                ("duckduckgo", f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"),
                ("bing", f"https://www.bing.com/search?q={quote_plus(query)}"),
            ]
            redirect_statuses = {301, 302, 303, 307, 308}
            for name, url in providers:
                try:
                    # [EE-G1] đọc SCP_EGRESS_MODE trước mỗi provider fetch;
                    # denial → except dưới → errors[] (graceful như provider lỗi).
                    enforce_egress_policy(url)
                    current_url = url
                    for _ in range(5):
                        # [EE-G1] mỗi redirect hop là một destination mới —
                        # re-gate ngay trước khi fetch (PEP mỗi hop; mirror
                        # web_navigator.browse_public). follow_redirects=False
                        # chặn httpx tự đi theo redirect vào destination chưa
                        # qua chính sách egress.
                        enforce_egress_policy(current_url)
                        response = await client.get(current_url)
                        if response.status_code in redirect_statuses:
                            location = response.headers.get("location")
                            if not location:
                                raise ValueError("Redirect response has no Location header")
                            current_url = urljoin(current_url, location)
                            continue
                        break
                    else:
                        raise ValueError("Too many redirects")
                    response.raise_for_status()
                    provider_results = self._parse(response.text, name, max_results)
                    # [SEARCH-FIX 2026-10-01] A 200 page that contributes zero
                    # results must be observable: previously DDG could silently
                    # contribute nothing while errors[] stayed empty (the user
                    # saw only the other provider's results and no hint why).
                    if not provider_results:
                        reason = (
                            "provider page had result markup but 0 results parsed (parser/markup mismatch)"
                            if ("result__a" in response.text or "b_algo" in response.text)
                            else "provider returned a page with 0 results (possible bot-block/anomaly or empty SERP)"
                        )
                        errors.append({"provider": name, "error": reason})
                    all_results.extend(provider_results)
                except Exception as exc:
                    logger.debug("internet_search: provider %s failed: %s", name, exc, exc_info=True)
                    errors.append({"provider": name, "error": str(exc)})

        results = self._dedupe(all_results, max_results)
        return {
            "success": bool(results),
            "query": query,
            "results": results,
            "providersTried": ["duckduckgo", "bing"],
            "errors": errors,
            "untrustedData": True,
            "method": "public-search",
            "timestamp": time.time(),
        }
