"""Tests for R2: PCController Capability Token PEP Boundary.

Verifies fail-closed PEP enforcement in PCController, token forwarding in
HandsExecutor, and dynamic token validation in pc_controller_routes.
Adheres strictly to FA-01 through FA-13, Zero-Trust, and Fail-Closed principles.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scp.core.capability_token import (
    InvalidTokenSignatureError,
)
from scp.hands.hands_executor import HandsExecutor
from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority, CapabilityToken

# ------------------------------------------------------------------------------
# Fixtures and Helpers
# ------------------------------------------------------------------------------

def _create_controller_with_authority(tmp_path: Path) -> tuple[PCController, CapabilityAuthority, Path]:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    cap_state = tmp_path / "capability_state.json"
    authority = CapabilityAuthority(cap_state)
    controller = PCController(working_dir=workspace, capability_authority=authority)
    return controller, authority, workspace


# ------------------------------------------------------------------------------
# 1. PCController.execute PEP Tests
# ------------------------------------------------------------------------------

def test_pc_controller_execute_rejects_missing_token(tmp_path: Path):
    """Calling execute() without capability_token must fail closed with PermissionError."""
    controller, _auth, _ws = _create_controller_with_authority(tmp_path)

    with pytest.raises(PermissionError) as exc_info:
        asyncio.run(controller.execute("whoami", capability_token=None))

    assert "CapabilityRequiredError" in str(exc_info.value)


def test_pc_controller_execute_rejects_tampered_signature(tmp_path: Path):
    """Calling execute() with a forged/tampered signature must raise InvalidTokenSignatureError."""
    controller, authority, _ws = _create_controller_with_authority(tmp_path)
    valid_token = authority.issue("pc.execute")

    # Forge the signature
    forged_token = CapabilityToken(
        subject=valid_token.subject,
        epoch=valid_token.epoch,
        token_id=valid_token.token_id,
        issued_at=valid_token.issued_at,
        signature="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    )

    with pytest.raises(InvalidTokenSignatureError) as exc_info:
        asyncio.run(controller.execute("whoami", capability_token=forged_token))

    assert "tampered" in str(exc_info.value).lower() or "signature" in str(exc_info.value).lower()


def test_pc_controller_execute_rejects_scope_mismatch(tmp_path: Path):
    """Calling execute() with a token scoped for pc.read_file must raise PermissionError."""
    controller, authority, _ws = _create_controller_with_authority(tmp_path)
    read_token = authority.issue("pc.read_file")

    with pytest.raises(PermissionError) as exc_info:
        asyncio.run(controller.execute("whoami", capability_token=read_token))

    assert "CapabilityScopeMismatchError" in str(exc_info.value)


def test_pc_controller_execute_rejects_revoked_epoch(tmp_path: Path):
    """Calling execute() with a revoked epoch token must raise PermissionError fail-closed."""
    controller, authority, _ws = _create_controller_with_authority(tmp_path)
    token = authority.issue("pc.execute")

    # Revoke authority
    authority.revoke(reason="security_alert")

    with pytest.raises(PermissionError) as exc_info:
        asyncio.run(controller.execute("whoami", capability_token=token))

    assert "revoked" in str(exc_info.value).lower() or "stale" in str(exc_info.value).lower()


def test_pc_controller_execute_succeeds_with_valid_token(tmp_path: Path):
    """Calling execute() with a valid pc.execute token runs allowlisted command and records audit.

    [S16 FIX 2026-09-13] No skip markers: both T00 gates reject new
    pytest.skip() calls and new skip/xfail/skipif decorators
    (tools/t00_meta_audit.py FA-01 delta, tests/T00_integrity/test_meta_audit.py).
    PCController._run_sync executes through powershell.exe (Windows-only
    product executor), so Windows asserts the full success + audit contract
    while every other OS asserts the fail-closed executor-absent result
    (success=False, returnCode=None). The PEP token echo is asserted on every
    OS.
    """
    controller, authority, _ws = _create_controller_with_authority(tmp_path)
    token = authority.issue("pc.execute")

    result = asyncio.run(controller.execute("whoami", capability_token=token))

    assert result.get("tokenId") == token.token_id
    assert result.get("epoch") == token.epoch
    if sys.platform == "win32":
        assert result.get("success") is True, f"Execution failed: {result}"
        assert result.get("returnCode") == 0

        # Verify physical audit log on disk contains token id
        assert controller.audit_path.exists()
        audit_lines = [json.loads(line) for line in controller.audit_path.read_text(encoding="utf-8").splitlines()]
        token_audits = [a for a in audit_lines if a.get("tokenId") == token.token_id]
        assert len(token_audits) >= 2  # EXECUTE_INTENT and EXECUTE
    else:
        # Executor absent on this OS: the product must fail closed (OSError →
        # success=False), never fake success.
        assert result.get("success") is False, f"Non-Windows must fail closed: {result}"
        assert result.get("returnCode") is None


# ------------------------------------------------------------------------------
# 2. PCController.write_file PEP Tests
# ------------------------------------------------------------------------------

def test_pc_controller_write_rejects_missing_token(tmp_path: Path):
    """Calling write_file() without token must raise PermissionError and write zero bytes."""
    controller, _auth, workspace = _create_controller_with_authority(tmp_path)
    target = workspace / "test_unauthorized.txt"

    with pytest.raises(PermissionError) as exc_info:
        asyncio.run(
            controller.write_file(
                str(target),
                "unauthorized content",
                capability_token=None,
                capability_level=3,
                approved=True,
            )
        )

    assert "CapabilityRequiredError" in str(exc_info.value)
    assert not target.exists(), "File was created without capability token (FA-05 violation)"


def test_pc_controller_write_rejects_tampered_token(tmp_path: Path):
    """Calling write_file() with tampered token must raise InvalidTokenSignatureError."""
    controller, authority, workspace = _create_controller_with_authority(tmp_path)
    target = workspace / "test_tampered.txt"
    token = authority.issue("pc.write_file")
    tampered = CapabilityToken(
        subject=token.subject,
        epoch=token.epoch,
        token_id=token.token_id,
        issued_at=token.issued_at,
        signature="bad" * 16,
    )

    with pytest.raises(InvalidTokenSignatureError):
        asyncio.run(
            controller.write_file(
                str(target),
                "unauthorized content",
                capability_token=tampered,
                capability_level=3,
                approved=True,
            )
        )

    assert not target.exists()


def test_pc_controller_write_succeeds_with_valid_token(tmp_path: Path):
    """Calling write_file() with valid token writes content to disk, creates backup, and audits."""
    controller, authority, workspace = _create_controller_with_authority(tmp_path)
    target = workspace / "test_authorized.txt"
    token = authority.issue("pc.write_file")
    content = "authentic_content_written_safely"

    # Pre-register human confirmation per SEC-R1-01
    cid = controller.human_store.record_confirmation(action="pc.write_file", target=str(target))

    result = asyncio.run(
        controller.write_file(
            str(target),
            content,
            capability_token=token,
            capability_level=3,
            approved=True,
            confirmation_id=cid,
        )
    )

    assert result.get("success") is True, f"Write failed: {result}"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == content
    assert result.get("tokenId") == token.token_id


# ------------------------------------------------------------------------------
# 3. PCController.read_file PEP Tests
# ------------------------------------------------------------------------------

def test_pc_controller_read_rejects_missing_token(tmp_path: Path):
    """Calling read_file() without token must raise PermissionError."""
    controller, _auth, workspace = _create_controller_with_authority(tmp_path)
    target = workspace / "data.txt"
    target.write_text("secret_data", encoding="utf-8")

    with pytest.raises(PermissionError) as exc_info:
        asyncio.run(controller.read_file(str(target), capability_token=None))

    assert "CapabilityRequiredError" in str(exc_info.value)


def test_pc_controller_read_succeeds_with_valid_token(tmp_path: Path):
    """Calling read_file() with valid pc.read_file token reads the content."""
    controller, authority, workspace = _create_controller_with_authority(tmp_path)
    target = workspace / "data.txt"
    target.write_text("accessible_data", encoding="utf-8")
    token = authority.issue("pc.read_file")

    result = asyncio.run(controller.read_file(str(target), capability_token=token))

    assert result.get("success") is True
    assert result.get("content") == "accessible_data"
    assert result.get("tokenId") == token.token_id


# ------------------------------------------------------------------------------
# 4. PCController.clear_kill_switch PEP Tests
# ------------------------------------------------------------------------------

def test_pc_controller_clear_kill_switch_requires_token(tmp_path: Path):
    """Clearing kill switch without token must raise PermissionError."""
    controller, authority, _ws = _create_controller_with_authority(tmp_path)
    controller.engage_kill_switch("test kill")
    assert controller.kill_switch_engaged() is True

    with pytest.raises(PermissionError):
        controller.clear_kill_switch(approved=True, capability_token=None)

    assert controller.kill_switch_engaged() is True, "Kill switch cleared without token!"

    # Now clear with authorized token
    token = authority.issue("pc.clear_kill_switch")
    clear_res = controller.clear_kill_switch(approved=True, capability_token=token)
    assert clear_res.get("success") is True
    assert controller.kill_switch_engaged() is False


# ------------------------------------------------------------------------------
# 5. HandsExecutor Token Forwarding Integration Tests
# ------------------------------------------------------------------------------

def test_hands_executor_forwards_token_to_controller(tmp_path: Path):
    """HandsExecutor must forward capability token to controller without dropping it."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    cap_state = tmp_path / "capability_state.json"
    authority = CapabilityAuthority(cap_state)
    controller = PCController(working_dir=workspace, capability_authority=authority)
    executor = HandsExecutor(
        controller=controller,
        capability_authority=authority,
        data_dir=tmp_path / "hands_data",
    )

    target = workspace / "hands_forwarded.txt"
    content = "hands_forwarded_content"
    token = authority.issue("hands:pc.write_file")

    controller.human_store.record_confirmation(action="pc.write_file", target=str(target))

    result = asyncio.run(
        executor.execute(
            action="pc.write_file",
            params={"path": str(target), "content": content},
            capability_level=3,
            approved=True,
            capability_token=token,
        )
    )

    assert result.get("success") is True, f"HandsExecutor write failed: {result}"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == content


