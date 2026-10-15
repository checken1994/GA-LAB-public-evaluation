# SCP CIRCUIT: M02 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M02-closure.json)
"""
History routes — Evidence ledger, Regression corpus, Semantic gate.

Routes:
  GET  /v105/history/evidence      — List evidence records
  POST /v105/history/evidence      — Record new evidence
  GET  /v105/history/regression    — List regression corpus entries
  GET  /v105/history/stats         — History subsystem stats
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from scp.api._shared import verify_admin
from scp.core.request_run_ledger import RequestRunLedger, traced_request
from scp.history.evidence_ledger import EvidenceRecord, append_record, promotion_evidence

router = APIRouter(prefix="/v105/history", tags=["history"])
_LEDGER = RequestRunLedger()
_DATA_DIR = Path(os.environ.get("SCP_DATA_DIR", "data"))
_EVIDENCE_PATH = _DATA_DIR / "history_evidence.jsonl"

logger = logging.getLogger("scp.api.routes.history")


def _internal_error(exc: Exception) -> HTTPException:
    """[AUDIT-20260909 MACH2-BUG4] Lỗi nội bộ KHÔNG được trả 200 kèm message
    nội bộ — log đầy đủ phía server, leak ra ngoài chỉ 'internal error'."""
    logger.warning("[history] internal error: %s", exc, exc_info=True)
    return HTTPException(status_code=500, detail="internal error")


@router.get("/stats", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="history_stats")
async def history_stats():
    """History subsystem stats."""
    try:
        count = 0
        if _EVIDENCE_PATH.exists():
            count = sum(1 for _ in _EVIDENCE_PATH.read_text(encoding="utf-8").splitlines() if _.strip())
        return {"subsystem": "history", "status": "active", "total_evidence_records": count}
    except Exception as exc:
        raise _internal_error(exc) from exc


@router.get("/evidence", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="history_list_evidence")
async def list_evidence(subject_id: str = ""):
    """List evidence records for a subject_id."""
    try:
        if not subject_id:
            return {"error": "subject_id required", "evidence": []}
        result = promotion_evidence(_EVIDENCE_PATH, subject_id)
        return {"evidence": result.get("evidence", []), "count": result.get("total_records", 0)}
    except Exception as exc:
        raise _internal_error(exc) from exc


@router.post("/evidence", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=True, action="history_record_evidence")
async def record_evidence(request: Request):
    """
    Record new evidence into the immutable evidence ledger.

    Body: {"subject_id": "claim-001", "lineage": "judge-v5",
           "kind": "factcheck_result", "locator": "run-001",
           "observed_claim": "...", "independent_of": "...",
           "status": "verified"}
    """
    body = await request.json()
    try:
        record = EvidenceRecord(
            subject_id=str(body.get("subject_id", "")),
            lineage=str(body.get("lineage", "scp-api")),
            kind=str(body.get("kind", "observation")),
            locator=str(body.get("locator", "")),
            observed_claim=str(body.get("observed_claim", "")),
            independent_of=str(body.get("independent_of", "")),
            status=str(body.get("status", "verified")),
            locator_sha256=body.get("locator_sha256"),
        )
        result = append_record(_EVIDENCE_PATH, record)
        return result
    except Exception as exc:
        raise _internal_error(exc) from exc

