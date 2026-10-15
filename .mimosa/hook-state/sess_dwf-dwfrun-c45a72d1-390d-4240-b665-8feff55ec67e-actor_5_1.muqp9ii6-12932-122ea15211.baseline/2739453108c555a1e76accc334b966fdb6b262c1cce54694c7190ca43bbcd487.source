"""Canonical epistemic verdicts (26-P0.2 / blueprint 26-P0.6).

PASS/FAIL belong to tests and gates. Epistemic truth uses ONLY these four
verdicts; model confidence can never upgrade a verdict.
"""
from __future__ import annotations

from enum import Enum


class Verdict(str, Enum):
    VERIFIED = "VERIFIED"          # evidence satisfies the verification contract in scope
    CONTRADICTED = "CONTRADICTED"  # reality/evidence proves the claim false in scope
    INSUFFICIENT = "INSUFFICIENT"  # the required evidence is known but not available/complete
    UNKNOWN = "UNKNOWN"            # cannot be decided with current capability/evidence


def parse_verdict(value: object) -> Verdict:
    raw = value.value if isinstance(value, Verdict) else str(value).strip().upper()
    try:
        return Verdict(raw)
    except ValueError as exc:
        raise ValueError(f"invalid verdict: {value!r} (canonical: {[v.value for v in Verdict]})") from exc
