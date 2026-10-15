# SCP CIRCUIT: M02 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M02-closure.json)
"""
Forecast routes — Prediction outcome tracking ledger.

Routes:
  GET  /v105/forecast/stats       — Forecast ledger stats
  POST /v105/forecast/cases       — Record a new forecast case
  GET  /v105/forecast/cases       — List forecast cases
  POST /v105/forecast/resolve     — Record the actual outcome of a case
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from scp.api._shared import verify_admin
from scp.core.request_run_ledger import RequestRunLedger, traced_request
from scp.forecast.ledger import ForecastLedger, ForecastRegistry, RegistrySnapshot

router = APIRouter(prefix="/v105/forecast", tags=["forecast"])
_LEDGER = RequestRunLedger()
_DATA_DIR = Path(os.environ.get("SCP_DATA_DIR", "data"))

logger = logging.getLogger("scp.api.routes.forecast")


def _internal_error(exc: Exception) -> HTTPException:
    """[AUDIT-20260909 MACH2-BUG4] 500 fail-closed, không leak message nội bộ."""
    logger.warning("[forecast] internal error: %s", exc, exc_info=True)
    return HTTPException(status_code=500, detail="internal error")


def _get_ledger() -> ForecastLedger:
    """Create a ForecastLedger with an empty in-memory registry for API use."""
    # ForecastRegistry is a frozen dataclass normally loaded from a JSON manifest.
    # For runtime API use, we create a minimal in-memory registry using proper constructors.
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    import hashlib
    import json
    empty_payload: dict = {"cases": []}
    raw = json.dumps(empty_payload, sort_keys=True, ensure_ascii=False).encode()
    raw_sha = hashlib.sha256(raw).hexdigest()
    snap = RegistrySnapshot(
        path="<api-runtime-registry>",
        raw_sha256=raw_sha,
        canonical_sha256=raw_sha,
        embedded_manifest_sha256=None,
        manifest_status="SKIPPED",
        case_count=0,
        lock_date=None,
    )
    registry = ForecastRegistry(payload=empty_payload, snapshot=snap)
    ledger_path = _DATA_DIR / "forecast_ledger.jsonl"
    return ForecastLedger(registry=registry, ledger_path=str(ledger_path))


@router.get("/stats", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="forecast_stats")
async def forecast_stats():
    """Forecast ledger summary stats."""
    try:
        ledger = _get_ledger()
        stats = ledger.stats() if hasattr(ledger, "stats") else {}
        ledger.close() if hasattr(ledger, "close") else None
        return {"subsystem": "forecast", "status": "active", **stats}
    except Exception as exc:
        raise _internal_error(exc) from exc


@router.post("/cases", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=True, action="forecast_record_case")
async def record_case(request: Request):
    """
    Record a new forecast case for later outcome resolution.

    Body: {"id": "...", "domain": "health", "claimant": "scp-judge",
           "claim": "X will happen", "date": "2024-01-01",
           "url": "...", "verdict": "PASS", "confidence": 0.8,
           "antibodies": [], "outcome_code": 9}
    """
    import json as _json

    from scp.forecast.ledger import ALLOWED_OUTCOME_CODES, REQUIRED_CASE_FIELDS
    body = await request.json()
    # Validate required fields
    missing = REQUIRED_CASE_FIELDS - set(body.keys())
    if missing:
        return {"error": f"Missing required fields: {sorted(missing)}", "received": list(body.keys())}
    # Validate outcome_code
    oc = body.get("outcome_code")
    if oc not in ALLOWED_OUTCOME_CODES:
        return {"error": f"outcome_code must be one of {sorted(ALLOWED_OUTCOME_CODES)}, got {oc}"}
    # Persist to registry JSONL file (append-only)
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    registry_file = _DATA_DIR / "forecast_registry.jsonl"
    entry = dict(body)
    entry["registered_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    line = _json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
    import os as _os
    fd = _os.open(str(registry_file), _os.O_WRONLY | _os.O_CREAT | _os.O_APPEND, 0o600)
    try:
        _os.write(fd, line.encode("utf-8"))
        _os.fsync(fd)
    finally:
        _os.close(fd)
    return {"event": "case_registered", "id": body["id"], "domain": body.get("domain"), "registered_at": entry["registered_at"]}


@router.get("/cases", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="forecast_list_cases")
async def list_cases(domain: str = "", limit: int = 50):
    """List forecast cases, optionally filtered by domain."""
    try:
        ledger = _get_ledger()
        cases = ledger.list_cases(domain=domain or None, limit=limit) if hasattr(ledger, "list_cases") else []
        ledger.close() if hasattr(ledger, "close") else None
        return {"cases": cases, "count": len(cases)}
    except Exception as exc:
        raise _internal_error(exc) from exc


@router.post("/resolve", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=True, action="forecast_resolve_case")
async def resolve_case(request: Request):
    """
    Record the actual outcome of a forecast case.

    Body: {"case_id": "...", "outcome_code": 1, "resolution_note": "..."}
    """
    body = await request.json()
    ledger = _get_ledger()
    try:
        result = ledger.resolve_case(
            case_id=str(body.get("case_id", "")),
            outcome_code=int(body.get("outcome_code", 9)),
            resolution_note=str(body.get("resolution_note", "")),
        )
        return result
    except Exception as exc:
        raise _internal_error(exc) from exc
    finally:
        ledger.close() if hasattr(ledger, "close") else None
