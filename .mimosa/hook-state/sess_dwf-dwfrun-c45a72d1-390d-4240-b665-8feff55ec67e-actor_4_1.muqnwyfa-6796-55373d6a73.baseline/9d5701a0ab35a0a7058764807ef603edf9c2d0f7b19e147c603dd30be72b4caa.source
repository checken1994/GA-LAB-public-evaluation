# SCP CIRCUIT: M11 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M11-closure.json)
"""
[Task 7-A] V98 Security endpoints │Ă¢â€Â¬Ă¢â‚¬Â extracted from api_server.py

TÄ‚Â¡Ă‚ÂºĂ‚Â I SAO: api_server.py 2,285 LOC god file. TĂ„â€Ă‚Â¡ch 8 routes /v98/* vĂ„â€Ă‚Â o module
nĂ„â€Ă‚Â y. Backward-compatible │Ă¢â€Â¬Ă¢â‚¬Â public API paths/methods unchanged.

Routes:
  POST /v98/analyze-session      │Ă¢â€Â¬Ă¢â‚¬Â Rogue AI detection on session
  POST /v98/run-simulation       │Ă¢â€Â¬Ă¢â‚¬Â Trigger threat simulation
  POST /v98/run-intel-crawl      │Ă¢â€Â¬Ă¢â‚¬Â Trigger threat intel crawl
  GET  /v98/status               │Ă¢â€Â¬Ă¢â‚¬Â All V98 module status
  GET  /v98/counter/stats        │Ă¢â€Â¬Ă¢â‚¬Â Counter response stats
  GET  /v98/canary/triggers      │Ă¢â€Â¬Ă¢â‚¬Â Canary token triggers
  GET  /v98/error-store/stats    │Ă¢â€Â¬Ă¢â‚¬Â ErrorStore stats
  GET  /v98/attack-memory/stats  │Ă¢â€Â¬Ă¢â‚¬Â AttackPatternMemory stats
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

# Import shared deps from api_server (same pattern as api/chat.py)
from scp.api import _shared
from scp.api._shared import SessionAnalyzeRequest, SimulationRequest, get_judge, verify_admin
from scp.core.request_run_ledger import RequestRunLedger, traced_request

_ADMIN_V98_LEDGER = RequestRunLedger()

router = APIRouter(tags=["v98"])


@router.post("/v98/analyze-session")
@traced_request(_ADMIN_V98_LEDGER, require_write=False, action="analyze_session")
async def analyze_session(req: SessionAnalyzeRequest, _admin: bool = Depends(verify_admin)):
    """Analyze session for rogue AI behavior (9 lenses)."""
    judge = get_judge()
    result = judge.analyze_session_rogue(req.session_logs, req.model_responses)
    if result is None:
        raise HTTPException(status_code=503, detail="RogueAIDetector not available")
    return result


@router.post("/v98/run-simulation")
@traced_request(_ADMIN_V98_LEDGER, require_write=True, action="run_simulation")
async def run_simulation(req: SimulationRequest, _admin: bool = Depends(verify_admin)):
    """Trigger threat simulation cycle."""
    judge = get_judge()
    result = await judge.run_threat_simulation(count=req.count)
    if result is None:
        raise HTTPException(status_code=503, detail="ThreatSimulatorEngine not available")
    return result


@router.post("/v98/run-intel-crawl")
@traced_request(_ADMIN_V98_LEDGER, require_write=True, action="run_intel_crawl")
async def run_intel_crawl(_admin: bool = Depends(verify_admin)):
    """Trigger threat intelligence crawl."""
    judge = get_judge()
    result = await judge.run_threat_intel_crawl()
    return {"updates": result, "count": len(result)}


@router.get("/v98/status", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_ADMIN_V98_LEDGER, require_write=False, action="v98_status")
async def v98_status():
    """Get status of all V98 security modules."""
    judge = get_judge()
    return {
        "version": _shared._SCP_VERSION,  # [FIX-12] single source
        "domain_experts": len(judge.domain_experts),
        "slms": len(judge.domain_experts),
        "v98_modules": judge.get_v98_status(),
        "falsification": judge.falsification is not None,
        "error_store": judge.error_store is not None,
        "governance": judge.governance is not None,
    }


@router.get("/v98/counter/stats", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_ADMIN_V98_LEDGER, require_write=False, action="counter_stats")
async def counter_stats():
    """Counter response engine stats."""
    judge = get_judge()
    if not judge.counter_response:
        raise HTTPException(status_code=503, detail="CounterResponseEngine not available")
    return judge.counter_response.stats()


@router.get("/v98/canary/triggers", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_ADMIN_V98_LEDGER, require_write=False, action="canary_triggers")
async def canary_triggers(limit: int = 20):
    """Get canary token triggers."""
    judge = get_judge()
    if not judge.canary_monitor:
        raise HTTPException(status_code=503, detail="CanaryTokenMonitor not available")
    return {"triggers": judge.canary_monitor.get_all_triggers(limit=limit)}


@router.get("/v98/error-store/stats", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_ADMIN_V98_LEDGER, require_write=False, action="error_store_stats")
async def error_store_stats():
    """ErrorStore stats."""
    judge = get_judge()
    if not judge.error_store:
        raise HTTPException(status_code=503, detail="ErrorStore not available")
    return judge.error_store.stats()


@router.get("/v98/attack-memory/stats", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_ADMIN_V98_LEDGER, require_write=False, action="attack_memory_stats")
async def attack_memory_stats():
    """AttackPatternMemory stats."""
    judge = get_judge()
    if not judge.attack_memory:
        raise HTTPException(status_code=503, detail="AttackPatternMemory not available")
    return judge.attack_memory.stats()
