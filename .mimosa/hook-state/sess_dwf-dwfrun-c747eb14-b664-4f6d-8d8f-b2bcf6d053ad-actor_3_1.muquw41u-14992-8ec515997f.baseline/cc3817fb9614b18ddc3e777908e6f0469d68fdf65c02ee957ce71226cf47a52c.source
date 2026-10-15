from __future__ import annotations

from dataclasses import dataclass

from scp.contracts.verdicts import Verdict, parse_verdict


@dataclass(frozen=True)
class CalibrationAdvice:
    """Confidence advice that can never upgrade/downgrade epistemic verdict."""

    original_confidence: float
    advisory_confidence: float
    canonical_verdict: Verdict
    source: str
    note: str

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.original_confidence) <= 1.0:
            raise ValueError("original_confidence must be in [0,1]")
        if not 0.0 <= float(self.advisory_confidence) <= 1.0:
            raise ValueError("advisory_confidence must be in [0,1]")
        object.__setattr__(self, "canonical_verdict", parse_verdict(self.canonical_verdict))
