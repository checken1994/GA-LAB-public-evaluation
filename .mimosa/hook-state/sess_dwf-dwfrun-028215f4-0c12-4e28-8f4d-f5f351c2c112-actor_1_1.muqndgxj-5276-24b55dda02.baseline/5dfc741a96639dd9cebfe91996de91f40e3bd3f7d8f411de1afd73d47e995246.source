import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')
os.environ['SCP_AUTH_TOKEN_SECRET'] = 'test-swe-token'

from fastapi.testclient import TestClient

from scp.api_server import app
from scp.security.auth import _auth_failures

client = TestClient(app)

def test_swe_bench_compat(monkeypatch):
    '''FA-13: Cover SWE-Bench compatibility route'''
    # Harness fixture isolation (convention from
    # tests/test_p0_security_adversarial_challenger2.py::reset_rate_limit):
    # other tests probe admin endpoints unauthenticated, accumulating 5+
    # recorded 401s for the shared "testclient" IP inside the auth rate
    # limiter's 60s window. Without this reset the authenticated request
    # below fail-closes with 429 in an order-dependent way. Clearing the
    # limiter does NOT weaken any assertion: the unauthenticated request
    # must still 401 and the authenticated one must still 200.
    #
    # [ISOLATION FIX — reverse env leak] load_auth_config() reads
    # SCP_AUTH_TOKEN_SECRET from os.environ PER REQUEST. Full-suite
    # collection imports T03_capability BEFORE root-level files, so a later
    # module-level writer (tests/test_p0_security_adversarial_challenger2.py
    # sets its own _ADMIN_TOKEN at import) wins the process env while this
    # test executes — the authenticated request then fail-closes 401
    # (observed as `assert 401 == 200` in full-suite runs, while the file
    # passes alone and in T03-only combos). Pin the auth config for the
    # duration of this test; monkeypatch restores the import-time value
    # afterwards, so the other side's pinning stays untouched. The limiter
    # itself (scp/security/auth.py) is NOT touched.
    _auth_failures.clear()
    monkeypatch.delenv("SCP_AUTH_PASSWORD", raising=False)
    monkeypatch.delenv("SCP_AUTH_PASSWORD_FILE", raising=False)
    monkeypatch.delenv("SCP_AUTH_TOKEN_SECRET_FILE", raising=False)
    monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", "test-swe-token")
    try:
        payload = {
            "model": "scp-agent",
            "messages": [{"role": "user", "content": "hello"}]
        }
        # Unauthenticated request fails closed with 401
        resp_unauth = client.post('/swe-bench/v1/chat/completions', json=payload)
        assert resp_unauth.status_code == 401

        # Authenticated request succeeds with 200
        resp = client.post(
            '/swe-bench/v1/chat/completions',
            json=payload,
            headers={"Authorization": "Bearer test-swe-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == "scp-agent"
        assert data["choices"][0]["message"]["content"] == "Function execution deferred to agent loop."
    finally:
        # Do not leak this test's single recorded failure into later tests.
        _auth_failures.clear()
