"""Canonical ID rules (26-P0.2).

IDs are globally unique within their namespace, immutable, secret-free, and
never derived from local DB row numbers. Occurrence identity is random
(`new_id`); content identity is deterministic (`content_id`). The same content
observed twice yields the SAME content_id but TWO different evidence IDs.
"""
from __future__ import annotations

import hashlib
import re
import secrets

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}_[0-9a-f]{16,64}$")
_PREFIX_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}$")


def new_id(prefix: str) -> str:
    if not _PREFIX_RE.fullmatch(prefix or ""):
        raise ValueError(f"invalid id prefix: {prefix!r}")
    return f"{prefix}_{secrets.token_hex(12)}"


def is_valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def require_id(value: object, expected_prefix: str | None = None) -> str:
    if not is_valid_id(value):
        raise ValueError(f"invalid id: {value!r}")
    if expected_prefix is not None and not str(value).startswith(f"{expected_prefix}_"):
        raise ValueError(f"id {value!r} does not carry the required prefix {expected_prefix!r}")
    return str(value)


def content_id(data: bytes) -> str:
    """Deterministic content identity - never used as an occurrence ID."""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("content_id requires raw bytes")
    return "sha256:" + hashlib.sha256(bytes(data)).hexdigest()
