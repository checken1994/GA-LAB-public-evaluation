"""Tests for R6: AutoFix Rollback Remediation (Cognitive Loop Perfect Isolation).

Verifies:
1. ShadowSnapshotManager creation of durable pre-patch snapshots under data/shadow/active/.
2. Atomic restoration and transaction state transition on rollback (to data/shadow/rolled_back/).
3. Commit transitions to data/shadow/completed/ with post-patch hashes.
4. Crash recovery via recover_abandoned_transactions() restoring corrupted files from dead processes.
5. AutoFix engine integration: automatic rollback on syntax error or failed verification.
6. Fail-closed reality test gate in _auto_approve_tier3.
7. Clean Workspace mandate: zero .tier3bak files left in the source tree.
"""
import hashlib
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from scp.autofix.engine import AutoFixEngine
from scp.autofix.runner_phases.ast_scan import BugReport
from scp.autofix.shadow_snapshot import (
    ShadowSnapshotManager,
)


@pytest.fixture(autouse=True)
def deterministic_why_gate(monkeypatch):
    """Pin the WHY gate to its deterministic (non-LLM) falsification layer.

    scp/autofix/runner.py loads the repo .env at import time and .env may
    carry SCP_WHY_LLM_ENABLED=1. In full-suite runs an earlier test module
    (e.g. tests/T03_capability/test_flow_07_autofix_scp_standard.py, which
    patches scp.autofix.runner.run_deep_audit) imports the runner; the .env
    value then leaks into os.environ for the rest of the pytest process and
    the WHY gate consults a real LLM. A hallucinated "SELF_FALSIFIED: yes"
    verdict blocks the fix inside _auto_fix_gates BEFORE the shadow snapshot
    transaction begins, so the end-to-end rollback test below would see an
    empty rolled_back/ directory. The deterministic falsification patterns
    remain authoritative here — same pin as
    tests/T09_golden_task/test_golden_b_epistemic_loop.py. monkeypatch
    restores the caller's environment afterwards.
    """
    monkeypatch.setenv("SCP_WHY_LLM_ENABLED", "0")


@pytest.fixture
def temp_workspace(tmp_path):
    """Creates a sandbox workspace with data and source directories."""
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shadow_dir = data_dir / "shadow"
    shadow_dir.mkdir(parents=True, exist_ok=True)
    return {
        "root": tmp_path,
        "src": src_dir,
        "data": data_dir,
        "shadow": shadow_dir,
    }


# =========================================================================
# 1. ShadowSnapshotManager Unit & Lifecycle Tests
# =========================================================================

def test_shadow_snapshot_begin_creates_active_transaction(temp_workspace):
    """Verifies that begin() creates active/<tx_id>/manifest.json and backup files."""
    mgr = ShadowSnapshotManager(shadow_dir=temp_workspace["shadow"])
    file1 = temp_workspace["src"] / "module_a.py"
    file1.write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    sha_expected = hashlib.sha256(file1.read_bytes()).hexdigest()

    tx_id = mgr.begin([file1], bug_id="test_bug_001")
    assert tx_id.startswith("tx_")

    tx_dir = temp_workspace["shadow"] / "active" / tx_id
    assert tx_dir.is_dir()
    manifest_path = tx_dir / "manifest.json"
    assert manifest_path.is_file()

    with manifest_path.open("r", encoding="utf-8") as mf:
        manifest = json.load(mf)

    assert manifest["tx_id"] == tx_id
    assert manifest["bug_id"] == "test_bug_001"
    assert manifest["status"] == "PRE_PATCH"
    assert manifest["pid"] == os.getpid()
    assert len(manifest["target_files"]) == 1

    rec = manifest["target_files"][0]
    assert rec["target_path"] == str(file1.resolve())
    assert rec["pre_sha256"] == sha_expected
    assert rec["exists"] is True

    backup_path = tx_dir / rec["backup_file"]
    assert backup_path.is_file()
    assert backup_path.read_text(encoding="utf-8") == "def hello():\n    return 'world'\n"


