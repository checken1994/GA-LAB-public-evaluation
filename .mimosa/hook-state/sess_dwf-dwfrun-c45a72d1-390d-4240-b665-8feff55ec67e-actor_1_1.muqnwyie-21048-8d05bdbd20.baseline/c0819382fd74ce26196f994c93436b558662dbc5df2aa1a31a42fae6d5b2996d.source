# SCP CIRCUIT: M12 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M12-closure.json)
"""
[Task 7-A] Wikipedia source handler — extracted from why_engine.py

TẠI SAO: WhyEngine._query_wikipedia() was 63 LOC inline. Extracted as
standalone function for modularity. Backward-compatible — WhyEngine delegates.

[Task 47-A / Subagent A] Added circuit breaker + retry + cache + 429 handling.
  - WHY: Wikipedia API can return 429 (rate limit) or transient 5xx. Without
    protection, every WHY-engine query could fail loudly or hammer the API.
  - DNA SCP #9 (No harm): circuit breaker protects external API from us.
  - DNA SCP #7 (AutoFix safe): doesn't change the parsing/extraction logic —
    only adds resilience layer around the HTTP call.

[G3-CONSOLIDATE RE-05 / G3-full-B] This file is the most-sophisticated of the
8 Wikipedia fetchers (circuit breaker + retry + cache + 429 backoff + action=query
extracts). Per the task hard rule: "Do NOT remove the wikipedia library usage in
why_sources/wikipedia.py if it's working — just add the canonical client as an
alternative." The existing _fetch_wikipedia_pages() + query_wikipedia() logic is
PRESERVED AS-IS. The canonical client (scp.core.wikipedia_client) is imported
below as an ALTERNATIVE for any new caller that wants the simpler REST-summary
path or wants to dedupe with the other 7 fetchers.

  - Existing path (kept):  _fetch_wikipedia_pages(target) -> action=query pages dict
                            query_wikipedia(target, question) -> extracted value/None
  - Canonical alternative: scp.core.wikipedia_client.fetch_summary(query, lang)
                            scp.core.wikipedia_client.fetch_full_extract(title, lang)
                            scp.core.wikipedia_client.search(query, lang, limit)
"""
from __future__ import annotations

import hashlib
import json as _json
import logging
import os as _os
import re as _re
import time
import urllib.error
import urllib.parse
import urllib.request

# [G3-CONSOLIDATE RE-05] Canonical client — available as alternative path.
# Not used by _fetch_wikipedia_pages() below (which keeps its own circuit
# breaker + retry logic per the hard rule). New callers SHOULD prefer this.
from scp.core.wikipedia_client import (  # noqa: F401  (re-exported for callers)
    fetch_summary as canonical_fetch_summary,
)
from scp.security.url_safety import safe_urlopen  # noqa: B310

logger = logging.getLogger("scp.why.sources.wikipedia")


# ---------------------------------------------------------------------------
# Circuit breaker + cache state (module-level — shared across all callers).
# ---------------------------------------------------------------------------
# Cache: target -> (cached_at_ts, pages_dict_or_None). 1h TTL.
_wiki_cache: dict[str, tuple[float, object]] = {}
_wiki_cache_ttl = 3600  # 1 hour

# Circuit breaker: opens after 5 consecutive failures, resets after 5 min.
_wiki_fail_count = 0
_wiki_circuit_open = False
_wiki_circuit_reset_time = 0.0
_WIKI_CB_THRESHOLD = 5
_WIKI_CB_RESET_SECS = 300  # 5 min


def _wiki_cache_key(target: str) -> str:
    """Stable cache key from target (question is parsed locally — not part of key)."""
    return hashlib.sha256(target.encode("utf-8")).hexdigest()[:16]


def _wiki_circuit_check() -> bool:
    """Return True if request may proceed (breaker closed or reset time elapsed)."""
    # [FALSE-POS-FIX] F824: removed `_wiki_circuit_reset_time` — read-only here
    # (only compared at L76). Assigned in _wiki_register_failure() which has its own global.
    # Kept _wiki_circuit_open (L78=) and _wiki_fail_count (L79=) — both assigned below.
    global _wiki_circuit_open, _wiki_fail_count
    if _wiki_circuit_open:
        if time.time() >= _wiki_circuit_reset_time:
            logger.info("[wikipedia] Circuit breaker RESET — retrying after cooldown")
            _wiki_circuit_open = False
            _wiki_fail_count = 0
            return True
        return False
    return True


