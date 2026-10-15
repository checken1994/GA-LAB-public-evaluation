"""Severity — canonical source of truth for severity definitions across SCP."""
from __future__ import annotations

from enum import Enum
from typing import Any


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    WARNING = "warning"  # for stubs only


# Aliases for governance compatibility
CRITICAL_SEVERITIES = {Severity.CRITICAL, Severity.HIGH}  # both trigger KILL path

# Provider adapters historically emitted these transport/status spellings.
# They are normalized at the policy boundary rather than silently accepted.
_SEVERITY_ALIASES: dict[str, Severity] = {
    "error": Severity.MEDIUM,
    "err": Severity.MEDIUM,
    "warn": Severity.WARNING,
}


def normalize_severity(raw: Any) -> str | None:
    """Return a canonical severity value, or ``None`` for an unknown value.

    Unknown values remain visible to Governance; they must not silently become
    ``info`` or an accepted result.
    """
    if isinstance(raw, Severity):
        return raw.value
    if raw is None:
        return None
    value = str(raw).strip().lower()
    if value in Severity._value2member_map_:
        return value
    alias = _SEVERITY_ALIASES.get(value)
    return alias.value if alias else None


__all__ = ["Severity", "CRITICAL_SEVERITIES", "_SEVERITY_ALIASES", "normalize_severity"]
