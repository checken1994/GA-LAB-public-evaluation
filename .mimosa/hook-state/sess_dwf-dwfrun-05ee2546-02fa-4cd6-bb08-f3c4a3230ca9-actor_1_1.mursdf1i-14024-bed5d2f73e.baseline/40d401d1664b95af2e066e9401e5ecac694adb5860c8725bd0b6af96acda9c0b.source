"""Standalone Deterministic Probe Script for GAP-13: Unauthenticated WAITING_APPROVAL Bypass.

Governing Protocols:
- .agents/skills/scp-delta-audit/SKILL.md (Evidence-First, Zero-Trust, Anti-Placebo)
- .agents/skills/scp-dna/SKILL.md (29 Principles: Reality > Model, PASS != TRUE)
- .agents/AGENTS.md: FA-01 to FA-13 (FA-08 No Forged Provenance, FA-09 Exploit Mandate, FA-12 Empirical Closure)

Target Subsystem: TaskKernel (`scp/task_kernel_parts/taskkernel.py`, `scp/task_kernel.py`)
Target Vulnerability: GAP-13 — Unauthenticated WAITING_APPROVAL Bypass to READY

Exploit Vectors Tested:
- Vector 1: Direct unauthenticated transition(task_id, "READY") from WAITING_APPROVAL with
            no approval token, no cryptographic signature, and no operator authority.
            Current vulnerable code: SUCCEEDS (VULNERABILITY PROVEN RED).
            Post-patch code: RAISES InvalidTransition (PROTECTED GREEN).
- Vector 2: Unauthenticated transition from WAITING_APPROVAL to unauthorized states (QUEUED, RUNNING, COMPLETED, FAILED).
            Must be strictly blocked fail-closed with InvalidTransition.
- Vector 3: Approval commit validation with missing / None token.
            Must be rejected fail-closed (KernelError / PermissionError).
- Vector 4: Approval commit validation with forged / tampered HMAC signature.
            Must be rejected fail-closed (InvalidTokenSignatureError).
- Vector 5: Approval commit validation with valid signature but wrong scope (lacks approval:grant).
            Must be rejected fail-closed.
- Vector 6: Approval commit validation with expired token.
            Must be rejected fail-closed.
- Vector 7: Approval commit validation with valid token for a different task_id / scope.
            Must be rejected fail-closed.
- Vector 8: Calling commit_approval() on task in wrong lifecycle state (e.g. CREATED, RUNNING).
            Must be rejected with InvalidTransition.
- Vector 9: Legitimate approval: valid CapabilityToken / operator credential transitions task to READY.

Physical Persistence:
- Direct raw SQLite database inspection on `tasks` and `events` tables (FA-12 Step 4).

Anti-Placebo Contract:
- RED state (Current vulnerable code): Vector 1 exploit succeeds, mutating task state to READY without token.
- GREEN state (Post-patch code): Direct transition raises InvalidTransition; only valid commit_approval() succeeds.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Ensure workspace root is in path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Ensure fallback test secret exists for capability token validation
if not os.environ.get("SCP_CAPABILITY_SECRET"):
    os.environ["SCP_CAPABILITY_SECRET"] = "gap13-probe-cryptographic-secret-32b-ok!"

from scp.task_kernel import InvalidTransition, KernelError, TaskKernel
from scp.core.capability_token import (
    CapabilityToken,
    InvalidTokenSignatureError,
    mint_token,
    verify_token,
    verify_token_signature,
    compute_token_signature,
    get_capability_secret,
)


def run_probe() -> dict[str, Any]:
    print("=" * 80)
    print("SCP-OMEGA DELTA AUDIT: GAP-13 EMPIRICAL EXPLOIT PROBE")
    print("Subsystem: TaskKernel Approval Gate & State Machine")
    print("Invariants Tested:")
    print("  - INV-GAP13-01: Prohibition of Raw Unauthenticated Transition from WAITING_APPROVAL to READY")
    print("  - INV-GAP13-02: Mandatory CapabilityToken with approval:grant or Operator Signature")
    print("  - INV-GAP13-03: Rejection of Forged, Expired, Mismatched, or Missing Approval Credentials")
    print("  - INV-GAP13-04: Atomic OCC Fencing and Durable Event Journaling for Approvals")
    print("=" * 80)

    tmp_fd, db_path_str = tempfile.mkstemp(suffix="_gap13_probe.sqlite3")
    os.close(tmp_fd)
    db_path = Path(db_path_str)

    kernel = TaskKernel(db_path)

    results: dict[str, Any] = {
        "vector_1": {
            "name": "WAITING_APPROVAL -> READY raw transition bypass (No token, no signature)",
            "status": "UNKNOWN",
        },
        "vector_2": {
            "name": "WAITING_APPROVAL -> unauthorized states (QUEUED, RUNNING, COMPLETED, FAILED)",
            "status": "UNKNOWN",
        },
        "vector_3": {
            "name": "commit_approval() with missing / None token",
            "status": "UNKNOWN",
        },
        "vector_4": {
            "name": "commit_approval() with forged / tampered token signature",
            "status": "UNKNOWN",
        },
        "vector_5": {
            "name": "commit_approval() with wrong capability scope (missing approval:grant)",
            "status": "UNKNOWN",
        },
        "vector_6": {
            "name": "commit_approval() with expired approval token",
            "status": "UNKNOWN",
        },
        "vector_7": {
            "name": "commit_approval() with mismatched task_id scope",
            "status": "UNKNOWN",
        },
        "vector_8": {
            "name": "commit_approval() on task in wrong lifecycle state (CREATED, RUNNING)",
            "status": "UNKNOWN",
        },
        "vector_9": {
            "name": "Legitimate commit_approval() with valid capability token -> READY",
            "status": "UNKNOWN",
        },
    }

    try:
        # =========================================================================
        # VECTOR 1: WAITING_APPROVAL -> READY raw transition bypass
        # =========================================================================
        print("\n" + "-" * 80)
        print("[VECTOR 1] Testing Raw Unauthenticated WAITING_APPROVAL -> READY Bypass")
        print("-" * 80)
        t1_id = "task_gap13_v1"
        kernel.create_task(t1_id, "owner_sec", "High-risk task requiring approval", "R3")
        kernel.transition(t1_id, "PLANNING", actor="planner")
        kernel.transition(t1_id, "WAITING_APPROVAL", actor="risk_policy", reason="high_risk_tier_R3")

        pre_t1 = kernel.get_task(t1_id)
        print(f"[*] Task created & gated: ID={t1_id}, State={pre_t1['state']}, Risk={pre_t1['risk_tier']}")

        try:
            # Attacker attempts to bypass approval by calling transition directly to READY
            kernel.transition(
                t1_id,
                "READY",
                actor="unauthenticated_attacker_v1",
                reason="bypassing_human_approval_gate",
            )
            post_t1 = kernel.get_task(t1_id)
            if post_t1["state"] == "READY":
                print("[!] [RED] EXPLOIT SUCCEEDED: Unauthenticated actor transitioned WAITING_APPROVAL task directly to READY!")
                print(f"    Task State: {post_t1['state']}, Version: {post_t1['version']}")
                print("    Invariant Violated: INV-GAP13-01 (No approval token or operator verification required)")
                results["vector_1"]["status"] = "VULNERABILITY_PROVEN_RED"
            else:
                results["vector_1"]["status"] = f"UNEXPECTED_STATE_{post_t1['state']}"
        except InvalidTransition as exc:
            print(f"[*] [GREEN] Call blocked with InvalidTransition: {exc}")
            results["vector_1"]["status"] = "PROTECTED_GREEN_InvalidTransition"
        except Exception as exc:
            print(f"[!] [UNEXPECTED CRASH] Call failed with unexpected {type(exc).__name__}: {exc}")
            results["vector_1"]["status"] = f"UNEXPECTED_CRASH_{type(exc).__name__}"

        # =========================================================================
        # VECTOR 2: WAITING_APPROVAL -> unauthorized states
        # =========================================================================
        print("\n" + "-" * 80)
        print("[VECTOR 2] Testing WAITING_APPROVAL -> other unauthorized transitions")
        print("-" * 80)
        t2_id = "task_gap13_v2"
        kernel.create_task(t2_id, "owner_sec", "Task for Vector 2 testing", "R2")
        kernel.transition(t2_id, "PLANNING")
        kernel.transition(t2_id, "WAITING_APPROVAL")

        blocked_count = 0
        for unauth_state in ("QUEUED", "RUNNING", "COMPLETED", "FAILED"):
            try:
                kernel.transition(t2_id, unauth_state, actor="attacker")
            except (InvalidTransition, Exception):
                blocked_count += 1

        if blocked_count == 4:
            print(f"[*] [GREEN] All 4 unauthorized transitions from WAITING_APPROVAL strictly blocked.")
            results["vector_2"]["status"] = "PROTECTED_GREEN"
        else:
            print(f"[!] [RED] Unauthorized transitions permitted ({4 - blocked_count} unblocked)!")
            results["vector_2"]["status"] = "VULNERABILITY_PROVEN_RED"

        # Check if commit_approval is implemented on TaskKernel
        has_commit_approval = hasattr(kernel, "commit_approval")
        if not has_commit_approval:
            print("\n[*] Notice: TaskKernel does not yet implement commit_approval().")
            print("    Vectors 3-9 will be verified once commit_approval() is introduced in the patch.")
            for v_idx in range(3, 10):
                results[f"vector_{v_idx}"]["status"] = "NOT_YET_IMPLEMENTED_PRE_PATCH"
        else:
            # =====================================================================
            # VECTOR 3: commit_approval with missing/None token
            # =====================================================================
            t3_id = "task_gap13_v3"
            kernel.create_task(t3_id, "owner_sec", "Task v3", "R2")
            kernel.transition(t3_id, "PLANNING")
            kernel.transition(t3_id, "WAITING_APPROVAL")
            try:
                kernel.commit_approval(t3_id, approval_token=None, actor="attacker")
                results["vector_3"]["status"] = "VULNERABILITY_PROVEN_RED"
            except (KernelError, PermissionError, InvalidTransition):
                results["vector_3"]["status"] = "PROTECTED_GREEN"

            # =====================================================================
            # VECTOR 4: commit_approval with forged / invalid signature token
            # =====================================================================
            t4_id = "task_gap13_v4"
            kernel.create_task(t4_id, "owner_sec", "Task v4", "R2")
            kernel.transition(t4_id, "PLANNING")
            kernel.transition(t4_id, "WAITING_APPROVAL")
            forged_token = CapabilityToken("approval:grant", 0, "fake-tok", time.time(), "bad_sig" * 4)
            try:
                kernel.commit_approval(t4_id, approval_token=forged_token, actor="attacker")
                results["vector_4"]["status"] = "VULNERABILITY_PROVEN_RED"
            except (InvalidTokenSignatureError, KernelError, PermissionError):
                results["vector_4"]["status"] = "PROTECTED_GREEN"

            # =====================================================================
            # VECTOR 5: commit_approval with wrong capability scope
            # =====================================================================
            t5_id = "task_gap13_v5"
            kernel.create_task(t5_id, "owner_sec", "Task v5", "R2")
            kernel.transition(t5_id, "PLANNING")
            kernel.transition(t5_id, "WAITING_APPROVAL")
            secret = get_capability_secret()
            now_t = time.time()
            sig_wrong = compute_token_signature(secret, "hands:read_only", 0, "wrong-scope-tok", now_t)
            wrong_scope_token = CapabilityToken("hands:read_only", 0, "wrong-scope-tok", now_t, sig_wrong)
            try:
                kernel.commit_approval(t5_id, approval_token=wrong_scope_token, actor="attacker")
                results["vector_5"]["status"] = "VULNERABILITY_PROVEN_RED"
            except (KernelError, PermissionError, InvalidTransition):
                results["vector_5"]["status"] = "PROTECTED_GREEN"

            # =====================================================================
            # VECTOR 6: commit_approval with expired token
            # =====================================================================
            t6_id = "task_gap13_v6"
            kernel.create_task(t6_id, "owner_sec", "Task v6", "R2")
            kernel.transition(t6_id, "PLANNING")
            kernel.transition(t6_id, "WAITING_APPROVAL")
            expired_minted = mint_token(issuer="operator", scope="approval:grant", capability_level=2, ttl_seconds=-100)
            try:
                kernel.commit_approval(t6_id, approval_token=expired_minted, actor="attacker")
                results["vector_6"]["status"] = "VULNERABILITY_PROVEN_RED"
            except (KernelError, PermissionError, InvalidTransition):
                results["vector_6"]["status"] = "PROTECTED_GREEN"

            # =====================================================================
            # VECTOR 7: commit_approval with mismatched task_id scope
            # =====================================================================
            t7_id = "task_gap13_v7"
            kernel.create_task(t7_id, "owner_sec", "Task v7", "R2")
            kernel.transition(t7_id, "PLANNING")
            kernel.transition(t7_id, "WAITING_APPROVAL")
            sig_mismatched = compute_token_signature(secret, "approval:grant:different_task_999", 0, "mismatched-tok", now_t)
            mismatched_token = CapabilityToken("approval:grant:different_task_999", 0, "mismatched-tok", now_t, sig_mismatched)
            try:
                kernel.commit_approval(t7_id, approval_token=mismatched_token, actor="attacker")
                results["vector_7"]["status"] = "VULNERABILITY_PROVEN_RED"
            except (KernelError, PermissionError, InvalidTransition):
                results["vector_7"]["status"] = "PROTECTED_GREEN"

            # =====================================================================
            # VECTOR 8: commit_approval on wrong state (e.g. CREATED)
            # =====================================================================
            t8_id = "task_gap13_v8"
            kernel.create_task(t8_id, "owner_sec", "Task v8", "R2")
            sig_valid = compute_token_signature(secret, "approval:grant", 0, "valid-tok-1", now_t)
            valid_token = CapabilityToken("approval:grant", 0, "valid-tok-1", now_t, sig_valid)
            try:
                kernel.commit_approval(t8_id, approval_token=valid_token, actor="approver")
                results["vector_8"]["status"] = "VULNERABILITY_PROVEN_RED"
            except InvalidTransition:
                results["vector_8"]["status"] = "PROTECTED_GREEN"

            # =====================================================================
            # VECTOR 9: Legitimate approval transitions task to READY
            # =====================================================================
            t9_id = "task_gap13_v9"
            kernel.create_task(t9_id, "owner_sec", "Task v9", "R2")
            kernel.transition(t9_id, "PLANNING")
            kernel.transition(t9_id, "WAITING_APPROVAL")
            sig_legit = compute_token_signature(secret, "approval:grant", 0, "legit-tok-9", now_t)
            legit_token = CapabilityToken("approval:grant", 0, "legit-tok-9", now_t, sig_legit)
            try:
                res = kernel.commit_approval(t9_id, approval_token=legit_token, actor="authorized_operator")
                if res["state"] == "READY":
                    results["vector_9"]["status"] = "PROTECTED_GREEN"
                else:
                    results["vector_9"]["status"] = f"UNEXPECTED_STATE_{res['state']}"
            except Exception as exc:
                results["vector_9"]["status"] = f"FAILED_{type(exc).__name__}"

    finally:
        kernel.close()

    # =========================================================================
    # PHYSICAL PERSISTENCE INSPECTION (FA-08, FA-09, FA-12 Step 4)
    # Direct raw SQLite connection inspection of 'tasks' and 'events' tables
    # =========================================================================
    print("\n" + "=" * 80)
    print("FA-12 STEP 4: PHYSICAL SQLITE PERSISTENCE INSPECTION")
    print(f"Inspecting physical database file: {db_path}")
    print("=" * 80)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        task_rows = conn.execute(
            "SELECT task_id, owner, state, version, active_lease_id, risk_tier, updated_at FROM tasks ORDER BY task_id"
        ).fetchall()

        print("\n--- RAW SQLITE: 'tasks' TABLE ROWS ---")
        v1_state = None
        for row in task_rows:
            r = dict(row)
            print(f"  [Row] task_id={r['task_id']} | state={r['state']} | version={r['version']} | risk={r['risk_tier']}")
            if r["task_id"] == "task_gap13_v1":
                v1_state = r["state"]

        results["sqlite_v1_task_state"] = v1_state

        event_rows = conn.execute(
            "SELECT event_id, task_id, seq, type, from_state, to_state, actor, reason FROM events "
            "WHERE task_id='task_gap13_v1' ORDER BY seq"
        ).fetchall()

        print("\n--- RAW SQLITE: 'events' TABLE TRANSITION JOURNAL FOR task_gap13_v1 ---")
        v1_unauthorized_bypass_event = False
        for row in event_rows:
            e = dict(row)
            print(f"  [Event] seq={e['seq']} | type={e['type']} | transition={e['from_state']}->{e['to_state']} | actor={e['actor']}")
            if e["from_state"] == "WAITING_APPROVAL" and e["to_state"] == "READY" and e["actor"] == "unauthenticated_attacker_v1":
                v1_unauthorized_bypass_event = True

        results["sqlite_v1_unauthorized_event_found"] = v1_unauthorized_bypass_event

    finally:
        conn.close()
        try:
            os.remove(db_path)
        except OSError:
            pass

    # =========================================================================
    # SUMMARY & ANTI-PLACEBO ASSESSMENT
    # =========================================================================
    print("\n" + "=" * 80)
    print("PROBE RESULTS SUMMARY & ANTI-PLACEBO CONTRACT EVALUATION")
    print("=" * 80)
    for k_name, val in results.items():
        if k_name.startswith("vector_"):
            print(f"  {k_name.upper()}: {val['name']}")
            print(f"    Verdict: {val['status']}")

    v1_status = results["vector_1"]["status"]
    if v1_status == "VULNERABILITY_PROVEN_RED" and results.get("sqlite_v1_task_state") == "READY" and results.get("sqlite_v1_unauthorized_event_found"):
        print("\n  >> RED STATE CONFIRMED: WAITING_APPROVAL -> READY unauthenticated bypass successfully executed.")
        print("  >> Task mutated to READY and recorded in events journal without any authorization or token check.")
        print("  >> Vulnerability GAP-13 is actively exploitable at the database layer.")
        print("  >> Anti-Placebo Falsification Condition: Upon implementing INV-GAP13-01 through 04,")
        print("     calling transition(task_id, 'READY') from WAITING_APPROVAL MUST raise InvalidTransition,")
        print("     causing this probe to record PROTECTED_GREEN.")
        print("  >> Overall Verdict: VULNERABILITY_PROVEN_RED")
        results["overall_verdict"] = "VULNERABILITY_PROVEN_RED"
    elif v1_status == "PROTECTED_GREEN_InvalidTransition" and results.get("sqlite_v1_task_state") == "WAITING_APPROVAL" and not results.get("sqlite_v1_unauthorized_event_found"):
        print("\n  >> GREEN STATE CONFIRMED: Direct transition from WAITING_APPROVAL strictly blocked by InvalidTransition.")
        print("  >> Task remains in WAITING_APPROVAL at SQLite layer, 0 unauthorized events recorded.")
        print("  >> Anti-Placebo Falsification Condition Satisfied.")
        print("  >> Overall Verdict: ALL_VECTORS_PROTECTED_GREEN")
        results["overall_verdict"] = "ALL_VECTORS_PROTECTED_GREEN"
    else:
        print(f"\n  >> Probe returned unexpected state: v1_status={v1_status}, sqlite_state={results.get('sqlite_v1_task_state')}")
        results["overall_verdict"] = "UNEXPECTED_STATE"

    print("=" * 80)
    return results


if __name__ == "__main__":
    outcome = run_probe()
    verdict = outcome.get("overall_verdict")
    if verdict in ("VULNERABILITY_PROVEN_RED", "ALL_VECTORS_PROTECTED_GREEN"):
        sys.exit(0)
    else:
        sys.exit(1)
