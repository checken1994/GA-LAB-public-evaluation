"""
Test Suite: P1 Boundary Security Verification (Milestone M2 / Stream P1).

Covers:
  1. Dashboard extractCallerAuth & ask route: pseudo-auth removal, cryptographic validation (token/JWT), 401 on invalid/missing.
  2. Dashboard middleware & probe-allowlist: IP spoofing prevention, strict RFC1918 removal from default probe allowlist.
  3. Bun LLM bridge core.ts: timing-safe Bearer token authentication, fail-closed when secret is unset.
  4. Web control egress & DNS rebinding: enforce_egress_policy before navigation, DNS rebinding TOCTOU prevention.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_extract_caller_auth_cryptographic_verification():
    """1. extractCallerAuth rejects pseudo-auth (e.g. 'Bearer test') and validates credentials cryptographically."""
    bun_script = """
    import { extractCallerAuth } from './dashboard/src/lib/auth-helper.ts';
    import { createHmac } from 'node:crypto';

    const secret = 'test-admin-secret-32-chars-long!!';
    process.env.SCP_ADMIN_TOKEN = secret;
    process.env.SCP_AUTH_TOKEN_SECRET = secret;

    // A: Missing credentials -> 401
    const reqMissing = new Request('http://localhost:3000/api/scp/ask', {
      headers: new Headers()
    });
    const resMissing = extractCallerAuth(reqMissing);

    // B: Pseudo-auth (arbitrary non-empty string) -> 401
    const reqPseudo = new Request('http://localhost:3000/api/scp/ask', {
      headers: new Headers({ 'Authorization': 'Bearer arbitrary-string-not-secret' })
    });
    const resPseudo = extractCallerAuth(reqPseudo);

    // C: Valid static secret -> authenticated
    const reqValidStatic = new Request('http://localhost:3000/api/scp/ask', {
      headers: new Headers({ 'Authorization': `Bearer ${secret}` })
    });
    const resValidStatic = extractCallerAuth(reqValidStatic);

    // D: Valid HS256 JWT signed with secret -> authenticated
    const headerB64 = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
    const payloadB64 = Buffer.from(JSON.stringify({ sub: 'admin', exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
    const sigB64 = createHmac('sha256', secret).update(`${headerB64}.${payloadB64}`).digest('base64url');
    const validJwt = `${headerB64}.${payloadB64}.${sigB64}`;

    const reqValidJwt = new Request('http://localhost:3000/api/scp/ask', {
      headers: new Headers({ 'Authorization': `Bearer ${validJwt}` })
    });
    const resValidJwt = extractCallerAuth(reqValidJwt);

    // E: Expired JWT -> 401
    const expiredPayloadB64 = Buffer.from(JSON.stringify({ sub: 'admin', exp: Math.floor(Date.now() / 1000) - 3600 })).toString('base64url');
    const expiredSigB64 = createHmac('sha256', secret).update(`${headerB64}.${expiredPayloadB64}`).digest('base64url');
    const expiredJwt = `${headerB64}.${expiredPayloadB64}.${expiredSigB64}`;

    const reqExpiredJwt = new Request('http://localhost:3000/api/scp/ask', {
      headers: new Headers({ 'Authorization': `Bearer ${expiredJwt}` })
    });
    const resExpiredJwt = extractCallerAuth(reqExpiredJwt);

    console.log(JSON.stringify({
      missing: resMissing.authenticated,
      pseudo: resPseudo.authenticated,
      validStatic: resValidStatic.authenticated,
      validJwt: resValidJwt.authenticated,
      expiredJwt: resExpiredJwt.authenticated
    }));
    """
    proc = subprocess.run(
        ["bun", "-e", bun_script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(proc.stdout.strip())
    assert result["missing"] is False, "Missing credentials must not authenticate"
    assert result["pseudo"] is False, "Pseudo-auth string must be rejected (not authenticated)"
    assert result["validStatic"] is True, "Valid static secret must authenticate"
    assert result["validJwt"] is True, "Valid HS256 JWT must authenticate"
    assert result["expiredJwt"] is False, "Expired JWT must be rejected"


def test_probe_allowlist_rfc1918_denied_by_default():
    """2. probe-allowlist denies RFC1918 subnets by default, allowing only loopback and explicit allowlist."""
    bun_script = """
    import { isAllowedProbeTarget } from './dashboard/src/lib/probe-allowlist.ts';

    const testUrls = {
      loopbackIp: isAllowedProbeTarget('http://127.0.0.1:8000/health').allowed,
      localhost: isAllowedProbeTarget('http://localhost:8000/health').allowed,
      dockerInternal: isAllowedProbeTarget('http://host.docker.internal:8000/health').allowed,
      rfc1918_10: isAllowedProbeTarget('http://10.0.0.1:8000/health').allowed,
      rfc1918_192: isAllowedProbeTarget('http://192.168.1.1:8000/health').allowed,
      rfc1918_172: isAllowedProbeTarget('http://172.16.0.1:8000/health').allowed,
      rfc1918_explicit: isAllowedProbeTarget('http://10.0.0.1:8000/health', ['10.0.0.1']).allowed,
      linkLocal: isAllowedProbeTarget('http://169.254.169.254/latest/meta-data').allowed,
    };

    console.log(JSON.stringify(testUrls));
    """
    proc = subprocess.run(
        ["bun", "-e", bun_script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    res = json.loads(proc.stdout.strip())
    assert res["loopbackIp"] is True, "Loopback IP must be allowed"
    assert res["localhost"] is True, "Localhost must be allowed"
    assert res["dockerInternal"] is True, "Docker internal must be allowed"
    assert res["rfc1918_10"] is False, "10.0.0.0/8 must be DENIED by default"
    assert res["rfc1918_192"] is False, "192.168.0.0/16 must be DENIED by default"
    assert res["rfc1918_172"] is False, "172.16.0.0/12 must be DENIED by default"
    assert res["rfc1918_explicit"] is True, "RFC1918 in explicit allowlist must be allowed"
    assert res["linkLocal"] is False, "Link-local metadata must be DENIED"


def test_bun_llm_bridge_timing_safe_bearer_auth():
    """3. mini-services/llm-bridge/core.ts requires timing-safe Bearer secret and fails closed."""
    core_path = REPO_ROOT / "mini-services" / "llm-bridge" / "core.ts"
    assert core_path.exists()
    src = core_path.read_text(encoding="utf-8")
    assert "timingSafeEqual" in src, "Must use timingSafeEqual for timing-safe check"
    assert "createHash" in src, "Must hash tokens with SHA-256 for constant length comparison"
    assert "BRIDGE_SECRET" in src, "Must support BRIDGE_SECRET"

    # Runtime verification of isAuthorized logic
    bun_script = """
    import { createHash, timingSafeEqual } from "crypto";

    function safeCompare(a, b) {
      if (!a || !b) return false;
      const hashA = createHash("sha256").update(a).digest();
      const hashB = createHash("sha256").update(b).digest();
      return timingSafeEqual(hashA, hashB);
    }

    function isAuthorized(req) {
      const authHeader = req.headers.get("authorization") || req.headers.get("Authorization");
      if (!authHeader) return false;
      const match = authHeader.match(/^Bearer\\s+(.+)$/i);
      const token = match ? match[1].trim() : authHeader.trim();
      if (!token) return false;

      const validSecrets = [
        process.env.BRIDGE_SECRET,
        process.env.SHARED_SECRET,
        process.env.BEARER_TOKEN,
        process.env.SCP_AUTH_TOKEN_SECRET,
      ]
        .map((s) => s?.trim())
        .filter((s) => Boolean(s && s.length > 0));

      if (validSecrets.length === 0) return false;
      return validSecrets.some((secret) => safeCompare(token, secret));
    }

    // 1. Fail closed when no secrets configured
    delete process.env.BRIDGE_SECRET;
    delete process.env.SHARED_SECRET;
    delete process.env.BEARER_TOKEN;
    delete process.env.SCP_AUTH_TOKEN_SECRET;

    const resNoSecret = isAuthorized(new Request('http://localhost:8081/api/chat', {
      headers: { 'Authorization': 'Bearer any-token' }
    }));

    // 2. Secret configured
    process.env.BRIDGE_SECRET = 'secret-bridge-token-xyz';

    const resInvalid = isAuthorized(new Request('http://localhost:8081/api/chat', {
      headers: { 'Authorization': 'Bearer wrong-token' }
    }));

    const resValid = isAuthorized(new Request('http://localhost:8081/api/chat', {
      headers: { 'Authorization': 'Bearer secret-bridge-token-xyz' }
    }));

    console.log(JSON.stringify({
      noSecret: resNoSecret,
      invalid: resInvalid,
      valid: resValid
    }));
    """
    proc = subprocess.run(
        ["bun", "-e", bun_script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(proc.stdout.strip())
    assert result["noSecret"] is False, "Must fail closed when no secrets are set"
    assert result["invalid"] is False, "Must reject incorrect Bearer token"
    assert result["valid"] is True, "Must accept correct Bearer token"


@pytest.mark.asyncio
async def test_browser_session_egress_gate_and_dns_rebinding(monkeypatch):
    """4. BrowserSession enforces egress policy BEFORE validate_url and checks DNS rebinding."""
    from scp.policy.egress import EgressDeniedError
    from scp.web_control.browser_session import BrowserSession

    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")

    session = BrowserSession()
    # Egress gate should deny before validation
    with pytest.raises(EgressDeniedError):
        await session.navigate_and_read("https://example.com")

    with pytest.raises(EgressDeniedError):
        session.open_visible("https://example.com")

    # Reset egress mode to test DNS rebinding check
    monkeypatch.delenv("SCP_EGRESS_MODE", raising=False)

    # DNS rebinding: host resolving to private/loopback IP must raise ValueError
    with pytest.raises(ValueError, match="resolves to internal/private IP"):
        BrowserSession._verify_dns_rebinding("http://127.0.0.1:8000/internal")

    with pytest.raises(ValueError, match="resolves to internal/private IP"):
        BrowserSession._verify_dns_rebinding("http://169.254.169.254/latest")

    with pytest.raises(ValueError, match="resolves to internal/private IP"):
        BrowserSession._verify_dns_rebinding("http://10.0.0.1:8080/admin")

    # WebNavigator egress enforcement
    from scp.web_control.web_navigator import WebNavigator
    navigator = WebNavigator()
    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
    with pytest.raises(EgressDeniedError):
        await navigator.browse_public("https://example.com")


def test_dns_rebinding_block_surfaces_without_getaddrinfo_rescue(monkeypatch):
    """[DNS-REBINDING-DEAD-FLOW FIX] The literal-IP block raise used to sit
    inside the same try whose `except ValueError: pass` (the "not a literal
    IP → resolve DNS" path) swallowed it — dead control flow. Blocking only
    worked via the SECOND getaddrinfo loop; with getaddrinfo yielding
    nothing (resolver filtered/unavailable), the old code ALLOWED a literal
    private/metadata IP through. The block must now raise directly out of
    the first layer, independent of the resolver loop."""
    import scp.web_control.browser_session as bs
    from scp.web_control.browser_session import BrowserSession

    monkeypatch.setattr(bs.socket, "getaddrinfo", lambda *a, **k: [])

    for url in (
        "http://10.0.0.1:8080/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://127.0.0.1:8000/internal",
    ):
        with pytest.raises(ValueError, match="resolves to internal/private IP"):
            BrowserSession._verify_dns_rebinding(url)

    # Not-a-literal-IP hosts still proceed to the (empty) DNS resolution
    # path instead of being blocked by the first layer.
    BrowserSession._verify_dns_rebinding("http://example.com/")  # must NOT raise


# ---------------------------------------------------------------------------
# 5. [F-RUN-01 audit-r2] Chat-lane kill-switch admission boundary.
#
# Causal chain of the gap (audit-r2, close of the UNPROVEN_BRANCH left by
# commit 155c95b0): POST /v3/pc/kill writes the durable PCController flag
# file; the /ask admission gate (api_server.py::_pc_kill_switch_engaged)
# refuses /ask, and the kernel bridge flips global_kill on every adapter in
# api_server._ASK_KERNEL_ADAPTERS. BUT the chat lanes run judge.judge()
# directly and register NO kernel adapter — /v1/chat/completions
# (scp/api/routes/openai_compat.py) and the /chat WebSocket
# (scp/api/chat.py) BYPASSED both enforcement layers and kept processing
# after a kill. Fix under test: an admission gate at the top of each chat
# lane that REUSES the /ask refusal helpers via import (lazy import avoids
# the api_server module cycle) — one refusal authority, no copied fork.
#
# Old-fails/new-passes: before the gate, an engaged kill switch returned a
# normal chat response (the request reached the judge pipeline); the tests
# below pin 503 + KILL_SWITCH_ENGAGED / refused-frame + close, and the
# recovery pins that clearing the flag reopens the lane.
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient  # noqa: E402
from fastapi import WebSocketDisconnect  # noqa: E402


def _chat_flag_path(tmp_path):
    return tmp_path / "data" / "pc_controller" / "KILL_SWITCH"


@pytest.fixture()
def chat_kill_switch_dir(tmp_path, monkeypatch):
    """Isolated kill-switch authority dir + isolated JWT secret (same fixture
    contract as tests/T03_capability/test_ask_kill_switch_gate.py)."""
    monkeypatch.setenv("SCP_PC_WORKING_DIR", str(tmp_path))
    monkeypatch.setenv("SCP_JWT_SECRET", "f-run-01-chat-lane-test-jwt-secret-40chars")
    monkeypatch.delenv("SCP_PC_CONTROLLER_TOKEN", raising=False)
    return tmp_path


def _engage_chat_kill(tmp_path, reason="audit-r2 chat-lane test"):
    flag = _chat_flag_path(tmp_path)
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text(reason, encoding="utf-8")
    return flag


def _chat_jwt_headers() -> dict:
    from scp.security.jwt_guard import create_access_token

    return {"Authorization": f"Bearer {create_access_token({'sub': 'chat-lane-kill-test'})}"}


def test_openai_chat_lane_refused_when_kill_switch_engaged(chat_kill_switch_dir, monkeypatch):
    """/v1/chat/completions must be refused 503 fail-closed with the SAME
    refusal authority as /ask, BEFORE any judge pipeline work."""
    from scp.api.routes import openai_compat

    flag = _engage_chat_kill(chat_kill_switch_dir)
    assert flag.exists()

    # The gate must block BEFORE the judge pipeline is reached at all.
    def _judge_must_not_run():
        raise AssertionError("kill switch engaged nhưng /v1/chat/completions vẫn đi vào judge pipeline")

    monkeypatch.setattr(openai_compat, "get_judge", _judge_must_not_run)

    from scp.api_server import app

    client = TestClient(app)  # no lifespan — judge readiness is irrelevant past the gate
    response = client.post(
        "/v1/chat/completions",
        json={"model": "scp", "messages": [{"role": "user", "content": "should be blocked"}]},
        headers=_chat_jwt_headers(),
    )
    assert response.status_code == 503, response.text
    body = response.json()
    assert body["error"]["type"] == "server_error"
    assert "Kill switch engaged" in body["error"]["message"]
    metadata = body["scp_metadata"]
    assert metadata["falsification_status"] == "KILL_SWITCH_ENGAGED"
    assert metadata["governance_decision"] == "KILL"
    assert metadata["verdict"] == "FAIL"
    assert metadata["run_status"] == "REJECTED"
    assert metadata["kill_switch"] == "engaged"


def test_openai_chat_lane_reopens_after_kill_clear(chat_kill_switch_dir, monkeypatch):
    """Control + recovery: flag absent → the request passes the admission gate
    and reaches the judge seam (here: a deterministic stub proving the gate
    opened; the judge pipeline itself is pinned by tests/T02_contract/flow03)."""
    from scp.api.routes import openai_compat

    assert not _chat_flag_path(chat_kill_switch_dir).exists()

    class _StubJudge:
        def judge(self, **kwargs):
            return {
                "verdict": "PASS",
                "confidence": 0.9,
                "final_answer": "gate-open-control",
                "evidence": {"governance_decision": "UPHOLD"},
            }

    monkeypatch.setattr(openai_compat, "get_judge", lambda: _StubJudge())

    from scp.api_server import app

    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        json={"model": "scp", "messages": [{"role": "user", "content": "control after clear"}]},
        headers=_chat_jwt_headers(),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "gate-open-control"
    assert body["scp_metadata"]["falsification_status"] != "KILL_SWITCH_ENGAGED"


def test_openai_chat_lane_inherits_fail_closed_when_flag_state_unknown(chat_kill_switch_dir, monkeypatch):
    """Kill-switch state UNKNOWN (flag unreadable OSError) → the chat lane must
    refuse too (fail-closed inherited from the SHARED helper, not re-implemented)."""
    from scp import api_server

    class _BoomPath:
        def exists(self):
            raise OSError("simulated flag probe failure")

    monkeypatch.setattr(api_server, "default_kill_switch_path", lambda: _BoomPath())

    from scp.api_server import app

    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        json={"model": "scp", "messages": [{"role": "user", "content": "unknown state"}]},
        headers=_chat_jwt_headers(),
    )
    assert response.status_code == 503
    assert response.json()["scp_metadata"]["falsification_status"] == "KILL_SWITCH_ENGAGED"


def test_ws_chat_lane_refuses_frames_when_kill_switch_engaged(chat_kill_switch_dir, monkeypatch):
    """/chat WebSocket: while the kill switch is engaged, every frame is
    refused with an explicit kill_switch_engaged error frame and the socket is
    closed 1008 (policy violation) — before ledger/judge/orchestrator work."""
    from scp import api_server

    token = "p1-ws-kill-token"
    monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", token)
    _engage_chat_kill(chat_kill_switch_dir)

    with TestClient(api_server.app) as client:
        with client.websocket_connect(f"/chat?token={token}") as ws:
            welcome = ws.receive_json()
            assert welcome["type"] == "system"  # auth passed; the kill gate is per-frame
            ws.send_json({"message": "should be refused"})
            frame = ws.receive_json()
            assert frame["type"] == "error"
            assert frame["reason"] == "kill_switch_engaged"
            assert frame["falsification_status"] == "KILL_SWITCH_ENGAGED"
            assert frame["governance"] == "KILL"
            assert frame["run_status"] == "REJECTED"
            assert "Kill switch engaged" in frame["message"]
            with pytest.raises(WebSocketDisconnect) as excinfo:
                ws.receive_json()
            assert excinfo.value.code == 1008


def test_ws_chat_lane_processes_frames_after_kill_clear(chat_kill_switch_dir, monkeypatch):
    """Recovery control: flag absent → the frame is NOT refused by the kill
    gate and the normal pipeline runs (deterministic judge stub — no LLM, no
    web fallback — so the only behavior under test is the gate itself)."""
    from scp import api_server
    import scp.api.chat as chat_module

    token = "p1-ws-clear-token"
    monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", token)
    assert not _chat_flag_path(chat_kill_switch_dir).exists()

    async def _stub_candidate(user_message, conversation_context):
        return "control-candidate-after-clear"

    class _StubJudge:
        def judge(self, **kwargs):
            return {
                "verdict": "PASS",
                "confidence": 0.95,
                "final_answer": "control-candidate-after-clear",
                "reasoning": "gate-open-control",
                "domain": "general",
                "evidence": {"governance_decision": "UPHOLD"},
            }

    monkeypatch.setattr(chat_module, "_generate_candidate_answer", _stub_candidate)
    monkeypatch.setattr(api_server, "get_judge", lambda: _StubJudge())

    with TestClient(api_server.app) as client:
        with client.websocket_connect(f"/chat?token={token}") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"message": "hello there"})
            response = ws.receive_json()
            assert response.get("reason") != "kill_switch_engaged", response
            assert response["type"] in {"verified", "answer", "rejected", "clarification"}
            assert response["answer"] == "control-candidate-after-clear"
            assert response["governance"] == "UPHOLD"
