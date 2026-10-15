import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

from fastapi.testclient import TestClient

from scp.api_server import app

client = TestClient(app)


def _admin_override(on: bool) -> None:
    """[M14-FIX] Toggle the verify_admin dependency for golden-path requests."""
    from scp.api._shared import verify_admin
    if on:
        app.dependency_overrides[verify_admin] = lambda: True
    else:
        app.dependency_overrides.pop(verify_admin, None)


def test_v106_audit_reports_requires_admin():
    '''[AUDIT-1][M14-FIX] GET /v106/audit/reports must fail closed without admin auth.

    Regression pin: both v106 endpoints used to be OPEN (probe-proven 200
    without any token at runtime during the M14 closure — BFLA gap).
    '''
    _admin_override(False)
    resp = client.get('/v106/audit/reports')
    assert resp.status_code in (401, 403, 429)


def test_v106_capabilities_requires_admin():
    '''[SELF-1][M14-FIX] GET /v106/capabilities/{cap_id} must fail closed without admin auth.

    Regression pin: this endpoint used to be OPEN (probe-proven 200 without
    any token at runtime during the M14 closure).
    '''
    _admin_override(False)
    resp = client.get('/v106/capabilities/self.capability_map')
    assert resp.status_code in (401, 403, 429)


def test_v106_capabilities_recompute():
    '''FA-13: Cover Self Model capability recomputation (admin authenticated).

    [M14-FIX] Now goes through verify_admin (dependency override) — the
    endpoint requires admin auth since the M14 fix.
    '''
    _admin_override(True)
    try:
        resp = client.get('/v106/capabilities/intelligence.zero_cost')
        assert resp.status_code == 200
        data = resp.json()
        assert 'status' in data
        assert 'maturity' in data
    finally:
        _admin_override(False)
