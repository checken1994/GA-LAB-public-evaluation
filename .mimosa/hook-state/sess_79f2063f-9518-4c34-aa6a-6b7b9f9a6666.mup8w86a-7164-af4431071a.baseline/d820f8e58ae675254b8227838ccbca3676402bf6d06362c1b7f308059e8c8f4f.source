"""[SEC-FIX /health-identity + /health-authz 2026-09-26] Regression tests.

FA-09 provenance: probes (temp dir) confirmed BEFORE fix:
  1. /health (unauthenticated) echoed the FULL sys.argv — a CLI-passed secret
     landed verbatim in the response body.
  2. /health/detailed answered 200 without any Authorization header,
     disclosing data-dir size, tracker stats, sandbox capability.
  3. The /health/detailed exception path echoed str(e)[:200] verbatim —
     internal paths / credential material included.

These tests pin the FIXED contract:
  - identity exposes commit/config_hash/configured_port but NEVER argv
  - /health stays minimal-200 and unauthenticated (liveness)
  - /health/detailed requires verify_admin (401 without a valid token)
  - exception text is redacted to the exception type name
"""
from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "SCP_CAPABILITY_SECRET",
    "test-capability-secret-for-automated-suites-only-32bytes",
)

_TEST_PW = "health-minimal-identity-regression-pw"


@pytest.fixture()
def _auth_env(monkeypatch):
    monkeypatch.setenv("SCP_AUTH_PASSWORD", _TEST_PW)
    monkeypatch.delenv("SCP_AUTH_PASSWORD_FILE", raising=False)
    monkeypatch.delenv("SCP_AUTH_TOKEN_SECRET", raising=False)
    monkeypatch.delenv("SCP_AUTH_TOKEN_SECRET_FILE", raising=False)
    from scp.security import auth as _auth

    with _auth._auth_failures_lock:
        _auth._auth_failures.clear()
    return _auth


def _client() -> TestClient:
    from scp import api_server

    return TestClient(api_server.app)  # no lifespan — routes only


def test_health_stays_minimal_200_without_auth():
    """/health phải giữ 200 không auth (liveness probe) nhưng KHÔNG lộ argv."""
    client = _client()
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    identity = body["service_identity"]
    # Commit/config/port vẫn phải có (startup-troubleshooter phụ thuộc).
    assert identity["commit"]
    assert identity["config_hash"]
    assert isinstance(identity["configured_port"], int)
    # [SEC-FIX] raw command line không được xuất hiện.
    assert "argv" not in identity


def test_health_never_echoes_cli_secret():
    """Probe-faithful regression: secret truyền qua CLI KHÔNG được vào /health."""
    import json
    import sys

    from scp import api_server

    marker = "REGRESSION-CLI-SECRET-XYZ"
    old_argv = list(sys.argv)
    sys.argv = ["python", "-m", "scp", "8000", f"--token={marker}"]
    try:
        body = asyncio.run(api_server.health())
    finally:
        sys.argv = old_argv
    assert isinstance(body["service_identity"]["configured_port"], int)
    assert marker not in json.dumps(body, default=str)


def test_health_detailed_requires_admin(_auth_env):
    """/health/detailed không auth → 401 (trước fix: 200 với đầy đủ internals)."""
    client = _client()
    response = client.get("/health/detailed")
    assert response.status_code == 401
    detail = response.json().get("detail", "")
    assert detail, "401 phải kèm detail"


def test_health_detailed_with_valid_admin_token(_auth_env, monkeypatch):
    """Token hợp lệ → 200 và body đầy đủ như contract cũ."""
    from scp import api_server

    class _FakeJudge:
        domain_experts: dict = {}

        def get_v98_status(self):
            return {}

        def _route_question(self, question: str):
            return ["math"]

    monkeypatch.setattr(api_server, "get_judge", lambda: _FakeJudge())
    client = _client()
    response = client.get(
        "/health/detailed", headers={"Authorization": f"Bearer {_TEST_PW}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "sandbox_capability" in body
    assert "data_size_mb" in body


def test_health_detailed_exception_text_is_redacted(_auth_env, monkeypatch):
    """Exception path chỉ trả TYPE NAME — không echo str(e) về client."""
    from scp import api_server

    def _boom():
        raise RuntimeError(
            "internal trace C:/Users/operator/.env SCP_AUTH_PASSWORD=hunter2"
        )

    monkeypatch.setattr(api_server, "get_judge", _boom)
    body = asyncio.run(api_server.health_detailed())
    assert body["error"] == "RuntimeError"
    assert "hunter2" not in str(body)
    assert ".env" not in str(body)
