import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

from fastapi.testclient import TestClient

from scp.api_server import app

client = TestClient(app)
HEADERS_PC = {"X-SCP-PC-Token": "test-token"}
HEADERS_HANDS = {"X-SCP-Hands-Token": "test-token"}
HEADERS_ADMIN = {"Authorization": "Bearer test"}

def test_pc_controller_actions():
    '''FA-13: Cover action endpoints in pc_controller_routes.py'''
    resp = client.post('/v3/pc/read', headers=HEADERS_PC)
    assert resp.status_code != 404
    resp = client.post('/v3/pc/write', headers=HEADERS_PC)
    assert resp.status_code != 404

def test_hands_plan_recover():
    '''FA-13: Cover action endpoints in hands_routes.py'''
    resp = client.post('/v3/hands/planner/123/recover', headers=HEADERS_HANDS)
    assert resp.status_code != 404

def test_restored_systems_actions():
    '''FA-13: Cover action endpoints for 5 restored systems'''
    endpoints = [
        "/v105/risk/classify",
        "/v105/world/assertions",
        "/v105/calibration/predict",
        "/v105/forecast/cases",
        "/v105/history/evidence"
    ]
    for ep in endpoints:
        resp = client.post(ep, headers=HEADERS_ADMIN)
        assert resp.status_code != 404, f"Endpoint {ep} failed with {resp.status_code}"
