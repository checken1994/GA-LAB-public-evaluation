# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
"""Minimal MCP-compatible stdio server for the SCP Hands tools.

Protocol choice (recorded for the D2 audit): the server is a self-implemented,
line-delimited JSON-RPC 2.0 handler (stdlib only) covering the MCP methods
``initialize``, ``ping``, ``tools/list`` and ``tools/call``. Rationale:

1. The MCP stdio transport is newline-delimited JSON-RPC 2.0, so three methods
   need roughly two hundred auditable lines — smaller than any SDK dependency
   tree and free of new supply-chain surface (no new pin required).
2. The security-sensitive parts (transport-token check, capability-token PEP)
   must stay in this repository's own fail-closed code, not inside a third-
   party abstraction.
3. No network listener is opened: stdin/stdout only, one JSON message per line.
   Everything the server logs goes to stderr, never to stdout (protocol
   channel).

Authorization contract (mirrors ``scp/api/routes/hands_routes.py``):

- Every tool call carries ``transportToken`` in its arguments — the exact
  equivalent of the ``X-SCP-PC-Token`` HTTP header — checked with
  ``hmac.compare_digest`` against ``SCP_PC_CONTROLLER_TOKEN``. Not configured,
  missing or wrong ⇒ PermissionError-shaped denial (deny-by-default).
- ``hands_execute`` additionally requires a Zero-Trust capability token via
  ``capabilityToken`` (tool argument — the equivalent of the
  ``capabilityToken`` field in ``HandsActionRequest``). The call goes through
  ``TaskKernelHandsBridge.execute`` — the same PEP as the HTTP route — so a
  missing/invalid token raises ``PermissionError`` (FA-05) before any action
  resolution or kernel mutation. There is no alternate executor path.
- ``hands_status`` / ``hands_plan`` are read-only but still guard the
  transport token, mirroring the route-level ``_guard``.

Runtime configuration:
- ``SCP_PC_CONTROLLER_TOKEN`` — transport token (required, deny-by-default).
- ``SCP_MCP_HANDS_DATA_DIR`` — optional hands data directory override
  (isolation for local runs); defaults to the standard ``data/hands``.
- ``SCP_CAPABILITY_SECRET`` — required by the capability subsystem itself
  (GAP-09 fail-closed); without it the process refuses to start.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from scp.core.capability_token import InvalidTokenSignatureError
from scp.hands.hands_executor import HandsExecutor
from scp.hands.planner import HandsPlanner
from scp.hands.task_kernel_bridge import TaskKernelHandsBridge
from scp.security.capability_epoch import parse_capability_token

logger = logging.getLogger("scp.mcp_server")

MCP_SERVER_NAME = "scp-hands-mcp"
MCP_SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
MAX_LINE_BYTES = 1_000_000
HANDS_DATA_DIR_ENV = "SCP_MCP_HANDS_DATA_DIR"

# JSON-RPC 2.0 / MCP error codes
_PARSE_ERROR = -32700
_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602
_NOT_INITIALIZED = -32002


class _RpcError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class TransportAuthError(PermissionError):
    """Transport-token guard denial (PermissionError-shaped, deny-by-default)."""


def _build_runtime() -> tuple[HandsExecutor, TaskKernelHandsBridge, HandsPlanner]:
    data_dir_override = os.environ.get(HANDS_DATA_DIR_ENV, "").strip()
    if data_dir_override:
        executor = HandsExecutor(data_dir=Path(data_dir_override))
    else:
        executor = HandsExecutor()
    bridge = TaskKernelHandsBridge(executor)
    planner = HandsPlanner(executor=bridge)
    return executor, bridge, planner


def _transport_token_schema() -> dict[str, Any]:
    return {
        "type": "string",
        "description": (
            "Transport token; the equivalent of the X-SCP-PC-Token HTTP header "
            "used by the /v3/hands routes. Required (deny-by-default)."
        ),
    }


def _tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "hands_status",
            "description": (
                "Read-only Hands executor and planner status through the same "
                "token guard as GET /v3/hands/status."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {"transportToken": _transport_token_schema()},
                "required": ["transportToken"],
            },
        },
        {
            "name": "hands_plan",
            "description": (
                "Preview the real Action Registry policy decision "
                "(allow/deny plus reason) for a Hands action, without executing."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "transportToken": _transport_token_schema(),
                    "action": {"type": "string", "description": "Registered Hands action name"},
                    "capabilityLevel": {"type": "integer", "minimum": 0, "maximum": 5},
                    "approved": {"type": "boolean"},
                },
                "required": ["transportToken", "action"],
            },
        },
        {
            "name": "hands_execute",
            "description": (
                "Execute a registered Hands action through the "
                "TaskKernelHandsBridge capability PEP (same path as POST "
                "/v3/hands/execute). Requires an authorized capability token; "
                "missing or invalid tokens are denied fail-closed."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "transportToken": _transport_token_schema(),
                    "action": {"type": "string", "description": "Registered Hands action name"},
                    "params": {"type": "object", "default": {}},
                    "capabilityToken": {
                        "description": (
                            "Zero-Trust capability token (dict or JSON string) "
                            "issued by CapabilityAuthority, scope hands:<action>"
                        )
                    },
                    "capabilityLevel": {"type": "integer", "minimum": 0, "maximum": 5},
                    "approved": {"type": "boolean"},
                    "dryRun": {"type": "boolean"},
                    "idempotencyKey": {
                        "type": "string",
                        "description": "Equivalent of the X-SCP-Idempotency-Key header",
                    },
                },
                "required": ["transportToken", "action"],
            },
        },
    ]


class McpStdioServer:
    """Sequential, single-process MCP stdio server (no concurrency, no ports)."""

    def __init__(
        self,
        executor: HandsExecutor,
        bridge: TaskKernelHandsBridge,
        planner: HandsPlanner,
        stdin: Any = None,
        stdout: Any = None,
    ) -> None:
        self._executor = executor
        self._bridge = bridge
        self._planner = planner
        self._stdin = stdin if stdin is not None else sys.stdin
        self._stdout = stdout if stdout is not None else sys.stdout
        self._initialized = False
        self._tool_handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "hands_status": self._tool_hands_status,
            "hands_plan": self._tool_hands_plan,
            "hands_execute": self._tool_hands_execute,
        }

    @classmethod
    def from_env(cls) -> McpStdioServer:
        executor, bridge, planner = _build_runtime()
        return cls(executor, bridge, planner)

    # ------------------------------------------------------------------
    # Protocol loop
    # ------------------------------------------------------------------
    def serve(self) -> int:
        for raw_line in self._stdin:
            line = raw_line.strip()
            if not line:
                continue
            if len(line.encode("utf-8", errors="replace")) > MAX_LINE_BYTES:
                response = self._error_response(None, _INVALID_REQUEST, "Request line exceeds the size cap")
            else:
                response = self._handle_line(line)
            if response is not None:
                self._write_message(response)
        return 0

    def _write_message(self, message: dict[str, Any]) -> None:
        self._stdout.write(json.dumps(message, ensure_ascii=True, default=str) + "\n")
        self._stdout.flush()

    def _handle_line(self, line: str) -> dict[str, Any] | None:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return self._error_response(None, _PARSE_ERROR, "Parse error")
        if not isinstance(message, dict) or not isinstance(message.get("method", ""), str):
            return self._error_response(None, _INVALID_REQUEST, "Invalid Request")
        method = message["method"]
        request_id = message.get("id")
        is_notification = "id" not in message
        params = message.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return self._error_response(request_id, _INVALID_PARAMS, "Invalid params: params must be an object")
        try:
            result = self._dispatch(method, params)
        except _RpcError as exc:
            if is_notification:
                return None
            return self._error_response(request_id, exc.code, exc.message)
        except Exception as exc:  # fail-closed for the caller, server stays alive
            logger.exception("Unhandled error while dispatching %s", method)
            if is_notification:
                return None
            return self._error_response(request_id, _INVALID_REQUEST, f"Unhandled server error: {type(exc).__name__}")
        if is_notification or result is None:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    # ------------------------------------------------------------------
    # Method dispatch
    # ------------------------------------------------------------------
    def _dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if method == "initialize":
            return self._initialize(params)
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return {}
        if method in {"tools/list", "tools/call"} and not self._initialized:
            raise _RpcError(_NOT_INITIALIZED, "Server not initialized")
        if method == "tools/list":
            return {"tools": _tool_definitions()}
        if method == "tools/call":
            return self._tools_call(params)
        raise _RpcError(_METHOD_NOT_FOUND, f"Method not found: {method}")

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        client_version = str(params.get("protocolVersion", ""))
        protocol_version = client_version if client_version in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
        self._initialized = True
        return {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": MCP_SERVER_NAME, "version": MCP_SERVER_VERSION},
            "instructions": (
                "SCP Hands MCP tools. Every call requires the transport token "
                "(tool argument, header equivalent); hands_execute additionally "
                "requires a scoped capability token. Deny-by-default."
            ),
        }

    # ------------------------------------------------------------------
    # tools/call
    # ------------------------------------------------------------------
    def _tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or name not in self._tool_handlers:
            raise _RpcError(_INVALID_PARAMS, f"Unknown tool: {name}")
        if not isinstance(arguments, dict):
            raise _RpcError(_INVALID_PARAMS, "Invalid params: arguments must be an object")
        handler = self._tool_handlers[name]
        try:
            payload = handler(arguments)
            is_error = False
        except (PermissionError, InvalidTokenSignatureError) as exc:
            # The exact authorization tuple handled by hands_routes (HTTP 403);
            # InvalidTokenSignatureError subclasses PermissionError, so this
            # branch maps both to the MCP PermissionError-shaped result.
            logger.warning("Tool %s denied: %s", name, type(exc).__name__)
            payload = self._permission_denied_payload(exc)
            is_error = True
        except (ValueError, TypeError, KeyError, RuntimeError) as exc:
            logger.warning("Tool %s failed: %s", name, type(exc).__name__)
            payload = {"errorType": type(exc).__name__, "code": "tool_failure", "error": str(exc)}
            is_error = True
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str),
                }
            ],
            "structuredContent": payload,
            "isError": is_error,
        }

    @staticmethod
    def _permission_denied_payload(exc: PermissionError) -> dict[str, Any]:
        return {
            "errorType": "PermissionError",
            "code": "permission_denied",
            "error": str(exc),
        }

    # ------------------------------------------------------------------
    # Transport guard (X-SCP-PC-Token equivalent)
    # ------------------------------------------------------------------
    def _check_transport_token(self, arguments: dict[str, Any]) -> None:
        configured = os.environ.get("SCP_PC_CONTROLLER_TOKEN", "")
        supplied = str(arguments.get("transportToken") or "")
        if not configured or not supplied or not hmac.compare_digest(supplied, configured):
            raise TransportAuthError("SCP MCP transport token is missing or invalid (deny-by-default)")

    # ------------------------------------------------------------------
    # Tool handlers — same PEP path as scp/api/routes/hands_routes.py
    # ------------------------------------------------------------------
    def _tool_hands_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._check_transport_token(arguments)
        result = self._executor.status()
        result["planner"] = self._planner.status()
        result["plannerVersion"] = "3.7"
        result["transport"] = "mcp-stdio"
        return result

    def _tool_hands_plan(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._check_transport_token(arguments)
        action = arguments.get("action")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("hands_plan requires a non-empty action name")
        capability_level = int(arguments.get("capabilityLevel") or 0)
        approved = bool(arguments.get("approved") or False)
        try:
            return {
                "success": True,
                **self._executor.registry.policy_preview(action, capability_level, approved),
            }
        except KeyError as exc:
            return {"success": False, "action": action, "error": str(exc), "allowed": False}

    def _tool_hands_execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._check_transport_token(arguments)
        action = arguments.get("action")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("hands_execute requires a non-empty action name")
        params = arguments.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError("hands_execute params must be an object")
        capability_level = int(arguments.get("capabilityLevel") or 0)
        approved = bool(arguments.get("approved") or False)
        dry_run = bool(arguments.get("dryRun") or False)
        capability_token = parse_capability_token(arguments.get("capabilityToken"))
        request_key = str(arguments.get("idempotencyKey") or "") or None
        result = asyncio.run(
            self._bridge.execute(
                action,
                params,
                capability_level,
                approved,
                dry_run,
                request_key=request_key,
                capability_token=capability_token,
            )
        )
        return result


def main() -> int:
    logging.basicConfig(
        stream=sys.stderr,
        level=os.environ.get("SCP_MCP_LOG_LEVEL", "WARNING"),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    try:
        server = McpStdioServer.from_env()
    except Exception as exc:
        # Fail-closed startup: without the capability secret or a usable hands
        # runtime the server must not serve anything.
        logger.error(
            "scp-mcp-server failed to start: %s: %s", type(exc).__name__, exc,
            exc_info=True,
        )
        print(
            f"scp-mcp-server failed to start: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2
    try:
        return server.serve()
    finally:
        close = getattr(server._bridge, "close", None)
        if callable(close):
            close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