def test_hands_executor_extracts_token_from_params(tmp_path: Path):
    """HandsExecutor must extract capability_token from params dict if omitted from kwargs."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    cap_state = tmp_path / "capability_state.json"
    authority = CapabilityAuthority(cap_state)
    controller = PCController(working_dir=workspace, capability_authority=authority)
    executor = HandsExecutor(
        controller=controller,
        capability_authority=authority,
        data_dir=tmp_path / "hands_data",
    )

    target = workspace / "params_token.txt"
    content = "params_token_content"
    token = authority.issue("hands:pc.write_file")

    controller.human_store.record_confirmation(action="pc.write_file", target=str(target))

    # Pass token inside params
    result = asyncio.run(
        executor.execute(
            action="pc.write_file",
            params={"path": str(target), "content": content, "capability_token": token.to_dict()},
            capability_level=3,
            approved=True,
        )
    )

    assert result.get("success") is True, f"Extraction from params failed: {result}"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == content


# ------------------------------------------------------------------------------
# 6. HTTP API Route Token Enforcement (pc_controller_routes)
# ------------------------------------------------------------------------------

def test_pc_controller_routes_rejects_missing_capability_token(monkeypatch, tmp_path: Path):
    """POST /v3/pc/execute without capability token must return HTTP 403."""
    from scp.api.routes import pc_controller_routes

    monkeypatch.setenv("SCP_PC_CONTROLLER_TOKEN", "mock_pc_token")
    app = FastAPI()
    app.include_router(pc_controller_routes.router)
    client = TestClient(app)

    # Missing capability token in headers and payload
    response = client.post(
        "/v3/pc/execute",
        headers={"X-SCP-PC-Token": "mock_pc_token"},
        json={"command": "whoami", "capabilityLevel": 0, "approved": False},
    )

    assert response.status_code == 403
    assert "CapabilityRequiredError" in response.text


def test_pc_controller_routes_succeeds_with_valid_capability_token(monkeypatch, tmp_path: Path):
    """POST /v3/pc/execute with valid capability token returns HTTP 200.

    [S16 FIX 2026-09-13] No skip markers: both T00 gates reject new
    pytest.skip() calls and new skip/xfail/skipif decorators. The route
    executes through PCController._run_sync (powershell.exe, Windows-only
    product executor): Windows asserts the full success contract on the HTTP
    200 body, every other OS asserts the fail-closed executor-absent body
    (success=False, returnCode=None) on the same HTTP 200.
    """
    from scp.api.routes import pc_controller_routes
    from scp.security.capability_epoch import CapabilityAuthority

    cap_state = tmp_path / "capability_state.json"
    authority = CapabilityAuthority(cap_state)
    pc_controller_routes._controller.capability_authority = authority
    # Clear any kill switch engaged by earlier tests (module-level singleton uses project_root data_dir)
    if pc_controller_routes._controller.kill_switch_engaged():
        token = authority.issue("pc.clear_kill_switch")
        pc_controller_routes._controller.clear_kill_switch(approved=True, capability_token=token)

    monkeypatch.setenv("SCP_PC_CONTROLLER_TOKEN", "mock_pc_token")
    app = FastAPI()
    app.include_router(pc_controller_routes.router)
    client = TestClient(app)

    token = authority.issue("pc.execute")

    response = client.post(
        "/v3/pc/execute",
        headers={
            "X-SCP-PC-Token": "mock_pc_token",
            "X-SCP-Capability-Token": json.dumps(token.to_dict()),
        },
        json={"command": "whoami", "capabilityLevel": 0, "approved": False},
    )

    assert response.status_code == 200, f"Route returned error: {response.text}"
    body = response.json()
    if sys.platform == "win32":
        assert body.get("success") is True
        assert body.get("returnCode") == 0
    else:
        # Executor absent on this OS: fail-closed body on the same HTTP 200.
        assert body.get("success") is False
        assert body.get("returnCode") is None
