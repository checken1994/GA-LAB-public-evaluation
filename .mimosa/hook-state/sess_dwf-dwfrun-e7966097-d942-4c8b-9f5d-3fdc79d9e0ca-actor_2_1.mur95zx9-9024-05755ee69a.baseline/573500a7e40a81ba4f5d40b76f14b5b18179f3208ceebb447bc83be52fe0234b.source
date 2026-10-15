"""Regression tests for the /v3/hands/reconcile capability-token gate.

[AUDIT-FIX 2026-09-24] External audit found that /v3/hands/reconcile accepted
outcome/evidenceRef WITHOUT a capability token, while execute/rollback both
require one. Reconcile commits a terminal outcome + evidence into the task
kernel — the same class of mutating decision — so it now requires a token
with subject `hands:reconcile`, validated against the executor's
CapabilityAuthority (same issue/validate pattern as the executor PEP).

Fail-closed contract: no token → 403; wrong subject → 403; valid token →
the request proceeds past the authorization boundary.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

TMP_DATA = Path(os.environ.get("SCP_TEST_TMP", "data"))


@pytest.fixture()
def client(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("SCP_PC_CONTROLLER_TOKEN", "test-hands-guard-token")
    monkeypatch.setenv("SCP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SCP_HANDS_DATA_DIR", str(tmp_path / "hands"))
    monkeypatch.setenv("SCP_KERNEL_DB_PATH", str(tmp_path / "kernel.sqlite3"))
    monkeypatch.setenv("SCP_KERNEL_TRACE_PATH", str(tmp_path / "kernel_trace.jsonl"))

    from scp.api.routes import hands_routes

    # [TEST-ISOLATION] hands_routes._hands is a process-wide singleton created
    # at import time. Earlier tests in this suite (e.g. the revoke-endpoint
    # regression) permanently revoke that singleton's CapabilityAuthority and
    # bind it to THEIR tmp dirs, so env vars alone cannot give this test a
    # usable authority. Bind a fresh executor + bridge backed by THIS test's
    # tmp dirs; monkeypatch restores the originals at teardown. Assertions are
    # unchanged — this only makes the fixture hermetic (strictness preserved).
    from scp.hands.hands_executor import HandsExecutor
    from scp.hands.task_kernel_bridge import TaskKernelHandsBridge

    fresh_executor = HandsExecutor(data_dir=tmp_path / "hands-fresh")
    monkeypatch.setattr(hands_routes, "_hands", fresh_executor)
    monkeypatch.setattr(hands_routes, "_hands_bridge", TaskKernelHandsBridge(fresh_executor))

    app = FastAPI()
    app.include_router(hands_routes.router)
    return TestClient(app), hands_routes


def _headers() -> dict:
    return {"X-SCP-PC-TOKEN": "test-hands-guard-token"}


def _reconcile_payload() -> dict:
    return {
        "taskId": "task-12345678",
        "checkpointId": "chk-12345678",
        "outcome": "APPLIED",
        "evidenceRef": "evidence://reconcile/regression",
    }


def test_reconcile_without_token_is_403(client):
    tc, _routes = client
    resp = tc.post("/v3/hands/reconcile", json=_reconcile_payload())
    assert resp.status_code == 403


def test_reconcile_with_wrong_subject_token_is_403(client):
    tc, routes = client
    token = routes._hands.capability_authority.issue("hands:pc.write_file")
    resp = tc.post(
        "/v3/hands/reconcile",
        json={**_reconcile_payload(), "capabilityToken": token.to_dict()},
        headers=_headers(),
    )
    assert resp.status_code == 403
    assert "CapabilityScopeMismatchError" in resp.json()["detail"]


def test_reconcile_with_valid_subject_token_proceeds(client):
    """A hands:reconcile token passes the authorization boundary — the request
    reaches the kernel layer (task-not-found is a domain error, NOT a 403)."""
    tc, routes = client
    token = routes._hands.capability_authority.issue("hands:reconcile")
    resp = tc.post(
        "/v3/hands/reconcile",
        json={**_reconcile_payload(), "capabilityToken": token.to_dict()},
        headers=_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    # Kernel-level outcome for an unknown task is a domain result, not auth.
    assert body["success"] is False
    assert body["taskId"] == "task-12345678"


def test_reconcile_with_tampered_token_signature_is_403(client):
    tc, routes = client
    token = routes._hands.capability_authority.issue("hands:reconcile").to_dict()
    token["signature"] = "0" * len(str(token.get("signature", "")))
    resp = tc.post(
        "/v3/hands/reconcile",
        json={**_reconcile_payload(), "capabilityToken": token},
        headers=_headers(),
    )
    assert resp.status_code == 403
