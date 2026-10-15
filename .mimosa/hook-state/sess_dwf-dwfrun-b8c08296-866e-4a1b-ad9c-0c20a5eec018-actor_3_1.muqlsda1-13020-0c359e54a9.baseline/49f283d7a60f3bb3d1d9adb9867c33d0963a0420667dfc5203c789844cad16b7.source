"""SCP canonical SSRF/LFI-safe URL fetcher.

[Fix 4-a-005 / Phase 3-A — DNA #5, #14, #19]
TẠI SAO this module exists:
  Before this fix, TWO divergent URL fetchers lived in the codebase:
    1. `scp.api_server_parts.helpers._safe_fetch_url` — had full SSRF defenses
       (scheme allowlist + IP/private-range check + safe-redirect handler +
       size cap + no-proxy opener). Used by /ask image_url/voice_url and
       /v104 image/voice check endpoints.
    2. `scp.core.api_utils.fetch_with_retry` — used urllib.request.urlopen
       directly with only a scheme check (`_validate_url_safe`), NO IP check,
       NO redirect policy (urllib follows 30x by default), NO size cap. Used
       by cross_verify, multi_source_verifier, crypto_verifier, predictive,
       weather/geo/numeric SLMs, etc.

  DNA #5 (ảo giác đồng thuận): scanners saw `_validate_url_safe` and assumed
  safety, missing the gap. DNA #14 (đồng thuận ≠ đúng): both fetchers were
  named "safe" but only one was. DNA #19 (tầng kiểm toán bằng chứng): no
  reality test enforced that any new fetcher must use the canonical defenses.

  Fix: ONE canonical implementation lives HERE. `helpers.py` and
  `api_utils.py` BOTH delegate to this module. If you need to add a fetcher,
  extend `_safe_fetch_url` here — do not create a third impl.

Defenses (kept identical to the previous `helpers._safe_fetch_url` so no
behavior regression on the safe path):
  1. scheme must be exactly http/https (rejects file://, ftp://, gopher://,
     data:, javascript:, etc.).
  2. hostname must NOT resolve to private / loopback / link-local / reserved /
     multicast / unspecified IP. Checked across ALL getaddrinfo results to
     mitigate DNS rebinding.
  3. strict User-Agent (`_SCP_SAFE_FETCH_UA`).
  4. [AUDIT-3 FIX] redirect following: ≤5 hops, each hop re-validated against
     `_is_disallowed_ip` (prevents SSRF via 302 → http://169.254.169.254/...).
  5. max_bytes cap via streaming read + early abort (no unbounded resp.read()).
  6. per-request timeout (default 8s).
  7. proxy disabled (prevents SSRF bypass via HTTP_PROXY env var).

On any policy violation or fetch error, raises ValueError; policy violations
before any network I/O raise the subclass FetchBlockedError. Callers should
catch ValueError and treat as a blocked fetch (NOT a server failure); callers
that must terminate the request on a security rejection catch
FetchBlockedError explicitly.
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

from scp.security.url_safety import enforce_egress_policy

logger = logging.getLogger("scp.core.url_fetcher")

# [SCP-A07 FIX 2026-09-25] Policy rejection vs genuine fetch failure.
# TẠI SAO: _safe_fetch_url previously raised a bare ValueError for BOTH
# security rejections (scheme, disallowed/loopback IP, egress policy) AND
# genuine connectivity failures (DNS, refused, HTTP 4xx/5xx). Callers could
# not distinguish them, and the /ask media path treated a loopback SSRF
# rejection as a benign "local target unreachable" degradation — the request
# continued instead of being rejected (fail-open for exactly the loopback
# SSRF class; acceptance SCP-A07 requires HTTP 400 + task FAILED).
# FetchBlockedError marks rejections that happened BEFORE any network I/O by
# a security policy. It subclasses ValueError so every existing
# `except ValueError` caller keeps working unchanged; only callers that must
# couple rejection to termination (the /ask media boundary) catch the
# subclass explicitly.
class FetchBlockedError(ValueError):
    """Fetch blocked by security policy before any network I/O."""


# [SCP-DNA-FIX R5-1] Single canonical User-Agent for the safe fetcher.
# Was previously duplicated in api_server.py:73 AND helpers.py:36 — two
# definitions, same value, but the duplication was the seed of the
# "two impls" anti-pattern (DNA #5). Now defined ONCE here.
_SCP_SAFE_FETCH_UA = "SCP-V104/1.0 (security-safe-fetch)"


def _is_disallowed_ip(ip) -> bool:
    """True if IP is private/loopback/link-local/multicast/reserved/unspecified.

    Covers: 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16,
    169.254.0.0/16 (link-local incl. AWS/GCP/Azure metadata 169.254.169.254),
    ::1, fc00::/7 (unique-local), fe80::/10 (link-local), 0.0.0.0, ::.
    """
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_public_ips(hostname: str) -> tuple[str, ...]:
    """Resolve and validate every address, returning IPs for pinned connects."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed: {exc}") from exc
    if not infos:
        raise ValueError("no DNS records")
    safe_ips: list[str] = []
    for _family, _stype, _proto, _canon, sockaddr in infos:
        if not sockaddr or not sockaddr[0]:
            continue
        ip_str = sockaddr[0]
        if "%" in ip_str:
            ip_str = ip_str.split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError(f"unparseable IP: {ip_str}") from None
        if _is_disallowed_ip(ip):
            # [SCP-A07 FIX] Policy rejection — loopback/private/link-local/
            # metadata targets are blocked BEFORE any connection attempt.
            raise FetchBlockedError("host resolves to disallowed IP range")
        if ip_str not in safe_ips:
            safe_ips.append(ip_str)
    if not safe_ips:
        raise ValueError("no usable DNS records")
    return tuple(safe_ips)


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
        from functools import partial
        return self.do_open(
            partial(_PinnedHTTPConnection, resolved_ip=self._resolved_ip), req
        )


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, resolved_ip: str):
        super().__init__()
        self._resolved_ip = resolved_ip

    def https_open(self, req):
        from functools import partial
        return self.do_open(
            partial(_PinnedHTTPSConnection, resolved_ip=self._resolved_ip),
            req,
            context=self._context,
        )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Return redirect responses to the caller for per-hop pinned handling."""

    def http_error_301(self, req, fp, code, msg, headers):
        return fp

    http_error_302 = http_error_301
    http_error_303 = http_error_301
    http_error_307 = http_error_301
    http_error_308 = http_error_301


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow HTTP 3xx redirects safely — ≤5 hops, each hop re-validates IP.

    [AUDIT-3 FIX] TẠI SAO: the old _NoRedirectHandler rejected ALL redirects,
    breaking legitimate image CDNs (Imgur, S3 presigned URLs, Bit.ly, Google
    Photos — all use 302/301 redirects). But blindly following redirects is an
    SSRF vector (attacker sets up external URL that 302→169.254.169.254).
    Root-cause fix: follow ≤5 redirects, but re-validate the target URL
    against _is_disallowed_ip BEFORE following. If the redirect target is to
    a private/internal/metadata IP, raise ValueError (block the redirect).
    """

    # Limit redirect hops (urllib default is 30, far too many)
    max_repeats = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Re-validate the redirect target URL before following
        if not newurl or not isinstance(newurl, str):
            raise FetchBlockedError("redirect target missing URL")
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme not in ("http", "https"):
            raise FetchBlockedError(f"redirect scheme not allowed: {parsed.scheme!r}")
        if not parsed.hostname:
            raise FetchBlockedError("redirect target missing hostname")
        # Resolve + check every address before following the redirect.
        _resolve_public_ips(parsed.hostname)
        # Target is safe — delegate to parent to construct the redirect request
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _safe_fetch_url(
    url: str,
    *,
    max_bytes: int = 5_000_000,
    timeout: float = 8.0,
) -> bytes:
    """Fetch a user-supplied URL with SSRF/LFI defenses. Returns bytes.

    Raises ValueError on any policy violation or fetch error;
    policy violations (raised before any network I/O) are raised as the
    subclass FetchBlockedError so callers can couple rejection to request
    termination while genuine fetch failures stay degradable.
    [Fix 4-a-005] This is the CANONICAL safe URL fetcher for the SCP system.
    Both `scp.api_server_parts.helpers._safe_fetch_url` (re-export) and
    `scp.core.api_utils.fetch_with_retry` (delegates the I/O here) MUST use
    this implementation. Do NOT add a third fetcher — extend this one instead.
    """
    if not url or not isinstance(url, str):
        raise FetchBlockedError("invalid url")
    parsed = urllib.parse.urlsplit(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise FetchBlockedError(f"scheme not allowed: {parsed.scheme!r}")
    if not parsed.hostname:
        raise FetchBlockedError("missing hostname")
    current_url = url.strip()
    for hop in range(6):
        current = urllib.parse.urlsplit(current_url)
        if current.scheme not in ("http", "https") or not current.hostname:
            raise FetchBlockedError("redirect target is not a valid HTTP(S) URL")
        # Explicit test/staging egress policy applies to every redirect hop.
        # [EE] enforce_egress_policy (idempotent, pure check) covers
        # SCP_EGRESS_MODE=deny/allowlist + production fail-closed for EVERY
        # hop. EgressDeniedError (PermissionError+ValueError) propagates with
        # its EXACT type — the egress contract tests pin it and callers
        # classify it as a policy rejection (400 at the /ask boundary).
        enforce_egress_policy(current_url)
        egress_mode = os.environ.get("SCP_EGRESS_MODE", "deny").strip().lower()
        if egress_mode in {"deny", "offline", "disabled"} and current.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise FetchBlockedError("external egress disabled by SCP_EGRESS_MODE")
        # Resolve every address and pin this hop to the validated destination.
        # A new hostname gets a new validation+connection pair; the original
        # hostname's IP is never reused for a redirect target.
        destination_ip = _resolve_public_ips(current.hostname)[0]
        handler = (
            _PinnedHTTPSHandler(destination_ip)
            if current.scheme == "https"
            else _PinnedHTTPHandler(destination_ip)
        )
        opener = urllib.request.build_opener(
            handler,
            _NoRedirectHandler,
            urllib.request.ProxyHandler({}),
        )
        req = urllib.request.Request(current_url, headers={"User-Agent": _SCP_SAFE_FETCH_UA})  # noqa: S310 — scheme validated above
        try:
            with opener.open(req, timeout=timeout) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                if status in {301, 302, 303, 307, 308}:
                    location = resp.headers.get("Location")
                    if not location:
                        raise ValueError("redirect response missing Location")
                    if hop == 5:
                        raise ValueError("too many redirects (maximum 5)")
                    current_url = urllib.parse.urljoin(current_url, location)
                    continue
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f"response exceeds max_bytes={max_bytes}")
                    chunks.append(chunk)
                return b"".join(chunks)
        except ValueError:
            raise
        except urllib.error.HTTPError as exc:
            raise ValueError(f"HTTP error: {exc.code}") from exc
        except (urllib.error.URLError, OSError) as exc:  # [FALSE-POS-FIX] B014: TimeoutError IS OSError in Python 3 — redundant
            raise ValueError(f"fetch error: {exc}") from exc
    raise ValueError("too many redirects (maximum 5)")


__all__ = [
    "_SCP_SAFE_FETCH_UA",
    "FetchBlockedError",
    "_is_disallowed_ip",
    "_SafeRedirectHandler",
    "_safe_fetch_url",
]
