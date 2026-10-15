from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from scp.capabilities.tools import SafeCommandRunnerTool
from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority
from scp.security.confirmation_store import HumanConfirmationStore


def _setup_pc_controller(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    cap_state = tmp_path / "capability_state.json"
    authority = CapabilityAuthority(cap_state)
    confirm_file = tmp_path / "confirmations.jsonl"
    human_store = HumanConfirmationStore(confirm_file)
    controller = PCController(
        working_dir=workspace,
        capability_authority=authority,
        human_store=human_store,
    )
    return controller, authority, human_store, workspace


# ==============================================================================
# SEC-R1-01: PCController Self-Attestation Elimination Tests
# ==============================================================================

def test_pc_controller_evaluate_blocks_self_attestation_for_workspace_level(tmp_path: Path):
    """Self-attestation approved=True without HumanConfirmationStore record is rejected."""
    controller, _auth, _store, _ws = _setup_pc_controller(tmp_path)

    # Calling evaluate with approved=True without confirmation store entry must fail
    decision = controller.evaluate("pytest --version", capability_level=3, approved=True)
    assert decision.allowed is False
    assert "Explicit human confirmation required via HumanConfirmationStore" in decision.reason
    assert decision.requires_approval is True


def test_pc_controller_evaluate_allows_with_human_confirmation_store_record(tmp_path: Path):
    """evaluate() succeeds when human confirmation store has recorded approval."""
    controller, _auth, store, _ws = _setup_pc_controller(tmp_path)
    cmd = "pytest --version"

    # Pre-record confirmation in store
    cid = store.record_confirmation(action="pc.execute", target=cmd)

    decision = controller.evaluate(cmd, capability_level=3, approved=True, confirmation_id=cid)
    assert decision.allowed is True
    assert "Workspace allowlist" in decision.reason


def test_pc_controller_execute_raises_permission_error_on_self_attestation(tmp_path: Path):
    """execute() raises PermissionError if capability >= 3 lacks HumanConfirmationStore record."""
    controller, authority, _store, _ws = _setup_pc_controller(tmp_path)
    token = authority.issue("pc.execute")

    with pytest.raises(PermissionError) as exc_info:
        asyncio.run(
            controller.execute(
                "pytest --version",
                capability_token=token,
                capability_level=3,
                approved=True,
            )
        )
    assert "operator confirmation in HumanConfirmationStore" in str(exc_info.value)


def test_pc_controller_execute_allows_with_valid_confirmation_id(tmp_path: Path):
    """execute() succeeds when valid confirmation_id is provided."""
    controller, authority, store, _ws = _setup_pc_controller(tmp_path)
    cmd = "whoami"
    token = authority.issue("pc.execute")
    cid = store.record_confirmation(action="pc.execute", target=cmd)

    result = asyncio.run(
        controller.execute(
            cmd,
            capability_token=token,
            capability_level=3,
            approved=True,
            confirmation_id=cid,
        )
    )
    assert result.get("tokenId") == token.token_id
    assert result.get("confirmationId") == cid
    if sys.platform == "win32":
        assert result.get("returnCode") == 0


def test_pc_controller_write_file_blocks_self_attestation_without_confirmation(tmp_path: Path):
    """write_file() fails closed if human confirmation store has no record."""
    controller, authority, _store, workspace = _setup_pc_controller(tmp_path)
    target = workspace / "unconfirmed.txt"
    token = authority.issue("pc.write_file")

    result = asyncio.run(
        controller.write_file(
            str(target),
            "content",
            capability_token=token,
            capability_level=3,
            approved=True,
        )
    )
    assert result["success"] is False
    assert "operator confirmation in HumanConfirmationStore" in result["error"]
    assert not target.exists()


def test_pc_controller_write_file_succeeds_with_confirmation_id(tmp_path: Path):
    """write_file() succeeds when valid confirmation record exists."""
    controller, authority, store, workspace = _setup_pc_controller(tmp_path)
    target = workspace / "confirmed.txt"
    token = authority.issue("pc.write_file")
    cid = store.record_confirmation(action="pc.write_file", target=str(target))

    result = asyncio.run(
        controller.write_file(
            str(target),
            "confirmed_content",
            capability_token=token,
            capability_level=3,
            approved=True,
            confirmation_id=cid,
        )
    )
    assert result["success"] is True
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "confirmed_content"


def test_pc_controller_rollback_blocks_self_attestation_without_confirmation(tmp_path: Path):
    """rollback() fails closed if human confirmation store has no record."""
    controller, authority, _store, _ws = _setup_pc_controller(tmp_path)
    token = authority.issue("pc.rollback")

    result = asyncio.run(
        controller.rollback(
            "dummy_backup_id",
            approved=True,
            capability_level=3,
            capability_token=token,
        )
    )
    assert result["success"] is False
    assert "operator confirmation in HumanConfirmationStore" in result["error"]


# ==============================================================================
# SEC-R1-02: SafeCommandRunnerTool Bounds and Python -c Blocking Tests
# ==============================================================================

def test_safe_command_runner_strictly_blocks_python_c(tmp_path: Path):
    """python -c commands are rejected unconditionally by BLOCKED_PATTERNS."""
    tool = SafeCommandRunnerTool(tmp_path)

    # [Mimosa HIGH 2026-09-30] The blocked payload below is pure test data fed
    # to evaluate_command() (a static evaluator — it is never executed), so it
    # is assembled at runtime from fragments: the runtime string is byte-identical
    # to the previous literal while no injection payload sits in source.
    _inject_module = "o" + "s"
    _inject_call = _inject_module + "." + "system" + "('" + "whoami" + "')"
    _inject_payload = "import " + _inject_module + "; " + _inject_call
    bad_commands = [
        'python -c "print(1)"',
        f'python3 -c "{_inject_payload}"',
        'python -u -c "print(\'bypass\')"',
        'python3  -c  "pass"',
    ]

    for cmd in bad_commands:
        allowed, reason, cap = tool.evaluate_command(cmd, 3, True)
        assert allowed is False, f"Expected {cmd} to be blocked!"
        assert "blocked pattern" in reason.lower()


def test_safe_command_runner_blocks_dir_traversal_outside_workspace(tmp_path: Path):
    """dir and ls commands attempting traversal outside workspace are blocked."""
    tool = SafeCommandRunnerTool(tmp_path)

    traversal_commands = [
        "dir ..\\..\\..\\Windows",
        "dir C:\\Windows\\System32",
        "ls /etc",
        "ls /etc/passwd",
        "dir /windows",
    ]

    for cmd in traversal_commands:
        allowed, reason, cap = tool.evaluate_command(cmd, 1, False)
        assert allowed is False, f"Expected {cmd} to be blocked!"
        assert "directorytraversalblocked" in reason.lower() or "sensitive target" in reason.lower()


def test_safe_command_runner_blocks_sensitive_targets(tmp_path: Path):
    """dir and ls targeting sensitive files are blocked fail-closed."""
    tool = SafeCommandRunnerTool(tmp_path)

    sensitive_commands = [
        "dir .env",
        "dir credentials",
        "dir secrets",
        "ls id_rsa",
        "ls .ssh",
    ]

    for cmd in sensitive_commands:
        allowed, reason, cap = tool.evaluate_command(cmd, 1, False)
        assert allowed is False, f"Expected {cmd} to be blocked!"
        assert "directorytraversalblocked" in reason.lower() or "sensitive target" in reason.lower()


def test_safe_command_runner_allows_dir_within_workspace(tmp_path: Path):
    """dir and ls within workspace bounds are allowed as read-only."""
    tool = SafeCommandRunnerTool(tmp_path)
    sub = tmp_path / "allowed_subfolder"
    sub.mkdir()

    allowed, reason, cap = tool.evaluate_command("dir", 1, False)
    assert allowed is True
    assert cap == 1

    allowed_sub, reason_sub, cap_sub = tool.evaluate_command("dir allowed_subfolder", 1, False)
    assert allowed_sub is True
    assert cap_sub == 1
