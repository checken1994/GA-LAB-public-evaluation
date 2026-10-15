"""[G3-CONSOLIDATE RE-05] Canonical Wikipedia client — replaces 8 duplicate fetchers.

Single source of truth for Wikipedia API calls. All other modules should
import from here instead of implementing their own fetch_wikipedia().

Why this exists:
- Task 9-C finding RE-05 (worklog.md line ~2772) documented 8 independent
  Wikipedia fetch implementations across the codebase. Same REST API hit
  8 ways with different error handling, different rate limits, different
  timeouts (3s/5s/8s/15s/30s), different article-selection logic.
- This file consolidates them into ONE client with:
  - REST API (en.wikipedia.org/api/rest_v1/page/summary/) for summaries
  - action=query API (en.wikipedia.org/w/api.php) for search + full extracts
  - Consistent error handling (try/except, return None on failure)
  - Consistent timeout (10s default, configurable per call)
  - Rate limiting (1 req/sec to respect Wikipedia ToS)
  - In-memory LRU cache (maxsize=256) — short-TTL, deduplicates hot keys
  - Configurable language (default "en"; "vi" used by live_knowledge)

Public API (callers should use these):
    fetch_summary(query, lang="en", timeout=10) -> dict | None
        dict shape: {"title", "extract", "url", "thumbnail"}
    fetch_extract(query, lang="en", timeout=10) -> str | None
        Convenience wrapper — returns just the extract text.
    search(query, lang="en", limit=5, timeout=10) -> list[dict]
        Each dict: {"title", "snippet"}
    fetch_full_extract(title, lang="en", timeout=10) -> str | None
        action=query with prop=extracts — first 500 chars of intro.
        Used by why_sources/wikipedia.py as the "alternative" path.

Backward compatibility:
    Existing modules keep their local fetch_wikipedia() functions but
    delegate to this client. Callers do not need to change.

References:
- Worklog Task 9-C finding RE-05 (line ~2772)
- Worklog Task 2-B finding B2 #1 (line ~248)
- Worklog Task G3-full-B (this task)
"""
from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from functools import lru_cache

# [AUDIT-20260909 SSRF-S1] safe_urlopen thay mọi raw requests.get.
from scp.security.url_safety import safe_urlopen

logger = logging.getLogger("scp.wikipedia")

# ---------------------------------------------------------------------------
# Constants — single source of truth for endpoint + timing.
# ---------------------------------------------------------------------------
WIKIPEDIA_REST_BASE = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
WIKIPEDIA_API_BASE = "https://{lang}.wikipedia.org/w/api.php"
DEFAULT_TIMEOUT = 10        # seconds (was inconsistent: 5s in astronomy.py,
                            # 8s in live_knowledge.py, 15s in reality_engine.py)
DEFAULT_RATE_LIMIT = 1.0    # seconds between requests (Wikipedia ToS asks ≤200
                            # req/sec per IP, but 1 req/sec is conservative + avoids
                            # 429s on shared infrastructure)
DEFAULT_USER_AGENT = (
    "SCP-Vietnam/1.0 (https://scp-vietnam.example.com; "
    "Vietnamese educational research project; contact: scp-vietnam@example.com)"
)

# Module-level rate-limiter state (single global — protects Wikipedia from us).
_last_request_time: float = 0.0

# [AUDIT-20260909 SSRF-S1] lang được nối vào HOST ({lang}.wikipedia.org) —
# PHẢI fullmatch language-code pattern, nếu không host có thể bị đổi.
_LANG_CODE_RE = None  # compiled lazily below to keep import light


def _lang_code_re():
    global _LANG_CODE_RE
    if _LANG_CODE_RE is None:
        import re
        _LANG_CODE_RE = re.compile(r"^[a-z]{2,3}(?:[-_][a-z]{2,4})?$")
    return _LANG_CODE_RE


def _validate_lang(lang: str) -> str:
    """[AUDIT-20260909 SSRF-S1] Wikipedia language code — fail-closed."""
    lang_s = str(lang or "").strip().lower()
    if not _lang_code_re().fullmatch(lang_s):
        raise ValueError(f"invalid_wikipedia_lang:{lang_s[:16]!r}")
    return lang_s


