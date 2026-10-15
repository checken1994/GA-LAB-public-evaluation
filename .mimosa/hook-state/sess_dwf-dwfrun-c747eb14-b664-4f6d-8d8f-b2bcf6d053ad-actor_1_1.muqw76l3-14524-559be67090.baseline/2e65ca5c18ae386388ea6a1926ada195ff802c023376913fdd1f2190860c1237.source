"""[S6b security sweep · 2026-09-11] Egress guard wrapper for tools/*.py.

Every outbound HTTP call in the batch/probe tools goes through one of these
wrappers. Enforcement (the proven ``scp.security.url_safety`` stack):

  1. ``validate_url`` — scheme allowlist (http/https), hostname required,
     resolved-IP boundary (DNS → private/loopback/link-local/metadata blocked
     unless ``allow_internal=True`` for operator-configured endpoints).
  2. ``safe_urlopen`` — the validated fetch driver (urllib), the same sink the
     rest of SCP uses. The raw ``requests.*`` sink tokens do not appear in
     this module at all.

``allow_internal`` semantics (forwarded to validate_url):
  True  — the target is an operator-configured endpoint (SCP backend,
          Ollama, self-hosted LLM proxy): loopback/RFC1918 allowed.
  False — the target URL comes from untrusted data (Bing results, scraped
          corpus URLs): private/loopback/link-local IPs are blocked.

Compatibility: the wrappers accept the kwargs the tools already pass
(params/json/headers/timeout/allow_redirects) and return a requests-like
response object (status_code / text / json() / raise_for_status() /
case-insensitive headers.get). Behavior notes vs the old direct requests
calls: timeouts may be a (connect, read) tuple — mapped to a single total
budget; redirects are followed (urllib default), matching requests'
allow_redirects=True; responses are read fully then decoded as UTF-8.
"""
from __future__ import annotations

import json as _json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scp.security.url_safety import safe_urlopen, validate_url  # noqa: E402


class HTTPStatusError(RuntimeError):
    """requests-style raise_for_status() signal (>=400)."""


class GuardedResponse:
    """Minimal requests-like view over a urllib response (read fully)."""

    def __init__(self, resp: Any) -> None:
        # urllib.error.HTTPError (4xx/5xx) carries .code; normal responses
        # carry .status / getcode(). requests returns the response object on
        # 4xx/5xx instead of raising, so HTTPError is wrapped here too and
        # raise_for_status() restores the requests-style signal.
        status = (
            getattr(resp, "status", None)
            or getattr(resp, "code", None)
            or resp.getcode()
        )
        self.status_code = int(status)
        self.headers = {
            str(k).lower(): str(v) for k, v in resp.headers.items()
        }
        self._bytes = resp.read()

    @property
    def text(self) -> str:
        return self._bytes.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return _json.loads(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPStatusError(f"HTTP {self.status_code}: {self.text[:200]}")


def _normalize_timeout(timeout: Any) -> float:
    # requests accepts (connect, read) tuples; urllib takes one scalar.
    if isinstance(timeout, (tuple, list)):
        return float(sum(float(t) for t in timeout))
    return float(timeout if timeout is not None else 30)


def _finish_url(url: str, params: Any) -> str:
    if params:
        return f"{url}?{urllib.parse.urlencode(params)}"
    return url


def _decode_guard_kwargs(kwargs: dict[str, Any]) -> tuple[dict[str, str], float]:
    """Pop the requests-style kwargs the tools pass; return (headers, timeout)."""
    headers = dict(kwargs.pop("headers", None) or {})
    timeout = _normalize_timeout(kwargs.pop("timeout", 30))
    kwargs.pop("allow_redirects", None)  # urllib follows redirects by default
    if kwargs:
        raise ValueError(f"unsupported egress kwargs: {sorted(kwargs)}")
    return headers, timeout


def _guarded_open(req: urllib.request.Request, *, timeout: float, allow_internal: bool) -> GuardedResponse:
    """Run safe_urlopen; wrap 4xx/5xx HTTPError into a GuardedResponse so the
    requests-style contract (response returned, raise_for_status() signals
    failure) is preserved. URL/hosts errors still raise ValueError."""
    try:
        with safe_urlopen(req, timeout=timeout, allow_internal=allow_internal) as resp:
            return GuardedResponse(resp)
    except urllib.error.HTTPError as exc:  # 4xx/5xx — requests-like contract
        return GuardedResponse(exc)


def safe_get(url: str, *, allow_internal: bool, **kwargs: Any) -> GuardedResponse:
    """Boundary-checked GET (params= encoded into the query string)."""
    params = kwargs.pop("params", None)
    full_url = _finish_url(url, params)
    headers, timeout = _decode_guard_kwargs(kwargs)
    validate_url(full_url, allow_internal=allow_internal)
    req = urllib.request.Request(full_url, headers=headers)
    return _guarded_open(req, timeout=timeout, allow_internal=allow_internal)


def safe_post(url: str, *, allow_internal: bool, **kwargs: Any) -> GuardedResponse:
    """Boundary-checked POST (json= encoded as the UTF-8 body)."""
    params = kwargs.pop("params", None)
    url = _finish_url(url, params)
    body: bytes | None = None
    if "json" in kwargs:
        payload = kwargs.pop("json")
        body = _json.dumps(payload).encode("utf-8")
    if "data" in kwargs:
        raw = kwargs.pop("data")
        body = raw if isinstance(raw, bytes) else str(raw).encode("utf-8")
    headers, timeout = _decode_guard_kwargs(kwargs)
    if body is not None and "content-type" not in {k.lower() for k in headers}:
        headers.setdefault("Content-Type", "application/json")
    validate_url(url, allow_internal=allow_internal)
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    return _guarded_open(req, timeout=timeout, allow_internal=allow_internal)


def safe_request(method: str, url: str, *, allow_internal: bool, **kwargs: Any) -> GuardedResponse:
    """Boundary-checked arbitrary-method request."""
    method = str(method).upper()
    if method == "GET":
        return safe_get(url, allow_internal=allow_internal, **kwargs)
    if method == "POST":
        return safe_post(url, allow_internal=allow_internal, **kwargs)
    params = kwargs.pop("params", None)
    url = _finish_url(url, params)
    body: bytes | None = None
    if "json" in kwargs:
        payload = kwargs.pop("json")
        body = _json.dumps(payload).encode("utf-8")
    headers, timeout = _decode_guard_kwargs(kwargs)
    if body is not None and "content-type" not in {k.lower() for k in headers}:
        headers.setdefault("Content-Type", "application/json")
    validate_url(url, allow_internal=allow_internal)
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    return _guarded_open(req, timeout=timeout, allow_internal=allow_internal)
