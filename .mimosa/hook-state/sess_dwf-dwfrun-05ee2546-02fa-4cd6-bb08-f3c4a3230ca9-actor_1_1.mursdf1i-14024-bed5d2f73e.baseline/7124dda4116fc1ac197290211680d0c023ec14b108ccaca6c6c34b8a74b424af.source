"""Advisory-only bridge for the legacy PASS/FAIL CalibrationEngine.

The old engine can suggest a confidence adjustment. It cannot create evidence,
change a canonical epistemic Verdict, or mark a capability/claim VERIFIED.
"""
from __future__ import annotations

import logging
from typing import Any

from scp.calibration.models import CalibrationAdvice
from scp.contracts.verdicts import Verdict, parse_verdict

logger = logging.getLogger(__name__)



class LegacyCalibrationAdapter:
    def __init__(self, legacy_engine: Any | None = None) -> None:
        self._engine = legacy_engine

    def advise(
        self,
        *,
        confidence: float,
        domain: str,
        canonical_verdict: Verdict | str,
    ) -> CalibrationAdvice:
        original = float(confidence)
        if not 0.0 <= original <= 1.0:
            raise ValueError("confidence must be in [0,1]")
        verdict = parse_verdict(canonical_verdict)
        tuned = original
        note = "legacy calibration unavailable; confidence unchanged"
        if self._engine is not None:
            try:
                tuned = float(self._engine.apply_calibration(original, str(domain)))
                tuned = max(0.0, min(1.0, tuned))
                note = "legacy PASS/FAIL factor applied as advisory confidence only"
            except Exception as exc:
                # Calibration failure must never alter truth semantics.
                logger.warning('LegacyCalibrationAdapter.advise: Exception not handled: %s', exc, exc_info=True)
                tuned = original
                note = f"legacy calibration failed closed to unchanged advisory confidence: {type(exc).__name__}"
        return CalibrationAdvice(
            original_confidence=original,
            advisory_confidence=tuned,
            canonical_verdict=verdict,
            source="legacy_calibration_engine",
            note=note,
        )

    @staticmethod
    def canonical_verdict_from_legacy_result(*, legacy_result: str, reality_verdict: Verdict | str) -> Verdict:
        """Explicitly ignore legacy PASS/FAIL as epistemic authority."""
        _ = str(legacy_result)  # retained only for audit/caller compatibility
        return parse_verdict(reality_verdict)
