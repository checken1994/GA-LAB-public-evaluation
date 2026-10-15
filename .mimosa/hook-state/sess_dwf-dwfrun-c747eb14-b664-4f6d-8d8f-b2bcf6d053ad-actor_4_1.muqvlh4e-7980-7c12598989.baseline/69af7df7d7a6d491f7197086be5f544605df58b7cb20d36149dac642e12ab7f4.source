# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
"""Local-only SCP V3.1 PC Controller API."""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from scp.core.capability_token import InvalidTokenSignatureError
from scp.core.request_run_ledger import RequestRunLedger, traced_request
from scp.pc_control.pc_controller import PCController

logger = logging.getLogger(__name__)

_PC_CONTROLLER_ROUTES_LEDGER = RequestRunLedger()

router = APIRouter(prefix="/v3/pc", tags=["v3-pc-controller"])
_controller = PCController()


def _iter_live_ask_kernel_adapters() -> list[tuple[str, Any]]:
    """[F-RUN-01 audit-r2 2026-10-01] Snapshot of the LIVE ask-kernel adapters.

    The /ask route's kernel adapters are owned by scp.api_server
    (`_ASK_KERNEL_ADAPTERS`, keyed by (db_path, trace_path)). The import is
    lazy and inside the function on purpose: pc_controller_routes is imported
    BY api_server at module level, so a module-level import would be circular;
    by request time api_server is fully loaded. When no adapter exists yet
    there is no live kernel to kill — the durable kill-switch flag plus the
    /ask admission gate (scp/api_server.py::_pc_kill_switch_engaged) cover
    every later ask.
    """
    try:
        from scp.api_server import _ASK_KERNEL_ADAPTERS

        return [(str(key), adapter) for key, adapter in list(_ASK_KERNEL_ADAPTERS.items())]
    except Exception as exc:
        logger.error("[F-RUN-01] cannot reach ask-kernel adapter registry: %s", type(exc).__name__, exc_info=True)
        return []


def _engage_kernel_global_kill() -> dict[str, Any]:
    """Best-effort TaskKernel-level kill on every live ask-kernel adapter.

    TẠI SAO: engaging only the PC flag left the ask path untouched (audit A9:
    /ask still ran to COMPLETED after POST /v3/pc/kill). Wiring the kill
    through taskkernel.set_global_kill (the existing kernel enforcement point)
    makes claim()/claim_next()/renew_lease() fail with KillSwitchActive and
    fences every in-flight lease via the epoch bump — in-flight asks die
    fail-closed instead of completing. Failures never undo the flag file:
    kernel kill is defense-in-depth on top of the /ask admission gate.
    """
    results: dict[str, Any] = {"engaged": [], "errors": []}
    for key, adapter in _iter_live_ask_kernel_adapters():
        kernel = getattr(adapter, "kernel", None)
        if kernel is None or not hasattr(kernel, "set_global_kill"):
            results["errors"].append({"adapter": key, "error": "no_kernel"})
            continue
        try:
            epoch = int(kernel.set_global_kill(True, actor="pc_kill_switch"))
            results["engaged"].append({"adapter": key, "epoch": epoch})
            logger.warning("[F-RUN-01] kernel GLOBAL_KILL_ON engaged via pc kill switch (adapter=%s epoch=%d)", key, epoch)
        except Exception as exc:
            results["errors"].append({"adapter": key, "error": type(exc).__name__})
            logger.error("[F-RUN-01] kernel global kill FAILED for adapter %s: %s", key, type(exc).__name__, exc_info=True)
    return results


def _release_kernel_global_kill() -> dict[str, Any]:
    """Counterpart of _engage_kernel_global_kill for /kill/clear.

    The kernel control row persists global_kill=1 in SQLite — without this
    release the asks would stay kernel-blocked after the flag file is cleared
    (fail-closed direction, but it would strand the operator). Best-effort +
    loudly logged: a failed release leaves the kernel killed (safe side) and
    the error visible.
    """
    results: dict[str, Any] = {"released": [], "errors": []}
    for key, adapter in _iter_live_ask_kernel_adapters():
        kernel = getattr(adapter, "kernel", None)
        if kernel is None or not hasattr(kernel, "set_global_kill"):
            results["errors"].append({"adapter": key, "error": "no_kernel"})
            continue
        try:
            kernel.set_global_kill(False, actor="pc_kill_switch_clear")
            results["released"].append({"adapter": key})
            logger.info("[F-RUN-01] kernel GLOBAL_KILL_OFF released via pc kill-switch clear (adapter=%s)", key)
        except Exception as exc:
            results["errors"].append({"adapter": key, "error": type(exc).__name__})
            logger.error("[F-RUN-01] kernel global-kill release FAILED for adapter %s: %s", key, type(exc).__name__, exc_info=True)
    return results


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
    result = _controller.engage_kill_switch(payload.reason)
    # [F-RUN-01 audit-r2 2026-10-01] Engaging the kill switch must ALSO engage
    # the TaskKernel-level global kill on every live ask-kernel adapter — the
    # flag file alone never reached the ask path (audit A9: /ask COMPLETED
    # after kill). The kernel bridge fences in-flight leases (epoch bump) and
    # blocks new claim(); the /ask admission gate covers adapters that do not
    # exist yet. Kernel engagement is additive in the response for operator
    # visibility; it never downgrades the flag-file engagement itself.
    if isinstance(result, dict) and result.get("success"):
        result = {**result, "kernel_global_kill": _engage_kernel_global_kill()}
    return result


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
        result = _controller.clear_kill_switch(payload.approved, capability_token=token, confirmation_id=confirmation_id)
    except (PermissionError, InvalidTokenSignatureError) as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    # [F-RUN-01 audit-r2 2026-10-01] Symmetric kernel release: the control row
    # global_kill=1 persists in the kernel DB, so a successful flag-file clear
    # must also flip taskkernel.set_global_kill(False) on live adapters or the
    # asks stay kernel-blocked after the operator cleared the switch.
    if isinstance(result, dict) and result.get("success") and result.get("killSwitch") is False:
        result = {**result, "kernel_global_kill": _release_kernel_global_kill()}
    return result
