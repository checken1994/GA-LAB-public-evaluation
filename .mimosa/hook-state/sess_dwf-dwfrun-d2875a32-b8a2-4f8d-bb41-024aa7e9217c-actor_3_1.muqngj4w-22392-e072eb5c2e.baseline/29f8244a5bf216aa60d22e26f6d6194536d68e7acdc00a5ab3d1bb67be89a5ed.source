# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
"""Admin control routes for capability and defensive escalation.

These endpoints are intentionally separate from the chat and agent lanes.
They require the canonical admin dependency, never accept an actor from the
client, and fail closed when the live judge/escalation manager is unavailable.
No audio/video or threat payload is stored here.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from scp.api._shared import verify_admin
from scp.meta.capability_levels import CapabilityLevel, get_capability_manager

router = APIRouter(tags=["control"])


class CapabilityChangeRequest(BaseModel):
    level: int = Field(ge=0, le=5)
    reason: str = Field(min_length=3, max_length=1000)


class CapabilityDeescalateRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class EscalationApprovalRequest(BaseModel):
    action: str = Field(default="default", min_length=1, max_length=200)


def _live_judge() -> Any:
    """Return the production judge singleton, never construct a new judge."""
    try:
        from scp.api_server_parts.helpers import _judge
    except Exception as exc:  # pragma: no cover - import guard
        raise HTTPException(503, "SCP judge is unavailable") from exc
    if _judge is None:
        raise HTTPException(503, "SCP judge is not ready")
    return _judge


def _escalation_manager() -> Any:
    judge = _live_judge()
    manager = getattr(judge, "escalation_manager", None)
    if manager is None:
        raise HTTPException(503, "Escalation manager is unavailable")
    return manager


def _redact(value: Any, key: str = "") -> Any:
    """Redact secrets from threat data before returning it to the dashboard."""
    sensitive = ("token", "secret", "password", "api_key", "authorization", "cookie")
    if any(part in key.lower() for part in sensitive):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item, key) for item in value[:100]]
    if isinstance(value, str):
        return value[:2000]
    return value


@router.get("/v105/capability/status", dependencies=[Depends(verify_admin)])
async def capability_status() -> dict[str, Any]:
    """Return current capability, allowed actions and audit trail."""
    return get_capability_manager().escalation_status()


@router.post("/v105/capability/escalate", dependencies=[Depends(verify_admin)])
async def capability_escalate(payload: CapabilityChangeRequest) -> dict[str, Any]:
    """Human-admin-only capability escalation; the client cannot choose actor."""
    try:
        target = CapabilityLevel(payload.level)
    except ValueError as exc:  # defensive even though Pydantic bounds the value
        raise HTTPException(422, "Invalid capability level") from exc
    manager = get_capability_manager()
    approved = manager.request_escalation(
        target, payload.reason, actor="human_via_api"
    )
    if not approved:
        raise HTTPException(403, "Capability escalation was denied")
    return {"approved": True, "status": manager.escalation_status()}


@router.post("/v105/capability/de-escalate", dependencies=[Depends(verify_admin)])
async def capability_deescalate(payload: CapabilityDeescalateRequest) -> dict[str, Any]:
    """Lower capability by one level; safer action is allowed for an admin."""
    manager = get_capability_manager()
    before = int(manager.get_current_level())
    manager.de_escalate(payload.reason, actor="human_via_api")
    return {
        "status": manager.escalation_status(),
        "changed": int(manager.get_current_level()) != before,
    }


@router.get("/v105/escalation/status", dependencies=[Depends(verify_admin)])
async def escalation_status() -> dict[str, Any]:
    """Return active escalation state from the production judge singleton."""
    manager = _escalation_manager()
    return _redact(manager.get_dashboard_status())


@router.post(
    "/v105/escalation/{threat_id}/approve",
    dependencies=[Depends(verify_admin)],
)
async def approve_escalation(
    threat_id: str = Path(min_length=1, max_length=200),
    payload: EscalationApprovalRequest | None = None,
) -> dict[str, Any]:
    """Cancel the dead-man timer after an authenticated human decision."""
    manager = _escalation_manager()
    status = manager.get_dashboard_status()
    active_ids = {str(item.get("threat_id")) for item in status.get("active", [])}
    if threat_id not in active_ids:
        raise HTTPException(404, "Active escalation not found")
    manager.approve(threat_id, (payload.action if payload else "default"))
    return {"status": "approved", "threat_id": threat_id, "escalation": _redact(manager.get_dashboard_status())}


@router.post(
    "/v105/escalation/{threat_id}/reject",
    dependencies=[Depends(verify_admin)],
)
async def reject_escalation(
    threat_id: str = Path(min_length=1, max_length=200),
) -> dict[str, Any]:
    """Cancel the dead-man timer after an authenticated human rejection."""
    manager = _escalation_manager()
    status = manager.get_dashboard_status()
    active_ids = {str(item.get("threat_id")) for item in status.get("active", [])}
    if threat_id not in active_ids:
        raise HTTPException(404, "Active escalation not found")
    manager.reject(threat_id)
    return {"status": "rejected", "threat_id": threat_id, "escalation": _redact(manager.get_dashboard_status())}
