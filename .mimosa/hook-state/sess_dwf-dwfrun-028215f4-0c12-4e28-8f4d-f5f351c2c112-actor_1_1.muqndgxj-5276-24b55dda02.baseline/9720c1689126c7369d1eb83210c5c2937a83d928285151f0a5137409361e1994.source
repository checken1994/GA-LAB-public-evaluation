"""
URL Safety Helper — B310 fix.

Validates URL scheme + blocks internal/private IPs before calling urllib.urlopen.
Use this instead of urllib.request.urlopen() to satisfy B310 (CWE-22).  # nosec B310 — URL validated by SCP

[EE egress enforcement — closes M13 G1]
This module is the single EGRESS CHOKE POINT for outbound HTTP fetches.
`enforce_egress_policy` reads SCP_EGRESS_MODE and fails closed:
  - deny/offline/disabled  → only loopback hosts (self-probe/internal services)
  - allowlist              → only loopback + hosts in SCP_EGRESS_ALLOWLIST
  - unset                  → no new restriction (historical dev behavior)
  - unknown value          → dev: no new restriction; production
                             (SCP_PRODUCTION_MODE) → deny (fail-closed)
`safe_urlopen` enforces it before the SSRF validation. The two other
canonical fetchers (`scp.core.url_fetcher._safe_fetch_url` and
`scp.core.api_utils.fetch_with_retry`) call the same idempotent gate.
Do NOT add a new raw HTTP call-site — the static regression gate in
tests/T03_capability/test_egress_enforcement.py fails on raw
urllib/requests/httpx calls outside the gated modules.
"""
from __future__ import annotations

import http.client
import ipaddress
import logging
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from functools import partial
from typing import Any

logger = logging.getLogger(__name__)

# Allowed URL schemes for outbound HTTP requests
ALLOWED_SCHEMES = frozenset({"http", "https"})

# [EE] Egress modes — mirror scp/llm_gateway/egress_policy.py _DENY_MODES so
# gateway and generic fetchers share one vocabulary. Deviation from the
# gateway: an UNKNOWN mode is only fail-closed here when production mode is
# explicitly declared (task contract: dev behavior must not be tightened).
_EGRESS_DENY_MODES = frozenset({"deny", "offline", "disabled"})
_EGRESS_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})  # mirrors production_guard._TRUE


from scp.policy.egress import (
    EgressDeniedError,
    EgressPolicy,
)


def _normalize_egress_host(hostname: str | None) -> str:
    """Lower-case, strip brackets/port remnants and trailing root dot."""
    return (hostname or "").strip().strip("[]").lower().rstrip(".")


def _is_loopback_host(hostname: str | None) -> bool:
    """True only for literal loopback: name in the loopback set or an IP
    literal whose ipaddress.is_loopback is True (covers 127.1, [::1] and
    integer spellings). Hostnames are intentionally NOT DNS-resolved here —
    resolution-based SSRF blocking stays in validate_url/_is_private_ip."""
    host = _normalize_egress_host(hostname)
    if not host:
        return False
    if host in _EGRESS_LOOPBACK_HOSTS:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _egress_allowlist_hosts() -> frozenset[str]:
    raw = os.environ.get("SCP_EGRESS_ALLOWLIST", "")
    return frozenset(
        _normalize_egress_host(item) for item in raw.split(",") if item.strip()
    )


def _production_mode_declared() -> bool:
    return os.environ.get("SCP_PRODUCTION_MODE", "0").strip().lower() in _TRUE_VALUES


def enforce_egress_policy(
    url: str | urllib.request.Request,
    extra_allowed_hosts: frozenset[str] | set[str] | None = None,
) -> None:
    """Fail-closed egress gate delegating to unified EgressPolicy."""
    url_str = url.full_url if isinstance(url, urllib.request.Request) else str(url)
    try:
        parsed = urllib.parse.urlparse(url_str)
    except Exception:
        logger.debug("enforce_egress_policy: unparseable URL rejected: %r", url_str, exc_info=True)
        raise EgressDeniedError(url_str, "unparseable URL", url=url_str) from None
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        return  # not an HTTP(S) egress decision; validate_url rejects the scheme

    policy = EgressPolicy()
    policy.enforce(url_str, token_allowed_hosts=extra_allowed_hosts)


