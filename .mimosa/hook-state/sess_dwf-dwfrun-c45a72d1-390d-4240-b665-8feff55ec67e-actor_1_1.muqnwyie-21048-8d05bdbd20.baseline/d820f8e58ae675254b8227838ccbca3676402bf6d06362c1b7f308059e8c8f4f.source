"""[SEC-FIX /health-identity + /health-authz 2026-09-26] Regression tests.

FA-09 provenance: probes (temp dir) confirmed BEFORE fix:
  1. /health (unauthenticated) echoed the FULL sys.argv — a CLI-passed secret
     landed verbatim in the response body.
  2. /health/detailed answered 200 without any Authorization header,
     disclosing data-dir size, tracker stats, sandbox capability.
  3. The /health/detailed exception path echoed str(e)[:200] verbatim —
     internal paths / credential material included.

These tests pin the FIXED contract:
  - identity exposes commit/configured_port but NEVER argv
  - [F-02 audit-r2 2026-10-01] identity NEVER contains config_hash — the old
    pin asserted its PRESENCE (sha256 of .env in an unauthenticated body = an
    offline cracking oracle for the admin key). The old assertion pinned the
    vulnerable behavior and was classified PRODUCT_FAIL, then strengthened:
    the field must be absent from the whole unauth response body.
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
    assert isinstance(identity["configured_port"], int)
    # [SEC-FIX] raw command line không được xuất hiện.
    assert "argv" not in identity


def test_health_unauth_never_discloses_config_hash():
    """[F-02 audit-r2 2026-10-01] /health unauth KHÔNG được chứa config_hash.

    Probe-faithful: trước fix, service_identity trả về
    ``sha256(<toàn bộ .env>)`` cho mọi caller không auth — một oracle crack
    offline cho SCP_ADMIN_KEY. Response body TOÀN BỘ (mọi cấp lồng) không được
    chứa field này, kể cả khi SCP_CONFIG_HASH được set trong env.
    """
    import json

    client = _client()
    response = client.get("/health")
    assert response.status_code == 200
    assert "config_hash" not in json.dumps(response.json(), default=str), (
        "/health unauth không được trả config_hash (sha256 của .env là oracle crack)"
    )
    # Cả identity object trực tiếp cũng không có key đó (kể tên field, bất kể giá trị).
    assert "config_hash" not in response.json()["service_identity"]


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