def _wiki_register_failure(reason: str) -> None:
    """Increment failure counter; open circuit breaker if threshold reached."""
    global _wiki_fail_count, _wiki_circuit_open, _wiki_circuit_reset_time
    _wiki_fail_count += 1
    logger.warning(f"[wikipedia] failure #{_wiki_fail_count}: {reason}")
    if _wiki_fail_count >= _WIKI_CB_THRESHOLD and not _wiki_circuit_open:
        _wiki_circuit_open = True
        _wiki_circuit_reset_time = time.time() + _WIKI_CB_RESET_SECS
        logger.warning(
            f"[wikipedia] Circuit breaker OPENED after {_wiki_fail_count} failures "
            f"— will reset in {_WIKI_CB_RESET_SECS}s"
        )


def _wiki_register_success() -> None:
    """Reset failure counter on success (closes half-open breaker)."""
    global _wiki_fail_count, _wiki_circuit_open
    if _wiki_fail_count > 0 or _wiki_circuit_open:
        logger.debug("[wikipedia] Circuit breaker CLOSED — healthy again")
    _wiki_fail_count = 0
    _wiki_circuit_open = False


def _fetch_wikipedia_pages(target: str) -> dict | None:
    """Fetch Wikipedia pages dict with circuit breaker + retry + cache.

    Returns the `pages` dict from the API response, or None on failure.
    Caches both successes (with TTL) and None results (negative cache, short TTL
    to allow retry later).
    """
    cache_key = _wiki_cache_key(target)

    # 1) Cache check.
    if cache_key in _wiki_cache:
        cached_at, cached_pages = _wiki_cache[cache_key]
        age = time.time() - cached_at
        if age < _wiki_cache_ttl:
            logger.debug(f"[wikipedia] cache HIT (age={age:.0f}s) for target='{target}'")
            return cached_pages if cached_pages is not None else None  # negative cache
        # Stale — evict.
        del _wiki_cache[cache_key]

    # 2) Circuit breaker check.
    if not _wiki_circuit_check():
        logger.debug("[wikipedia] circuit OPEN — skipping request")
        return None

    # 3) Retry loop with exponential backoff.
    # [M12-FIX PF-5] Endpoint seam (same trust level as OPENAI_BASE_URL):
    # SCP_WHY_WIKIPEDIA_BASE redirects the API host (default unchanged:
    # https://en.wikipedia.org). When overridden, loopback/private targets are
    # explicitly allowed — an operator-set env IS the choice of endpoint; the
    # default path keeps SSRF protection (allow_internal=False).
    _base_override = _os.environ.get("SCP_WHY_WIKIPEDIA_BASE")
    _wiki_base = _base_override or "https://en.wikipedia.org"
    _allow_internal = bool(_base_override)
    url = None
    last_err: str | None = None
    for attempt in range(3):
        try:
            params = urllib.parse.urlencode({
                "action": "query",
                "titles": target[:50],
                "prop": "extracts",
                "exintro": "",
                "format": "json",
                "exchars": "500",
            })
            url = f"{_wiki_base}/w/api.php?{params}"
            req = urllib.request.Request(url, headers={  # noqa: S310
                "User-Agent": _os.environ.get(
                    "WIKIPEDIA_USER_AGENT",
                    "SCP-V3/1.0 (scp-research@example.com)",
                )
            })
            with safe_urlopen(req, timeout=10, allow_internal=_allow_internal) as resp:
                # safe_urlopen raises HTTPError for 4xx/5xx — a non-exception
                # response here is 2xx.
                status = getattr(resp, "status", None) or getattr(resp, "code", 200)
                if status == 429:
                    wait = 2 ** attempt
                    logger.warning(
                        f"[wikipedia] HTTP 429 rate-limited (attempt {attempt + 1}/3) "
                        f"— backing off {wait}s"
                    )
                    _wiki_register_failure(f"HTTP 429 on attempt {attempt + 1}")
                    if attempt < 2:
                        time.sleep(wait)
                        continue
                    return None
                if status != 200:
                    _wiki_register_failure(f"HTTP {status}")
                    return None
                raw = resp.read().decode("utf-8")
                data = _json.loads(raw)
                pages = data.get("query", {}).get("pages", {}) or {}
                # Success — reset fail count, cache result.
                _wiki_register_success()
                _wiki_cache[cache_key] = (time.time(), pages)
                return pages

        except urllib.error.HTTPError as he:
            # 429 may surface as HTTPError depending on urllib version.
            if he.code == 429:
                wait = 2 ** attempt
                retry_after = he.headers.get("Retry-After") if he.headers else None
                if retry_after:
                    try:
                        wait = max(wait, float(retry_after))
                    except (TypeError, ValueError) as _re:
                        logger.debug(f"[wikipedia] non-numeric Retry-After header: {retry_after!r} ({_re})")
                logger.warning(
                    f"[wikipedia] HTTPError 429 rate-limited (attempt {attempt + 1}/3) "
                    f"— backing off {wait}s"
                )
                _wiki_register_failure("HTTPError 429")
                if attempt < 2:
                    time.sleep(min(wait, 30))  # cap backoff at 30s
                    continue
                # Cache negative for shorter window (5 min) so we retry sooner.
                _wiki_cache[cache_key] = (time.time() - _wiki_cache_ttl + 300, None)
                return None
            # Other HTTP errors (404, 500, etc.) — register failure, no retry.
            _wiki_register_failure(f"HTTPError {he.code}: {he.reason}")
            last_err = f"HTTPError {he.code}"
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return None

        except (urllib.error.URLError, OSError) as ue:  # [FALSE-POS-FIX] B014: TimeoutError IS OSError in Python 3 — redundant
            # Transient network/timeout — retry with backoff.
            wait = 2 ** attempt
            logger.warning(
                f"[wikipedia] network error (attempt {attempt + 1}/3): {ue} — retry in {wait}s"
            )
            _wiki_register_failure(f"URLError: {ue}")
            last_err = str(ue)
            if attempt < 2:
                time.sleep(wait)
                continue
            return None

        except Exception as exc:
            # Parse error or unexpected — register failure.
            # failure is logged below, registered via _wiki_register_failure (source health) and surfaced via last_err.
            logger.debug("[wikipedia] unexpected failure during fetch: %s", exc, exc_info=True)
            _wiki_register_failure(f"unexpected: {exc}")
            last_err = f"unexpected: {exc}"
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return None

    # All retries exhausted.
    if last_err:
        logger.warning(f"[wikipedia] all 3 retries failed for target='{target}': {last_err}")
    # Negative cache (short TTL — 5 min) to avoid hammering on persistent failure.
    _wiki_cache[cache_key] = (time.time() - _wiki_cache_ttl + 300, None)
    return None