def test_shadow_snapshot_commit_lifecycle(temp_workspace):
    """Verifies that commit() updates post-patch hash and moves tx to completed/."""
    mgr = ShadowSnapshotManager(shadow_dir=temp_workspace["shadow"])
    file1 = temp_workspace["src"] / "service.py"
    file1.write_text("VAL = 1\n", encoding="utf-8")

    tx_id = mgr.begin([file1], bug_id="commit_test")
    assert (temp_workspace["shadow"] / "active" / tx_id).is_dir()

    # Apply patch
    file1.write_text("VAL = 2\n", encoding="utf-8")
    post_sha = hashlib.sha256(file1.read_bytes()).hexdigest()

    ok = mgr.commit(tx_id)
    assert ok is True
    assert not (temp_workspace["shadow"] / "active" / tx_id).exists()

    completed_dir = temp_workspace["shadow"] / "completed" / tx_id
    assert completed_dir.is_dir()

    with (completed_dir / "manifest.json").open("r", encoding="utf-8") as mf:
        manifest = json.load(mf)

    assert manifest["status"] == "COMMITTED"
    assert manifest["target_files"][0]["post_sha256"] == post_sha
    assert file1.read_text(encoding="utf-8") == "VAL = 2\n"


def test_shadow_snapshot_atomic_rollback(temp_workspace):
    """Verifies that rollback() restores the exact pre-patch bytes and moves tx to rolled_back/."""
    mgr = ShadowSnapshotManager(shadow_dir=temp_workspace["shadow"])
    original_code = "def calculate(x):\n    return x * 10\n"
    target = temp_workspace["src"] / "calc.py"
    target.write_text(original_code, encoding="utf-8")

    tx_id = mgr.begin([target], bug_id="rollback_test")

    # Corrupt target with broken syntax
    target.write_text("def calculate(x):\n    SYNTAX ERROR !!!\n", encoding="utf-8")

    ok = mgr.rollback(tx_id, reason="Broken syntax detected during verify")
    assert ok is True

    # Check file restored
    assert target.read_text(encoding="utf-8") == original_code
    assert not (temp_workspace["shadow"] / "active" / tx_id).exists()

    rolled_back_dir = temp_workspace["shadow"] / "rolled_back" / tx_id
    assert rolled_back_dir.is_dir()
    assert (rolled_back_dir / "failure_reason.txt").is_file()

    with (rolled_back_dir / "manifest.json").open("r", encoding="utf-8") as mf:
        manifest = json.load(mf)
    assert manifest["status"] == "ROLLED_BACK"
    assert "Broken syntax" in manifest["rollback_reason"]


def test_shadow_snapshot_rollback_unlinks_newly_created_file(temp_workspace):
    """Verifies that rollback() removes a file that did not exist before the transaction."""
    mgr = ShadowSnapshotManager(shadow_dir=temp_workspace["shadow"])
    new_file = temp_workspace["src"] / "brand_new.py"
    assert not new_file.exists()

    tx_id = mgr.begin([new_file], bug_id="new_file_test")

    # Create the file during the patch step
    new_file.write_text("print('should be removed on rollback')\n", encoding="utf-8")
    assert new_file.exists()

    ok = mgr.rollback(tx_id, reason="Patch failed")
    assert ok is True
    assert not new_file.exists()


# =========================================================================
# 2. Crash Recovery of Abandoned Transactions
# =========================================================================

