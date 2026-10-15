
import pytest
from fastapi import HTTPException, Request


@pytest.mark.parametrize(
    "route_import_path,env_flag",
    [
        ("scp.api.routes.web_control_routes", "SCP_LOCAL_ONLY"),
        ("scp.api.routes.hands_routes", "SCP_HANDS_LOCAL_ONLY"),
        ("scp.api.routes.pc_controller_routes", "SCP_PC_LOCAL_ONLY"),
        ("scp.api.routes.call_routes", "SCP_AGENT_LOCAL_ONLY"),
    ],
)
def test_controller_xff_guard_rejects_external_ips(monkeypatch, route_import_path, env_flag):
    import importlib
    module = importlib.import_module(route_import_path)
    guard_fn = module._guard
    
    # 1. Simulate a request from a local IP but with an external X-Forwarded-For
    scope_fake_xff = {
        "type": "http",
        "client": ("127.0.0.1", 50000),
        "headers": [
            (b"host", b"127.0.0.1:8000"),
            (b"x-forwarded-for", b"203.0.113.195")
        ]
    }
    req_fake_xff = Request(scope_fake_xff)
    
    # Clean isolated environment via monkeypatch
    monkeypatch.setenv(env_flag, "1")
    monkeypatch.setenv("SCP_PC_CONTROLLER_TOKEN", "test_token")
    
    with pytest.raises(HTTPException) as exc_info:
        guard_fn(req_fake_xff, None)
    
    assert exc_info.value.status_code == 403
    
    # 2. Simulate a legitimate local request (no XFF, local client)
    scope_local = {
        "type": "http",
        "client": ("127.0.0.1", 50000),
        "headers": [
            (b"host", b"127.0.0.1:8000")
        ]
    }
    req_local = Request(scope_local)
    
    result = guard_fn(req_local, "test_token")
    assert result is None


def test_agent_routes_internal_secret_guard(monkeypatch):
    from scp.api.routes.agent_routes import _guard
    
    scope_caddy = {
        "type": "http",
        "client": ("127.0.0.1", 50000),
        "headers": [
            (b"host", b"127.0.0.1:8000"),
            (b"x-scp-internal-token", b"correct_secret")
        ]
    }
    req_caddy = Request(scope_caddy)
    
    monkeypatch.setenv("SCP_INTERNAL_SECRET", "correct_secret")
    monkeypatch.setenv("SCP_PC_CONTROLLER_TOKEN", "test_token")
    
    # Valid internal token returns None (passes)
    assert _guard(req_caddy, None) is None
    
    # If bad internal token and XFF is present (external client via proxy), raises 403
    scope_bad_xff = {
        "type": "http",
        "client": ("127.0.0.1", 50000),
        "headers": [
            (b"host", b"127.0.0.1:8000"),
            (b"x-scp-internal-token", b"wrong_secret"),
            (b"x-forwarded-for", b"203.0.113.195")
        ]
    }
    with pytest.raises(HTTPException) as exc_info:
        _guard(Request(scope_bad_xff), None)
    assert exc_info.value.status_code == 403

