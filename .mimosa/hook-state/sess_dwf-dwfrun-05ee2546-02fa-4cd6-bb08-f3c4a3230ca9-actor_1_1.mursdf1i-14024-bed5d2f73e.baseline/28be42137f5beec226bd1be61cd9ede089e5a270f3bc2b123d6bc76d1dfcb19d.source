"""Regression tests for the PCController command path guard.

[AUDIT-FIX 2026-09-24] External audit probe PROVED that READ_ONLY_PATTERNS
allowed `evaluate('type .env', capability_level=0)` and that
`execute('type .env')` returned the file content: the sensitive-path policy
(_sensitive/_inside_root) was only applied to read_file/write_file, never to
command evaluation. A PCController token holder could read .env and any
absolute path through the read-only command allowlist.

Fix contract: for file-read verbs (type|cat|get-content) the referenced path
arguments must pass the SAME sensitive-path / workspace-root validation as
read_file. A violation denies with CapabilityScopeMismatchError semantics,
regardless of capability level. FA-09: these tests are the exploit scenarios
proving both the old failure and the new fail-closed behavior.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority


@pytest.fixture()
def controller(tmp_path: Path) -> tuple[PCController, Path]:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "notes.txt").write_text("benign content", encoding="utf-8")
    (workspace / ".env").write_text("SECRET_VALUE=1", encoding="utf-8")
    (workspace / "sub").mkdir(exist_ok=True)
    (workspace / "sub" / "report.txt").write_text("report", encoding="utf-8")
    authority = CapabilityAuthority(tmp_path / "capability_state.json")
    controller = PCController(working_dir=workspace, capability_authority=authority)
    return controller, workspace


def test_type_dotenv_denied_at_read_only_level(controller):
    """`type .env` must be denied even at capability_level 0 (read-only)."""
    pc, _ws = controller
    decision = pc.evaluate("type .env", 0)
    assert decision.allowed is False
    assert "CapabilityScopeMismatchError" in decision.reason
    assert "sensitive" in decision.reason


def test_type_dotenv_denied_even_when_approved_high_level(controller):
    """No capability level or approval makes a sensitive read acceptable."""
    pc, _ws = controller
    for level in (0, 2, 3, 5):
        decision = pc.evaluate("type .env", level, approved=True)
        assert decision.allowed is False, f"level={level}"


def test_type_workspace_file_allowed(controller):
    """Legitimate read-only reads inside the workspace keep working."""
    pc, _ws = controller
    for cmd in ("type notes.txt", "cat notes.txt", "get-content notes.txt", "type sub/report.txt"):
        decision = pc.evaluate(cmd, 0)
        assert decision.allowed is True, f"{cmd}: {decision.reason}"


def test_get_content_absolute_sensitive_path_denied(controller):
    """`get-content <abs>/.env` (absolute path) must be denied."""
    pc, ws = controller
    decision = pc.evaluate(f"get-content {ws.parent / 'outside' / '.env'}", 0)
    assert decision.allowed is False
    assert "CapabilityScopeMismatchError" in decision.reason


def test_get_content_absolute_outside_root_denied(controller):
    """Absolute non-sensitive paths outside the workspace root are denied too."""
    pc, _ws = controller
    decision = pc.evaluate("get-content C:/Windows/win.ini", 0)
    assert decision.allowed is False
    assert "outside" in decision.reason


def test_type_parent_traversal_denied(controller):
    pc, _ws = controller
    decision = pc.evaluate("type ..\\.env", 0)
    assert decision.allowed is False


def test_type_quoted_absolute_path_denied(controller):
    """Quoted absolute paths (spaces) must not slip past tokenized extraction."""
    pc, _ws = controller
    decision = pc.evaluate('type "C:/Program Files/secret file.txt"', 0)
    assert decision.allowed is False


def test_non_path_read_only_commands_unchanged(controller):
    """Read-only commands without file-read verbs keep the old behavior."""
    pc, _ws = controller
    for cmd in ("git status", "whoami", "hostname", "tasklist"):
        decision = pc.evaluate(cmd, 0)
        assert decision.allowed is True, f"{cmd}: {decision.reason}"


def test_execute_blocks_sensitive_read_command(controller):
    """execute() fail-closes on `type .env` — the command must never run."""
    pc, _ws = controller
    with pytest.raises(PermissionError):
        asyncio.run(pc.execute("type .env", capability_token=None))
