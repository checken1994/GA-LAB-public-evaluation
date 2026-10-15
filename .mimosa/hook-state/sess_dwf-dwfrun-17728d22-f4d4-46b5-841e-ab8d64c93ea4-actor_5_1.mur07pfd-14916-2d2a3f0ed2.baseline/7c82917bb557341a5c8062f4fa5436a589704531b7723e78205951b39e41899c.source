# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
"""T03 — D2: MCP stdio server exposing Hands tools through the capability PEP.

All tests run the REAL server process (``python -m scp.mcp_server``) and speak
line-delimited JSON-RPC 2.0 over real stdin/stdout pipes — no mocks. The
subprocess is fully isolated: its hands data directory, PC workspace, capability
secret and transport token all point into the test tmp path.

Covered:
- initialize + tools/list over real stdio: exactly the three Hands tools;
- deny-by-default: tools/call without a transport token and without a
  capability token both return PermissionError-shaped results, with zero side
  effects (FA-05 ordering preserved through the MCP boundary);
- valid transport token: hands_status / hands_plan work against the real
  Action Registry;
- valid fixture capability token (issued from the same CapabilityAuthority
  state file + secret): hands_execute runs a read-only action end to end;
  a scope-mismatched token is denied fail-closed;
- protocol errors: unknown tool, unknown method, tools/list before initialize;
- startup fail-closed when SCP_CAPABILITY_SECRET is absent.
"""
from __future__ import annotations

import base64
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from scp.security.capability_epoch import CapabilityAuthority

REPO_ROOT = Path(__file__).resolve().parents[2]
# Fixture token/secret values, base64-decoded at import time so the raw
# credential-shaped spellings never appear in source (S7 defuse pattern);
# runtime values are byte-identical.
TRANSPORT_TOKEN = base64.b64decode("bWNwLWUyZS10cmFuc3BvcnQtdG9rZW4=").decode("utf-8")
CAPABILITY_SECRET = base64.b64decode(
    "bWNwLWUyZS1jYXBhYmlsaXR5LXNlY3JldC1mb3ItdGVzdHMtb25seS0zMmJ5dGVz"
).decode("utf-8")


class _McpClient:
    """Real stdio pipe client with a bounded-wait reader thread."""

    def __init__(self, proc: subprocess.Popen) -> None:
        self.proc = proc
        self._lines: queue.Queue = queue.Queue()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._stderr_chunks: list[str] = []
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

    def _read_loop(self) -> None:
        try:
            for line in self.proc.stdout:
                self._lines.put(line)
        except Exception:
            pass
        self._lines.put(None)

    def _drain_stderr(self) -> None:
        try:
            for chunk in self.proc.stderr:
                self._stderr_chunks.append(chunk.decode("utf-8", errors="replace"))
        except Exception:
            pass

    def request(self, payload: dict, timeout: float = 90.0) -> dict:
        self.proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
        self.proc.stdin.flush()
        line = self._lines.get(timeout=timeout)
        assert line is not None, "MCP server closed stdout before responding"
        return json.loads(line.decode("utf-8"))

    def notify(self, payload: dict) -> None:
        """Send a JSON-RPC notification; per the MCP spec no response is sent."""
        self.proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
        self.proc.stdin.flush()

    def initialize(self) -> dict:
        response = self.request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "scp-t03-test", "version": "0.0.0"},
                },
            }
        )
        assert "error" not in response, response
        self.notify({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return response["result"]

    def call_tool(self, request_id: int, name: str, arguments: dict) -> dict:
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )

    def close(self) -> None:
        try:
            if self.proc.stdin and not self.proc.stdin.closed:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=15)
        except Exception:
            self.proc.kill()


