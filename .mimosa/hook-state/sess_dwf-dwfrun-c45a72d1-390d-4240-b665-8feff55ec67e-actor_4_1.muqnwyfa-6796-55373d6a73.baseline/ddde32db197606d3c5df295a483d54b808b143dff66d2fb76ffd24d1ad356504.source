import asyncio
from pathlib import Path

import pytest

from scp.hands.hands_executor import HandsExecutor
from scp.hands.planner import HandsPlanner
from scp.hands.task_kernel_bridge import TaskKernelHandsBridge
from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority

# ==============================================================================
# T03 - HANDS AUTHORITY PEP (FA-05 ERADICATION & INV-AUTH-02 SCOPED VALIDATION)
# ==============================================================================
# Verifies that HandsExecutor never self-issues capability authority, rejects
# unauthorized actions fail-closed, validates exact scoped subjects, respects
# authority revocations, and requires explicit tokens for rollback.
# ==============================================================================


def _setup_executor(tmp_path: Path) -> tuple[HandsExecutor, Path, CapabilityAuthority]:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    cap_state = tmp_path / "capability_state.json"
    cap_auth = CapabilityAuthority(cap_state)
    executor = HandsExecutor(
        controller=PCController(working_dir=workspace),
        capability_authority=cap_auth,
        data_dir=tmp_path / "hands_data",
    )
    return executor, workspace, cap_auth


def _confirm_write(executor: HandsExecutor, target: Path) -> str:
    return executor.controller.human_store.record_confirmation(
        action="pc.write_file", target=str(target.resolve()), ttl_seconds=60,
    )


def test_hands_executor_rejects_missing_token_fail_closed(tmp_path):
    """Execution with capability_token=None must fail closed without side-effects."""
    executor, workspace, _cap_auth = _setup_executor(tmp_path)
    target = workspace / "blocked_missing.txt"

    result = asyncio.run(
        executor.execute(
            action="pc.write_file",
            params={"path": str(target), "content": "forbidden_payload"},
            capability_level=3,
            approved=True,
            capability_token=None,
        )
    )

    assert result.get("success") is False
    assert "CapabilityRequiredError" in result.get("error", "")
    assert not target.exists(), "Side effect executed without capability token (FA-05 violation)"


def test_hands_executor_rejects_scope_mismatch_fail_closed(tmp_path):
    """Token authorized for a different action must be rejected fail-closed."""
    executor, workspace, cap_auth = _setup_executor(tmp_path)
    target = workspace / "blocked_scope.txt"
    status_token = cap_auth.issue("hands:pc.status")

    result = asyncio.run(
        executor.execute(
            action="pc.write_file",
            params={"path": str(target), "content": "forbidden_payload"},
            capability_level=3,
            approved=True,
            capability_token=status_token,
        )
    )

    assert result.get("success") is False
    assert "CapabilityScopeMismatchError" in result.get("error", "")
    assert not target.exists(), "Side effect executed with mismatched token scope (INV-AUTH-02 violation)"


def test_hands_executor_rejects_revoked_epoch(tmp_path):
    """Token with an obsolete or revoked epoch must be rejected fail-closed."""
    executor, workspace, cap_auth = _setup_executor(tmp_path)
    target = workspace / "blocked_revoked.txt"
    write_token = cap_auth.issue("hands:pc.write_file")

    # Revoke all tokens across the authority
    cap_auth.revoke(reason="security_alert", actor="sec_op")

    result = asyncio.run(
        executor.execute(
            action="pc.write_file",
            params={"path": str(target), "content": "forbidden_payload"},
            capability_level=3,
            approved=True,
            capability_token=write_token,
        )
    )

    assert result.get("success") is False
    error = result.get("error", "").lower()
    assert "revoked" in error or "stale" in error, f"Unexpected error: {result.get('error')}"
    assert not target.exists(), "Side effect executed with revoked capability token"


def test_hands_executor_rollback_requires_token(tmp_path):
    """Rollback requires an authorized token with scoped subject hands:rollback."""
    executor, workspace, cap_auth = _setup_executor(tmp_path)
    target = workspace / "rollback_target.txt"
    write_token = cap_auth.issue("hands:pc.write_file")
    write_confirmation = _confirm_write(executor, target)

    write_res = asyncio.run(
        executor.execute(
            action="pc.write_file",
            params={"path": str(target), "content": "initial_content", "confirmation_id": write_confirmation},
            capability_level=3,
            approved=True,
            capability_token=write_token,
        )
    )
    assert write_res.get("success") is True
    checkpoint_id = write_res.get("checkpointId")
    assert checkpoint_id is not None
    assert target.exists()

    # 1. Rollback without token -> rejected fail-closed
    rb_missing = asyncio.run(
        executor.rollback(
            checkpoint_id=checkpoint_id,
            capability_level=3,
            approved=True,
            capability_token=None,
        )
    )
    assert rb_missing.get("success") is False
    assert "CapabilityRequiredError" in rb_missing.get("error", "")
    assert target.exists(), "Rollback occurred without capability token"

    # 2. Rollback with write token (scope mismatch) -> rejected fail-closed
    rb_wrong_scope = asyncio.run(
        executor.rollback(
            checkpoint_id=checkpoint_id,
            capability_level=3,
            approved=True,
            capability_token=write_token,
        )
    )
    assert rb_wrong_scope.get("success") is False
    assert "CapabilityScopeMismatchError" in rb_wrong_scope.get("error", "")
    assert target.exists(), "Rollback occurred with wrong token scope"

    # 3. Rollback with valid hands:rollback token -> succeeds and reverts state
    rollback_token = cap_auth.issue("hands:rollback")
    rb_valid = asyncio.run(
        executor.rollback(
            checkpoint_id=checkpoint_id,
            capability_level=3,
            approved=True,
            capability_token=rollback_token,
        )
    )
    assert rb_valid.get("success") is True, f"Rollback failed: {rb_valid}"
    assert not target.exists(), "Rollback did not remove newly created file"


