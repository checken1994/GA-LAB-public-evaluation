"""Safe request metadata extraction for security detectors.

The request context may reach model-adjacent security code.  This module keeps
only bounded, non-secret metadata and deliberately never forwards credential,
cookie, authorization, or arbitrary header values.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_SENSITIVE_HEADER_NAMES = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "proxy-authorization",
        "proxy-authenticate",
        "x-api-key",
        "x-auth-token",
        "x-scp-pc-token",
        "x-scp-admin-token",
    }
)


def safe_header_metadata(headers: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return bounded header metadata without exposing sensitive values.

    The threat detector needs a user-agent fingerprint, but does not need
    credentials or arbitrary request-header values.  Header names are retained
    as a bounded list for observability; only the user-agent value is retained,
    truncated to a small fixed size for fingerprinting compatibility.
    """
    names: set[str] = set()
    sensitive_present = False
    user_agent = ""
    for raw_name, raw_value in (headers or {}).items():
        name = str(raw_name).strip().lower()
        if not name:
            continue
        if name in _SENSITIVE_HEADER_NAMES:
            sensitive_present = True
            continue
        names.add(name[:64])
        if name == "user-agent":
            user_agent = str(raw_value or "")[:256]

    safe_headers = {"user-agent": user_agent} if user_agent else {}
    return {
        "headers": safe_headers,
        "header_names": sorted(names)[:32],
        "sensitive_headers_present": sensitive_present,
        "user_agent_present": bool(user_agent),
    }


__all__ = ["safe_header_metadata"]

