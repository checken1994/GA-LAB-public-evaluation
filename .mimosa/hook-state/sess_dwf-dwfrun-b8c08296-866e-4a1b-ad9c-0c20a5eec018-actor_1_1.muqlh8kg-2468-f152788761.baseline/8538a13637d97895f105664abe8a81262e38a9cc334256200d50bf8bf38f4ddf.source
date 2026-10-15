"""Unified Egress Policy Engine for SCP Agent OS Autonomous Operations."""
from __future__ import annotations

import enum
import ipaddress
import logging
import os
import urllib.parse
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class EgressMode(str, enum.Enum):
    DENY = "deny"
    ALLOWLIST = "allowlist"
    OPEN = "open"


def _redact_url_for_message(url: str) -> str:
    """[AUDIT-FIX med-1] Redact secrets trong query string trước khi URL vào
    message của EgressDeniedError (message bị caller log ở mọi tầng).

    Canonical helper: ``scp.core.api_utils.redact_query_secrets`` (import lười
    để file policy nền tảng này không bị gắn thêm dependency). Fail-closed:
    nếu helper không khả dụng, drop TOÀN BỘ query thay vì leak credential.
    """
    try:
        from scp.core.api_utils import redact_query_secrets

        return redact_query_secrets(url)
    except Exception as _redact_err:
        logger.debug("redact_query_secrets unavailable, falling back to urlsplit redaction: %s", _redact_err, exc_info=True)
        try:
            parts = urllib.parse.urlsplit(str(url))
            return urllib.parse.urlunsplit(parts._replace(query="", fragment=""))
        except Exception as _split_err:
            logger.debug("urlsplit redaction fallback failed, returning fully redacted placeholder: %s", _split_err, exc_info=True)
            return "[REDACTED-URL]"


def _numeric_host_to_ip(host: str) -> str | None:
    """[AUDIT-FIX 2026-09-29 Agent1, extended by Agent5 F4a] Numeric IPv4
    spellings to canonical form.

    OS resolvers (inet_aton semantics) accept far more IPv4 spellings than
    ipaddress.ip_address, which raises ValueError for all of them. Left
    unrecognized, those spellings bypassed the cloud-metadata block
    (Invariant 1) in OPEN mode. Normalized here, fail-closed:

    - single-integer decimal:      '2852039166'  == 169.254.169.254
    - single-integer octal:        '025177524776' == 169.254.169.254
      (a leading-0 single integer is OCTAL per inet_aton; decimal parse would
      overflow → None, silently skipping normalization and dodging the
      metadata block on Linux)
    - single-integer hex:          '0xA9FEA9FE'
    - octal-dotted (inet_aton):    '0251.0376.0251.0376' == 169.254.169.254
      (a leading-0 part is OCTAL per POSIX inet_aton; a part > '0377' octal
      or a 4-part form with any plain-decimal overflow falls through to the
      standard parser)
    - hex-dotted / mixed-radix:    '0xA9FE.0xA9FE' (2 parts hex), '169.254.0xA9.FE'
      (mixed decimal/hex parts), per inet_aton part-radix rules
    - trailing/inner empty parts are rejected here (None) so the standard
      parser decides, matching its behavior.

    Anything not numeric-looking returns None and normal parsing applies.
    Pure string/int math (no socket) so the result is identical on every
    platform. Multi-part forms always yield exactly 4 octets or None.
    """
    if not host or len(host) > 64:
        return None

    def _part_value(part: str) -> int | None:
        # inet_aton part rules: '0x'/'0X' prefix -> hex (1..8 digits),
        # leading '0' -> octal (0..0377), else decimal; empty is invalid.
        if not part:
            return None
        if len(part) > 2 and part[0] == "0" and part[1] in ("x", "X"):
            digits = part[2:]
            if not digits or any(c not in "0123456789abcdefABCDEF" for c in digits):
                return None
            value = int(digits, 16)
        elif part[0] == "0" and len(part) > 1:
            if any(c not in "01234567" for c in part):
                return None
            value = int(part, 8)
        else:
            if not part.isdigit():
                return None
            value = int(part, 10)
        return value if 0 <= value <= 0xFF else None

    if host.isdigit():
        if len(host) > 1 and host[0] == "0":
            # inet_aton: a leading-0 SINGLE integer is OCTAL ('025177524776'
            # == 169.254.169.254). A decimal parse overflows 32-bit → None
            # (or lands on an unrelated address), letting the metadata
            # spelling dodge the block on Linux. Non-octal digits (8/9)
            # after the leading zero are invalid octal → None, matching
            # inet_aton (the standard parser rejects them too).
            if any(c not in "01234567" for c in host):
                return None
            value = int(host, 8)
        else:
            value = int(host, 10)
    elif len(host) > 2 and host[0] == "0" and host[1] in ("x", "X") and all(
        c in "0123456789abcdefABCDEF" for c in host[2:]
    ):
        value = int(host[2:], 16)
    elif "." in host and any(part.startswith(("0x", "0X")) for part in host.split(".")):
        # Hex-part multi-part forms: rejected by Windows inet_addr but ACCEPTED
        # by Linux inet_aton. Fail-closed across platforms: parse every part as
        # hex-capable and require exactly the inet_aton shape (1-4 parts, each
        # <= 0xFF for a 4-part form). If anything is off, return None so the
        # standard parser (which rejects these on Windows anyway) decides.
        parts = host.split(".")
        if not parts or any(part == "" for part in parts):
            return None

        def _hexish(part: str) -> int | None:
            if part.startswith(("0x", "0X")):
                digits = part[2:]
                if not digits or len(digits) > 8 or any(
                    c not in "0123456789abcdefABCDEF" for c in digits
                ):
                    return None
                return int(digits, 16)
            return _part_value(part)

        if len(parts) == 4:
            octets = [_hexish(part) for part in parts]
            if any(o is None or o > 0xFF for o in octets):
                return None
            value = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
        elif len(parts) in (1, 2, 3):
            # inet_aton n-part form: first n-1 parts are octets, the final
            # part carries the remaining (5-n) bytes (16/24/32-bit bound).
            head = [_hexish(part) for part in parts[:-1]]
            if any(h is None or h > 0xFF for h in head):
                return None
            tail = _hexish(parts[-1])
            if tail is None or tail >= (1 << (8 * (5 - len(parts)))):
                return None
            value = 0
            for h in head:
                value = (value << 8) | h
            value = (value << (8 * (5 - len(parts)))) | tail
        else:
            return None
    elif "." in host:
        parts = host.split(".")
        # inet_aton: 1-3 part forms embed a final 24/16/8-bit integer; the
        # 4-part form is the plain dotted quad. Empty parts are invalid.
        if not parts or any(part == "" for part in parts):
            return None
        if len(parts) == 4:
            octets = [_part_value(part) for part in parts]
            if any(octet is None for octet in octets):
                return None
            value = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
        elif len(parts) in (1, 2, 3):
            # inet_aton n-part form: the first n-1 parts are single octets;
            # the final part carries the remaining (5-n) bytes:
            #   a.b.c   -> (a<<24)|(b<<16)|c          (c < 2**16)
            #   a.b     -> (a<<24)|b                  (b < 2**24)
            #   a       -> a                          (a < 2**32)
            head = [_part_value(part) for part in parts[:-1]]
            if any(h is None for h in head):
                return None
            tail_value = _part_value(parts[-1])
            if tail_value is None or tail_value >= (1 << (8 * (5 - len(parts)))):
                return None
            # head octets occupy the top (len(parts)-1) bytes of the address
            value = 0
            for h in head:
                value = (value << 8) | h
            value = (value << (8 * (5 - len(parts)))) | tail_value
        else:
            return None
    else:
        return None

    if not 0 <= value <= 0xFFFFFFFF:
        return None
    return ".".join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))