def build_wikipedia_summary_url(query: str, lang: str = "en") -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — lang validated (host là
    literal sau khi format), title được quote(safe='') vào 1 path segment."""
    lang_v = _validate_lang(lang)
    quoted = urllib.parse.quote(str(query or ""), safe="")
    return WIKIPEDIA_REST_BASE.format(lang=lang_v) + quoted


def build_wikipedia_api_url(params: dict, lang: str = "en") -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — lang validated, mọi param
    động được urlencode thành query values. Host cố định {lang}.wikipedia.org."""
    lang_v = _validate_lang(lang)
    return WIKIPEDIA_API_BASE.format(lang=lang_v) + "?" + urllib.parse.urlencode(params)


def _rate_limit() -> None:
    """Enforce DEFAULT_RATE_LIMIT seconds between successive Wikipedia requests.

    DNA SCP #9 (No harm): we protect the external API from being hammered by
    our own concurrent callers. Module-level state (not per-call) so all
    callers share the same throttle.
    """
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < DEFAULT_RATE_LIMIT:
        time.sleep(DEFAULT_RATE_LIMIT - elapsed)
    _last_request_time = time.time()


def _headers() -> dict[str, str]:
    """Standard headers — User-Agent required by Wikipedia policy."""
    return {"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
@lru_cache(maxsize=256)
def fetch_summary(query: str, lang: str = "en",
                  timeout: int = DEFAULT_TIMEOUT) -> dict | None:
    """Fetch Wikipedia page summary via REST API.

    Args:
        query: Page title or search query (Wikipedia REST does its own
               disambiguation — for ambiguous queries, returns the top result
               or a disambiguation page).
        lang:   Wikipedia language code ("en", "vi", "fr", ...). Default "en".
        timeout: HTTP timeout in seconds. Default 10.

    Returns:
        dict with keys: title, extract, url, thumbnail. None on failure
        (404, network error, timeout, etc.).
    """
    if not query or not query.strip():
        return None
    try:
        _rate_limit()
        # [AUDIT-20260909 SSRF-S1] builder (validate lang + quote title) rồi
        # fetch qua safe_urlopen thay raw requests.get.
        url = build_wikipedia_summary_url(query, lang)
        req = urllib.request.Request(url, headers=_headers())  # noqa: S310 — validated by safe_urlopen
        with safe_urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        # Wikipedia REST returns type="not_found" for missing pages
        # (HTTP 200 with a small JSON body) — treat as None.
        if data.get("type") == "not_found":
            logger.debug(f"Wikipedia REST not_found for: {query!r}")
            return None
        return {
            "title": data.get("title", ""),
            "extract": data.get("extract", ""),
            "url": (data.get("content_urls", {})
                       .get("desktop", {})
                       .get("page", "")),
            "thumbnail": (data.get("thumbnail", {})
                             .get("source", "")),
        }
    except Exception as e:
        logger.warning(f"Wikipedia fetch_summary error for {query!r} (lang={lang}): {e}", exc_info=True)
        return None


def fetch_extract(query: str, lang: str = "en",
                  timeout: int = DEFAULT_TIMEOUT) -> str | None:
    """Fetch just the text extract. None on failure.

    Thin wrapper around fetch_summary — same caching + rate limit.
    """
    result = fetch_summary(query, lang, timeout)
    return result["extract"] if result else None


def search(query: str, lang: str = "en", limit: int = 5,
           timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    """Search Wikipedia for matching pages via action=query API.

    Args:
        query: Free-text search query.
        lang:   Wikipedia language code.
        limit:  Max results (1-50). Default 5.
        timeout: HTTP timeout in seconds.

    Returns:
        List of dicts: [{"title": str, "snippet": str}, ...]. Empty list on
        failure (never raises — failures degrade to []).
    """
    if not query or not query.strip():
        return []
    try:
        _rate_limit()
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": str(max(1, min(50, limit))),
            "format": "json",
            "origin": "*",  # CORS bypass for action API
        }
        # [AUDIT-20260909 SSRF-S1] builder (validate lang + urlencode) rồi
        # fetch qua safe_urlopen thay raw requests.get.
        url = build_wikipedia_api_url(params, lang)
        req = urllib.request.Request(url, headers=_headers())  # noqa: S310 — validated by safe_urlopen
        with safe_urlopen(req, timeout=timeout) as resp:
            results = (json.loads(resp.read().decode("utf-8", errors="replace"))
                          .get("query", {})
                          .get("search", []))
        return [{"title": r.get("title", ""),
                 "snippet": r.get("snippet", "")}
                for r in results]
    except Exception as e:
        logger.warning(f"Wikipedia search error for {query!r} (lang={lang}): {e}", exc_info=True)
        return []


@lru_cache(maxsize=128)
def fetch_full_extract(title: str, lang: str = "en",
                       timeout: int = DEFAULT_TIMEOUT) -> str | None:
    """Fetch the intro extract (first ~500 chars) of a Wikipedia page.

    Uses action=query with prop=extracts&exintro=true — same approach as
    why_sources/wikipedia.py (the "alternative" path mentioned in the
    G3-full-B hard rules). Provided here so that module can delegate to
    the canonical client without losing its richer parsing logic.

    Args:
        title: Exact Wikipedia page title (use search() first if unsure).
        lang:  Wikipedia language code.
        timeout: HTTP timeout in seconds.

    Returns:
        Plain-text extract (HTML stripped), or None on failure.
    """
    if not title or not title.strip():
        return None
    try:
        _rate_limit()
        params = {
            "action": "query",
            "titles": title[:50],  # Wikipedia title cap
            "prop": "extracts",
            "exintro": "",
            "format": "json",
            "exchars": "500",
        }
        # [AUDIT-20260909 SSRF-S1] builder (validate lang + urlencode) rồi
        # fetch qua safe_urlopen thay raw requests.get.
        url = build_wikipedia_api_url(params, lang)
        req = urllib.request.Request(url, headers=_headers())  # noqa: S310 — validated by safe_urlopen
        with safe_urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        pages = (data.get("query", {})
                    .get("pages", {}) or {})
        for _pid, page in pages.items():
            extract = page.get("extract", "")
            if extract:
                # Strip HTML tags (Wikipedia returns <p>...</p>)
                import re
                clean = re.sub(r"<[^>]+>", "", extract).strip()
                if clean:
                    return clean
        return None
    except Exception as e:
        logger.debug(f"fetch_full_extract ignored: {e}", exc_info=True)
        logger.warning(
            f"Wikipedia fetch_full_extract error for {title!r} (lang={lang}): {e}"
        )
        return None


# ---------------------------------------------------------------------------
# Convenience: search-then-summary (the live_knowledge.py pattern).
# ---------------------------------------------------------------------------
def search_then_summary(query: str, lang: str = "en",
                        timeout: int = DEFAULT_TIMEOUT) -> dict | None:
    """Search Wikipedia for the query, then fetch the summary of the top hit.

    Mirrors the original live_knowledge.py:81 fetch_wikipedia() pattern:
    1. action=query search to find a matching page title.
    2. REST summary on that title.

    Falls back to direct fetch_summary(query) if search returns nothing
    (REST API does its own disambiguation in many cases).

    Returns the same dict shape as fetch_summary, or None.
    """
    # 1) Try direct REST summary first — handles most cases.
    direct = fetch_summary(query, lang=lang, timeout=timeout)
    if direct and direct.get("extract"):
        return direct

    # 2) Fall back to search → summary on the top hit.
    results = search(query, lang=lang, limit=1, timeout=timeout)
    if results:
        top_title = results[0]["title"]
        if top_title:
            return fetch_summary(top_title, lang=lang, timeout=timeout)
    return None


__all__ = [
    "fetch_summary",
    "fetch_extract",
    "fetch_full_extract",
    "search",
    "search_then_summary",
    "DEFAULT_TIMEOUT",
    "DEFAULT_RATE_LIMIT",
]
