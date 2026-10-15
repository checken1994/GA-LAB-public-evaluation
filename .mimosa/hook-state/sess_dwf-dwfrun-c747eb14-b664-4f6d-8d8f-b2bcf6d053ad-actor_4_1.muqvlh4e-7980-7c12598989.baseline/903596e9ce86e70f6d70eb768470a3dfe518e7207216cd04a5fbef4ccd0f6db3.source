# SCP CIRCUIT: M02 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M02-closure.json)
"""
Calibration routes — Prediction→Reality resolution ledger (26-P0.08/09).

Routes:
  GET  /v105/calibration/stats    — Ledger summary stats
  POST /v105/calibration/predict  — Record a prediction to track
  POST /v105/calibration/resolve  — Resolve a prediction against reality
  GET  /v105/calibration/accuracy — Get accuracy metrics by domain
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from scp.api._shared import verify_admin
from scp.calibration.ledger import CalibrationLedger
from scp.core.request_run_ledger import RequestRunLedger, traced_request

router = APIRouter(prefix="/v105/calibration", tags=["calibration"])
_LEDGER = RequestRunLedger()
_DATA_DIR = Path(os.environ.get("SCP_DATA_DIR", "data"))

logger = logging.getLogger("scp.api.routes.calibration")


def _internal_error(exc: Exception) -> HTTPException:
    """[AUDIT-20260909 MACH2-BUG4] 500 fail-closed, không leak message nội bộ."""
    logger.warning("[calibration] internal error: %s", exc, exc_info=True)
    return HTTPException(status_code=500, detail="internal error")


def _get_ledger() -> CalibrationLedger:
    return CalibrationLedger(db_path=str(_DATA_DIR / "calibration.sqlite"))


@router.get("/stats", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="calibration_stats")
async def calibration_stats():
    """Calibration ledger summary: total predictions, resolution rate."""
    try:
        ledger = _get_ledger()
        stats = ledger.stats() if hasattr(ledger, "stats") else {}
        ledger.close() if hasattr(ledger, "close") else None
        return {"subsystem": "calibration", "status": "active", **stats}
    except Exception as exc:
        raise _internal_error(exc) from exc


@router.post("/predict", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=True, action="calibration_record_prediction")
async def record_prediction(request: Request):
    """
    Record a new prediction for later reality resolution.

    Body: {"domain": "health", "task_class": "factcheck",
           "predictor_type": "judge", "predictor_id": "...",
           "prediction": {"verdict": "PASS", "confidence": 0.85}}
    """
    body = await request.json()
    ledger = _get_ledger()
    try:
        result = ledger.record_prediction(
            domain=str(body.get("domain", "general")),
            task_class=str(body.get("task_class", "factcheck")),
            predictor_type=str(body.get("predictor_type", "judge")),
            predictor_id=str(body.get("predictor_id", "")),
            predictor_version=body.get("predictor_version"),
            subject_claim_id=body.get("subject_claim_id"),
            prediction=body.get("prediction", {}),
        )
        return result
    finally:
        ledger.close() if hasattr(ledger, "close") else None


@router.post("/resolve", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=True, action="calibration_resolve")
async def resolve_prediction(request: Request):
    """
    Resolve a tracked prediction against observed reality.

    Body: {"prediction_id": "...", "reality_verdict": "PASS|FAIL",
           "resolution_evidence": "..."}
    """
    body = await request.json()
    ledger = _get_ledger()
    try:
        result = ledger.resolve(
            prediction_id=str(body.get("prediction_id", "")),
            reality_verdict=str(body.get("reality_verdict", "")),
            resolution_evidence=body.get("resolution_evidence", ""),
        )
        return result
    except Exception as exc:
        raise _internal_error(exc) from exc
    finally:
        ledger.close() if hasattr(ledger, "close") else None


@router.get("/accuracy", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="calibration_accuracy")
async def calibration_accuracy(domain: str = ""):
    """Get Brier score / accuracy metrics by domain."""
    try:
        ledger = _get_ledger()
        result = ledger.accuracy_by_domain(domain or None) if hasattr(ledger, "accuracy_by_domain") else {}
        ledger.close() if hasattr(ledger, "close") else None
        return {"domain_filter": domain or "*", "accuracy": result}
    except Exception as exc:
        raise _internal_error(exc) from exc
