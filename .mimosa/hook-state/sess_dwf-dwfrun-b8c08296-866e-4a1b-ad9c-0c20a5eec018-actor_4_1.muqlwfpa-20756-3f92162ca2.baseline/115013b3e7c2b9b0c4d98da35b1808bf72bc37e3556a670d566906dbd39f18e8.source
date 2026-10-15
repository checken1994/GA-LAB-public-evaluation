
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from scp.api.routes import hands_routes, pc_controller_routes, web_control_routes
from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    monkeypatch.setenv("SCP_PC_CONTROLLER_TOKEN", "strict_test_token")
    # [S16 FIX 2026-09-13] The route singleton binds KILL_SWITCH to the repo
    # data/ directory. test_localhost_requires_token_pc_kill engages
    # POST /v3/pc/kill, which used to write data/pc_controller/KILL_SWITCH
    # into the repo (poisoning later tests in the same pytest process, e.g.
    # test_security's read-only allowlist check). Swap in a tmp-isolated
    # controller so kill-switch state lives and dies with tmp_path.
    monkeypatch.setattr(
        pc_controller_routes,
        "_controller",
        PCController(
            working_dir=tmp_path / "route_workspace",
            capability_authority=CapabilityAuthority(tmp_path / "route_capability_state.json"),
        ),
    )
    app = FastAPI()
    
    # Middleware to mock client as 127.0.0.1
    @app.middleware("http")
    async def mock_ip(request: Request, call_next):
        request.scope["client"] = ("127.0.0.1", 12345)
        return await call_next(request)
        
    app.include_router(pc_controller_routes.router)
    app.include_router(hands_routes.router)
    app.include_router(web_control_routes.router)
    return TestClient(app)

def test_localhost_requires_token_pc_kill(api_client):
    # Without token -> 403
    resp = api_client.post("/v3/pc/kill", json={"reason": "test"}, headers={})
    assert resp.status_code == 403, "Localhost bypass allowed on /v3/pc/kill"

    # With valid token -> 200
    resp = api_client.post("/v3/pc/kill", json={"reason": "test"}, headers={"X-SCP-PC-Token": "strict_test_token"})
    assert resp.status_code == 200

    # [S16 FIX 2026-09-13] No repo cleanup needed: the api_client fixture
    # swaps the route singleton for a tmp-isolated controller, so the
    # engagement above never touches repo data/pc_controller/ (the previous
    # inline unlink of the repo KILL_SWITCH file is obsolete by isolation).

def test_localhost_requires_token_hands_status(api_client):
    # Without token -> 403
    resp = api_client.get("/v3/hands/status", headers={})
    assert resp.status_code == 403, f"Localhost bypass allowed on /v3/hands/status. Got {resp.status_code}"

def test_localhost_requires_token_web_status(api_client):
    # Without token -> 403
    resp = api_client.get("/v3/web/status", headers={})
    assert resp.status_code == 403, f"Localhost bypass allowed on /v3/web/status. Got {resp.status_code}"