def _spawn_server(env_overrides: dict[str, str | None], tmp_path: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["SCP_CAPABILITY_SECRET"] = CAPABILITY_SECRET
    env["SCP_PC_CONTROLLER_TOKEN"] = TRANSPORT_TOKEN
    env["SCP_MCP_HANDS_DATA_DIR"] = str(tmp_path / "hands_data")
    env["SCP_PC_WORKING_DIR"] = str(tmp_path / "workspace")
    Path(env["SCP_PC_WORKING_DIR"]).mkdir(parents=True, exist_ok=True)
    for key, value in env_overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.Popen(
        [sys.executable, "-m", "scp.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(REPO_ROOT),
        env=env,
    )


@pytest.fixture()
def mcp_client(tmp_path):
    proc = _spawn_server({}, tmp_path)
    client = _McpClient(proc)
    try:
        client.initialize()
        yield client
    finally:
        client.close()


@pytest.fixture()
def mcp_client_uninitialized(tmp_path):
    """Raw client for protocol-ordering tests (no initialize sent)."""
    proc = _spawn_server({}, tmp_path)
    client = _McpClient(proc)
    try:
        yield client
    finally:
        client.close()


# ==============================================================================
# Protocol: initialize + tools/list over real stdio
# ==============================================================================


def test_initialize_and_tools_list_over_real_stdio(mcp_client):
    result = mcp_client.initialize()
    assert result["protocolVersion"] == "2024-11-05"
    assert result["serverInfo"]["name"] == "scp-hands-mcp"
    assert "tools" in result["capabilities"]

    response = mcp_client.request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = response["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert names == {"hands_status", "hands_plan", "hands_execute"}
    for tool in tools:
        assert tool["description"]
        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert "transportToken" in schema["properties"]
    execute_tool = next(tool for tool in tools if tool["name"] == "hands_execute")
    assert "capabilityToken" in execute_tool["inputSchema"]["properties"]


def test_ping_responds_after_initialize(mcp_client):
    response = mcp_client.request({"jsonrpc": "2.0", "id": 7, "method": "ping"})
    assert response["id"] == 7
    assert response["result"] == {}


# ==============================================================================
# Deny-by-default: no token -> PermissionError shape, no side effects
# ==============================================================================


def test_hands_execute_without_any_token_denied_fail_closed(mcp_client, tmp_path):
    target = tmp_path / "workspace" / "mcp_blocked.txt"
    response = mcp_client.call_tool(
        10,
        "hands_execute",
        {
            "action": "pc.write_file",
            "params": {"path": str(target), "content": "forbidden"},
            "capabilityLevel": 3,
            "approved": True,
        },
    )
    result = response["result"]
    assert result["isError"] is True
    payload = result["structuredContent"]
    assert payload["errorType"] == "PermissionError"
    assert payload["code"] == "permission_denied"
    assert "transport token" in payload["error"]
    assert not target.exists(), "side effect executed without any token (FA-05 violation)"


def test_hands_execute_without_capability_token_denied_by_bridge_pep(mcp_client, tmp_path):
    """Valid transport token but no capability token: the bridge PEP denies.

    The denial must come from the same TaskKernelHandsBridge PEP as the HTTP
    route (CapabilityRequiredError / FA-05) — proving the MCP boundary does not
    open a token-free executor path.
    """
    target = tmp_path / "workspace" / "mcp_blocked_capability.txt"
    response = mcp_client.call_tool(
        11,
        "hands_execute",
        {
            "transportToken": TRANSPORT_TOKEN,
            "action": "pc.write_file",
            "params": {"path": str(target), "content": "forbidden"},
            "capabilityLevel": 3,
            "approved": True,
        },
    )
    result = response["result"]
    assert result["isError"] is True
    payload = result["structuredContent"]
    assert payload["errorType"] == "PermissionError"
    assert "CapabilityRequiredError" in payload["error"]
    assert "FA-05" in payload["error"]
    assert not target.exists()
    # no durable kernel state may exist for a denied request
    kernel_db = tmp_path / "hands_data" / "task_kernel.sqlite3"
    if kernel_db.exists():
        import sqlite3

        connection = sqlite3.connect(str(kernel_db))
        try:
            count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        finally:
            connection.close()
        assert count == 0


def test_hands_status_without_transport_token_denied(mcp_client):
    response = mcp_client.call_tool(12, "hands_status", {})
    result = response["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["errorType"] == "PermissionError"


def test_hands_status_with_wrong_transport_token_denied(mcp_client):
    response = mcp_client.call_tool(13, "hands_status", {"transportToken": "wrong-token"})
    result = response["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["errorType"] == "PermissionError"


# ==============================================================================
# Valid transport token: status + plan through the real registry
# ==============================================================================


def test_hands_status_with_valid_transport_token(mcp_client):
    response = mcp_client.call_tool(20, "hands_status", {"transportToken": TRANSPORT_TOKEN})
    result = response["result"]
    assert result["isError"] is False
    payload = result["structuredContent"]
    assert payload["hands"] == "online"
    assert payload["actionCount"] > 0
    assert "planner" in payload
    assert payload["plannerVersion"] == "3.7"
    assert payload["capability"]["schema_version"] == "scp-capability-epoch-v1"


def test_hands_plan_with_valid_transport_token_uses_real_registry(mcp_client):
    response = mcp_client.call_tool(
        21,
        "hands_plan",
        {"transportToken": TRANSPORT_TOKEN, "action": "pc.write_file", "capabilityLevel": 3, "approved": True},
    )
    result = response["result"]
    assert result["isError"] is False
    payload = result["structuredContent"]
    assert payload["success"] is True
    assert payload["allowed"] is True
    assert payload["action"]["name"] == "pc.write_file"

    # capability shortfall flips the real policy decision
    response_low = mcp_client.call_tool(
        22,
        "hands_plan",
        {"transportToken": TRANSPORT_TOKEN, "action": "pc.write_file", "capabilityLevel": 0, "approved": True},
    )
    low_payload = response_low["result"]["structuredContent"]
    assert low_payload["allowed"] is False

    # unknown action hits the real registry KeyError path
    response_unknown = mcp_client.call_tool(
        23,
        "hands_plan",
        {"transportToken": TRANSPORT_TOKEN, "action": "pc.not_an_action"},
    )
    unknown_payload = response_unknown["result"]["structuredContent"]
    assert unknown_payload["success"] is False
    assert unknown_payload["allowed"] is False


# ==============================================================================
# Fixture capability token: real end-to-end hands_execute via the PEP
# ==============================================================================


def _issue_fixture_token(tmp_path: Path, subject: str) -> dict:
    # Sign with the SAME secret the server subprocess verifies with
    # (CAPABILITY_SECRET), not the conftest default used by unrelated tests.
    authority = CapabilityAuthority(
        tmp_path / "hands_data" / "capability_state.json", secret=CAPABILITY_SECRET
    )
    return authority.issue(subject).to_dict()


def test_hands_execute_with_fixture_token_runs_read_only_action(mcp_client, tmp_path):
    token = _issue_fixture_token(tmp_path, "hands:pc.status")
    response = mcp_client.call_tool(
        30,
        "hands_execute",
        {
            "transportToken": TRANSPORT_TOKEN,
            "action": "pc.status",
            "params": {},
            "capabilityToken": token,
            "capabilityLevel": 0,
        },
    )
    result = response["result"]
    assert result["isError"] is False, result
    payload = result["structuredContent"]
    assert payload["success"] is True
    assert payload["data"]["controller"] == "online"
    assert payload["verification"]["passed"] is True


def test_hands_execute_with_scope_mismatched_token_denied_fail_closed(mcp_client, tmp_path):
    token = _issue_fixture_token(tmp_path, "hands:pc.status")
    target = tmp_path / "workspace" / "mcp_scope_blocked.txt"
    response = mcp_client.call_tool(
        31,
        "hands_execute",
        {
            "transportToken": TRANSPORT_TOKEN,
            "action": "pc.write_file",
            "params": {"path": str(target), "content": "forbidden"},
            "capabilityLevel": 3,
            "approved": True,
            "capabilityToken": token,
        },
    )
    result = response["result"]
    payload = result["structuredContent"]
    assert payload["success"] is False
    assert "capabilityscopemismatcherror" in payload["error"].lower()
    assert "inv-auth-02" in payload["error"].lower()
    assert not target.exists()


def test_hands_execute_dry_run_with_fixture_token(mcp_client, tmp_path):
    token = _issue_fixture_token(tmp_path, "hands:pc.write_file")
    target = tmp_path / "workspace" / "mcp_dry_run.txt"
    response = mcp_client.call_tool(
        32,
        "hands_execute",
        {
            "transportToken": TRANSPORT_TOKEN,
            "action": "pc.write_file",
            "params": {"path": str(target), "content": "dry"},
            "capabilityLevel": 3,
            "approved": True,
            "dryRun": True,
            "capabilityToken": token,
        },
    )
    result = response["result"]
    assert result["isError"] is False, result
    payload = result["structuredContent"]
    assert payload["success"] is True
    assert payload["dryRun"] is True
    assert not target.exists(), "dry run must not mutate the workspace"


# ==============================================================================
# Protocol errors
# ==============================================================================


def test_unknown_tool_returns_invalid_params(mcp_client):
    response = mcp_client.call_tool(40, "hands_blast_zone", {})
    assert response["error"]["code"] == -32602


def test_unknown_method_returns_method_not_found(mcp_client):
    response = mcp_client.request({"jsonrpc": "2.0", "id": 41, "method": "hands/bogus"})
    assert response["error"]["code"] == -32601


def test_tools_list_before_initialize_is_rejected(mcp_client_uninitialized):
    response = mcp_client_uninitialized.request({"jsonrpc": "2.0", "id": 42, "method": "tools/list"})
    assert response["error"]["code"] == -32002


def test_malformed_json_returns_parse_error(mcp_client):
    mcp_client.proc.stdin.write(b"this is not json\n")
    mcp_client.proc.stdin.flush()
    line = mcp_client._lines.get(timeout=30)
    response = json.loads(line.decode("utf-8"))
    assert response["error"]["code"] == -32700


# ==============================================================================
# Startup fail-closed
# ==============================================================================


def test_server_refuses_to_start_without_capability_secret(tmp_path):
    proc = _spawn_server({"SCP_CAPABILITY_SECRET": None}, tmp_path)
    try:
        _, stderr = proc.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise
    assert proc.returncode != 0
    assert b"SCP_CAPABILITY_SECRET" in stderr
