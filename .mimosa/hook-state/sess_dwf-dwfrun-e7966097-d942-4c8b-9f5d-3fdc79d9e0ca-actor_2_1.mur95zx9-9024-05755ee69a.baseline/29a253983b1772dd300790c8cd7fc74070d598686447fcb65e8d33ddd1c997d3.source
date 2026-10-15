# SCP CIRCUIT: M05 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M05-closure.json)
"""Local-only API for the bounded SCP AgentOrchestrator."""
from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from scp.api._shared import verify_admin
from scp.core.agent_orchestrator import AgentOrchestrator
from scp.core.request_run_ledger import RequestRunLedger, traced_request

_AGENT_LEDGER = RequestRunLedger()
_AGENT = AgentOrchestrator(ledger=_AGENT_LEDGER)
router = APIRouter(prefix="/v3/agent", tags=["v3-agent"])


class AgentPlanRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)
    parentTraceId: str | None = Field(default=None, max_length=120)


class AgentRunRequest(BaseModel):
    goal: str | None = Field(default=None, max_length=2000)
    planId: str | None = Field(default=None, max_length=120)
    execute: bool = False
    capabilityLevel: int = Field(default=0, ge=0, le=5)
    approved: bool = False
    dryRun: bool = False
    parentTraceId: str | None = Field(default=None, max_length=120)
    agentRunId: str | None = Field(default=None, max_length=120)


class AgentResumeRequest(BaseModel):
    agentRunId: str = Field(min_length=8, max_length=120)
    approvalId: str = Field(min_length=8, max_length=120)
    capabilityLevel: int = Field(default=3, ge=0, le=5)
    parentTraceId: str | None = Field(default=None, max_length=120)


class AutoFixPayload(BaseModel):
    file: str = Field(min_length=1, max_length=500)
    line: int = Field(default=0, ge=0, le=1_000_000)
    bugType: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    suggestedFix: str = Field(default="", max_length=20000)


class AutoFixApplyRequest(AutoFixPayload):
    proposalId: str = Field(min_length=8, max_length=120)
    parentTraceId: str | None = Field(default=None, max_length=120)


class AutoFixResumeRequest(BaseModel):
    proposalId: str = Field(min_length=8, max_length=120)
    permissionRequestId: str = Field(min_length=8, max_length=160)
    parentTraceId: str | None = Field(default=None, max_length=120)


def _guard(request: Request, token: str | None) -> None:
    # [Caddy bypass fix] request.client.host qua reverse proxy = 127.0.0.1
    # (Caddy's IP), KHÔNG phải client thật. Fix: bắt buộc dùng shared secret
    # header X-SCP-Internal-Token từ Caddy, HOẶC SCP_AGENT_LOCAL_ONLY=0
    # + token hợp lệ. Không còn tin tưởng địa chỉ IP.
    internal_secret = os.environ.get("SCP_INTERNAL_SECRET", "")
    provided_internal = request.headers.get("X-SCP-Internal-Token", "")
    if internal_secret and hmac.compare_digest(provided_internal, internal_secret):
        return  # Caddy đã xác thực phía trước

    # Direct localhost access (không qua proxy) — vẫn cho phép nhưng cần token
    configured = os.environ.get("SCP_PC_CONTROLLER_TOKEN", "")
    if configured and token and hmac.compare_digest(token, configured):
        return


    raise HTTPException(status_code=403, detail="SCP Agent requires internal token or valid controller token")


def _parent_trace(request: Request, supplied: str | None) -> str | None:
    value = str(supplied or "").strip()
    if value:
        return value[:120]
    run = getattr(getattr(request, "state", None), "scp_run", None)
    return str(getattr(run, "trace_id", "") or "")[:120] or None


@router.get("/status")
@traced_request(_AGENT_LEDGER, require_write=False, action="agent_status")
async def agent_status(request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return {"success": True, **_AGENT.status()}


@router.post("/plan")
@traced_request(_AGENT_LEDGER, require_write=False, action="agent_plan")
async def agent_plan(payload: AgentPlanRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return await _AGENT.propose(payload.goal, parent_trace_id=_parent_trace(request, payload.parentTraceId))


@router.post("/run")
@traced_request(_AGENT_LEDGER, require_write=True, action="agent_run")
async def agent_run(payload: AgentRunRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return await _AGENT.run(
        goal=payload.goal,
        plan_id=payload.planId,
        execute=payload.execute,
        capability_level=payload.capabilityLevel,
        approved=payload.approved,
        dry_run=payload.dryRun,
        parent_trace_id=_parent_trace(request, payload.parentTraceId),
        agent_run_id=payload.agentRunId,
    )


@router.post("/resume")
@traced_request(_AGENT_LEDGER, require_write=True, action="agent_resume")
async def agent_resume(payload: AgentResumeRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return await _AGENT.resume(
        payload.agentRunId,
        payload.approvalId,
        capability_level=payload.capabilityLevel,
        parent_trace_id=_parent_trace(request, payload.parentTraceId),
    )


@router.post("/autofix/propose")
@traced_request(_AGENT_LEDGER, require_write=False, action="agent_autofix_propose")
async def agent_autofix_propose(payload: AutoFixPayload, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return await _AGENT.autofix_propose(payload.model_dump(), parent_trace_id=_parent_trace(request, None))


@router.post("/autofix/apply", dependencies=[Depends(verify_admin)])
@traced_request(_AGENT_LEDGER, require_write=True, action="agent_autofix_apply")
async def agent_autofix_apply(payload: AutoFixApplyRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    data = payload.model_dump()
    proposal_id = str(data.pop("proposalId"))
    parent_trace_id = str(data.pop("parentTraceId", "") or "") or _parent_trace(request, None)
    return await _AGENT.autofix_apply(proposal_id, data, parent_trace_id=parent_trace_id)


@router.post("/autofix/resume")
@traced_request(_AGENT_LEDGER, require_write=True, action="agent_autofix_resume")
async def agent_autofix_resume(payload: AutoFixResumeRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return await _AGENT.autofix_resume(
        payload.proposalId,
        payload.permissionRequestId,
        parent_trace_id=_parent_trace(request, payload.parentTraceId),
    )


__all__ = ["router"]
