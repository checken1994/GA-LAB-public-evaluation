"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
SCP V14 — API Utilities
APICache + fetch_with_retry (V29: tích hợp CircuitBreaker).

[Fix 4-a-005 / Phase 3-A — DNA #5, #14, #19]
`fetch_with_retry` is now a THIN WRAPPER around the canonical
`_safe_fetch_url` in `scp.core.url_fetcher`. Previously it had its OWN
urllib.request.urlopen implementation with only a scheme check, NO IP
allowlist, NO redirect policy (urllib follows 30x by default), NO size
cap — divergent from `helpers._safe_fetch_url` which had all those
defenses. ONE safety impl now; this file only adds circuit-breaker +
retry + JSON-parse logic on top.
"""
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger("scp.api_utils")


# ============================================================
#  URL SECRET REDACTION — [AUDIT-FIX med-1]
#  TẠI SAO: nhiều API (NASA, USDA, ...) nhận API key qua query string
#  (?api_key=...). Bất kỳ log/exception message nào chứa URL đầy đủ sẽ
#  leak key vào WARNING/ERROR logs. Mọi điểm log/raise URL phải đi qua
#  redact_query_secrets(). Host + path được GIỮ NGUYÊN để còn debug;
#  chỉ giá trị của query param nhạy cảm bị thay bằng [REDACTED].
#  Fail-closed: nếu URL không parse được, toàn bộ query bị loại bỏ.
# ============================================================
_REDACTED_MARKER = "[REDACTED]"

_SECRET_PARAM_EXACT = frozenset({
    "key", "api_key", "apikey", "access_key", "accesskey", "app_key",
    "appkey", "auth_key", "authorization", "token", "access_token",
    "auth_token", "id_token", "secret", "client_secret", "password",
    "passwd", "pwd", "passphrase", "credential", "credentials",
    "sig", "signature", "session_key",
    # [REDACT-AUTHSESSIONKEY-FIX] wikiart.py passes its API key under the
    # camelCase param 'authSessionKey' — normalized lowercase it does not end
    # with any secret suffix, so it survived redaction into WARNING/ERROR logs.
    "authsessionkey",
})

_SECRET_PARAM_SUFFIXES = (
    "_key", "key_", "_token", "token_", "_secret", "secret_",
    "_password", "password_", "_credential", "_signature",
)


def _is_secret_query_param(name: str) -> bool:
    """True nếu query param ``name`` có khả năng chứa secret."""
    normalized = re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")
    if not normalized:
        return False
    if normalized in _SECRET_PARAM_EXACT:
        return True
    return normalized.startswith(_SECRET_PARAM_SUFFIXES) or normalized.endswith(_SECRET_PARAM_SUFFIXES)


def redact_query_secrets(url: str) -> str:
    """Trả về bản sao của ``url`` với giá trị các query param nhạy cảm
    (api_key/key/token/access_key/secret/...) và thông tin xác thực authority
    (username:password@) được thay bằng ``[REDACTED]``.

    Dùng cho MỌI log/exception message có thể chứa URL đầy đủ. Không bao giờ
    raise — với input lạ nó fail-closed (drop query/auth) thay vì leak.
    """
    if not isinstance(url, str) or not url.strip():
        return "" if not isinstance(url, str) else url
    try:
        parts = urllib.parse.urlsplit(url)
        new_netloc = parts.netloc
        if "@" in parts.netloc:
            userinfo, _, host_port = parts.netloc.rpartition("@")
            if ":" in userinfo:
                redacted_userinfo = f"{_REDACTED_MARKER}:{_REDACTED_MARKER}"
            else:
                redacted_userinfo = _REDACTED_MARKER
            new_netloc = f"{redacted_userinfo}@{host_port}"

        query = parts.query
        redacted_query = query
        if query and "=" in query:
            def _redact_pair(match: "re.Match[str]") -> str:
                name = match.group(1)
                if _is_secret_query_param(name):
                    return f"{name}={_REDACTED_MARKER}"
                return match.group(0)

            redacted_query = re.sub(r"([^&=]+)=([^&]*)", _redact_pair, query)

        if new_netloc == parts.netloc and redacted_query == query:
            return url
        return urllib.parse.urlunsplit(parts._replace(netloc=new_netloc, query=redacted_query))
    except Exception:
        logger.debug("redact_query_secrets ignored", exc_info=True)
        # Fail-closed: không parse được → loại bỏ toàn bộ query + fragment + userinfo.
        try:
            parts = urllib.parse.urlsplit(url)
            safe_netloc = parts.hostname or ""
            return urllib.parse.urlunsplit(parts._replace(netloc=safe_netloc, query="", fragment=""))
        except Exception:
            logger.debug("redact_query_secrets ignored", exc_info=True)
            return "[REDACTED-URL]"

class APICache:
    def __init__(self, ttl=300):
        self.cache: dict[str, tuple[float, Any]] = {}
        self.ttl = ttl

    def _key(self, url_template, entity):
        if isinstance(entity, (list, tuple)):
            entity_str = "|".join(str(e) for e in entity)
        else:
            entity_str = str(entity)
        return f"{url_template}::{entity_str}"

    def get(self, url_template, entity):
        key = self._key(url_template, entity)
        if key in self.cache:
            ts, val = self.cache[key]
            if time.time() - ts < self.ttl:
                return val
            del self.cache[key]
        return None

    def set(self, url_template, entity, value):
        key = self._key(url_template, entity)
        self.cache[key] = (time.time(), value)
        if len(self.cache) > 10000:
            items = sorted(self.cache.items(), key=lambda x: x[1][0])
            for i in range(len(self.cache) // 5):
                del self.cache[items[i][0]]

    def clear(self):
        self.cache.clear()

    def stats(self):
        return {"cache_size": len(self.cache), "ttl_seconds": self.ttl}


# ============================================================
#  CIRCUIT BREAKER REGISTRY — auto-detect API by URL
# ============================================================
def _detect_breaker(url: str):
    """Detect appropriate circuit breaker dựa trên URL."""
    try:
        from scp.core.circuit_breaker import (
            CircuitBreakerRegistry,
            get_coingecko_breaker,
            get_frankfurter_breaker,
            get_openmeteo_breaker,
            get_pubchem_breaker,
            get_restcountries_breaker,
            get_wikipedia_breaker,
        )
        url_lower = url.lower()
        if 'pubchem.ncbi.nlm.nih.gov' in url_lower:
            return get_pubchem_breaker()
        if 'coingecko.com' in url_lower:
            return get_coingecko_breaker()
        if 'frankfurter.app' in url_lower:
            return get_frankfurter_breaker()
        if 'open-meteo.com' in url_lower:
            return get_openmeteo_breaker()
        if 'wikipedia.org' in url_lower:
            return get_wikipedia_breaker()
        if 'restcountries.com' in url_lower:
            return get_restcountries_breaker()
        # Generic breaker cho APIs khác
        if 'api.' in url_lower or 'http' in url_lower:
            # Use domain as breaker name
            from urllib.parse import urlparse
            domain = urlparse(url).netloc or "unknown"
            return CircuitBreakerRegistry().get(domain, fail_threshold=5, cooldown_sec=60)
        return None
    except Exception as e:
        logger.debug(f"Breaker detect error: {e}", exc_info=True)
        return None


# [Fix 4-a-005 / Phase 3-A] `_validate_url_safe` was the INCOMPLETE safety
# check (scheme-only, no IP allowlist, no redirect policy). It has been
# REMOVED — the canonical safety check now lives inside
# `scp.core.url_fetcher._safe_fetch_url` (scheme + IP allowlist + redirect
# re-validation + size cap + no-proxy opener). `fetch_with_retry` delegates
# ALL HTTP I/O to `_safe_fetch_url`. Do NOT re-add a local validator — that
# would re-introduce the divergent-implementation anti-pattern (DNA #5/#14).


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((urllib.error.URLError, ConnectionError, TimeoutError)),
    reraise=False
)
def fetch_with_retry(url, headers=None, timeout=10, max_retries=3):
    # --- SCP V3 ENTERPRISE: TENACITY RETRY & CIRCUIT BREAKER ---
    from scp.core.url_fetcher import FetchBlockedError, _safe_fetch_url
    from scp.policy.egress import EgressDeniedError
    from scp.security.url_safety import enforce_egress_policy

    try:
        # [EE] Egress gate FIRST (idempotent — also enforced inside
        # _safe_fetch_url). EgressDeniedError is a ValueError, so the
        # "policy violation → no retry, return None" contract below holds.
        enforce_egress_policy(url)
        raw_bytes = _safe_fetch_url(url)
        return json.loads(raw_bytes.decode("utf-8"))
    except EgressDeniedError as e:
        # [LOG-LABEL-404 2026-09-26] Egress policy rejection — the ONLY class
        # that may be labeled a policy violation here. Previously EVERY
        # ValueError (including plain "HTTP error: 404" fetch failures) was
        # logged as "Policy violation fetching ...", mislabeling ordinary
        # HTTP 404s as security events. Contract unchanged: no retry, None.
        # [AUDIT-FIX med-1] URL/message qua redact_query_secrets.
        logger.warning(
            "Policy violation (egress denied) fetching %s: %s",
            redact_query_secrets(url), redact_query_secrets(str(e)),
        )
        return None
    except FetchBlockedError as e:
        # Security rejection raised by _safe_fetch_url BEFORE any network I/O
        # (scheme not allowed, disallowed/private IP, blocked redirect target).
        logger.warning(
            "Policy violation fetching %s: %s",
            redact_query_secrets(url), redact_query_secrets(str(e)),
        )
        return None
    except json.JSONDecodeError as e:
        # NOTE: must precede `except ValueError` — JSONDecodeError IS a
        # ValueError subclass and keeps its own accurate label.
        logger.warning("JSON decode failed for %s: %s", redact_query_secrets(url), e)
        return None
    except ValueError as e:
        # [LOG-LABEL-404 2026-09-26] Non-policy fetch failure. _safe_fetch_url
        # converts urllib HTTPError into ValueError("HTTP error: <code>") —
        # surface the real status with its own label instead of pretending it
        # is a policy violation.
        _status_match = re.search(r"HTTP error:\s*(\d{3})", str(e))
        if _status_match:
            logger.warning(
                "http_error status=%s fetching %s: %s",
                _status_match.group(1), redact_query_secrets(url), redact_query_secrets(str(e)),
            )
        else:
            logger.warning(
                "fetch_failed fetching %s: %s",
                redact_query_secrets(url), redact_query_secrets(str(e)),
            )
        return None
    except Exception as e:
        logger.error("Transient error fetching %s: %s", redact_query_secrets(url), e)
        raise  # Reraise to trigger Tenacity retry
