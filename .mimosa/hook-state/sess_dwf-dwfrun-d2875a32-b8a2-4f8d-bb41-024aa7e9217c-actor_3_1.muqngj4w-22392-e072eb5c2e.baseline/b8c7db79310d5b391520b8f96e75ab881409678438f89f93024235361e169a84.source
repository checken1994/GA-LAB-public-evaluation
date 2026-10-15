# SCP CIRCUIT: M09 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M09-closure.json)
"""SCP V105 — Threat + Harm endpoints (Layer 2+3).

Live - admin auth required (Fix 4-a-003). Router IS registered in
api_server.py (route group "threat", minimum profile "full") via
`app.include_router(threat_router)`.
All 4 routes below (`/ai-scan/stats`, `/ai-scan/findings`, `/harm/stats`,
`/harm/incidents` — the router carries no prefix, so these are the real
registered paths) are LIVE and require `Depends(verify_admin)` directly in
every route decorator (audited pattern per reality test 4-a-003; the former
`check_admin` wrapper + its MagicMock test hook were removed — test hooks do
not belong in production auth paths) because `data/ai_threats.jsonl` +
`data/ai_harm_incidents.jsonl` contain sensitive threat findings + attack
signatures an attacker could use to bypass detection.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends

from scp.api._shared import verify_admin
from scp.core.request_run_ledger import RequestRunLedger, traced_request

logger = logging.getLogger("scp.api.threats")

_THREAT_ROUTES_LEDGER = RequestRunLedger()

router = APIRouter(prefix="", tags=["threats"])



def get_ai_scan_stats():
    from scp.core.ai_threat_scanner import get_threat_stats
    return get_threat_stats()

@router.get("/ai-scan/stats", dependencies=[Depends(verify_admin)])  # Fix 4-a-003: BFLA auth
@traced_request(_THREAT_ROUTES_LEDGER, require_write=False, action="ai_threat_stats")
async def ai_threat_stats():
    return get_ai_scan_stats()

@router.get("/ai-scan/findings", dependencies=[Depends(verify_admin)])  # Fix 4-a-003: BFLA auth
@traced_request(_THREAT_ROUTES_LEDGER, require_write=False, action="ai_threat_findings")
async def ai_threat_findings(limit: int = 20, source: str = ""):
    from scp.core.ai_threat_scanner import THREATS_DB
    db = THREATS_DB
    if not db.exists(): return {"findings": [], "total": 0}
    findings = []
    with open(db, encoding="utf-8") as f:
        for line in f:
            try:
                t = json.loads(line)
                if not source or t.get("source") == source:
                    findings.append(t)
            except Exception as _e:
                logger.debug("[silent-except] %s", _e, exc_info=True)
    findings.reverse()
    return {"findings": findings[:limit], "total": len(findings)}

@router.get("/harm/stats", dependencies=[Depends(verify_admin)])  # Fix 4-a-003: BFLA auth
@traced_request(_THREAT_ROUTES_LEDGER, require_write=False, action="harm_stats")
async def harm_stats():
    from scp.core.harm_detector import get_harm_stats
    return get_harm_stats()

@router.get("/harm/incidents", dependencies=[Depends(verify_admin)])  # Fix 4-a-003: BFLA auth
@traced_request(_THREAT_ROUTES_LEDGER, require_write=False, action="harm_incidents")
async def harm_incidents(limit: int = 20, harm_type: str = ""):
    from scp.core.harm_detector import HARM_DB
    db = HARM_DB
    if not db.exists(): return {"incidents": [], "total": 0}
    incidents = []
    with open(db, encoding="utf-8") as f:
        for line in f:
            try:
                inc = json.loads(line)
                if not harm_type or inc.get("harm_type") == harm_type:
                    incidents.append(inc)
            except Exception as _e:
                logger.debug("[silent-except] %s", _e, exc_info=True)
    incidents.reverse()
    return {"incidents": incidents[:limit], "total": len(incidents)}