class EgressDeniedError(PermissionError, ValueError):
    """Raised when an outbound network request is forbidden by egress policy."""

    def __init__(self, target: str, reason: str, url: str | None = None) -> None:
        self.target = target
        self.reason = reason
        self.url = url or target
        # [AUDIT-FIX med-1] Message có thể được log bởi bất kỳ caller nào —
        # query string chứa credential (api_key/token/...) phải được redact
        # TRƯỚC khi vào message. Host + path giữ nguyên để còn debug.
        super().__init__(f"egress denied for {_redact_url_for_message(self.url)!r}: {reason}")


@dataclass(frozen=True)
class EgressDestination:
    host: str
    port: int | None = None
    scheme: str = "https"

    @classmethod
    def from_url(cls, url: str | Any) -> EgressDestination:
        if hasattr(url, "full_url"):
            url_str = str(url.full_url)
        else:
            url_str = str(url)
        if "://" not in url_str and not url_str.startswith("//"):
            parsed = urllib.parse.urlparse("//" + url_str)
        else:
            parsed = urllib.parse.urlparse(url_str)
        scheme = (parsed.scheme or "https").lower()
        host = (parsed.hostname or "").strip().strip("[]").lower().rstrip(".")
        port = parsed.port
        return cls(host=host, port=port, scheme=scheme)


