"""Canonical capability maturity ladder (blueprint 26-P0.7)."""
from __future__ import annotations

from enum import Enum


class Maturity(str, Enum):
    M0_IDEA = "M0"
    M1_SPECIFIED = "M1"
    M2_STATIC_PRESENT = "M2"
    M3_INTEGRATED = "M3"
    M4_RUNTIME_VERIFIED = "M4"
    M5_RECOVERY_VERIFIED = "M5"
    M6_RELEASE_GATED = "M6"


_ORDER = {member: index for index, member in enumerate(Maturity)}


def parse_maturity(value: object) -> Maturity:
    raw = value.value if isinstance(value, Maturity) else str(value).strip().upper()
    try:
        return Maturity(raw)
    except ValueError as exc:
        raise ValueError(f"invalid maturity: {value!r} (canonical: {[m.value for m in Maturity]})") from exc


def at_least(actual: object, required: object) -> bool:
    """True when `actual` maturity >= `required` on the M0..M6 ladder."""
    return _ORDER[parse_maturity(actual)] >= _ORDER[parse_maturity(required)]