def egress_host_allowed(url: str) -> bool:
    """[EGRESS-DEGRADE 2026-09-26] Non-raising egress probe for OPTIONAL
    external sources (openlibrary/wikidata cross-verification).

    True  → chính sách egress hiện hành cho phép fetch ``url``.
    False → bị từ chối (EgressDeniedError): caller phải degrade nguồn sang
            cache-only (không attempt fetch, không WARNING mỗi ask).
    Any other error → True: hàm này KHÔNG MỞ CỔNG — gate fail-closed thật
    vẫn nằm ở enforce_egress_policy tại điểm fetch; kết quả dự phòng chỉ
    quyết định việc degrade trước, không quyết định việc cho phép I/O.
    """
    try:
        enforce_egress_policy(url)
        return True
    except EgressDeniedError:
        return False
    except Exception as _probe_err:
        logger.debug("egress_host_allowed probe error (degrade-only, fail-closed gate lives at fetch): %s", _probe_err, exc_info=True)
        return True

# Disallowed IP ranges (RFC1918 + loopback + link-local + multicast + reserved)
def _is_private_ip(host: str) -> bool:
    """Return True if host resolves to / is a private or loopback IP."""
    if not host:
        return True
    # Strip port
    if ":" in host and not host.startswith("["):
        host = host.rsplit(":", 1)[0]
    host = host.strip("[]")
    try:
        # Already an IP literal?
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
        except ValueError:
            # [LOG-NOISE-FIX 2026-09-26] A plain hostname (e.g.
            # 'raw.githubusercontent.com') is NOT an IP literal — that parse
            # failure is the EXPECTED path here and execution falls through to
            # DNS resolution below. It used to be logged as a WARNING
            # ("Silent except: 'host' does not appear to be an IPv4 or IPv6
            # address"), mislabeling every hostname validation as an error.
            # Debug level + accurate message; classification unchanged.
            logger.debug("not an IP literal, resolving hostname: %s", host)
        # Resolve hostname
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            logger.debug('_is_private_ip: socket.gaierror ignored', exc_info=True)
            return True  # unresolvable = treat as unsafe
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return True
        return False
    except Exception:
        logger.warning('_is_private_ip: Exception not handled', exc_info=True)
        return True


def validate_url(url: str, *, allow_internal: bool = False) -> urllib.parse.ParseResult:
    """Validate URL scheme + (optionally) internal IP. Raises ValueError on disallowed."""
    if not isinstance(url, str) or not url:
        raise ValueError("URL must be a non-empty string")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"URL scheme '{parsed.scheme}' not in allowlist {sorted(ALLOWED_SCHEMES)}")
    if not parsed.hostname:
        raise ValueError("URL missing hostname")
    if not allow_internal and _is_private_ip(parsed.hostname):
        raise ValueError(f"URL host '{parsed.hostname}' resolves to internal/private IP — blocked")
    return parsed


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """HTTP connection that uses a previously validated destination IP."""

    def __init__(self, host, *args, resolved_ip: str, **kwargs):
        super().__init__(host, *args, **kwargs)
        self._resolved_ip = resolved_ip

    def connect(self):
        self.sock = self._create_connection(
            (self._resolved_ip, self.port), self.timeout, self.source_address
        )
        try:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError as exc:
            if exc.errno != getattr(socket, "ENOPROTOOPT", 92):
                raise
        if self._tunnel_host:
            self._tunnel()


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection pinned to a validated IP while retaining hostname SNI."""

    def __init__(self, host, *args, resolved_ip: str, **kwargs):
        super().__init__(host, *args, **kwargs)
        self._resolved_ip = resolved_ip

    def connect(self):
        _PinnedHTTPConnection.connect(self)
        server_hostname = self._tunnel_host or self.host
        self.sock = self._context.wrap_socket(
            self.sock, server_hostname=server_hostname
        )


class _PinnedHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, resolved_ip: str):
        super().__init__()
        self._resolved_ip = resolved_ip

    def http_open(self, req):
        return self.do_open(
            partial(_PinnedHTTPConnection, resolved_ip=self._resolved_ip), req
        )


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, resolved_ip: str):
        super().__init__()
        self._resolved_ip = resolved_ip

    def https_open(self, req):
        return self.do_open(
            partial(_PinnedHTTPSConnection, resolved_ip=self._resolved_ip),
            req,
            context=self._context,
        )


class _SafeHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Intercept HTTP 301/302/303/307/308 redirects and enforce egress policy and URL safety."""

    def __init__(
        self,
        *,
        allow_internal: bool = False,
        extra_allowed_hosts: frozenset[str] | set[str] | None = None,
    ) -> None:
        super().__init__()
        self.allow_internal = allow_internal
        self.extra_allowed_hosts = extra_allowed_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        full_new_url = urllib.parse.urljoin(req.full_url, newurl)
        enforce_egress_policy(full_new_url, extra_allowed_hosts=self.extra_allowed_hosts)
        validate_url(full_new_url, allow_internal=self.allow_internal)
        return super().redirect_request(req, fp, code, msg, headers, full_new_url)

    def http_error_302(self, req, fp, code, msg, headers):
        if "location" in headers:
            newurl = headers["location"]
        elif "uri" in headers:
            newurl = headers["uri"]
        else:
            return None

        full_new_url = urllib.parse.urljoin(req.full_url, newurl)
        enforce_egress_policy(full_new_url, extra_allowed_hosts=self.extra_allowed_hosts)
        validate_url(full_new_url, allow_internal=self.allow_internal)

        new = self.redirect_request(req, fp, code, msg, headers, full_new_url)
        if new is None:
            return None

        # Loop detection
        if hasattr(req, "redirect_dict"):
            visited = new.redirect_dict = req.redirect_dict
            if visited.get(full_new_url, 0) >= self.max_repeats or len(visited) >= self.max_redirections:
                raise urllib.error.HTTPError(
                    req.full_url, code, self.inf_msg + msg, headers, fp
                )
        else:
            visited = new.redirect_dict = req.redirect_dict = {}
        visited[full_new_url] = visited.get(full_new_url, 0) + 1

        fp.read()
        fp.close()

        timeout = getattr(req, "timeout", 30)
        return safe_urlopen(
            new,
            timeout=timeout,
            allow_internal=self.allow_internal,
            extra_allowed_hosts=self.extra_allowed_hosts,
        )

    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302


