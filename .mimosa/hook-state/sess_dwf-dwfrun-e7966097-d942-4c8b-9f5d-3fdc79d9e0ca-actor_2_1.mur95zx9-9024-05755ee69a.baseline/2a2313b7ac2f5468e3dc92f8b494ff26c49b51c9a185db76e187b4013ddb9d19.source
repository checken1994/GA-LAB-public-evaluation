from __future__ import annotations

import sqlite3

import pytest

from scp.calibration import CalibrationLedger, LegacyCalibrationAdapter
from scp.contracts.verdicts import Verdict


class _LegacyEngine:
    def apply_calibration(self, confidence: float, domain: str) -> float:
        assert domain == "coding"
        return confidence * 0.5


def test_prediction_and_resolution_are_append_only_and_evidence_bound(tmp_path):
    ledger = CalibrationLedger(tmp_path / "calibration.sqlite")
    pred = ledger.record_prediction(
        domain="coding",
        task_class="root_cause",
        predictor_type="model",
        predictor_id="model-x",
        prediction={"claim": "X"},
        semantic_verdict=Verdict.VERIFIED,
        confidence=0.9,
        tested_sha="abc1234",
    )
    with pytest.raises(ValueError):
        ledger.resolve(
            pred["prediction_id"],
            outcome=Verdict.VERIFIED,
            resolver_type="reality",
            resolver_id="rv",
            evidence_refs=[],
        )
    resolution = ledger.resolve(
        pred["prediction_id"],
        outcome=Verdict.CONTRADICTED,
        resolver_type="reality",
        resolver_id="rv",
        evidence_refs=["ev_0000000000000001"],
    )
    assert ledger.current_resolution(pred["prediction_id"])["resolution_id"] == resolution["resolution_id"]
    metrics = ledger.metrics(domain="coding")
    assert metrics["count"] == 1
    assert metrics["resolved_count"] == 1
    assert metrics["binary_scored_count"] == 1
    assert metrics["brier_score"] == pytest.approx(0.81)

    with pytest.raises(sqlite3.IntegrityError):
        with ledger.db.transaction() as conn:
            conn.execute(
                "UPDATE calibration_predictions SET confidence=0.1 WHERE prediction_id=?",
                (pred["prediction_id"],),
            )
    ledger.close()


def test_resolution_correction_supersedes_instead_of_rewriting(tmp_path):
    ledger = CalibrationLedger(tmp_path / "calibration.sqlite")
    pred = ledger.record_prediction(
        domain="coding",
        task_class="judge",
        predictor_type="model",
        predictor_id="m",
        prediction="answer",
        semantic_verdict=Verdict.UNKNOWN,
        confidence=0.99,
    )
    first = ledger.resolve(
        pred["prediction_id"],
        outcome=Verdict.UNKNOWN,
        resolver_type="reality",
        resolver_id="v1",
        evidence_refs=["ev_0000000000000001"],
    )
    second = ledger.resolve(
        pred["prediction_id"],
        outcome=Verdict.VERIFIED,
        resolver_type="reality",
        resolver_id="v2",
        evidence_refs=["ev_0000000000000002"],
        supersedes_resolution_id=first["resolution_id"],
    )
    assert ledger.current_resolution(pred["prediction_id"])["resolution_id"] == second["resolution_id"]
    ledger.close()


def test_legacy_pass_fail_engine_is_advisory_only():
    adapter = LegacyCalibrationAdapter(_LegacyEngine())
    advice = adapter.advise(
        confidence=0.99,
        domain="coding",
        canonical_verdict=Verdict.UNKNOWN,
    )
    assert advice.advisory_confidence == pytest.approx(0.495)
    assert advice.canonical_verdict is Verdict.UNKNOWN
    assert adapter.canonical_verdict_from_legacy_result(
        legacy_result="PASS", reality_verdict=Verdict.UNKNOWN
    ) is Verdict.UNKNOWN
    assert adapter.canonical_verdict_from_legacy_result(
        legacy_result="FAIL", reality_verdict=Verdict.VERIFIED
    ) is Verdict.VERIFIED