class EgressPolicy:
    """Strict Zero-Trust Policy Engine governing network egress for tools."""

    BLOCKED_METADATA_HOSTS = frozenset({
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.aws",
        "169.254.170.2",
        "fd00:ec2::254",
    })
    LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

    def __init__(
        self,
        mode: EgressMode | str | None = None,
        allowlist: Iterable[str] | None = None,
        production_mode: bool | None = None,
    ) -> None:
        if mode is None:
            raw_mode = os.environ.get("SCP_EGRESS_MODE", "").lower().strip() or "allowlist"
            if raw_mode in EgressMode._value2member_map_:
                self.mode = EgressMode(raw_mode)
            elif raw_mode in ("offline", "disabled", "deny"):
                self.mode = EgressMode.DENY
            else:
                self.mode = EgressMode.DENY
        elif isinstance(mode, str):
            clean_mode = mode.lower().strip()
            if clean_mode in EgressMode._value2member_map_:
                self.mode = EgressMode(clean_mode)
            elif clean_mode in ("offline", "disabled", "deny"):
                self.mode = EgressMode.DENY
            else:
                self.mode = EgressMode.DENY
        else:
            self.mode = mode

        if allowlist is not None:
            raw_allowlist = allowlist
        else:
            raw_allowlist = os.environ.get("SCP_EGRESS_ALLOWLIST", "").split(",")

        self.allowlist: frozenset[str] = frozenset(
            item.strip().strip("[]").lower().rstrip(".") for item in raw_allowlist if item.strip()
        )
        self.production_mode = (
            production_mode
            if production_mode is not None
            else os.environ.get("SCP_PRODUCTION_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}
        )

    def is_loopback(self, host: str) -> bool:
        norm_host = host.strip().strip("[]").lower().rstrip(".")
        if norm_host in self.LOOPBACK_HOSTS:
            return True
        try:
            return ipaddress.ip_address(norm_host).is_loopback
        except ValueError:
            return False

    def is_cloud_metadata(self, host: str) -> bool:
        norm_host = host.strip().strip("[]").lower().rstrip(".")
        if norm_host in self.BLOCKED_METADATA_HOSTS:
            return True
        ip = None
        try:
            ip = ipaddress.ip_address(norm_host)
            if getattr(ip, "ipv4_mapped", None) is not None and ip.ipv4_mapped:
                return ip.ipv4_mapped in ipaddress.ip_network("169.254.0.0/16")
            if isinstance(ip, ipaddress.IPv6Address):
                return ip == ipaddress.ip_address("fd00:ec2::254")
            return ip in ipaddress.ip_network("169.254.0.0/16")
        except ValueError:
            # [AUDIT-FIX 2026-09-29 Agent1] Numeric spellings ('2852039166',
            # '0xA9FEA9FE') that resolvers accept but ipaddress rejects must
            # not dodge the metadata block - normalize and re-check fail-closed.
            numeric = _numeric_host_to_ip(norm_host)
            if not numeric:
                return False
            try:
                ip = ipaddress.ip_address(numeric)
            except ValueError:
                return False
        if getattr(ip, "ipv4_mapped", None) is not None and ip.ipv4_mapped:
            return ip.ipv4_mapped in ipaddress.ip_network("169.254.0.0/16")
        if isinstance(ip, ipaddress.IPv6Address):
            return ip == ipaddress.ip_address("fd00:ec2::254")
        return ip in ipaddress.ip_network("169.254.0.0/16")

    def enforce(self, destination: str | EgressDestination, token_allowed_hosts: Iterable[str] | None = None) -> None:
        """Enforce egress policy fail-closed. Raises EgressDeniedError on violation."""
        dest = EgressDestination.from_url(destination) if isinstance(destination, str) else destination
        url_context = str(getattr(destination, "full_url", destination)) if not isinstance(destination, EgressDestination) else dest.host

        if not dest.host:
            raise EgressDeniedError(str(destination), "Missing or invalid host in destination", url=url_context)

        # Invariant 1: Cloud metadata is unconditionally blocked in all modes
        if self.is_cloud_metadata(dest.host):
            raise EgressDeniedError(dest.host, "Access to cloud metadata endpoints is unconditionally prohibited", url=url_context)

        # Invariant 2: Loopback is always permitted for internal microservices
        if self.is_loopback(dest.host):
            return

        # Invariant 3: Deny mode blocks all external traffic
        if self.mode == EgressMode.DENY:
            raise EgressDeniedError(dest.host, "SCP_EGRESS_MODE=deny blocks all non-loopback outbound traffic", url=url_context)

        # Invariant 4: Allowlist mode checks global allowlist and capability token-bound allowlist
        if self.mode == EgressMode.ALLOWLIST:
            permitted = set(self.allowlist)
            if token_allowed_hosts:
                permitted.update(h.strip().strip("[]").lower().rstrip(".") for h in token_allowed_hosts if h.strip())

            matched = False
            for item in permitted:
                if item.startswith("*."):
                    suffix = item[2:]
                    if dest.host == suffix or dest.host.endswith("." + suffix):
                        matched = True
                        break
                elif dest.host == item:
                    matched = True
                    break

            if not matched:
                raise EgressDeniedError(dest.host, f"Host not present in egress allowlist: {sorted(permitted)}", url=url_context)
            return

        # Invariant 5: In production mode, open/unknown modes fail-closed
        if self.production_mode and self.mode not in {EgressMode.DENY, EgressMode.ALLOWLIST}:
            raise EgressDeniedError(dest.host, "Production mode requires explicit deny or allowlist egress policy", url=url_context)


__all__ = [
    "EgressMode",
    "EgressDeniedError",
    "EgressDestination",
    "EgressPolicy",
]