# ==============================================================================
# TaskKernelHandsBridge PEP & Policy Denial Regression Tests
# ==============================================================================


def _setup_bridge(tmp_path: Path) -> tuple[TaskKernelHandsBridge, Path, CapabilityAuthority]:
    executor, workspace, cap_auth = _setup_executor(tmp_path)
    bridge = TaskKernelHandsBridge(executor, db_path=tmp_path / "kernel.sqlite3")
    return bridge, workspace, cap_auth


def test_bridge_execute_missing_token_clean_policy_denial_no_recovery(tmp_path: Path):
    """Direct bridge execution with capability_token=None must fail closed.

    Verifies:
    1. PermissionError raised (CapabilityRequiredError contract, FA-05 marker)
    2. Zero side effects on disk
    3. Zero durable kernel state (no task, no lease, no journal events)

    [C1s2 TRIAGE 2026-09-12] This test pinned the PRE-M4 contract: it expected
    a missing token to produce a structured denial result with a FAILED kernel
    task (kernel mutation before authz). Commit 0d13c85 (M4 FIX 2026-09-11)
    deliberately changed the product to fail closed EARLIER: PermissionError
    (CapabilityRequiredError, FA-05) is raised BEFORE action resolution and
    BEFORE any TaskKernel state mutation. The M4-era T03 fix updated
    test_flow_04_control_hands_scp_standard.py but missed this file — same
    root cause as the T04 branch-9 triage (session C1s2). Strictness
    INCREASED: the durable database must now contain ZERO kernel state
    instead of merely a FAILED task row with a released lease.
    """
    bridge, workspace, _cap_auth = _setup_bridge(tmp_path)
    target = workspace / "blocked_bridge_missing.txt"

    try:
        with pytest.raises(PermissionError) as perm_exc:
            asyncio.run(
                bridge.execute(
                    action="pc.write_file",
                    params={"path": str(target), "content": "test"},
                    capability_level=3,
                    approved=True,
                    capability_token=None,
                )
            )

        # 1. Fail-closed ordering contract (M4): PermissionError escapes the
        #    bridge call — not a structured result, not a registry KeyError.
        assert "CapabilityRequiredError" in str(perm_exc.value)
        assert "FA-05" in str(perm_exc.value)

        # 2. Zero side effects on disk (unchanged from the original contract).
        assert target.exists() is False, "Side effect executed without capability token (FA-05 violation)"

        # 3. Stronger durable-state contract: NO kernel mutation at all — no
        #    task row, no lease, no journal events (pre-M4 the denial left a
        #    FAILED task + released lease behind).
        assert bridge.kernel.conn.execute(
            "SELECT COUNT(*) AS n FROM tasks"
        ).fetchone()["n"] == 0
        assert bridge.kernel.conn.execute(
            "SELECT COUNT(*) AS n FROM leases"
        ).fetchone()["n"] == 0
        assert bridge.kernel.conn.execute(
            "SELECT COUNT(*) AS n FROM events"
        ).fetchone()["n"] == 0
    finally:
        bridge.close()


def test_bridge_rejects_scope_mismatch_fail_closed(tmp_path: Path):
    """Bridge execution with token authorized for a different action must fail closed."""
    bridge, workspace, cap_auth = _setup_bridge(tmp_path)
    target = workspace / "blocked_bridge_scope.txt"
    status_token = cap_auth.issue("hands:pc.status")

    try:
        result = asyncio.run(
            bridge.execute(
                action="pc.write_file",
                params={"path": str(target), "content": "test"},
                capability_level=3,
                approved=True,
                capability_token=status_token,
            )
        )

        assert result.get("success") is False
        assert "CapabilityScopeMismatchError" in result.get("error", "")
        assert "OptimisticLockError" not in result.get("error", "")
        assert result.get("requiresRecovery") is False
        assert result.get("kernel", {}).get("requiresRecovery") is False
        assert result.get("kernel", {}).get("taskState") == "FAILED"
        assert result.get("kernel", {}).get("state") == "FAILED"
        assert target.exists() is False
    finally:
        bridge.close()


