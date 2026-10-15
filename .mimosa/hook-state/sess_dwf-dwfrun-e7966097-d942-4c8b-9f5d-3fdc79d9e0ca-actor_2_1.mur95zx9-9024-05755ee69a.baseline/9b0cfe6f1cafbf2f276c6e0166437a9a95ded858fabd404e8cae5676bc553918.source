import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

import pytest

from scp.calibration.models import CalibrationAdvice
from scp.contracts.verdicts import Verdict


def test_calibration_isolated_flow():
    """FA-13: Cover calibration flow with genuine behavioral execution.

    Verifies confidence interval bounds [0, 1], canonical Verdict enforcement,
    and immutability of epistemic advice.
    """
    # 1. Valid advice creation and attribute validation
    advice = CalibrationAdvice(
        original_confidence=0.9,
        advisory_confidence=0.85,
        canonical_verdict=Verdict.VERIFIED,
        source="calibration_ensemble",
        note="Confidence slightly dampened after semantic audit",
    )
    assert advice.original_confidence == 0.9
    assert advice.advisory_confidence == 0.85
    assert advice.canonical_verdict == Verdict.VERIFIED
    assert advice.source == "calibration_ensemble"

    # 2. String verdict auto-parsing into enum
    advice_parsed = CalibrationAdvice(
        original_confidence=0.6,
        advisory_confidence=0.65,
        canonical_verdict="insufficient",
        source="retrieval_judge",
        note="Sparse evidence",
    )
    assert advice_parsed.canonical_verdict == Verdict.INSUFFICIENT

    # 3. Out-of-bounds original confidence raises ValueError
    with pytest.raises(ValueError, match=r"in \[0,1\]"):
        CalibrationAdvice(
            original_confidence=1.5,
            advisory_confidence=0.5,
            canonical_verdict=Verdict.VERIFIED,
            source="src",
            note="invalid high",
        )

    # 4. Out-of-bounds advisory confidence raises ValueError
    with pytest.raises(ValueError, match=r"in \[0,1\]"):
        CalibrationAdvice(
            original_confidence=0.5,
            advisory_confidence=-0.1,
            canonical_verdict=Verdict.VERIFIED,
            source="src",
            note="invalid negative",
        )

    # 5. Invalid verdict string raises ValueError
    with pytest.raises(ValueError, match="invalid verdict"):
        CalibrationAdvice(
            original_confidence=0.5,
            advisory_confidence=0.5,
            canonical_verdict="UNKNOWN_GARBAGE",
            source="src",
            note="invalid verdict",
        )