def query_wikipedia(target: str, question: str) -> str | None:
    """Query Wikipedia API for target (using action=query — more reliable than REST API).

    [FIX #22b] TẠI SAO: was returning the full Wikipedia extract (description text)
    which caused WHY engine to see "France, officially the French Republic..."
    vs LocalDB "Paris" -> CONFLICT. Fix: if question asks for capital/population/area,
    extract that specific value from Wikipedia's page props (pageimages + coordinates)
    or parse from extract. If can't extract, return None (don't return description).

    [Task 47-A] HTTP layer wrapped with circuit breaker + 3x retry + 429 backoff
    + 1h cache. Parsing logic unchanged.
    """
    pages = _fetch_wikipedia_pages(target)
    if not pages:
        return None

    try:
        for _pid, page in pages.items():
            extract = page.get("extract", "")
            if extract:
                clean = _re.sub(r'<[^>]+>', '', extract).strip()
                if not clean:
                    continue
                # [FIX #22b] If question asks for specific fact (capital/population/area),
                # try to extract it from the extract text. Otherwise return description.
                q_lower = question.lower() if question else ""
                if 'capital' in q_lower:
                    # Pattern: "capital is X", "capital city of X is Y"
                    cap_match = _re.search(
                        r'(?:capital(?:\s+city)?(?:\s+of\s+\w+)?\s+(?:is|:)\s+)([A-Z][a-zA-Z\s,]+?)(?:[.,;]|\s+is\s|\s+and\s)',
                        clean
                    )
                    if cap_match:
                        return cap_match.group(1).strip()
                    # If can't extract capital from text, return None
                    # (don't return description — causes CONFLICT with LocalDB)
                    return None
                elif 'population' in q_lower:
                    pop_match = _re.search(r'population\s+(?:of\s+)?(?:[^\d]*?)([\d,]+)', clean, _re.IGNORECASE)
                    if pop_match:
                        return pop_match.group(1).replace(',', '')
                    return None
                elif 'area' in q_lower:
                    area_match = _re.search(r'(?:area|size)\s+(?:of\s+)?(?:[^\d]*?)([\d,]+(?:\.\d+)?)\s*(?:km|square)', clean, _re.IGNORECASE)
                    if area_match:
                        return area_match.group(1).replace(',', '')
                    return None
                # No specific fact requested — return description
                return clean[:200]
        return None
    except Exception as e:  # [RC-7 FIX Task 6-B] silent swallow → log context
        logger.warning(f"[why_sources.wikipedia] parse failed for target='{target}': {e}", exc_info=True)
        return None
