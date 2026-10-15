"""Reality test for Fix 4-a-003: threat/audit/prediction routes need admin auth.

Behavioral execution test: uses FastAPI TestClient to test authentication on
prediction and admin endpoints fail-closed without token and succeed with valid admin token.
"""
import os
import secrets
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Hermetic boot (S17 contract, GAP-09): scp.core.capability_token fail-closes at
# import when SCP_CAPABILITY_SECRET is missing. The portable runner provides an
# isolated env (no repo .env), so generate a random per-run secret here instead
# of reading the repo .env. Auth assertions below are unchanged.
os.environ.setdefault("SCP_CAPABILITY_SECRET", secrets.token_hex(32))

def test_prediction_verify_endpoint_requires_admin_auth():
    from scp.api_server import app
    client = TestClient(app, raise_server_exceptions=False)

    # 1. Unauthenticated request must fail closed with 401
    res_no_auth = client.post("/v105/predictions/verify", json={"limit": 10})
    assert res_no_auth.status_code == 401, f"Expected 401 for unauthenticated request, got {res_no_auth.status_code}"

    # 2. Invalid token must fail closed with 401
    res_bad_auth = client.post(
        "/v105/predictions/verify",
        json={"limit": 10},
        headers={"Authorization": "Bearer invalid_secret_token"}
    )
    assert res_bad_auth.status_code == 401, f"Expected 401 for invalid token, got {res_bad_auth.status_code}"

    # 3. Valid admin token should pass authentication (status is not 401)
    admin_token = os.environ.get("SCP_AUTH_PASSWORD", "test-admin-secret-token-12345")
    os.environ["SCP_AUTH_PASSWORD"] = admin_token

    res_auth = client.post(
        "/v105/predictions/verify",
        json={"limit": 10},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    # Auth passed: should not be 401
    assert res_auth.status_code != 401, f"Expected non-401 for valid token, got {res_auth.status_code}"

def test_prediction_stats_endpoint_requires_admin_auth():
    from scp.api_server import app
    client = TestClient(app, raise_server_exceptions=False)

    res_no_auth = client.get("/v105/predictions/stats")
    assert res_no_auth.status_code == 401, f"Expected 401, got {res_no_auth.status_code}"

if __name__ == "__main__":
    test_prediction_verify_endpoint_requires_admin_auth()
    test_prediction_stats_endpoint_requires_admin_auth()
    print("PASS: reality_4-a-003 behavioral tests passed")
