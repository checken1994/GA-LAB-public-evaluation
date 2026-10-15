"""Extended guard probe: XFF bypass, missing-config, and cross-route consistency."""
import os

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from scp.api.routes import hands_routes, pc_controller_routes, web_control_routes
from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority


@pytest.fixture
def app_with_token(monkeypatch):
    monkeypatch.setenv("SCP_PC_CONTROLLER_TOKEN", "strict_test_token")
    app = FastAPI()
    @app.middleware("http")
    async def mock_ip(request: Request, call_next):
        request.scope["client"] = ("127.0.0.1", 12345)
        return await call_next(request)
    app.include_router(pc_controller_routes.router)
    app.include_router(hands_routes.router)
    app.include_router(web_control_routes.router)
    return TestClient(app)

@pytest.fixture
def app_no_token(monkeypatch):
    """SCP_PC_CONTROLLER_TOKEN not configured = fail-closed."""
    if "SCP_PC_CONTROLLER_TOKEN" in os.environ:
        monkeypatch.delenv("SCP_PC_CONTROLLER_TOKEN", raising=False)
    app = FastAPI()
    @app.middleware("http")
    async def mock_ip(request: Request, call_next):
        request.scope["client"] = ("127.0.0.1", 12345)
        return await call_next(request)
    app.include_router(pc_controller_routes.router)
    app.include_router(hands_routes.router)
    app.include_router(web_control_routes.router)
    return TestClient(app)

@pytest.fixture
def app_xff_token(monkeypatch, tmp_path):
    """Token configured, but request has X-Forwarded-For (proxied).

    [S16 FIX 2026-09-13] test_xff_bypass_pc_controller engages
    POST /v3/pc/kill with a valid token; the route singleton binds
    KILL_SWITCH to the repo data/ directory, so that engagement used to
    write data/pc_controller/KILL_SWITCH into the repo and poison later
    tests in the same pytest process. Swap in a tmp-isolated controller so
    kill-switch state lives and dies with tmp_path.
    """
    monkeypatch.setenv("SCP_PC_CONTROLLER_TOKEN", "strict_test_token")
    monkeypatch.setattr(
        pc_controller_routes,
        "_controller",
        PCController(
            working_dir=tmp_path / "route_workspace",
            capability_authority=CapabilityAuthority(tmp_path / "route_capability_state.json"),
        ),
    )
    app = FastAPI()
    @app.middleware("http")
    async def mock_ip(request: Request, call_next):
        # Simulate proxy: client is 127.0.0.1 but XFF present
        request.scope["client"] = ("127.0.0.1", 12345)
        return await call_next(request)
    app.include_router(pc_controller_routes.router)
    app.include_router(hands_routes.router)
    app.include_router(web_control_routes.router)
    return TestClient(app)

# ===== MISSING CONFIG (INV-FAILCLOSED-03) =====
def test_missing_config_pc_kill(app_no_token):
    resp = app_no_token.post("/v3/pc/kill", json={"reason": "test"}, headers={})
    assert resp.status_code == 403, "Missing config must reject on /v3/pc/kill"

def test_missing_config_hands_status(app_no_token):
    resp = app_no_token.get("/v3/hands/status", headers={})
    assert resp.status_code == 403, "Missing config must reject on /v3/hands/status"

def test_missing_config_web_status(app_no_token):
    resp = app_no_token.get("/v3/web/status", headers={})
    assert resp.status_code == 403, "Missing config must reject on /v3/web/status"

# ===== XFF BYPASS PROBE (INV-PROXY-02) =====
# web_control_routes has XFF check inline in _guard
# pc_controller_routes has _is_local() with XFF check BUT _guard doesn't call it
# hands_routes has NO XFF check

def test_xff_bypass_pc_controller(app_xff_token):
    """pc_controller: XFF present → should still require token (current behavior: token-only)"""
    # Token present + XFF → should PASS (token-only logic)
    resp = app_xff_token.post("/v3/pc/kill", json={"reason": "test"}, 
                               headers={"X-SCP-PC-Token": "strict_test_token", "X-Forwarded-For": "10.0.0.1"})
    assert resp.status_code == 200, "Token + XFF should PASS with token-only logic"

    # No token + XFF → 403
    resp = app_xff_token.post("/v3/pc/kill", json={"reason": "test"}, 
                               headers={"X-Forwarded-For": "10.0.0.1"})
    assert resp.status_code == 403, "No token + XFF must be 403"

def test_xff_bypass_hands(app_xff_token):
    """hands_routes: XFF present → token-only logic"""
    resp = app_xff_token.get("/v3/hands/status", 
                              headers={"X-SCP-PC-Token": "strict_test_token", "X-Forwarded-For": "10.0.0.1"})
    assert resp.status_code == 200

    resp = app_xff_token.get("/v3/hands/status", headers={"X-Forwarded-For": "10.0.0.1"})
    assert resp.status_code == 403

def test_xff_bypass_web_control(app_xff_token):
    """web_control_routes: CURRENT working tree has NO XFF check (reverted).
    If XFF check existed → should reject proxied even with token.
    Current behavior: token-only PASS."""
    resp = app_xff_token.get("/v3/web/status", 
                              headers={"X-SCP-PC-Token": "strict_test_token", "X-Forwarded-For": "10.0.0.1"})
    # Current code: token-only → PASS
    assert resp.status_code == 200

    resp = app_xff_token.get("/v3/web/status", headers={"X-Forwarded-For": "10.0.0.1"})
    assert resp.status_code == 403

# ===== HMAC CONSTANT-TIME (INV-HMAC-04) =====
def test_token_hmac_constant_time(app_with_token):
    """Invalid token must still take same code path (no early exit on length mismatch)."""
    resp = app_with_token.get("/v3/hands/status", headers={"X-SCP-PC-Token": "wrong_token"})
    assert resp.status_code == 403
    # Note: full timing attack test requires separate timing probe

# ===== CROSS-ROUTE CONSISTENCY =====
def test_all_routes_same_token_acceptance(app_with_token):
    """All 3 route groups must accept same valid token."""
    token = "strict_test_token"
    resp1 = app_with_token.get("/v3/pc/status", headers={"X-SCP-PC-Token": token})
    resp2 = app_with_token.get("/v3/hands/status", headers={"X-SCP-PC-Token": token})
    resp3 = app_with_token.get("/v3/web/status", headers={"X-SCP-PC-Token": token})
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp3.status_code == 200
