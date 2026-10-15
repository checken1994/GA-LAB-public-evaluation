# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
"""Local-only SCP V3.1 PC Controller API."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from scp.core.capability_token import InvalidTokenSignatureError
from scp.core.request_run_ledger import RequestRunLedger, traced_request
from scp.pc_control.pc_controller import PCController

_PC_CONTROLLER_ROUTES_LEDGER = RequestRunLedger()

router = APIRouter(prefix="/v3/pc", tags=["v3-pc-controller"])
_controller = PCController()


class PlanRequest(BaseModel):
    command: str = Field(min_length=1, max_length=2000)
    capabilityLevel: int = Field(default=0, ge=0, le=5)
    approved: bool = False
    capability_token: str | None = None
    capabilityToken: str | None = None
    confirmation_id: str | None = None
    confirmationId: str | None = None


class ExecuteRequest(PlanRequest):
    timeout: int = Field(default=120, ge=1, le=300)


class ReadRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1000)
    maxBytes: int = Field(default=200_000, ge=1_000, le=1_000_000)
    capability_token: str | None = None
    capabilityToken: str | None = None


class WriteRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1000)
    content: str = Field(max_length=2_000_000)
    capabilityLevel: int = Field(default=0, ge=0, le=5)
    approved: bool = False
    capability_token: str | None = None
    capabilityToken: str | None = None
    confirmation_id: str | None = None
    confirmationId: str | None = None


class KillRequest(BaseModel):
    reason: str = Field(default="user requested", max_length=500)


class ClearKillRequest(BaseModel):
    approved: bool = False
    capability_token: str | None = None
    capabilityToken: str | None = None
    confirmation_id: str | None = None
    confirmationId: str | None = None


def _is_local(request: Request) -> bool:
    """[Caddy bypass fix] KHÔNG tin request.client.host qua reverse proxy.
    Nếu có X-Forwarded-For → request đi qua proxy → KHÔNG phải local."""
    if request.headers.get("X-Forwarded-For"):
        return False  # proxied = not local
    host = request.client.host if request.client else ""
    return host in {"127.0.0.1", "::1", "localhost"}


def _guard(request: Request, token: str | None) -> None:
    """Require token for all requests to ensure zero-trust boundary."""
    configured = os.environ.get("SCP_PC_CONTROLLER_TOKEN", "")
    if not configured or not token or not __import__("hmac").compare_digest(token, configured):
        raise HTTPException(status_code=403, detail="PC Controller token is missing or invalid")


@router.get("/status")
@traced_request(_PC_CONTROLLER_ROUTES_LEDGER, require_write=False, action="pc_status")
async def pc_status(request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return _controller.status()


@router.post("/plan")
@traced_request(_PC_CONTROLLER_ROUTES_LEDGER, require_write=False, action="pc_plan")
async def pc_plan(payload: PlanRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    cid = payload.confirmation_id or payload.confirmationId
    return _controller.plan(payload.command, payload.capabilityLevel, payload.approved, confirmation_id=cid)


@router.post("/execute")
@traced_request(_PC_CONTROLLER_ROUTES_LEDGER, require_write=True, action="pc_execute")
async def pc_execute(
    payload: ExecuteRequest,
    request: Request,
    x_scp_pc_token: str | None = Header(default=None),
    x_scp_capability_token: str | None = Header(default=None),
) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    token = x_scp_capability_token or payload.capability_token or payload.capabilityToken
    cid = payload.confirmation_id or payload.confirmationId
    try:
        return await _controller.execute(
            payload.command,
            capability_token=token,
            capability_level=payload.capabilityLevel,
            approved=payload.approved,
            timeout=payload.timeout,
            confirmation_id=cid,
        )
    except (PermissionError, InvalidTokenSignatureError) as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/read")
@traced_request(_PC_CONTROLLER_ROUTES_LEDGER, require_write=False, action="pc_read")
async def pc_read(
    payload: ReadRequest,
    request: Request,
    x_scp_pc_token: str | None = Header(default=None),
    x_scp_capability_token: str | None = Header(default=None),
) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    token = x_scp_capability_token or payload.capability_token or payload.capabilityToken
    try:
        return await _controller.read_file(payload.path, payload.maxBytes, capability_token=token)
    except (PermissionError, InvalidTokenSignatureError) as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/write")
@traced_request(_PC_CONTROLLER_ROUTES_LEDGER, require_write=True, action="pc_write")
async def pc_write(
    payload: WriteRequest,
    request: Request,
    x_scp_pc_token: str | None = Header(default=None),
    x_scp_capability_token: str | None = Header(default=None),
) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    token = x_scp_capability_token or payload.capability_token or payload.capabilityToken
    cid = payload.confirmation_id or payload.confirmationId
    try:
        return await _controller.write_file(
            payload.path,
            payload.content,
            capability_token=token,
            capability_level=payload.capabilityLevel,
            approved=payload.approved,
            confirmation_id=cid,
        )
    except (PermissionError, InvalidTokenSignatureError) as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/kill")
@traced_request(_PC_CONTROLLER_ROUTES_LEDGER, require_write=True, action="pc_kill")
async def pc_kill(payload: KillRequest, request: Request, x_scp_pc_token: str | None = Header(default=None)) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    return _controller.engage_kill_switch(payload.reason)


@router.post("/kill/clear")
@traced_request(_PC_CONTROLLER_ROUTES_LEDGER, require_write=True, action="pc_clear_kill")
async def pc_clear_kill(
    payload: ClearKillRequest,
    request: Request,
    x_scp_pc_token: str | None = Header(default=None),
    x_scp_capability_token: str | None = Header(default=None),
) -> dict[str, Any]:
    _guard(request, x_scp_pc_token)
    token = x_scp_capability_token or payload.capability_token or payload.capabilityToken
    confirmation_id = payload.confirmation_id or payload.confirmationId
    try:
        return _controller.clear_kill_switch(payload.approved, capability_token=token, confirmation_id=confirmation_id)
    except (PermissionError, InvalidTokenSignatureError) as exc:
        raise HTTPException(status_code=403, detail=str(exc))
