"""
Risk Intelligence routes (S10) — PR0-PR5 graded public-risk response.

Routes:
  GET  /v105/risk/stats          — RiskClassifier + IncidentStateMachine stats
  POST /v105/risk/classify       — Classify a set of signals into PR0-PR5
  GET  /v105/risk/incidents      — List active incidents
  POST /v105/risk/incidents      — Open a new incident
  GET  /v105/risk/alert-rules    — Inspect AlertRouter channel config
"""
from __future__ import annotations

import threading
from collections import OrderedDict

from fastapi import APIRouter, Depends, Request

from scp.api._shared import verify_admin
from scp.core.request_run_ledger import RequestRunLedger, traced_request
from scp.risk_intelligence import (
    FORBIDDEN_BROADCAST_OPERATIONS,
    AlertRouter,
    IncidentState,
    IncidentStateMachine,
    RiskAssessment,
    RiskClassifier,
    RiskLevel,
    RiskSignal,
)

router = APIRouter(prefix="/v105/risk", tags=["risk-intelligence"])
_LEDGER = RequestRunLedger()

# Singleton classifier (stateless, safe to share)
_classifier = RiskClassifier()
_alert_router = AlertRouter()

# In-process incident registry (bounded, thread-safe)
_MAX_INCIDENTS = 1000
_incidents: OrderedDict[str, dict] = OrderedDict()
_incidents_lock = threading.Lock()


@router.get("/stats", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="risk_stats")
async def risk_stats():
    """Risk Intelligence subsystem status."""
    return {
        "subsystem": "risk_intelligence",
        "status": "active",
        "risk_levels": [lv.value for lv in RiskLevel],
        "forbidden_operations": list(FORBIDDEN_BROADCAST_OPERATIONS),
        "active_incidents": len(_incidents),
        "alert_channels_configured": len(_alert_router.channels),
    }


@router.post("/classify", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="risk_classify")
async def risk_classify(request: Request):
    """
    Classify risk signals into PR0-PR5.

    Body: {"signals": [{"source_id": ..., "kind": "official|independent|...", ...}],
           "desired_level": "PR2", "hazard_severity": "moderate"}
    """
    body = await request.json()
    raw_signals = body.get("signals", [])
    desired_level = body.get("desired_level", "PR2")
    hazard_severity = body.get("hazard_severity", "moderate")

    signals = [
        RiskSignal(
            source_id=str(s.get("source_id", "")),
            kind=str(s.get("kind", "independent")),
            lineage_id=s.get("lineage_id"),
            fresh=bool(s.get("fresh", True)),
            location_validated=bool(s.get("location_validated", False)),
            observed_directly=bool(s.get("observed_directly", False)),
        )
        for s in raw_signals
    ]

    assessment: RiskAssessment = _classifier.classify(
        signals,
        desired_level=desired_level,
        hazard_severity=hazard_severity,
    )
    return {
        "level": assessment.level.value if assessment.level else None,
        "pending_verification": assessment.pending_verification,
        "official_sources": assessment.official_sources,
        "independent_lineages": assessment.independent_lineages,
        "reasons": assessment.reasons,
    }


@router.get("/incidents", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="risk_incidents_list")
async def list_incidents():
    """List all tracked incidents and their current state."""
    with _incidents_lock:
        return {"incidents": list(_incidents.values())}


@router.post("/incidents", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=True, action="risk_open_incident")
async def open_incident(request: Request):
    """
    Open a new incident and start its state machine.

    Body: {"incident_id": ..., "category": "CYBER|HEALTH|...",
           "pr_level": "PR3", "description": "..."}
    """
    body = await request.json()
    incident_id = str(body.get("incident_id", "")) or f"inc_{len(_incidents) + 1:04d}"
    category = str(body.get("category", "INTERNAL"))
    pr_level = str(body.get("pr_level", "PR2"))
    description = str(body.get("description", ""))

    sm = IncidentStateMachine(incident_id=incident_id)
    record = {
        "incident_id": incident_id,
        "category": category,
        "pr_level": pr_level,
        "description": description,
        "state": sm.state.value if hasattr(sm, "state") else IncidentState.OBSERVED.value,
    }
    with _incidents_lock:
        if len(_incidents) >= _MAX_INCIDENTS:
            _incidents.popitem(last=False)
        _incidents[incident_id] = record
    return record


@router.get("/alert-rules", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="risk_alert_rules")
async def alert_rules():
    """Inspect AlertRouter routing table and forbidden operations."""
    return {
        "default_routes": {
            "CYBER": "SOC",
            "HEALTH": "HEALTH_AUTHORITY",
            "FIRE": "AUTHORIZED_EMERGENCY_CONTACT",
            "INFRASTRUCTURE": "UTILITY_OPERATOR",
            "INTERNAL": "SCP_ADMIN",
        },
        "forbidden_operations": list(FORBIDDEN_BROADCAST_OPERATIONS),
        "configured_channels": list(_alert_router.channels.keys()),
    }
