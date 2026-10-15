# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
"""SCP Hands v3.2│Ă¢â€Â¬Ă¢â‚¬Å“v3.6 local-only action and planner endpoints."""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from scp.core.capability_token import InvalidTokenSignatureError
from scp.core.request_run_ledger import RequestRunLedger, traced_request
from scp.hands.goal_parser import GoalParser
from scp.hands.hands_executor import HandsExecutor
from scp.hands.planner import HandsPlanner
from scp.hands.task_kernel_bridge import TaskKernelHandsBridge
from scp.security.capability_epoch import parse_capability_token

logger = logging.getLogger(__name__)

_HANDS_ROUTES_LEDGER = RequestRunLedger()

router = APIRouter(prefix="/v3/hands", tags=["v3.5-hands", "v3.6-planner"])
_hands = HandsExecutor()
_hands_bridge = TaskKernelHandsBridge(_hands)
_planner = HandsPlanner(_hands_bridge)
_goal_parser = GoalParser(_planner)


def _active_bridge() -> TaskKernelHandsBridge:
    global _hands_bridge
    if _hands_bridge.executor is not _hands:
        _hands_bridge = TaskKernelHandsBridge(_hands)
    return _hands_bridge


class CapabilityControlRequest(BaseModel):
    reason: str = Field(default="operator_control", min_length=1, max_length=256)


class HandsActionRequest(BaseModel):
    action: str = Field(min_length=3, max_length=64)
    params: dict[str, Any] = Field(default_factory=dict)
    capabilityLevel: int = Field(default=0, ge=0, le=5)
    approved: bool = False
    dryRun: bool = False
    capabilityToken: Any = Field(default=None, description="Zero-Trust capability token")


class HandsRollbackRequest(BaseModel):
    checkpointId: str = Field(min_length=8, max_length=128)
    capabilityLevel: int = Field(default=3, ge=0, le=5)
    approved: bool = False
    capabilityToken: Any = Field(default=None, description="Zero-Trust capability token")


class HandsReconcileRequest(BaseModel):
    taskId: str = Field(min_length=8, max_length=128)
    checkpointId: str = Field(min_length=8, max_length=128)
    outcome: str = Field(min_length=7, max_length=16)
    evidenceRef: str = Field(min_length=1, max_length=512)
    verifierId: str | None = Field(default=None, max_length=128)
    capabilityToken: Any = Field(default=None, description="Zero-Trust capability token (subject hands:reconcile)")


class ConfirmationRecordRequest(BaseModel):
    action: str = Field(min_length=1, max_length=128)
    target: str = Field(default="", max_length=2000)
    ttl_seconds: float | None = Field(default=3600.0, ge=1.0, le=86400.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlannerCreateRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=1000)
    steps: list[dict[str, Any]] = Field(min_length=1, max_length=20)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlannerRunRequest(BaseModel):
    capabilityLevel: int = Field(default=0, ge=0, le=5)
    approved: bool = False
    dryRun: bool = False
    stopOnFailure: bool = True
    capabilityToken: str = ""


class PlannerDagRunRequest(BaseModel):
    capabilityLevel: int = Field(default=0, ge=0, le=5)
    approved: bool = False
    dryRun: bool = False
    maxParallel: int = Field(default=2, ge=1, le=4)
    stopOnFailure: bool = True
    capabilityToken: str = ""


class GoalParseRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)


class PlannerRollbackRequest(BaseModel):
    capabilityLevel: int = Field(default=3, ge=0, le=5)
    approved: bool = False
    capabilityToken: Any = Field(default=None, description="Zero-Trust capability token")


class PlannerRecoveryRequest(BaseModel):
    decision: str = Field(min_length=6, max_length=32)
    evidenceRef: str = Field(min_length=1, max_length=512)
    approved: bool = False