def test_recover_abandoned_transactions_from_dead_process(temp_workspace):
    """Simulates a prior process crash during patch testing and verifies startup recovery."""
    mgr = ShadowSnapshotManager(shadow_dir=temp_workspace["shadow"])
    target = temp_workspace["src"] / "important.py"
    target.write_text("ORIGINAL_CONTENT = True\n", encoding="utf-8")
    orig_sha = hashlib.sha256(target.read_bytes()).hexdigest()

    # Simulate an active transaction directory left by a dead process
    tx_id = "tx_crash_simulation_999"
    tx_dir = temp_workspace["shadow"] / "active" / tx_id
    files_dir = tx_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    backup_file = files_dir / "0_important.py.bak"
    backup_file.write_text("ORIGINAL_CONTENT = True\n", encoding="utf-8")

    manifest = {
        "tx_id": tx_id,
        "bug_id": "simulated_crash_bug",
        "status": "PRE_PATCH",
        "created_at": 100000.0,
        "pid": 9999999,  # Definitely non-existent PID
        "target_files": [
            {
                "target_path": str(target.resolve()),
                "backup_file": "files/0_important.py.bak",
                "pre_sha256": orig_sha,
                "exists": True,
            }
        ],
    }
    with (tx_dir / "manifest.json").open("w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

    # Simulate that the crash left the target file corrupted on disk
    target.write_text("CORRUPTED_DUE_TO_CRASH = False\n", encoding="utf-8")
    assert target.read_text(encoding="utf-8") != "ORIGINAL_CONTENT = True\n"

    # Now run crash recovery reconciler
    recovered = mgr.recover_abandoned_transactions()
    assert tx_id in recovered

    # Target must be restored to original state!
    assert target.read_text(encoding="utf-8") == "ORIGINAL_CONTENT = True\n"
    assert not (temp_workspace["shadow"] / "active" / tx_id).exists()
    assert (temp_workspace["shadow"] / "rolled_back" / tx_id).is_dir()


def test_autofix_engine_startup_runs_crash_recovery(temp_workspace):
    """Verifies that AutoFixEngine.__init__ invokes recover_abandoned_transactions automatically."""
    shadow_dir = temp_workspace["shadow"]
    target = temp_workspace["src"] / "kernel_state.py"
    target.write_text("SAFE_STATE = 'normal'\n", encoding="utf-8")
    orig_sha = hashlib.sha256(target.read_bytes()).hexdigest()

    tx_id = "tx_startup_recovery_123"
    tx_dir = shadow_dir / "active" / tx_id
    files_dir = tx_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    backup_file = files_dir / "0_kernel_state.py.bak"
    backup_file.write_text("SAFE_STATE = 'normal'\n", encoding="utf-8")

    manifest = {
        "tx_id": tx_id,
        "bug_id": "startup_test",
        "status": "PRE_PATCH",
        "created_at": 100000.0,
        "pid": 9999998,
        "target_files": [
            {
                "target_path": str(target.resolve()),
                "backup_file": "files/0_kernel_state.py.bak",
                "pre_sha256": orig_sha,
                "exists": True,
            }
        ],
    }
    with (tx_dir / "manifest.json").open("w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

    # Corrupt target
    target.write_text("BROKEN_STATE_BEFORE_INIT = True\n", encoding="utf-8")

    # Initialize AutoFixEngine
    engine = AutoFixEngine(data_dir=str(temp_workspace["data"]))
    assert hasattr(engine, "shadow_snapshot_mgr")

    # File must be restored upon engine initialization
    assert target.read_text(encoding="utf-8") == "SAFE_STATE = 'normal'\n"
    assert not (shadow_dir / "active" / tx_id).exists()
    assert (shadow_dir / "rolled_back" / tx_id).is_dir()


# =========================================================================
# 3. Clean Workspace Mandate: Zero .tier3bak Files
# =========================================================================

def test_clean_workspace_no_tier3bak_files(temp_workspace):
    """Verifies that no .tier3bak files are created in the source tree during patching or rollback."""
    src_file = temp_workspace["src"] / "app_logic.py"
    src_file.write_text("import html\n\ndef render(val):\n    return html.escape(val)\n", encoding="utf-8")

    engine = AutoFixEngine(data_dir=str(temp_workspace["data"]))

    bug = BugReport(
        file=str(src_file),
        line=4,
        bug_type="BareExceptPass",
        description="swallows error",
        suggested_fix="try:\n    pass\nexcept Exception:\n    pass",
        tier=2,
    )

    engine._auto_fix(bug, report=False)
    # Check that regardless of fix result, no .tier3bak files were created anywhere in src
    tier3bak_files = list(temp_workspace["src"].rglob("*.tier3bak*"))
    assert len(tier3bak_files) == 0, f"Found unexpected .tier3bak files: {tier3bak_files}"


# =========================================================================
# 4. Tier-3 Auto-Approve Fail-Closed Gate & Rollback
# =========================================================================

def test_tier3_auto_approve_reality_test_failure_triggers_rollback(temp_workspace):
    """Verifies that if post-patch reality test fails with SyntaxError, _auto_approve_tier3 rolls back."""
    target = temp_workspace["src"] / "critical_auth.py"
    initial_content = "def authenticate():\n    return True\n"
    target.write_text(initial_content, encoding="utf-8")

    engine = AutoFixEngine(data_dir=str(temp_workspace["data"]))

    bug = BugReport(
        file=str(target),
        line=1,
        bug_type="HardcodedSecret",
        description="hardcoded secret in auth",
        suggested_fix="def authenticate():\n    return False",
        tier=3,
    )

    # Mock _auto_fix to simulate a bad patch that introduces a SyntaxError on disk
    def mock_bad_auto_fix(b, report=True, attack_mode=False):
        target.write_text("def authenticate( invalid syntax (((\n", encoding="utf-8")
        return {"action": "fixed", "tier": 3, "patched": True}

    with patch.object(engine, "_auto_fix", side_effect=mock_bad_auto_fix):
        result = engine._auto_approve_tier3(bug)

    # Result must be fail-closed (action skipped, patched False)
    assert result["action"] == "skipped"
    assert result["patched"] is False
    assert "FAIL:SyntaxError" in result["reality_test_result"]

    # Target file must be rolled back to initial_content!
    assert target.read_text(encoding="utf-8") == initial_content

    # Zero .tier3bak files in source tree
    assert len(list(temp_workspace["src"].rglob("*.tier3bak*"))) == 0


def test_tier3_auto_approve_success_commits(temp_workspace):
    """Verifies that a valid fix that passes reality test commits the transaction."""
    target = temp_workspace["src"] / "normal_mod.py"
    initial_content = "def calc():\n    return 1\n"
    target.write_text(initial_content, encoding="utf-8")

    engine = AutoFixEngine(data_dir=str(temp_workspace["data"]))

    bug = BugReport(
        file=str(target),
        line=2,
        bug_type="HardcodedSecret",
        description="hardcoded secret",
        suggested_fix="def calc():\n    return 2",
        tier=3,
    )

    def mock_good_auto_fix(b, report=True, attack_mode=False):
        target.write_text("def calc():\n    return 2\n", encoding="utf-8")
        return {"action": "fixed", "tier": 3, "patched": True}

    with patch.object(engine, "_auto_fix", side_effect=mock_good_auto_fix):
        result = engine._auto_approve_tier3(bug)

    assert result["action"] == "fixed"
    assert result["reality_test_result"] == "PASS"
    assert target.read_text(encoding="utf-8") == "def calc():\n    return 2\n"

    # Transaction committed in shadow dir
    completed_txs = list((temp_workspace["shadow"] / "completed").iterdir())
    assert len(completed_txs) >= 1


# =========================================================================
# 5. Fail-Closed Pytest Gate & End-to-End AutoFix Rollback Tests
# =========================================================================

def test_verify_fix_pytest_gate_fail_closed_on_exception(temp_workspace):
    """Verifies that an exception during pytest execution fails closed (returns False), NOT fail-open."""
    target = temp_workspace["src"] / "mod_fail.py"
    target.write_text("def test_it():\n    assert True\n", encoding="utf-8")

    engine = AutoFixEngine(data_dir=str(temp_workspace["data"]))

    bug = BugReport(
        file=str(target),
        line=1,
        bug_type="BareExceptPass",
        description="test bug",
        suggested_fix="pass",
        tier=2,
    )

    # Patch subprocess.run to simulate an execution error/crash during pytest
    with patch("subprocess.run", side_effect=RuntimeError("Pytest execution crashed unexpectedly")):
        is_ok, reason = engine._verify_fix(target, [bug])

    assert is_ok is False
    assert "fail-closed" in reason.lower()


def test_verify_fix_pytest_gate_fail_closed_on_regression(temp_workspace):
    """Verifies that a pytest failure with regression returns False and triggers rollback."""
    target = temp_workspace["src"] / "mod_regress.py"
    target.write_text("def test_sample():\n    assert False\n", encoding="utf-8")

    engine = AutoFixEngine(data_dir=str(temp_workspace["data"]))

    bug = BugReport(
        file=str(target),
        line=1,
        bug_type="BareExceptPass",
        description="test bug",
        suggested_fix="pass",
        tier=2,
    )

    # Mock subprocess.run to return exit code 1 (failure) with regression
    mock_post_proc = MagicMock()
    mock_post_proc.returncode = 1
    mock_post_proc.stdout = "1 failed in 0.05s"
    mock_post_proc.stderr = ""

    mock_base_proc = MagicMock()
    mock_base_proc.returncode = 0
    mock_base_proc.stdout = "1 passed in 0.05s"
    mock_base_proc.stderr = ""

    # Mock _find_pre_patch_backup to return a mock backup file
    backup_file = temp_workspace["src"] / "mod_regress_bak.py"
    backup_file.write_text("def test_sample():\n    assert True\n", encoding="utf-8")

    with patch("scp.autofix.engine_parts.verify_mixin._find_pre_patch_backup", return_value=backup_file):
        with patch("subprocess.run", side_effect=[mock_post_proc, mock_base_proc]):
            is_ok, reason = engine._verify_fix(target, [bug])

    assert is_ok is False
    assert "REGRESSION" in reason or "fail-closed" in reason.lower()


def test_autofix_end_to_end_rollback_on_verify_failure(temp_workspace):
    """Verifies that when _verify_fix fails in _auto_fix, the file is restored and tx rolled back."""
    target = temp_workspace["src"] / "worker_task.py"
    original_source = "def perform():\n    return 'ORIGINAL_STATE'\n"
    target.write_text(original_source, encoding="utf-8")

    engine = AutoFixEngine(data_dir=str(temp_workspace["data"]))

    suggested_fix = (
        "<<<<<<< SEARCH\n"
        "def perform():\n"
        "    return 'ORIGINAL_STATE'\n"
        "=======\n"
        "def perform():\n"
        "    return 'MUTATED_STATE'\n"
        ">>>>>>>"
    )

    bug = BugReport(
        file=str(target),
        line=1,
        bug_type="BareExceptPass",
        description="needs fix",
        suggested_fix=suggested_fix,
        tier=2,
    )

    def mock_apply(fp, fix):
        target.write_text("def perform():\n    return 'MUTATED_STATE'\n", encoding="utf-8")
        return True

    mock_rtv = MagicMock()
    mock_rtv.verified = True
    mock_rtv.passed = True

    mock_ranked = MagicMock()
    mock_ranked.confidence = 0.95
    mock_ranked.disposition = "auto_apply"

    with patch.object(engine, "_auto_fix_part2", return_value=None), \
         patch("scp.autofix.confidence_ranker.best_fix", return_value=mock_ranked), \
         patch("scp.autofix.realtime_verifier.verify_patch_realtime", return_value=mock_rtv), \
         patch("scp.core.code_evolution_agent.CodeEvolutionAgent._apply_fix", side_effect=mock_apply), \
         patch.object(engine, "_verify_fix", return_value=(False, "Regression detected in unit tests")):
        result = engine._auto_fix(bug, report=False)

    # Action must be skipped due to verify failure
    assert result["action"] == "skipped"

    # Target file must have been rolled back to original_source on disk!
    assert target.read_text(encoding="utf-8") == original_source

    # Active shadow directory must have 0 transactions (rolled back)
    active_txs = list((temp_workspace["shadow"] / "active").iterdir())
    assert len(active_txs) == 0

    # Rolled back shadow directory must have the rolled-back transaction
    rb_txs = list((temp_workspace["shadow"] / "rolled_back").iterdir())
    assert len(rb_txs) >= 1

