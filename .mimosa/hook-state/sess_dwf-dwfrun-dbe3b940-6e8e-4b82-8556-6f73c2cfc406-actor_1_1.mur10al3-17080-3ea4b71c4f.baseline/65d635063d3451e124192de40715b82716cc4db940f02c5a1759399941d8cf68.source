# SCP CIRCUIT: M06 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M06-closure.json)
"""
SCP V105 Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â Prediction endpoints (Reality v4)

Live - admin auth required (Fix 4-a-003). Router IS registered in
api_server.py (around line 589-611) via `app.include_router(prediction_router)`.
The 5 routes below (`/v105/predictions/run-cycle`,
`/v105/predictions/pending`, `/v105/predictions/all`,
`/v105/predictions/verify`, `/v105/predictions/stats`) are LIVE and
require `Depends(verify_admin)` because `run-cycle` + `verify` are
state-changing POST endpoints that trigger the Crawl Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ Generate Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢
Predict Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ Verify Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ Learn pipeline (CPU/IO expensive Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â DoS amplifier
if unauthenticated). It imports the engine singleton from the canonical owner
`scp.api_server_parts.helpers` (set by `get_judge()`), so the engine must be
initialised first - see `_predictive_engine` initialisation in
api_server_parts/helpers.py.

[COMPLETION-FIX] Wire PredictiveOrchestrator v-Ă¢â‚¬Â-Ă‚Â o API:
- POST /v105/predictions/run-cycle Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â chĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â¡y 1 prediction cycle
- GET  /v105/predictions/pending Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â list pending predictions
- GET  /v105/predictions/all Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â list all predictions
- POST /v105/predictions/verify Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â verify pending predictions
- GET  /v105/predictions/stats Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â prediction statistics
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from scp.api._shared import verify_admin

logger = logging.getLogger("scp.api.predictions")

from scp.core.request_run_ledger import RequestRunLedger, traced_request

_PREDICTION_ROUTES_LEDGER = RequestRunLedger()

router = APIRouter(prefix="/v105/predictions", tags=["predictions"])


class VerifyRequest(BaseModel):
    limit: int = Field(20, ge=1, le=100)


def _get_engine():
    """Get PredictiveOrchestrator singleton.

    [M6-FIX wiring] Canonical owner of the singleton is
    ``scp.api_server_parts.helpers`` (set inside ``get_judge()`` right after
    the production judge is created). This route previously read
    ``scp.api_server._predictive_engine``, which is a separate module global
    that is NEVER assigned outside its ``= None`` initializer — so every
    prediction endpoint failed with 503 "PredictiveEngine not initialized"
    even on a healthy boot (silent wiring drop, D6). Read the canonical
    attribute at call time instead.
    """
    from scp.api_server_parts import helpers as _api_helpers
    engine = getattr(_api_helpers, "_predictive_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="PredictiveEngine not initialized")
    return engine


@router.post("/run-cycle", dependencies=[Depends(verify_admin)])  # Fix 4-a-003: BFLA auth (state-changing)
@traced_request(_PREDICTION_ROUTES_LEDGER, require_write=True, action="run_prediction_cycle")
async def run_prediction_cycle():
    """ChĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â¡y 1 cycle: Crawl Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ Generate Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ Predict Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ Verify Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ Learn."""
    engine = _get_engine()
    try:
        result = engine.run_cycle()
        return {"status": "ok", "cycle": result}
    except Exception as e:
        logger.error(f"Prediction cycle failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Prediction cycle failed Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â see server logs") from e


@router.get("/pending", dependencies=[Depends(verify_admin)])  # Fix 4-a-003: BFLA auth
@traced_request(_PREDICTION_ROUTES_LEDGER, require_write=False, action="get_pending_predictions")
async def get_pending_predictions(limit: int = 20):
    """List pending predictions (chĂ„â€Ă¢â‚¬Â -Ă‚Â°a verify)."""
    engine = _get_engine()
    preds = engine.predictor.get_pending_predictions()
    return {"pending": preds[:limit], "total": len(preds)}


@router.get("/all", dependencies=[Depends(verify_admin)])  # Fix 4-a-003: BFLA auth
@traced_request(_PREDICTION_ROUTES_LEDGER, require_write=False, action="get_all_predictions")
async def get_all_predictions(limit: int = 100):
    """List all predictions (pending + verified)."""
    engine = _get_engine()
    preds = engine.predictor.get_all_predictions(limit=limit)
    return {"predictions": preds, "total": len(preds)}


@router.post("/verify", dependencies=[Depends(verify_admin)])  # Fix 4-a-003: BFLA auth (state-changing)
@traced_request(_PREDICTION_ROUTES_LEDGER, require_write=True, action="verify_predictions")
async def verify_predictions(req: VerifyRequest):
    """Verify pending predictions (nĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â¿u Ă„â€Ă¢â‚¬Â│Ă¢â€Â¬Ă‹Å“Ă„â€Ă‚Â¡-Ă‚Âº-Ă‚Â¿n check_date)."""
    engine = _get_engine()
    try:
        results = engine.verifier.verify_pending(limit=req.limit)
        return {"verified": len(results), "results": results}
    except Exception as e:
        logger.error(f"Verify failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Verify failed Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â see server logs") from e


@router.get("/stats", dependencies=[Depends(verify_admin)])  # Fix 4-a-003: BFLA auth
@traced_request(_PREDICTION_ROUTES_LEDGER, require_write=False, action="prediction_stats")
async def prediction_stats():
    """Prediction statistics."""
    engine = _get_engine()
    all_preds = engine.predictor.get_all_predictions(limit=10000)
    pending = [p for p in all_preds if p.get("status") == "pending"]
    verified = [p for p in all_preds if p.get("status") != "pending"]
    correct = [p for p in verified if p.get("status") == "correct"]
    wrong = [p for p in verified if p.get("status") == "wrong"]
    return {
        "total": len(all_preds),
        "pending": len(pending),
        "verified": len(verified),
        "correct": len(correct),
        "wrong": len(wrong),
        "accuracy": len(correct) / len(verified) if verified else 0.0,
    }
