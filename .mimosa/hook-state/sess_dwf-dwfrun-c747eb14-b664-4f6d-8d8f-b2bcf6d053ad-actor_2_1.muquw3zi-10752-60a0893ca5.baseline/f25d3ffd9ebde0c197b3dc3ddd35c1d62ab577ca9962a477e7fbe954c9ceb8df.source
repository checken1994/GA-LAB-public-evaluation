"""Empirical Probe for UNPROVEN_BRANCH vulnerabilities: GAP-12 and GAP-13.

FA-11 Anti-Scope Creep & FA-13 Causal Matrix Compliance:
These branches represent identified peripheral architectural gaps documented in
EMERGENCY_GAP_REPORT.md that are NOT yet authorized for fixing in this session.
Per FA-13, we prove their empirical behavior via this probe script without
introducing failing pytest assertions into the permanent test suite.

Probes executed:
1. GAP-12: Direct transition to FAILED without verifier indictment from:
   - PLANNING -> FAILED
   - RUNNING -> FAILED
   - VERIFYING -> FAILED
   - Rogue worker sabotage: rogue worker forces FAILED without proof
2. GAP-13: WAITING_APPROVAL bypass:
   - PLANNING -> WAITING_APPROVAL -> READY without capability token or signature
"""

import sys
import tempfile
from pathlib import Path

from scp.task_kernel import TaskKernel


def run_probe() -> None:
    print("[PROBE GAP-12/13] Probing Unproven Branches for Peripheral GAPs...")
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "gap_probe.sqlite3"
        kernel = TaskKernel(db_path)

        # -------------------------------------------------------------
        # 1. GAP-12: transition -> FAILED without evidence
        # -------------------------------------------------------------
        print("\n--- GAP-12: Unverified FAILED Transitions ---")

        # 1.1 PLANNING -> FAILED
        kernel.create_task("task_fail_1", "owner_1", "test planning to failed")
        kernel.transition("task_fail_1", "PLANNING")
        kernel.transition("task_fail_1", "FAILED", actor="unverified_actor", reason="arbitrary failure without proof")
        t1 = kernel.get_task("task_fail_1")
        assert t1["state"] == "FAILED"
        print("[GAP-12.1] EXPLOIT CONFIRMED: PLANNING -> FAILED succeeded without crash evidence or verifier indictment.")

        # 1.2 RUNNING -> FAILED
        kernel.create_task("task_fail_2", "owner_1", "test running to failed")
        kernel.transition("task_fail_2", "PLANNING")
        kernel.transition("task_fail_2", "READY")
        kernel.transition("task_fail_2", "QUEUED")
        l2 = kernel.claim("task_fail_2", "worker_2")
        kernel.start("task_fail_2", l2.lease_id)
        kernel.transition("task_fail_2", "FAILED", lease_id=l2.lease_id, actor="worker_2", reason="unverified crash")
        t2 = kernel.get_task("task_fail_2")
        assert t2["state"] == "FAILED"
        print("[GAP-12.2] EXPLOIT CONFIRMED: RUNNING -> FAILED succeeded with only worker self-claim.")

        # 1.3 VERIFYING -> FAILED
        kernel.create_task("task_fail_3", "owner_1", "test verifying to failed")
        kernel.transition("task_fail_3", "PLANNING")
        kernel.transition("task_fail_3", "READY")
        kernel.transition("task_fail_3", "QUEUED")
        l3 = kernel.claim("task_fail_3", "worker_3")
        kernel.start("task_fail_3", l3.lease_id)
        kernel.transition("task_fail_3", "VERIFYING", lease_id=l3.lease_id)
        kernel.transition("task_fail_3", "FAILED", lease_id=l3.lease_id, actor="worker_3", reason="sabotage in verifying")
        t3 = kernel.get_task("task_fail_3")
        assert t3["state"] == "FAILED"
        print("[GAP-12.3] EXPLOIT CONFIRMED: VERIFYING -> FAILED succeeded bypassing independent verifier check.")

        # 1.4 Rogue worker sabotage
        kernel.create_task("task_fail_4", "owner_1", "test rogue worker sabotage")
        kernel.transition("task_fail_4", "PLANNING")
        kernel.transition("task_fail_4", "READY")
        kernel.transition("task_fail_4", "QUEUED")
        l4 = kernel.claim("task_fail_4", "worker_legit")
        kernel.start("task_fail_4", l4.lease_id)
        # Rogue worker with instance lease authority calls transition FAILED
        kernel._bound_leases["task_fail_4"] = l4.lease_id
        kernel.transition("task_fail_4", "FAILED", lease_id=l4.lease_id, actor="rogue_saboteur", reason="malicious cancel/fail")
        t4 = kernel.get_task("task_fail_4")
        assert t4["state"] == "FAILED"
        print("[GAP-12.4] EXPLOIT CONFIRMED: Rogue actor sabotaged task into terminal FAILED using stolen lease.")

        # -------------------------------------------------------------
        # 2. GAP-13: WAITING_APPROVAL -> READY bypass
        # -------------------------------------------------------------
        print("\n--- GAP-13: WAITING_APPROVAL Unauthenticated Bypass ---")
        kernel.create_task("task_approval_1", "owner_1", "test approval bypass")
        kernel.transition("task_approval_1", "PLANNING")
        kernel.transition("task_approval_1", "WAITING_APPROVAL", actor="planner", reason="high_risk_action_detected")
        t_app = kernel.get_task("task_approval_1")
        assert t_app["state"] == "WAITING_APPROVAL"
        print("[GAP-13.1] Task moved to WAITING_APPROVAL.")

        # Bypass approval: anyone calls transition(READY) without token or signature
        kernel.transition("task_approval_1", "READY", actor="unauthenticated_bypasser", reason="bypassing human approval gate")
        t_ready = kernel.get_task("task_approval_1")
        assert t_ready["state"] == "READY"
        print("[GAP-13.2] EXPLOIT CONFIRMED: WAITING_APPROVAL -> READY succeeded with zero tokens or cryptographic signatures.")

        kernel.close()
    print("\nALL GAP-12 AND GAP-13 UNPROVEN VULNERABILITIES EMPIRICALLY REPRODUCED!")


if __name__ == "__main__":
    run_probe()
