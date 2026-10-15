from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from scp.security import auth


def test_verify_admin_receives_real_request_client_ip(monkeypatch) -> None:
    monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", "integration-token")
    monkeypatch.delenv("SCP_AUTH_TOKEN_SECRET_FILE", raising=False)
    monkeypatch.delenv("SCP_AUTH_PASSWORD", raising=False)
    monkeypatch.delenv("SCP_AUTH_PASSWORD_FILE", raising=False)
    auth._auth_failures.clear()
    app = FastAPI()

    @app.get("/admin")
    def admin(_admin: bool = Depends(auth.verify_admin)):
        return {"ok": True}

    with TestClient(app, client=("203.0.113.10", 5000)) as client_a, TestClient(app, client=("203.0.113.11", 5000)) as client_b:
        for _ in range(auth._RATE_LIMIT_MAX_FAILURES):
            response = client_a.get("/admin", headers={"Authorization": "Bearer wrong"})
            assert response.status_code == 401
        blocked_a = client_a.get("/admin", headers={"Authorization": "Bearer wrong"})
        allowed_b = client_b.get("/admin", headers={"Authorization": "Bearer integration-token"})

    assert blocked_a.status_code == 429
    assert allowed_b.status_code == 200
    assert len(auth._auth_failures["203.0.113.10"]) == auth._RATE_LIMIT_MAX_FAILURES
    assert "203.0.113.11" not in auth._auth_failures