def test_bridge_rejects_revoked_token_fail_closed(tmp_path: Path):
    """Bridge execution with revoked token must fail closed without recovery."""
    bridge, workspace, cap_auth = _setup_bridge(tmp_path)
    target = workspace / "blocked_bridge_revoked.txt"
    write_token = cap_auth.issue("hands:pc.write_file")
    cap_auth.revoke(reason="security_alert", actor="sec_op")

    try:
        result = asyncio.run(
            bridge.execute(
                action="pc.write_file",
                params={"path": str(target), "content": "test"},
                capability_level=3,
                approved=True,
                capability_token=write_token,
            )
        )

        assert result.get("success") is False
        error = result.get("error", "").lower()
        assert "revoked" in error or "stale" in error
        assert "OptimisticLockError" not in result.get("error", "")
        assert result.get("requiresRecovery") is False
        assert result.get("kernel", {}).get("requiresRecovery") is False
        assert result.get("kernel", {}).get("taskState") == "FAILED"
        assert result.get("kernel", {}).get("state") == "FAILED"
        assert target.exists() is False
    finally:
        bridge.close()


# ==============================================================================
# HandsPlanner Step-Level Capability Token Regression Tests
# ==============================================================================


def test_planner_step_capability_token_preservation_and_execution(tmp_path: Path):
    """Step-level capabilityToken must be preserved during plan creation and applied during execution."""
    executor, workspace, cap_auth = _setup_executor(tmp_path)
    planner = HandsPlanner(executor=executor)

    # 1. Step with dict capabilityToken
    tok1 = cap_auth.issue("hands:pc.write_file")
    target1 = workspace / "plan_step1.txt"
    confirmation1 = _confirm_write(executor, target1)
    plan1 = planner.create_plan(
        "write step 1",
        [
            {
                "action": "pc.write_file",
                "params": {"path": str(target1), "content": "hello_step_1", "confirmation_id": confirmation1},
                "capabilityToken": tok1.to_dict(),
            }
        ],
    )
    assert plan1["steps"][0]["capabilityToken"] is not None
    assert plan1["steps"][0]["capabilityToken"]["subject"] == "hands:pc.write_file"

    res1 = asyncio.run(planner.run_plan(plan1["planId"], capability_level=3, approved=True))
    assert res1.get("success") is True, f"Plan 1 run failed: {res1}"
    assert target1.exists()
    assert target1.read_text(encoding="utf-8") == "hello_step_1"

    # 2. Step with CapabilityToken dataclass object directly
    tok2 = cap_auth.issue("hands:pc.write_file")
    target2 = workspace / "plan_step2.txt"
    confirmation2 = _confirm_write(executor, target2)
    plan2 = planner.create_plan(
        "write step 2",
        [
            {
                "action": "pc.write_file",
                "params": {"path": str(target2), "content": "hello_step_2", "confirmation_id": confirmation2},
                "capabilityToken": tok2,
            }
        ],
    )
    assert isinstance(plan2["steps"][0]["capabilityToken"], dict)
    assert plan2["steps"][0]["capabilityToken"]["subject"] == "hands:pc.write_file"

    res2 = asyncio.run(planner.run_plan(plan2["planId"], capability_level=3, approved=True))
    assert res2.get("success") is True, f"Plan 2 run failed: {res2}"
    assert target2.exists()
    assert target2.read_text(encoding="utf-8") == "hello_step_2"


def test_planner_step_capability_token_scope_mismatch_fails_closed(tmp_path: Path):
    """Step-level capability token with mismatched scope must fail closed."""
    executor, workspace, cap_auth = _setup_executor(tmp_path)
    planner = HandsPlanner(executor=executor)

    tok_mismatched = cap_auth.issue("hands:pc.status")
    target = workspace / "plan_mismatched.txt"
    plan = planner.create_plan(
        "mismatched step",
        [
            {
                "action": "pc.write_file",
                "params": {"path": str(target), "content": "should_fail"},
                "capabilityToken": tok_mismatched,
            }
        ],
    )
    res = asyncio.run(planner.run_plan(plan["planId"], capability_level=3, approved=True))
    assert res.get("success") is False
    assert "CapabilityScopeMismatchError" in str(res.get("result", {}).get("error", ""))
    assert not target.exists()


def test_human_confirmation_store_flow(tmp_path: Path):
    """HumanConfirmationStore properly validates recorded confirmations and rejects mismatched actions/targets."""
    from scp.security.confirmation_store import HumanConfirmationStore

    store_file = tmp_path / "confirmations.jsonl"
    store = HumanConfirmationStore(store_path=store_file)

    cid = store.record_confirmation(action="cmd.run", target="pytest -q", ttl_seconds=60)
    assert cid.startswith("conf-")
    assert store.is_confirmed(action="cmd.run", target="pytest -q", confirmation_id=cid) is True
    assert store.is_confirmed(action="cmd.run", target="rm -rf /", confirmation_id=cid) is False
    assert store.is_confirmed(action="other.action", target="pytest -q", confirmation_id=cid) is False
