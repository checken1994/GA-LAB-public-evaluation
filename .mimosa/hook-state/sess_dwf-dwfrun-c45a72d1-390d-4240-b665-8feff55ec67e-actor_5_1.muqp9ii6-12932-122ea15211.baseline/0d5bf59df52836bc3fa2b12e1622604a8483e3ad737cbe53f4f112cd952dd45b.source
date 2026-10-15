"""Canonical evidence levels A-D (blueprint: never promote A to C by volume)."""
from __future__ import annotations

from enum import Enum


class EvidenceLevel(str, Enum):
    A = "A"  # static: file/schema/pattern exists, no runtime proof
    B = "B"  # integration: modules connect, partial runtime proof
    C = "C"  # end_to_end: real task crosses the production path
    D = "D"  # recovery: C + real crash/timeout/restart/unknown-state handled


def parse_evidence_level(value: object) -> EvidenceLevel:
    raw = value.value if isinstance(value, EvidenceLevel) else str(value).strip().upper()
    try:
        return EvidenceLevel(raw)
    except ValueError as exc:
        raise ValueError(f"invalid evidence level: {value!r}") from exc