def _guard(request: Request, token: str | None) -> None:
    """Require token for all requests to ensure zero-trust boundary."""
    configured = os.environ.get("SCP_PC_CONTROLLER_TOKEN", "")
    if not configured or not token or not __import__("hmac").compare_digest(token, configured):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="SCP Hands token is missing or invalid")


@router.get("/status")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=False, action="hands_status")
async def hands_status(request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    result = _hands.status()
    result["planner"] = _planner.status()
    result["plannerVersion"] = "3.7"
    return result


@router.get("/ledger/verify")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=False, action="hands_ledger_verify")
async def hands_ledger_verify(request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return _hands.audit_ledger.verify_provenance()


@router.post("/confirmations")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=True, action="hands_record_confirmation")
async def hands_record_confirmation(payload: ConfirmationRecordRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    from scp.security.confirmation_store import get_confirmation_store
    conf_store = get_confirmation_store()
    cid = conf_store.record_confirmation(
        action=payload.action,
        target=payload.target,
        user="operator",
        ttl_seconds=payload.ttl_seconds,
        metadata=payload.metadata,
    )
    return {"success": True, "confirmation_id": cid}



@router.get("/capabilities")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=False, action="hands_capability_status")
async def hands_capability_status(request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return {"success": True, "capability": _hands.capability_status()}


@router.post("/capabilities/revoke")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=True, action="hands_capability_revoke")
async def hands_capability_revoke(payload: CapabilityControlRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return {"success": True, "capability": _hands.revoke_capabilities(payload.reason, "operator")}


@router.post("/capabilities/restore")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=True, action="hands_capability_restore")
async def hands_capability_restore(payload: CapabilityControlRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return {"success": True, "capability": _hands.restore_capabilities(payload.reason, "operator")}


@router.get("/actions")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=False, action="hands_actions")
async def hands_actions(request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return {"version": "3.5", "actions": _hands.registry.list(), "backwardCompatibleRoutes": ["/status", "/actions", "/plan", "/execute", "/rollback"], "plannerVersion": "3.7"}


@router.post("/plan")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=False, action="hands_plan")
async def hands_plan(payload: HandsActionRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    try:
        return {"success": True, **_hands.registry.policy_preview(payload.action, payload.capabilityLevel, payload.approved)}
    except KeyError as exc:
        return {"success": False, "action": payload.action, "error": str(exc), "allowed": False}


@router.post("/execute")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=True, action="hands_execute")
async def hands_execute(payload: HandsActionRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    request_key = request.headers.get("X-SCP-Idempotency-Key") or request.headers.get("Idempotency-Key")
    token = parse_capability_token(payload.capabilityToken)
    try:
        return await _active_bridge().execute(
            payload.action,
            payload.params,
            payload.capabilityLevel,
            payload.approved,
            payload.dryRun,
            request_key=request_key,
            capability_token=token,
        )
    except (PermissionError, InvalidTokenSignatureError) as exc:
        # [M4 FIX 2026-09-11] The kernel bridge is fail-closed at the PEP:
        # a missing/invalid capability token raises PermissionError BEFORE
        # any action resolution or kernel mutation (FA-05). At the HTTP
        # boundary that is an authorization failure (403), mirroring the
        # pc_controller_routes convention — never a 500.
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/rollback")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=True, action="hands_rollback")
async def hands_rollback(payload: HandsRollbackRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    token = parse_capability_token(payload.capabilityToken)
    return await _active_bridge().rollback(
        payload.checkpointId,
        payload.capabilityLevel,
        payload.approved,
        capability_token=token,
    )


@router.post("/reconcile")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=True, action="hands_reconcile")
async def hands_reconcile(payload: HandsReconcileRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    # [AUDIT-FIX 2026-09-24] Reconcile writes a terminal outcome + evidence
    # into the task kernel — the same class of mutating decision as
    # execute/rollback — so it requires a capability token with subject
    # `hands:reconcile` (same issue/validate pattern as the executor PEP).
    # Fail-closed: missing/invalid/revoked/mismatched token → 403 before any
    # kernel mutation (FA-05).
    token = parse_capability_token(payload.capabilityToken)
    if token is None:
        raise HTTPException(
            status_code=403,
            detail="CapabilityRequiredError: hands reconcile requires an authorized capability token (FA-05)",
        )
    if str(getattr(token, "subject", "")) != "hands:reconcile":
        raise HTTPException(
            status_code=403,
            detail=(
                f"CapabilityScopeMismatchError: Token subject '{getattr(token, 'subject', None)}' "
                "does not permit action 'hands:reconcile' (INV-AUTH-02)"
            ),
        )
    try:
        token_valid = _hands.capability_authority.validate(token, required_subject="hands:reconcile")
    except InvalidTokenSignatureError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if not token_valid:
        raise HTTPException(
            status_code=403,
            detail="CapabilityRevokedError: Capability token is revoked or epoch is stale",
        )
    try:
        task = _active_bridge().reconcile_unknown(
            payload.taskId,
            payload.checkpointId,
            payload.outcome,
            payload.evidenceRef,
            payload.verifierId,
        )
        return {"success": True, "task": task}
    except Exception as exc:
        logger.warning("hands reconcile failed for task %s: %s", payload.taskId, exc, exc_info=True)
        return {"success": False, "error": str(exc), "taskId": payload.taskId}


@router.get("/planner/status")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=False, action="planner_status")
async def planner_status(request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return _planner.status()


@router.get("/planner")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=False, action="planner_list")
async def planner_list(request: Request, limit: int = 20, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return {"version": "3.7", "plans": _planner.list_plans(limit)}


@router.get("/planner/{plan_id}")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=False, action="planner_get")
async def planner_get(plan_id: str, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    plan = _planner.get_plan(plan_id)
    if not plan:
        return {"success": False, "error": "Plan not found", "planId": plan_id}
    return {"success": True, "plan": plan}


@router.post("/planner")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=True, action="planner_create")
async def planner_create(payload: PlannerCreateRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    for step in payload.steps:
        if step.get("approved"):
            step["approved"] = False
    try:
        plan = _planner.create_plan(payload.goal, payload.steps, payload.metadata)
        return {"success": True, "version": "3.7", "plan": plan}
    except (TypeError, ValueError, KeyError) as exc:
        return {"success": False, "version": "3.7", "error": str(exc)}


@router.post("/planner/{plan_id}/run")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=True, action="planner_run")
async def planner_run(plan_id: str, payload: PlannerRunRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return await _planner.run_plan(plan_id, payload.capabilityLevel, payload.approved, payload.dryRun, payload.stopOnFailure, capability_token=payload.capabilityToken)


@router.post("/planner/parse")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=False, action="planner_parse")
async def planner_parse(payload: GoalParseRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return await _goal_parser.parse(payload.goal)


@router.post("/planner/{plan_id}/run-dag")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=True, action="planner_run_dag")
async def planner_run_dag(plan_id: str, payload: PlannerDagRunRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return await _planner.run_dag(plan_id, payload.capabilityLevel, payload.approved, payload.dryRun, payload.maxParallel, payload.stopOnFailure, capability_token=payload.capabilityToken)


@router.post("/planner/{plan_id}/rollback")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=True, action="planner_rollback")
async def planner_rollback(plan_id: str, payload: PlannerRollbackRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    token = parse_capability_token(payload.capabilityToken)
    return await _planner.rollback_plan(
        plan_id,
        payload.capabilityLevel,
        payload.approved,
        capability_token=token,
    )


@router.post("/planner/{plan_id}/recover")
@traced_request(_HANDS_ROUTES_LEDGER, require_write=True, action="planner_recover")
async def planner_recover(plan_id: str, payload: PlannerRecoveryRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return _planner.recover_plan(plan_id, payload.decision, payload.evidenceRef, payload.approved)
