#!/usr/bin/env python3
"""
SCP Delta Audit Phase 4: Adversarial Probe Script
Target: scp/hands/hands_executor.py & Capability/Authority Infrastructure
Auditor: Challenger 1 (challenger_probe_1)
Date: 2026-09-07

This script empirically tests and verifies:
1. Sub-test 1: Self-Granting Authority reproduction (EV-AUTH-01 / FA-05).
   Calling HandsExecutor.execute("pc.write_file", ..., capability_token=None)
   proves that file is written to disk without the caller providing an authorized token.
2. Sub-test 2: Scope Confusion / Privilege Escalation (EV-AUTH-02 / INV-AUTH-02).
   Calling HandsExecutor.execute("pc.write_file", ..., capability_token=token_for_pc_status)
   proves that a read token is accepted for a state-mutating write action.
3. Sub-test 3: Mutation Anti-Placebo Verification (Phase 4 Anti-Placebo Mandate).
   Demonstrates that:
   - Under Current Baseline Code: Invariant assertions FAIL with AssertionError (RED).
   - Under Invariant-Preserving Guard: The exact same invariant assertions PASS (GREEN).
   - Under Legitimate Authorized Token: Normal operations succeed (GREEN, No Regression).
   This proves the probe is sensitive and NOT a placebo!
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scp.hands.hands_executor import HandsExecutor
from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority, CapabilityToken


def print_banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


def verify_zero_trust_invariant(
    result: dict[str, Any], target_path: Path, test_label: str
) -> None:
    """
    Formal Zero-Trust Invariant Verifier.
    Enforces:
    1. result["success"] must be False.
    2. target_path must NOT exist on disk.
    3. Error description must indicate capability/authorization denial.
    """
    if result.get("success") is not False:
        raise AssertionError(
            f"[{test_label}] INVARIANT VIOLATION: Action execution succeeded without valid authorized capability token! "
            f"Result: {json.dumps(result, default=str)}"
        )

    if target_path.exists():
        raise AssertionError(
            f"[{test_label}] INVARIANT VIOLATION: State mutation committed to host filesystem at: {target_path}!"
        )

    error_msg = str(result.get("error", ""))
    if not any(k in error_msg.lower() for k in ["capability", "unauthorized", "scope", "revoked"]):
        raise AssertionError(
            f"[{test_label}] INVARIANT VIOLATION: Rejection reason does not reflect capability enforcement! "
            f"Error: {error_msg}"
        )


class GuardedHandsExecutor(HandsExecutor):
    """
    Simulated Invariant-Preserving Guard (Phase 5 Evolution Path).
    Simulates the PEP boundary fix WITHOUT modifying production code in scp/.
    Enforces:
    - INV-AUTH-01 (FA-05): Strict deny-by-default if caller omits capability token.
    - INV-AUTH-02: Strict scoped subject-to-action binding.
    """

    async def execute(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        capability_level: int = 0,
        approved: bool = False,
        dry_run: bool = False,
        capability_token: CapabilityToken | None = None,
    ) -> dict[str, Any]:
        # Guard 1: Zero-Trust PEP Fail-Closed if token is missing
        if capability_token is None:
            result = {
                "success": False,
                "action": action,
                "error": "CapabilityRequiredError: Caller must provide an authorized capability token (FA-05 violation: self-granting prohibited)",
                "verification": {"passed": False},
            }
            self._audit("ACTION_BLOCKED_NO_CAPABILITY", result)
            return result

        # Guard 2: Scoped Subject-Resource Binding (No Scope Confusion)
        expected_subject = f"hands:{action}"
        if capability_token.subject != expected_subject:
            result = {
                "success": False,
                "action": action,
                "error": f"CapabilityScopeMismatchError: Token subject '{capability_token.subject}' does not match required action '{expected_subject}' (INV-AUTH-02)",
                "verification": {"passed": False},
            }
            self._audit("ACTION_BLOCKED_SCOPE_MISMATCH", result)
            return result

        # Pass through to super().execute only after Zero-Trust PEP validation succeeds
        return await super().execute(
            action=action,
            params=params,
            capability_level=capability_level,
            approved=approved,
            dry_run=dry_run,
            capability_token=capability_token,
        )


async def run_subtest_1_self_granting(test_dir: Path) -> dict[str, Any]:
    print_banner("SUB-TEST 1: Self-Granting Authority Reproduction (FA-05 Breach)")
    print("Precondition: Caller provides capability_token=None.")
    print("Action Requested: pc.write_file (Mutating, Level 3, Approved=True).")

    controller = PCController(working_dir=test_dir)
    cap_auth = CapabilityAuthority(test_dir / "cap_state_1.json")
    executor = HandsExecutor(controller=controller, capability_authority=cap_auth)

    target_file = test_dir / "unauthorized_self_granted.txt"
    payload_content = "VULNERABILITY_PROVEN: Written without caller capability token"

    result = await executor.execute(
        action="pc.write_file",
        params={"path": str(target_file), "content": payload_content},
        capability_level=3,
        approved=True,
        capability_token=None,  # Exploitation trigger: caller omits token!
    )

    print(f"Execution Result 'success': {result.get('success')}")
    print(f"Action Executed: {result.get('action')}")
    print(f"Capability Epoch Attached in Result: {result.get('capabilityEpoch')}")
    print(f"Verification Passed: {(result.get('verification') or {}).get('passed')}")
    print(f"Physical File Exists on Disk: {target_file.exists()}")

    if target_file.exists():
        disk_content = target_file.read_text(encoding="utf-8")
        print(f"Physical File Content on Disk: '{disk_content}'")

    evidence = {
        "subtest": "1_self_granting",
        "caller_provided_token": None,
        "execution_success": result.get("success"),
        "epoch_attached": result.get("capabilityEpoch"),
        "file_persisted": target_file.exists(),
        "file_content_matches": target_file.exists() and (target_file.read_text(encoding="utf-8") == payload_content),
    }

    if evidence["execution_success"] is True and evidence["file_persisted"] is True:
        print("\n>>> VERDICT SUB-TEST 1: [CONFIRMED VULNERABLE]")
        print("    HandsExecutor self-minted authority and committed physical filesystem side effects!")
    else:
        print("\n>>> VERDICT SUB-TEST 1: [NOT REPRODUCED]")

    return {"result": result, "target_file": target_file, "evidence": evidence}


async def run_subtest_2_scope_confusion(test_dir: Path) -> dict[str, Any]:
    print_banner("SUB-TEST 2: Scope Confusion / Privilege Escalation (INV-AUTH-02 Breach)")
    print("Precondition: Caller holds token issued solely for 'hands:pc.status' (Read-Only, Level 0).")
    print("Action Requested: pc.write_file (Mutating, Level 3, Approved=True).")

    controller = PCController(working_dir=test_dir)
    cap_auth = CapabilityAuthority(test_dir / "cap_state_2.json")
    executor = HandsExecutor(controller=controller, capability_authority=cap_auth)

    status_token = cap_auth.issue("hands:pc.status")
    print(f"Caller Token Subject: '{status_token.subject}'")
    print(f"Caller Token Epoch: {status_token.epoch}")
    print(f"Caller Token ID: {status_token.token_id}")

    target_file = test_dir / "unauthorized_scope_bypass.txt"
    payload_content = "VULNERABILITY_PROVEN: Written using pc.status read-only token"

    result = await executor.execute(
        action="pc.write_file",
        params={"path": str(target_file), "content": payload_content},
        capability_level=3,
        approved=True,
        capability_token=status_token,  # Exploitation trigger: read-only token submitted for write!
    )

    print(f"Execution Result 'success': {result.get('success')}")
    print(f"Action Executed: {result.get('action')}")
    print(f"Verification Passed: {(result.get('verification') or {}).get('passed')}")
    print(f"Physical File Exists on Disk: {target_file.exists()}")

    if target_file.exists():
        disk_content = target_file.read_text(encoding="utf-8")
        print(f"Physical File Content on Disk: '{disk_content}'")

    evidence = {
        "subtest": "2_scope_confusion",
        "caller_token_subject": status_token.subject,
        "execution_success": result.get("success"),
        "file_persisted": target_file.exists(),
        "file_content_matches": target_file.exists() and (target_file.read_text(encoding="utf-8") == payload_content),
    }

    if evidence["execution_success"] is True and evidence["file_persisted"] is True:
        print("\n>>> VERDICT SUB-TEST 2: [CONFIRMED VULNERABLE]")
        print("    HandsExecutor accepted a read-only token for a write action (Scope-blind validation)!")
    else:
        print("\n>>> VERDICT SUB-TEST 2: [NOT REPRODUCED]")

    return {"result": result, "target_file": target_file, "evidence": evidence}


async def run_subtest_3_anti_placebo_mutation(test_dir: Path) -> dict[str, Any]:
    print_banner("SUB-TEST 3: Mutation Anti-Placebo Verification")
    print("Requirement: Prove probe sensitivity by demonstrating RED on Baseline, GREEN on Guarded.")

    # --------------------------------------------------------------------------
    # Step 3A: Baseline Mutation Check (Expect RED / AssertionError)
    # --------------------------------------------------------------------------
    print("\n--- [Step 3A] Evaluating Invariant Assertions against CURRENT BASELINE CODE ---")

    controller_base = PCController(working_dir=test_dir)
    cap_auth_base = CapabilityAuthority(test_dir / "cap_state_base.json")
    executor_base = HandsExecutor(controller=controller_base, capability_authority=cap_auth_base)

    target_base_1 = test_dir / "baseline_no_token.txt"
    res_base_1 = await executor_base.execute(
        "pc.write_file",
        {"path": str(target_base_1), "content": "base1"},
        capability_level=3,
        approved=True,
        capability_token=None,
    )

    baseline_subtest_1_threw = False
    try:
        verify_zero_trust_invariant(res_base_1, target_base_1, "Baseline No-Token")
        print("[FAIL - PLACEBO DETECTED]: Baseline unexpectedly PASSED invariant assertion!")
    except AssertionError as exc:
        baseline_subtest_1_threw = True
        print(f"[EXPECTED RED]: Baseline failed invariant check as predicted: {exc}")

    status_token_base = cap_auth_base.issue("hands:pc.status")
    target_base_2 = test_dir / "baseline_scope.txt"
    res_base_2 = await executor_base.execute(
        "pc.write_file",
        {"path": str(target_base_2), "content": "base2"},
        capability_level=3,
        approved=True,
        capability_token=status_token_base,
    )

    baseline_subtest_2_threw = False
    try:
        verify_zero_trust_invariant(res_base_2, target_base_2, "Baseline Scope-Confusion")
        print("[FAIL - PLACEBO DETECTED]: Baseline unexpectedly PASSED invariant assertion!")
    except AssertionError as exc:
        baseline_subtest_2_threw = True
        print(f"[EXPECTED RED]: Baseline failed invariant check as predicted: {exc}")

    baseline_is_red = baseline_subtest_1_threw and baseline_subtest_2_threw
    print(f"\nBaseline Vulnerability Status: {'DEMONSTRABLY RED (Vulnerable)' if baseline_is_red else 'INVALID'}")

    # --------------------------------------------------------------------------
    # Step 3B: Invariant-Preserving Guard Simulation (Expect GREEN / PASS)
    # --------------------------------------------------------------------------
    print("\n--- [Step 3B] Evaluating Invariant Assertions against GUARDED IMPLEMENTATION ---")

    controller_guard = PCController(working_dir=test_dir)
    cap_auth_guard = CapabilityAuthority(test_dir / "cap_state_guard.json")
    executor_guard = GuardedHandsExecutor(controller=controller_guard, capability_authority=cap_auth_guard)

    # 1. Guarded with None token
    target_guard_1 = test_dir / "guarded_no_token.txt"
    res_guard_1 = await executor_guard.execute(
        "pc.write_file",
        {"path": str(target_guard_1), "content": "guard1"},
        capability_level=3,
        approved=True,
        capability_token=None,
    )
    print(f"Guarded (No-Token) Result: success={res_guard_1.get('success')}, error='{res_guard_1.get('error')}'")
    guarded_subtest_1_passed = False
    try:
        verify_zero_trust_invariant(res_guard_1, target_guard_1, "Guarded No-Token")
        guarded_subtest_1_passed = True
        print("[EXPECTED GREEN]: Guarded No-Token successfully enforced Zero-Trust PEP (Blocked fail-closed, no disk mutation)!")
    except AssertionError as exc:
        print(f"[UNEXPECTED FAILURE]: Guarded No-Token check raised: {exc}")

    # 2. Guarded with mismatched scope token
    status_token_guard = cap_auth_guard.issue("hands:pc.status")
    target_guard_2 = test_dir / "guarded_scope.txt"
    res_guard_2 = await executor_guard.execute(
        "pc.write_file",
        {"path": str(target_guard_2), "content": "guard2"},
        capability_level=3,
        approved=True,
        capability_token=status_token_guard,
    )
    print(f"Guarded (Scope-Mismatch) Result: success={res_guard_2.get('success')}, error='{res_guard_2.get('error')}'")
    guarded_subtest_2_passed = False
    try:
        verify_zero_trust_invariant(res_guard_2, target_guard_2, "Guarded Scope-Mismatch")
        guarded_subtest_2_passed = True
        print("[EXPECTED GREEN]: Guarded Scope-Mismatch successfully enforced INV-AUTH-02 (Blocked fail-closed, no disk mutation)!")
    except AssertionError as exc:
        print(f"[UNEXPECTED FAILURE]: Guarded Scope-Mismatch check raised: {exc}")

    # 3. Guarded with genuine authorized write token (Sanity check: Legitimate operations still work)
    write_token_guard = cap_auth_guard.issue("hands:pc.write_file")
    target_guard_valid = test_dir / "guarded_valid_auth.txt"
    res_guard_valid = await executor_guard.execute(
        "pc.write_file",
        {"path": str(target_guard_valid), "content": "legitimate_authorized_write"},
        capability_level=3,
        approved=True,
        capability_token=write_token_guard,
    )
    valid_authorized_passed = (
        res_guard_valid.get("success") is True
        and target_guard_valid.exists()
        and target_guard_valid.read_text(encoding="utf-8") == "legitimate_authorized_write"
    )
    print(f"Guarded (Valid Token) Result: success={res_guard_valid.get('success')}, file_exists={target_guard_valid.exists()}")
    if valid_authorized_passed:
        print("[EXPECTED GREEN]: Legitimate authorized operation executed successfully without regression!")
    else:
        print("[UNEXPECTED FAILURE]: Legitimate authorized operation failed!")

    guarded_is_green = guarded_subtest_1_passed and guarded_subtest_2_passed and valid_authorized_passed

    anti_placebo_proven = baseline_is_red and guarded_is_green

    print_banner("ANTI-PLACEBO SENSITIVITY SUMMARY")
    print(f"Baseline Mutation Assertion Fails (RED):       {baseline_is_red}  [Proven Vulnerable]")
    print(f"Guarded Invariant Assertion Passes (GREEN):     {guarded_is_green}  [Proven Correct]")
    print(f"Overall Anti-Placebo Sensitivity Proven:        {anti_placebo_proven}  [NON-PLACEBO CONFIRMED]")

    return {
        "baseline_is_red": baseline_is_red,
        "guarded_is_green": guarded_is_green,
        "anti_placebo_proven": anti_placebo_proven,
    }


async def main() -> int:
    start_time = time.time()
    print_banner("SCP PHASE 4 EMPIRICAL ADVERSARIAL PROBE HARNESS")
    print(f"Execution Target: {PROJECT_ROOT / 'scp' / 'hands' / 'hands_executor.py'}")
    print(f"Python Runtime:   {sys.version}")
    print(f"Timestamp:        {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")

    tmp_root = Path(tempfile.mkdtemp(prefix="scp_probe_pep_"))
    try:
        print(f"Isolated Sandbox Workspace: {tmp_root}")

        # Run Sub-Test 1
        t1 = await run_subtest_1_self_granting(tmp_root)

        # Run Sub-Test 2
        t2 = await run_subtest_2_scope_confusion(tmp_root)

        # Run Sub-Test 3
        t3 = await run_subtest_3_anti_placebo_mutation(tmp_root)

        print_banner("OVERALL PROBE HARNESS VERDICT")
        all_passed = (
            t1["evidence"]["execution_success"] is True
            and t1["evidence"]["file_persisted"] is True
            and t2["evidence"]["execution_success"] is True
            and t2["evidence"]["file_persisted"] is True
            and t3["anti_placebo_proven"] is True
        )

        if all_passed:
            print("[SUCCESS]: ALL 3 SUB-TESTS SATISFIED EMPIRICALLY.")
            print("1. Sub-test 1: Self-Granting reproduced live (FA-05 breach confirmed).")
            print("2. Sub-test 2: Scope Confusion reproduced live (INV-AUTH-02 breach confirmed).")
            print("3. Sub-test 3: Mutation Anti-Placebo proven (Red on Baseline -> Green on Guarded).")
            print(f"Execution Duration: {time.time() - start_time:.2f}s")
            return 0
        else:
            print("[FAILURE]: One or more sub-tests failed to produce expected empirical results.")
            return 1

    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
        print(f"Cleaned up sandbox workspace: {tmp_root}")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