def safe_urlopen(url: str | urllib.request.Request, *, timeout: float = 30, allow_internal: bool = False, **kwargs: Any):
    """Drop-in replacement for urllib.request.urlopen() that enforces B310 safety and pinned IP.

    Args:
        url: URL string or Request object.
        timeout: Request timeout.
        allow_internal: Set True to allow internal/private IPs (e.g. for Ollama at 127.0.0.1).
        **kwargs: Forwarded to urllib.request.urlopen.

    Returns:
        HTTP response object (same as urllib.request.urlopen).
    """
    extra_allowed = kwargs.pop("extra_allowed_hosts", None)
    if isinstance(url, urllib.request.Request):
        url_str = url.full_url
    else:
        url_str = str(url)
    # [EE] Egress gate FIRST: deterministic EgressDeniedError (a ValueError)
    # under explicit SCP_EGRESS_MODE, before any DNS resolution/SSRF check.
    enforce_egress_policy(url, extra_allowed_hosts=extra_allowed)
    parsed = validate_url(url_str, allow_internal=allow_internal)

    host = (parsed.hostname or "").strip().strip("[]")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # Pin to validated destination IP to eliminate TOCTOU DNS window
    try:
        ip_obj = ipaddress.ip_address(host)
        resolved_ip = str(ip_obj)
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise ValueError(f"URL host '{host}' could not be resolved: {exc}") from exc

        resolved_ip = None
        for info in infos:
            candidate_ip = info[4][0]
            ip_cand_obj = ipaddress.ip_address(candidate_ip)
            if not allow_internal and (
                ip_cand_obj.is_private
                or ip_cand_obj.is_loopback
                or ip_cand_obj.is_link_local
                or ip_cand_obj.is_reserved
                or ip_cand_obj.is_multicast
            ):
                continue
            resolved_ip = candidate_ip
            break

        if not resolved_ip:
            raise ValueError(f"URL host '{host}' resolves to internal/private IP — blocked")

    context = kwargs.pop("context", None)
    scheme = (parsed.scheme or "").lower()
    if scheme == "https":
        handler = _PinnedHTTPSHandler(resolved_ip)
        if context is not None:
            handler._context = context
    else:
        handler = _PinnedHTTPHandler(resolved_ip)

    redirect_handler = _SafeHTTPRedirectHandler(
        allow_internal=allow_internal,
        extra_allowed_hosts=extra_allowed,
    )
    opener = urllib.request.build_opener(handler, redirect_handler)
    return opener.open(url, timeout=timeout, **kwargs)
