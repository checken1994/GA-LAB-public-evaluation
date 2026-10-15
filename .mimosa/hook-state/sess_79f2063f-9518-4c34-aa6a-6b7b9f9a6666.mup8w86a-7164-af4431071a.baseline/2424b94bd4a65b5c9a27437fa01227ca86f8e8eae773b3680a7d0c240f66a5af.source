# SCP CIRCUIT: M08 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M08-closure.json)
"""SCP V105 Ă¢â‚¬â€ Audit endpoints (24/7 multi-source audit).

Live - admin auth required (Fix 4-a-003). Router IS registered in
api_server.py (around line 589-611) via `app.include_router(audit_router)`.
The 2 routes below (`/v105/audit/stats`, `/v105/audit/findings`) are LIVE
and require `Depends(verify_admin)` because `data/audit_findings.jsonl`
contains sensitive audit findings (vulnerability disclosures + bypass
techniques) that an attacker could use to bypass detection.

After `python3 -m scp 8000` the 2 routes appear in `/openapi.json` and
the dashboard route table marks them `wired: true`.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends

from scp.api._shared import verify_admin
from scp.core.audit_fetcher import AUDIT_DB
from scp.core.request_run_ledger import RequestRunLedger, traced_request

logger = logging.getLogger("scp.api.audit")

_AUDIT_ROUTES_LEDGER = RequestRunLedger()

router = APIRouter(prefix="/v105/audit", tags=["audit"])

@router.get("/stats", dependencies=[Depends(verify_admin)])  # Fix 4-a-003: BFLA auth
@traced_request(_AUDIT_ROUTES_LEDGER, require_write=False, action="audit_stats")
async def audit_stats():
    """Get audit fetcher statistics."""
    from scp.core.audit_fetcher import get_audit_stats
    return get_audit_stats()

@router.get("/findings", dependencies=[Depends(verify_admin)])  # Fix 4-a-003: BFLA auth
@traced_request(_AUDIT_ROUTES_LEDGER, require_write=False, action="audit_findings")
async def audit_findings(limit: int = 20, source: str = ""):
    """Get recent audit findings."""
    db = AUDIT_DB
    if not db.exists():
        return {"findings": [], "total": 0}
    findings = []
    with open(db, encoding="utf-8") as f:
        for line in f:
            try:
                finding = json.loads(line)
                if not source or finding.get("source") == source:
                    findings.append(finding)
            except Exception as _e:
                logger.debug("[silent-except] %s", _e, exc_info=True)
    findings.reverse()  # newest first
    return {"findings": findings[:limit], "total": len(findings)}
