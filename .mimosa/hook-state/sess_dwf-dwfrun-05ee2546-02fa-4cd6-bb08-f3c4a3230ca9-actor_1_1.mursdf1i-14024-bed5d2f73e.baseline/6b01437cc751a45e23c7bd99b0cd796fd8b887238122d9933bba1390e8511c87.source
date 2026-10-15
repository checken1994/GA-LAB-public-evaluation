"""Standalone Deterministic Probe Script for GAP-12 Delta Audit.

Governing Protocols:
- .agents/skills/scp-delta-audit/SKILL.md (Evidence-First, Zero-Trust, Anti-Placebo)
- .agents/skills/scp-dna/SKILL.md (29 Principles: Reality > Model, PASS != TRUE)
- .agents/AGENTS.md: FA-01 to FA-13 (FA-08 No Forged Provenance, FA-09 Exploit Mandate, FA-12 Empirical Closure)

Target Subsystem: TaskKernel (`scp/task_kernel_parts/taskkernel.py`, `scp/task_kernel.py`)
Target Vulnerability: GAP-12 — Unverified Terminal FAILED Transition & Rogue Worker Sabotage

Exploit Vectors Tested:
- Vector 1: Unauthenticated caller invokes transition(task_id, "FAILED") from PLANNING with
            no lease, no authority, and no evidence -> succeeds on current code (VULNERABILITY PROVEN).
- Vector 2: Worker in RUNNING invokes transition(task_id, "FAILED") with zero crash evidence /
            indictment -> succeeds on current code (VULNERABILITY PROVEN).
- Vector 3: Caller in VERIFYING invokes transition(task_id, "FAILED") bypassing independent
            verifier check -> succeeds on current code (VULNERABILITY PROVEN).
- Vector 4: Stolen lease holder / rogue actor forces task into terminal FAILED, permanently killing
            task and bypassing recovery state machine -> succeeds on current code (VULNERABILITY PROVEN).

Physical Persistence:
- Direct raw SQLite database inspection on `tasks` and `events` tables (FA-12 Step 4).

Anti-Placebo Contract:
- RED state (Current vulnerable code): All 4 exploit transitions succeed directly.
- GREEN state (Post-evolution code): Direct transition to FAILED raises `InvalidTransition`,
  mandating `commit_failed()` with verifiable evidence and valid authority.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

# Ensure workspace root is in path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scp.task_kernel import InvalidTransition, TaskKernel


def run_probe() -> dict[str, Any]:
    print("=" * 80)
    print("SCP-OMEGA DELTA AUDIT: GAP-12 EMPIRICAL PROBE")
    print("Subsystem: TaskKernel State Machine")
    print("Invariants Tested:")
    print("  - INV-GAP12-01: Prohibition of Raw Unverified Transition to Terminal FAILED")
    print("  - INV-GAP12-02: Mandatory Indictment & Evidence for Failure Commitment")
    print("  - INV-GAP12-03: Preservation of Retry Budget and Recovery Routing")
    print("  - INV-GAP12-04: System Authority Separation for Pre-execution Indictment")
    print("=" * 80)

    # Use a temporary SQLite database file for physical persistence verification
    tmp_fd, db_path_str = tempfile.mkstemp(suffix="_gap12_probe.sqlite3")
    os.close(tmp_fd)
    db_path = Path(db_path_str)

    kernel = TaskKernel(db_path)

    results: dict[str, Any] = {
        "vector_1": {"name": "PLANNING -> FAILED (Unauthenticated, No Lease, No Evidence)", "status": "UNKNOWN"},
        "vector_2": {"name": "RUNNING -> FAILED (No Crash Evidence / Zero Indictment)", "status": "UNKNOWN"},
        "vector_3": {"name": "VERIFYING -> FAILED (Verifier Check Bypassed)", "status": "UNKNOWN"},
        "vector_4": {"name": "Stolen Lease Sabotage (Recovery Machine Bypassed)", "status": "UNKNOWN"},
    }

    try:
        # =========================================================================
        # VECTOR 1: PLANNING -> FAILED (Unauthenticated, No Lease, No Evidence)
        # =========================================================================
        print("\n" + "-" * 80)
        print("[VECTOR 1] Testing Unauthenticated Pre-Execution Sabotage (PLANNING -> FAILED)")
        print("-" * 80)
        t1_id = "task_gap12_v1"
        kernel.create_task(t1_id, "owner_alpha", "Task for Vector 1: unauthenticated fail in planning")
        kernel.transition(t1_id, "PLANNING", actor="planner_agent", reason="initial_planning")
        
        pre_t1 = kernel.get_task(t1_id)
        print(f"[*] Task created: ID={t1_id}, State={pre_t1['state']}, ActiveLease={pre_t1['active_lease_id']}")

        try:
            # Attacker calls transition to FAILED with no lease, no system authority, no evidence
            kernel.transition(
                t1_id,
                "FAILED",
                actor="unauthenticated_attacker_v1",
                reason="arbitrary_external_cancellation_without_proof",
            )
            post_t1 = kernel.get_task(t1_id)
            if post_t1["state"] == "FAILED":
                print("[!] [RED] EXPLOIT SUCCEEDED: Unauthenticated actor transitioned task directly to FAILED!")
                print(f"    Task State: {post_t1['state']}, Version: {post_t1['version']}")
                print("    Invariant Violated: INV-GAP12-01 & INV-GAP12-04 (No authority or evidence required)")
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
        # VECTOR 2: RUNNING -> FAILED (Zero Crash Evidence / Bypassing Retry Budget)
        # =========================================================================
        print("\n" + "-" * 80)
        print("[VECTOR 2] Testing Worker Execution Failure with Zero Crash Evidence (RUNNING -> FAILED)")
        print("-" * 80)
        t2_id = "task_gap12_v2"
        kernel.create_task(t2_id, "owner_alpha", "Task for Vector 2: worker fail without evidence", max_attempts=3)
        kernel.transition(t2_id, "PLANNING", actor="planner")
        kernel.transition(t2_id, "READY", actor="planner")
        kernel.transition(t2_id, "QUEUED", actor="scheduler")
        l2 = kernel.claim(t2_id, "worker_beta")
        kernel.start(t2_id, l2.lease_id)

        pre_t2 = kernel.get_task(t2_id)
        print(f"[*] Task running: ID={t2_id}, State={pre_t2['state']}, Lease={pre_t2['active_lease_id']}, MaxAttempts={pre_t2['max_attempts']}")

        try:
            # Worker self-claims failure without crash dump, trace, or verifier indictment
            kernel.transition(
                t2_id,
                "FAILED",
                lease_id=l2.lease_id,
                actor="worker_beta",
                reason="unverified_worker_crash_claim",
            )
            post_t2 = kernel.get_task(t2_id)
            if post_t2["state"] == "FAILED":
                print("[!] [RED] EXPLOIT SUCCEEDED: Worker transitioned task directly to terminal FAILED on attempt 1!")
                print(f"    Task State: {post_t2['state']}, Version: {post_t2['version']}, ActiveLease: {post_t2['active_lease_id']}")
                print("    Invariant Violated: INV-GAP12-01, INV-GAP12-02 & INV-GAP12-03 (No failure evidence, retry budget discarded)")
                results["vector_2"]["status"] = "VULNERABILITY_PROVEN_RED"
            else:
                results["vector_2"]["status"] = f"UNEXPECTED_STATE_{post_t2['state']}"
        except InvalidTransition as exc:
            print(f"[*] [GREEN] Call blocked with InvalidTransition: {exc}")
            results["vector_2"]["status"] = "PROTECTED_GREEN_InvalidTransition"
        except Exception as exc:
            print(f"[!] [UNEXPECTED CRASH] Call failed with unexpected {type(exc).__name__}: {exc}")
            results["vector_2"]["status"] = f"UNEXPECTED_CRASH_{type(exc).__name__}"

        # =========================================================================
        # VECTOR 3: VERIFYING -> FAILED (Independent Verifier Check Bypassed)
        # =========================================================================
        print("\n" + "-" * 80)
        print("[VECTOR 3] Testing Verification Sabotage (VERIFYING -> FAILED without Verifier Check)")
        print("-" * 80)
        t3_id = "task_gap12_v3"
        kernel.create_task(t3_id, "owner_alpha", "Task for Vector 3: verifying to failed bypass")
        kernel.transition(t3_id, "PLANNING", actor="planner")
        kernel.transition(t3_id, "READY", actor="planner")
        kernel.transition(t3_id, "QUEUED", actor="scheduler")
        l3 = kernel.claim(t3_id, "worker_gamma")
        kernel.start(t3_id, l3.lease_id)
        kernel.transition(t3_id, "VERIFYING", lease_id=l3.lease_id, actor="worker_gamma")

        pre_t3 = kernel.get_task(t3_id)
        print(f"[*] Task in verification: ID={t3_id}, State={pre_t3['state']}, Lease={pre_t3['active_lease_id']}")

        try:
            # Caller forces FAILED without independent verifier indictment (unlike GAP-11 commit_completed)
            kernel.transition(
                t3_id,
                "FAILED",
                lease_id=l3.lease_id,
                actor="worker_gamma",
                reason="sabotage_in_verifying_phase",
            )
            post_t3 = kernel.get_task(t3_id)
            if post_t3["state"] == "FAILED":
                print("[!] [RED] EXPLOIT SUCCEEDED: Task terminated in FAILED without independent verifier indictment!")
                print(f"    Task State: {post_t3['state']}, Version: {post_t3['version']}")
                print("    Invariant Violated: INV-GAP12-01 & INV-GAP12-02 (Missing verifier counter-evidence)")
                results["vector_3"]["status"] = "VULNERABILITY_PROVEN_RED"
            else:
                results["vector_3"]["status"] = f"UNEXPECTED_STATE_{post_t3['state']}"
        except InvalidTransition as exc:
            print(f"[*] [GREEN] Call blocked with InvalidTransition: {exc}")
            results["vector_3"]["status"] = "PROTECTED_GREEN_InvalidTransition"
        except Exception as exc:
            print(f"[!] [UNEXPECTED CRASH] Call failed with unexpected {type(exc).__name__}: {exc}")
            results["vector_3"]["status"] = f"UNEXPECTED_CRASH_{type(exc).__name__}"

        # =========================================================================
        # VECTOR 4: Stolen Lease Sabotage (Bypassing Recovery State Machine)
        # =========================================================================
        print("\n" + "-" * 80)
        print("[VECTOR 4] Testing Stolen Lease Sabotage & Recovery Bypass")
        print("-" * 80)
        t4_id = "task_gap12_v4"
        kernel.create_task(t4_id, "owner_alpha", "Task for Vector 4: stolen lease sabotage", max_attempts=3)
        kernel.transition(t4_id, "PLANNING", actor="planner")
        kernel.transition(t4_id, "READY", actor="planner")
        kernel.transition(t4_id, "QUEUED", actor="scheduler")
        l4 = kernel.claim(t4_id, "legitimate_worker_delta")
        kernel.start(t4_id, l4.lease_id)

        pre_t4 = kernel.get_task(t4_id)
        print(f"[*] Task running: ID={t4_id}, LegitimateWorker=legitimate_worker_delta, Lease={l4.lease_id}")

        try:
            # Stolen lease scenario: actor 'rogue_saboteur_delta' uses the stolen lease ID
            # transition() checks caller_lease == bound lease, but DOES NOT verify caller actor matches lease worker_id
            kernel.transition(
                t4_id,
                "FAILED",
                lease_id=l4.lease_id,
                actor="rogue_saboteur_delta",
                reason="malicious_kill_via_stolen_lease",
            )
            post_t4 = kernel.get_task(t4_id)
            if post_t4["state"] == "FAILED":
                print("[!] [RED] EXPLOIT SUCCEEDED: Rogue actor with stolen lease killed task into terminal FAILED!")
                print(f"    Task State: {post_t4['state']}, Version: {post_t4['version']}, RemainingAttempts: Discarded")
                print("    Invariant Violated: INV-GAP12-01, INV-GAP12-02 & INV-GAP12-03 (Recovery engine completely bypassed)")
                results["vector_4"]["status"] = "VULNERABILITY_PROVEN_RED"
            else:
                results["vector_4"]["status"] = f"UNEXPECTED_STATE_{post_t4['state']}"
        except InvalidTransition as exc:
            print(f"[*] [GREEN] Call blocked with InvalidTransition: {exc}")
            results["vector_4"]["status"] = "PROTECTED_GREEN_InvalidTransition"
        except Exception as exc:
            print(f"[!] [UNEXPECTED CRASH] Call failed with unexpected {type(exc).__name__}: {exc}")
            results["vector_4"]["status"] = f"UNEXPECTED_CRASH_{type(exc).__name__}"

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
        # 1. Inspect tasks table
        print("\n--- RAW SQLITE: 'tasks' TABLE ROWS ---")
        task_rows = conn.execute(
            "SELECT task_id, owner, state, version, active_lease_id, active_fencing_token, max_attempts, created_at, updated_at "
            "FROM tasks ORDER BY task_id"
        ).fetchall()

        all_mutated_to_failed = True if task_rows else False
        any_mutated_to_failed = False
        for row in task_rows:
            r_dict = dict(row)
            print(f"  [Row] task_id={r_dict['task_id']} | state={r_dict['state']} | version={r_dict['version']} | "
                  f"active_lease={r_dict['active_lease_id']} | fencing_token={r_dict['active_fencing_token']} | "
                  f"max_attempts={r_dict['max_attempts']}")
            if r_dict["state"] == "FAILED":
                any_mutated_to_failed = True
            else:
                all_mutated_to_failed = False

        results["sqlite_tasks_state_failed"] = all_mutated_to_failed
        results["sqlite_tasks_state_any_failed"] = any_mutated_to_failed

        # 2. Inspect events table (task events journal)
        print("\n--- RAW SQLITE: 'events' TABLE TRANSITION JOURNAL ---")
        event_rows = conn.execute(
            "SELECT event_id, task_id, seq, type, from_state, to_state, actor, reason, event_hash "
            "FROM events WHERE to_state='FAILED' ORDER BY task_id, seq"
        ).fetchall()

        for row in event_rows:
            r_dict = dict(row)
            print(f"  [Event] task_id={r_dict['task_id']} | seq={r_dict['seq']} | type={r_dict['type']} | "
                  f"transition={r_dict['from_state']}->{r_dict['to_state']} | actor={r_dict['actor']} | "
                  f"reason='{r_dict['reason']}'")

        results["sqlite_events_count_failed"] = len(event_rows)
        print(f"\nTotal terminal FAILED transition events recorded in DB: {len(event_rows)}")

    finally:
        conn.close()
        # Clean up database file
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
    all_red = True
    all_green = True
    for key, val in results.items():
        if key.startswith("vector_"):
            print(f"  {key.upper()}: {val['name']}")
            print(f"    Verdict: {val['status']}")
            if val["status"] != "VULNERABILITY_PROVEN_RED":
                all_red = False
            if val["status"] != "PROTECTED_GREEN_InvalidTransition":
                all_green = False

    print("\nAnti-Placebo Contract Status:")
    if all_red and results.get("sqlite_tasks_state_failed") and results.get("sqlite_events_count_failed") == 4:
        print("  >> RED STATE CONFIRMED: All 4 exploit vectors succeed on current codebase.")
        print("  >> Vulnerability GAP-12 is actively exploitable at the database layer.")
        print("  >> Anti-Placebo Falsification Condition: Upon implementing INV-GAP12-01 through 04,")
        print("     calls to transition(..., 'FAILED') must raise InvalidTransition, causing this probe")
        print("     to record PROTECTED_GREEN for all vectors.")
        print("  >> Verdict: ALL_VECTORS_PROVEN_RED")
        results["overall_verdict"] = "ALL_VECTORS_PROVEN_RED"
    elif all_green and results.get("sqlite_events_count_failed") == 0 and not results.get("sqlite_tasks_state_any_failed"):
        print("  >> GREEN STATE CONFIRMED: All 4 exploit vectors protected by InvalidTransition.")
        print("  >> Tasks and events verified in database: 0 unauthorized transitions to FAILED.")
        print("  >> Anti-Placebo Falsification Condition Satisfied.")
        print("  >> Verdict: ALL_VECTORS_PROTECTED_GREEN")
        results["overall_verdict"] = "ALL_VECTORS_PROTECTED_GREEN"
    else:
        print("  >> Probe did not reproduce expected RED or GREEN state cleanly.")
        print(f"     all_red={all_red}, all_green={all_green}, "
              f"sqlite_tasks_state_failed={results.get('sqlite_tasks_state_failed')}, "
              f"sqlite_events_count_failed={results.get('sqlite_events_count_failed')}")
        results["overall_verdict"] = "UNEXPECTED_STATE"

    print("=" * 80)
    return results


if __name__ == "__main__":
    outcome = run_probe()
    verdict = outcome.get("overall_verdict")
    if verdict in ("ALL_VECTORS_PROVEN_RED", "ALL_VECTORS_PROTECTED_GREEN"):
        sys.exit(0)
    else:
        sys.exit(1)
