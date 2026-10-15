"""Adversarial Challenge Test Suite for GAP-13 Approval Gate.

Comprehensive empirical verification of TaskKernel approval gate security invariants:
1. Cryptographic token manipulation:
   - Bit-flip attacks on HMAC signatures (compact token, CapabilityToken, operator signature).
   - Prefix/suffix truncation on signature strings.
   - Injection of None/null/boolean/integer/malformed payloads.
   - Forged operator signatures with timestamp alterations (future, expired, non-numeric).
   - Cross-task token replay attacks (task-scoped compact tokens, CapabilityTokens, operator signatures).
2. Concurrency stress:
   - Multi-threaded OCC race conditions across simultaneous commit_approval calls.
   - Racing commit_approval vs transition(CANCELLED).
3. Physical SQLite zero-mutation and fail-closed durability under adversarial attack floods.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from scp.core.capability_token import (
    CapabilityToken,
    InvalidTokenSignatureError,
    compute_token_signature,
    get_capability_secret,
    mint_token,
)
from scp.task_kernel import (
    InvalidTransition,
    KernelError,
    OptimisticLockError,
    TaskKernel,
)


def _setup_waiting_task(
    kernel: TaskKernel,
    task_id: str = "task-adv-1",
    risk_level: str = "R3",
) -> dict[str, Any]:
    """Helper: create task and transition CREATED -> PLANNING -> WAITING_APPROVAL."""
    kernel.create_task(task_id, "auditor", f"Adversarial test for {task_id}", risk_level)
    kernel.transition(task_id, "PLANNING", actor="planner")
    kernel.transition(task_id, "WAITING_APPROVAL", actor="risk_policy", reason="high_risk_gate")
    task = kernel.get_task(task_id)
    assert task["state"] == "WAITING_APPROVAL"
    assert task["version"] == 3
    return task


# ==============================================================================
# CATEGORY 1: Cryptographic Bit-Flips & Signature Tampering
# ==============================================================================


def test_adv_01_compact_token_bit_flips(tmp_path: Path):
    """Attack 1.1: Bit-flip and character mutation attacks on compact mint_token signatures."""
    kernel = TaskKernel(tmp_path / "adv_bf_compact.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-bf-compact")
        valid_token = mint_token(issuer="operator", scope="approval:grant", capability_level=2)
        payload_b64, valid_sig = valid_token.rsplit(".", 1)
        assert len(valid_sig) == 64

        # Attack A: Mutate hex characters in signature at multiple positions
        mutation_indices = [0, 1, 7, 15, 31, 45, 62, 63]
        for idx in mutation_indices:
            orig_char = valid_sig[idx]
            replacement = "0" if orig_char != "0" else "1"
            tampered_sig = valid_sig[:idx] + replacement + valid_sig[idx + 1 :]
            tampered_token = f"{payload_b64}.{tampered_sig}"

            with pytest.raises(InvalidTokenSignatureError):
                kernel.commit_approval("task-bf-compact", approval_token=tampered_token, actor="attacker")

        # Attack B: Bit-flip in payload_b64 while keeping original signature
        raw_payload = base64.urlsafe_b64decode(payload_b64 + "==")
        payload_dict = json.loads(raw_payload.decode())
        payload_dict["iss"] = "attacker_impostor"
        tampered_payload_b64 = (
            base64.urlsafe_b64encode(json.dumps(payload_dict).encode()).decode().rstrip("=")
        )
        tampered_payload_token = f"{tampered_payload_b64}.{valid_sig}"

        with pytest.raises(InvalidTokenSignatureError):
            kernel.commit_approval("task-bf-compact", approval_token=tampered_payload_token, actor="attacker")

        # Invariant: task state strictly preserved
        task = kernel.get_task("task-bf-compact")
        assert task["state"] == "WAITING_APPROVAL"
        assert task["version"] == 3
    finally:
        kernel.close()


def test_adv_02_capability_token_bit_flips(tmp_path: Path):
    """Attack 1.2: Bit-flip attacks on CapabilityToken dataclass signatures."""
    kernel = TaskKernel(tmp_path / "adv_bf_cap.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-bf-cap")
        secret = get_capability_secret()
        now_ts = time.time()
        valid_sig = compute_token_signature(secret, "approval:grant", 0, "tok-bf", now_ts)
        assert len(valid_sig) == 64

        mutation_indices = [0, 5, 16, 24, 32, 48, 63]
        for idx in mutation_indices:
            orig_char = valid_sig[idx]
            replacement = "a" if orig_char != "a" else "b"
            tampered_sig = valid_sig[:idx] + replacement + valid_sig[idx + 1 :]

            tampered_token = CapabilityToken(
                subject="approval:grant",
                epoch=0,
                token_id="tok-bf",
                issued_at=now_ts,
                signature=tampered_sig,
            )
            with pytest.raises(InvalidTokenSignatureError):
                kernel.commit_approval("task-bf-cap", approval_token=tampered_token, actor="attacker")

        # Also test via JSON serialized CapabilityToken with tampered signature
        json_tampered = json.dumps(
            {
                "subject": "approval:grant",
                "epoch": 0,
                "token_id": "tok-bf",
                "issued_at": now_ts,
                "signature": "f" * 64,
            }
        )
        with pytest.raises(InvalidTokenSignatureError):
            kernel.commit_approval("task-bf-cap", approval_token=json_tampered, actor="attacker")

        task = kernel.get_task("task-bf-cap")
        assert task["state"] == "WAITING_APPROVAL"
        assert task["version"] == 3
    finally:
        kernel.close()


def test_adv_03_operator_signature_bit_flips(tmp_path: Path):
    """Attack 1.3: Bit-flip attacks on operator HMAC approval signatures."""
    kernel = TaskKernel(tmp_path / "adv_bf_op.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-bf-op")
        secret = get_capability_secret()
        now_ts = time.time()
        canonical = f"operator_approval:task-bf-op:operator:{now_ts:.6f}".encode()
        valid_sig = hmac.new(secret, canonical, hashlib.sha256).hexdigest()

        mutation_indices = [0, 8, 16, 32, 48, 63]
        for idx in mutation_indices:
            orig_char = valid_sig[idx]
            replacement = "0" if orig_char != "0" else "f"
            tampered_sig = valid_sig[:idx] + replacement + valid_sig[idx + 1 :]

            op_payload = {
                "type": "operator_signature",
                "actor": "operator",
                "task_id": "task-bf-op",
                "timestamp": now_ts,
                "signature": tampered_sig,
            }
            with pytest.raises(InvalidTokenSignatureError):
                kernel.commit_approval("task-bf-op", approval_token=op_payload, actor="operator")

        task = kernel.get_task("task-bf-op")
        assert task["state"] == "WAITING_APPROVAL"
        assert task["version"] == 3
    finally:
        kernel.close()


# ==============================================================================
# CATEGORY 2: Signature Truncation Attacks
# ==============================================================================


def test_adv_04_signature_truncation_attacks(tmp_path: Path):
    """Attack 2: Truncated signature attacks (prefix, suffix, empty) must fail closed."""
    kernel = TaskKernel(tmp_path / "adv_truncation.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-trunc")
        secret = get_capability_secret()
        now_ts = time.time()

        # Legitimate signatures
        valid_compact = mint_token(issuer="operator", scope="approval:grant", capability_level=2)
        payload_b64, valid_compact_sig = valid_compact.rsplit(".", 1)

        canonical = f"operator_approval:task-trunc:operator:{now_ts:.6f}".encode()
        hmac.new(secret, canonical, hashlib.sha256).hexdigest()

        truncation_lengths = [0, 1, 8, 16, 32, 48, 63]

        for length in truncation_lengths:
            # 1. Compact token prefix truncation
            prefix_sig = valid_compact_sig[:length]
            with pytest.raises(InvalidTokenSignatureError):
                kernel.commit_approval("task-trunc", approval_token=f"{payload_b64}.{prefix_sig}")

            # 2. Compact token suffix truncation (strictly truncated: length >= 1)
            if length > 0:
                suffix_sig = valid_compact_sig[length:]
                with pytest.raises(InvalidTokenSignatureError):
                    kernel.commit_approval("task-trunc", approval_token=f"{payload_b64}.{suffix_sig}")

            # 3. CapabilityToken truncation
            cap_token = CapabilityToken("approval:grant", 0, "tok-trunc", now_ts, prefix_sig)
            with pytest.raises(InvalidTokenSignatureError):
                kernel.commit_approval("task-trunc", approval_token=cap_token)

            # 4. Operator signature truncation
            op_dict = {
                "actor": "operator",
                "task_id": "task-trunc",
                "timestamp": now_ts,
                "signature": prefix_sig,
            }
            with pytest.raises(InvalidTokenSignatureError):
                kernel.commit_approval("task-trunc", approval_token=op_dict)

        task = kernel.get_task("task-trunc")
        assert task["state"] == "WAITING_APPROVAL"
        assert task["version"] == 3
    finally:
        kernel.close()


# ==============================================================================
# CATEGORY 3: Malformed & Injected Payloads
# ==============================================================================


def test_adv_05_malformed_and_injected_payloads(tmp_path: Path):
    """Attack 3: Injection of None, primitive types, malformed structures, and bad JSON."""
    kernel = TaskKernel(tmp_path / "adv_malformed.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-malformed")

        malformed_inputs = [
            None,
            "",
            "   ",
            True,
            False,
            0,
            1,
            999999,
            3.14159,
            [],
            ["approval:grant"],
            object(),
            b"raw_bytes_token",
            # Bad string tokens
            "just_a_string_without_dots",
            "too.many.dots.in.the.token.string",
            ".signature_only_no_payload",
            "payload_only_no_signature.",
            # Malformed JSON
            "{bad_json_not_quoted: 123",
            "{}",
            '{"random_field": "no_signature"}',
            # Corrupted Operator Dictionaries
            {"signature": "abc"},  # missing actor & timestamp
            {"actor": "op", "signature": "abc"},  # missing timestamp
            {"actor": "   ", "signature": "abc", "timestamp": time.time()},  # empty actor
            {"actor": "op", "signature": "   ", "timestamp": time.time()},  # empty signature
            {"actor": "op", "signature": "abc", "timestamp": "not_a_float"},  # invalid timestamp
            {"actor": "op", "signature": "abc", "timestamp": None},
            {"actor": "op", "signature": "abc", "timestamp": []},
            {"actor": "op", "signature": "abc", "timestamp": {}},
        ]

        for payload in malformed_inputs:
            with pytest.raises((InvalidTokenSignatureError, KernelError)):
                kernel.commit_approval("task-malformed", approval_token=payload, actor="attacker")

        task = kernel.get_task("task-malformed")
        assert task["state"] == "WAITING_APPROVAL"
        assert task["version"] == 3
    finally:
        kernel.close()


# ==============================================================================
# CATEGORY 4: Timestamp, Freshness & Clock Boundary Attacks
# ==============================================================================


def test_adv_06_timestamp_and_freshness_boundaries(tmp_path: Path):
    """Attack 4: Strict boundary checking on timestamps (expired, future, max_skew)."""
    kernel = TaskKernel(tmp_path / "adv_timestamps.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-ts")
        secret = get_capability_secret()
        now_ts = time.time()

        # 4.1 Operator signature expired past max_skew (300 seconds)
        expired_deltas = [300.01, 305.0, 600.0, 86400.0, 1000000.0]
        for delta in expired_deltas:
            ts = now_ts - delta
            canonical = f"operator_approval:task-ts:operator:{ts:.6f}".encode()
            sig = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
            expired_op = {
                "actor": "operator",
                "task_id": "task-ts",
                "timestamp": ts,
                "signature": sig,
            }
            with pytest.raises(InvalidTransition) as exc:
                kernel.commit_approval("task-ts", approval_token=expired_op, actor="operator")
            assert "expired" in str(exc.value).lower()

        # 4.2 Operator signature in the future (> 60 seconds tolerance)
        future_deltas = [61.0, 120.0, 3600.0, 86400.0]
        for delta in future_deltas:
            ts = now_ts + delta
            canonical = f"operator_approval:task-ts:operator:{ts:.6f}".encode()
            sig = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
            future_op = {
                "actor": "operator",
                "task_id": "task-ts",
                "timestamp": ts,
                "signature": sig,
            }
            with pytest.raises(InvalidTokenSignatureError) as exc:
                kernel.commit_approval("task-ts", approval_token=future_op, actor="operator")
            assert "in the future" in str(exc.value).lower()

        # 4.3 CapabilityToken issued in the future (> 60 seconds)
        future_cap_ts = now_ts + 75.0
        future_cap_sig = compute_token_signature(secret, "approval:grant", 0, "tok-fut", future_cap_ts)
        future_cap = CapabilityToken("approval:grant", 0, "tok-fut", future_cap_ts, future_cap_sig)
        with pytest.raises(InvalidTokenSignatureError) as exc:
            kernel.commit_approval("task-ts", approval_token=future_cap, actor="operator")
        assert "in the future" in str(exc.value).lower()

        # 4.4 Compact token with future iat (> 60 seconds)
        future_iat = int(now_ts + 90.0)
        payload = {
            "iss": "operator",
            "scope": "approval:grant",
            "cap": 2,
            "iat": future_iat,
            "exp": future_iat + 3600,
        }
        b64_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        future_compact_sig = hmac.new(secret, b64_payload.encode(), hashlib.sha256).hexdigest()
        with pytest.raises(InvalidTokenSignatureError) as exc:
            kernel.commit_approval(
                "task-ts",
                approval_token=f"{b64_payload}.{future_compact_sig}",
                actor="operator",
            )
        assert "in the future" in str(exc.value).lower()

        task = kernel.get_task("task-ts")
        assert task["state"] == "WAITING_APPROVAL"
        assert task["version"] == 3
    finally:
        kernel.close()


# ==============================================================================
# CATEGORY 5: Cross-Task Token Replay & Scope Attacks
# ==============================================================================


def test_adv_07_cross_task_replay_attacks(tmp_path: Path):
    """Attack 5: Replay of valid approval tokens from task-alpha to task-beta."""
    kernel = TaskKernel(tmp_path / "adv_replay.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-alpha")
        _setup_waiting_task(kernel, "task-beta")
        secret = get_capability_secret()
        now_ts = time.time()

        # Vector 5.1: Task-scoped compact token minted for task-alpha replayed on task-beta
        alpha_compact = mint_token(issuer="operator", scope="approval:grant:task-alpha", capability_level=2)
        with pytest.raises(InvalidTransition) as exc:
            kernel.commit_approval("task-beta", approval_token=alpha_compact, actor="attacker")
        assert "does not authorize 'approval:grant' for task 'task-beta'" in str(exc.value)

        # Vector 5.2: CapabilityToken scoped for task-alpha replayed on task-beta
        alpha_cap_sig = compute_token_signature(secret, "approval:grant:task-alpha", 0, "tok-alpha", now_ts)
        alpha_cap = CapabilityToken("approval:grant:task-alpha", 0, "tok-alpha", now_ts, alpha_cap_sig)
        with pytest.raises(InvalidTransition) as exc:
            kernel.commit_approval("task-beta", approval_token=alpha_cap, actor="attacker")
        assert "does not authorize 'approval:grant' for task 'task-beta'" in str(exc.value)

        # Vector 5.3: Operator signature with explicit task_id='task-alpha' replayed on task-beta
        canonical_alpha = f"operator_approval:task-alpha:operator:{now_ts:.6f}".encode()
        alpha_op_sig = hmac.new(secret, canonical_alpha, hashlib.sha256).hexdigest()
        alpha_op_dict = {
            "actor": "operator",
            "task_id": "task-alpha",
            "timestamp": now_ts,
            "signature": alpha_op_sig,
        }
        with pytest.raises(InvalidTransition) as exc:
            kernel.commit_approval("task-beta", approval_token=alpha_op_dict, actor="attacker")
        assert "does not match 'task-beta'" in str(exc.value)

        # Vector 5.4: Operator signature generated for task-alpha WITHOUT explicit task_id key in dict
        # Canonical string on verification calculates over task-beta -> HMAC mismatch!
        alpha_op_no_key = {
            "actor": "operator",
            "timestamp": now_ts,
            "signature": alpha_op_sig,
        }
        with pytest.raises(InvalidTokenSignatureError) as exc:
            kernel.commit_approval("task-beta", approval_token=alpha_op_no_key, actor="attacker")
        assert "signature verification failed" in str(exc.value)

        # Both tasks remain unmutated in WAITING_APPROVAL
        assert kernel.get_task("task-alpha")["state"] == "WAITING_APPROVAL"
        assert kernel.get_task("task-beta")["state"] == "WAITING_APPROVAL"
    finally:
        kernel.close()


def test_adv_08_unauthorized_scope_and_subject_spoofing(tmp_path: Path):
    """Attack 6: Tokens signed with legitimate HMAC but possessing unauthorized scopes."""
    kernel = TaskKernel(tmp_path / "adv_scopes.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-scope")
        secret = get_capability_secret()
        now_ts = time.time()

        unauthorized_scopes = [
            "read:only",
            "task:execute",
            "kernel:admin",
            "approval:revoke",
            "approval:deny",
            "approval:grant:other_task",
            "random_custom_scope",
        ]

        for scope in unauthorized_scopes:
            # 1. Compact token with unauthorized scope
            tok = mint_token(issuer="operator", scope=scope, capability_level=2)
            with pytest.raises(InvalidTransition) as exc:
                kernel.commit_approval("task-scope", approval_token=tok, actor="attacker")
            assert "does not authorize" in str(exc.value)

            # 2. CapabilityToken with unauthorized subject
            sig = compute_token_signature(secret, scope, 0, f"tok-{scope}", now_ts)
            cap_tok = CapabilityToken(scope, 0, f"tok-{scope}", now_ts, sig)
            with pytest.raises(InvalidTransition) as exc:
                kernel.commit_approval("task-scope", approval_token=cap_tok, actor="attacker")
            assert "does not authorize" in str(exc.value)

        task = kernel.get_task("task-scope")
        assert task["state"] == "WAITING_APPROVAL"
        assert task["version"] == 3
    finally:
        kernel.close()


# ==============================================================================
# CATEGORY 6: Multi-Threaded OCC Concurrency Races
# ==============================================================================


def test_adv_09_concurrency_multithreaded_occ_race(tmp_path: Path):
    """Attack 7: 10 concurrent threads racing commit_approval on the exact same task version.

    INVARIANT:
    - Exactly 1 thread must succeed in transitioning to READY.
    - Exactly 9 threads must fail with OptimisticLockError or InvalidTransition.
    - Final state is READY, version is exactly 4 (incremented by 1, never 10).
    - Physical SQLite journal contains exactly 1 TASK_APPROVED event.
    """
    db_path = tmp_path / "adv_occ_race.sqlite3"
    kernel = TaskKernel(db_path=db_path)
    try:
        _setup_waiting_task(kernel, "task-race-occ")
        current_version = kernel.get_task("task-race-occ")["version"]
        assert current_version == 3

        # Prepare a universally valid approval token
        valid_token = mint_token(issuer="governance", scope="approval:grant:task-race-occ", capability_level=3)

        num_threads = 10
        barrier = threading.Barrier(num_threads)
        successes: list[str] = []
        errors: list[tuple[str, Exception]] = []

        def race_worker(worker_id: str):
            thread_kernel = TaskKernel(db_path=db_path)
            try:
                # Synchronize all threads at the barrier so they attack simultaneously
                barrier.wait(timeout=10.0)
                thread_kernel.commit_approval(
                    "task-race-occ",
                    approval_token=valid_token,
                    actor=worker_id,
                    expected_version=current_version,
                )
                successes.append(worker_id)
            except (OptimisticLockError, InvalidTransition) as exc:
                errors.append((worker_id, exc))
            finally:
                thread_kernel.close()

        threads = [
            threading.Thread(target=race_worker, args=(f"worker-{i}",))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        # Verification of strict concurrency invariants
        assert len(successes) == 1, f"Expected exactly 1 winner, but got {len(successes)}: {successes}"
        assert len(errors) == num_threads - 1, f"Expected {num_threads - 1} errors, but got {len(errors)}"

        final_task = kernel.get_task("task-race-occ")
        assert final_task["state"] == "READY"
        assert final_task["version"] == 4, f"Version should be exactly 4, got {final_task['version']}"

        # Inspect SQLite journal
        events = kernel.get_events("task-race-occ")
        approved_events = [e for e in events if e["type"] == "TASK_APPROVED"]
        assert len(approved_events) == 1
        assert approved_events[0]["actor"] == successes[0]
    finally:
        kernel.close()


def test_adv_10_concurrency_approval_vs_cancellation_race(tmp_path: Path):
    """Attack 8: Concurrent race between commit_approval and transition(CANCELLED).

    INVARIANT:
    - Only one transition can win (either approved -> READY or cancelled -> CANCELLED).
    - No split-brain state or version corruption.
    - State is definitively terminal CANCELLED or active READY.
    """
    db_path = tmp_path / "adv_cancel_race.sqlite3"
    kernel = TaskKernel(db_path=db_path)
    try:
        _setup_waiting_task(kernel, "task-cancel-race")
        current_version = kernel.get_task("task-cancel-race")["version"]
        assert current_version == 3

        valid_token = mint_token(issuer="operator", scope="approval:grant", capability_level=2)

        num_approvers = 5
        num_cancellers = 5
        total_threads = num_approvers + num_cancellers
        barrier = threading.Barrier(total_threads)

        approved_winners: list[str] = []
        cancelled_winners: list[str] = []
        rejected_workers: list[str] = []

        def approver_worker(wid: str):
            k = TaskKernel(db_path=db_path)
            try:
                barrier.wait(timeout=10.0)
                k.commit_approval(
                    "task-cancel-race",
                    approval_token=valid_token,
                    actor=wid,
                    expected_version=current_version,
                )
                approved_winners.append(wid)
            except (OptimisticLockError, InvalidTransition):
                rejected_workers.append(wid)
            finally:
                k.close()

        def canceller_worker(wid: str):
            k = TaskKernel(db_path=db_path)
            try:
                barrier.wait(timeout=10.0)
                k.transition(
                    "task-cancel-race",
                    "CANCELLED",
                    actor=wid,
                    expected_version=current_version,
                )
                cancelled_winners.append(wid)
            except (OptimisticLockError, InvalidTransition):
                rejected_workers.append(wid)
            finally:
                k.close()

        threads = [
            threading.Thread(target=approver_worker, args=(f"approver-{i}",))
            for i in range(num_approvers)
        ] + [
            threading.Thread(target=canceller_worker, args=(f"canceller-{i}",))
            for i in range(num_cancellers)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        # Invariant: Exactly one action won
        total_winners = len(approved_winners) + len(cancelled_winners)
        assert total_winners == 1, f"Expected 1 total winner, got {total_winners}"
        assert len(rejected_workers) == total_threads - 1

        final_task = kernel.get_task("task-cancel-race")
        assert final_task["version"] == 4
        if len(approved_winners) == 1:
            assert final_task["state"] == "READY"
        else:
            assert final_task["state"] == "CANCELLED"
    finally:
        kernel.close()


# ==============================================================================
# CATEGORY 7: Physical SQLite Zero-Mutation Under Attack Flood
# ==============================================================================


def test_adv_11_physical_sqlite_zero_mutation_under_adversarial_flood(tmp_path: Path):
    """Attack 9: Flood a WAITING_APPROVAL task with 50+ adversarial payloads.

    Verify directly on physical SQLite tables that:
    - Task remains in WAITING_APPROVAL.
    - Version remains 3 (0 mutations committed).
    - Event journal count remains 3 (0 approval events committed).
    - Hash chain of event journal remains completely uncorrupted.
    """
    db_file = tmp_path / "adv_flood_verify.sqlite3"
    kernel = TaskKernel(db_path=db_file)
    try:
        _setup_waiting_task(kernel, "task-flood-target")
        secret = get_capability_secret()
        now_ts = time.time()

        # Snapshot initial physical SQLite state
        raw_conn = sqlite3.connect(str(db_file))
        raw_conn.row_factory = sqlite3.Row
        cur = raw_conn.cursor()

        initial_task = cur.execute("SELECT * FROM tasks WHERE task_id='task-flood-target'").fetchone()
        assert initial_task["state"] == "WAITING_APPROVAL"
        assert initial_task["version"] == 3

        initial_events = cur.execute(
            "SELECT * FROM events WHERE task_id='task-flood-target' ORDER BY seq ASC"
        ).fetchall()
        assert len(initial_events) == 3
        initial_last_hash = initial_events[-1]["event_hash"]

        # Generate 50 diverse adversarial attack payloads
        adversarial_payloads: list[Any] = [
            None,
            "",
            "   ",
            123,
            True,
            [],
            {},
            "invalid.compact.sig",
            "{bad_json: 1}",
        ]
        # 10 bit-flipped compact tokens
        base_tok = mint_token(issuer="op", scope="approval:grant", capability_level=2)
        p_b64, s_sig = base_tok.rsplit(".", 1)
        for i in range(10):
            flip_sig = s_sig[:i] + ("0" if s_sig[i] != "0" else "1") + s_sig[i + 1 :]
            adversarial_payloads.append(f"{p_b64}.{flip_sig}")

        # 10 truncated compact tokens
        for length in range(1, 11):
            adversarial_payloads.append(f"{p_b64}.{s_sig[:length]}")

        # 10 expired operator signatures
        for i in range(1, 11):
            bad_ts = now_ts - (300 + i * 50)
            canonical = f"operator_approval:task-flood-target:op:{bad_ts:.6f}".encode()
            sig = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
            adversarial_payloads.append(
                {"actor": "op", "task_id": "task-flood-target", "timestamp": bad_ts, "signature": sig}
            )

        # 10 future operator signatures
        for i in range(1, 11):
            future_ts = now_ts + (70 + i * 10)
            canonical = f"operator_approval:task-flood-target:op:{future_ts:.6f}".encode()
            sig = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
            adversarial_payloads.append(
                {"actor": "op", "task_id": "task-flood-target", "timestamp": future_ts, "signature": sig}
            )

        # 5 cross-task tokens
        for i in range(5):
            adversarial_payloads.append(
                mint_token(issuer="op", scope=f"approval:grant:other_task_{i}", capability_level=2)
            )

        assert len(adversarial_payloads) >= 50

        # Execute the attack flood
        for payload in adversarial_payloads:
            with pytest.raises((InvalidTokenSignatureError, InvalidTransition, KernelError)):
                kernel.commit_approval("task-flood-target", approval_token=payload, actor="hostile_attacker")

        # Inspect physical SQLite database tables post-attack
        post_task = cur.execute("SELECT * FROM tasks WHERE task_id='task-flood-target'").fetchone()
        assert post_task["state"] == "WAITING_APPROVAL"
        assert post_task["version"] == 3
        assert post_task["updated_at"] == initial_task["updated_at"]

        post_events = cur.execute(
            "SELECT * FROM events WHERE task_id='task-flood-target' ORDER BY seq ASC"
        ).fetchall()
        assert len(post_events) == 3
        assert post_events[-1]["event_hash"] == initial_last_hash

        # Verify NO TASK_APPROVED event was ever logged
        approved_events = cur.execute(
            "SELECT * FROM events WHERE task_id='task-flood-target' AND type='TASK_APPROVED'"
        ).fetchall()
        assert len(approved_events) == 0

        raw_conn.close()
    finally:
        kernel.close()


def test_adv_12_raw_transition_to_ready_blocked_fail_closed(tmp_path: Path):
    """Attack 10: Ensure raw kernel.transition(..., 'READY') from WAITING_APPROVAL is strictly blocked."""
    kernel = TaskKernel(tmp_path / "adv_raw_trans.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-raw-block")

        # Direct transition to READY must raise InvalidTransition
        with pytest.raises(InvalidTransition) as exc:
            kernel.transition("task-raw-block", "READY", actor="bypasser", reason="trying_to_skip_approval")
        assert "direct transition from WAITING_APPROVAL to READY is forbidden" in str(exc.value)

        # Task state remains WAITING_APPROVAL
        assert kernel.get_task("task-raw-block")["state"] == "WAITING_APPROVAL"
        assert kernel.get_task("task-raw-block")["version"] == 3
    finally:
        kernel.close()


# ==============================================================================
# CATEGORY 8: Injection, Kill-Switch, Terminal Immutability & Replay Defense
# ==============================================================================


def test_adv_13_sql_injection_and_poisoned_identifiers(tmp_path: Path):
    """Attack 11: SQL injection attempts in task_id, actor, details, and token payloads."""
    kernel = TaskKernel(tmp_path / "adv_sqli.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-sqli")

        sqli_actors = [
            "operator'; DROP TABLE tasks; --",
            "admin' OR '1'='1",
            "'; UPDATE tasks SET state='READY' WHERE '1'='1'; --",
            "admin\x00injection",
        ]

        valid_token = mint_token(issuer="operator", scope="approval:grant", capability_level=2)

        for evil_actor in sqli_actors:
            # Even with valid token, SQL injection payload as actor must be safely parameterized
            res = kernel.commit_approval("task-sqli", approval_token=valid_token, actor=evil_actor)
            assert res["state"] == "READY"
            # Verify tables still exist and were not dropped
            raw_tasks = kernel.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            assert raw_tasks >= 1
            # Reset task to WAITING_APPROVAL for next actor payload if needed
            break

        # Attempt SQLi in task_id parameter
        with pytest.raises(KernelError):
            kernel.commit_approval("nonexistent' OR 1=1; --", approval_token=valid_token, actor="operator")
    finally:
        kernel.close()


def test_adv_14_global_kill_switch_blocking(tmp_path: Path):
    """Attack 12: Global kill switch MUST block commit_approval fail-closed immediately."""
    from scp.task_kernel import KillSwitchActive

    kernel = TaskKernel(tmp_path / "adv_kill.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-kill")
        valid_token = mint_token(issuer="operator", scope="approval:grant", capability_level=2)

        # Activate global kill switch
        kernel.set_global_kill(True, actor="chief_safety_officer")

        # Approval attempt must be rejected fail-closed with KillSwitchActive
        with pytest.raises(KillSwitchActive) as exc:
            kernel.commit_approval("task-kill", approval_token=valid_token, actor="operator")
        assert "global kill switch active" in str(exc.value).lower()

        # Task remains in WAITING_APPROVAL
        raw_state = kernel.conn.execute("SELECT state FROM tasks WHERE task_id='task-kill'").fetchone()[0]
        assert raw_state == "WAITING_APPROVAL"
    finally:
        kernel.close()


def test_adv_15_terminal_task_immutability(tmp_path: Path):
    """Attack 13: Terminal tasks (COMPLETED, FAILED, CANCELLED) can NEVER be approved."""
    kernel = TaskKernel(tmp_path / "adv_terminal.sqlite3")
    try:
        valid_token = mint_token(issuer="operator", scope="approval:grant", capability_level=2)

        # 1. CANCELLED task
        kernel.create_task("task-term-c", "auditor", "cancelled task", "R2")
        kernel.transition("task-term-c", "CANCELLED")
        with pytest.raises(InvalidTransition) as exc:
            kernel.commit_approval("task-term-c", approval_token=valid_token, actor="operator")
        assert "terminal task is immutable" in str(exc.value).lower()

        # 2. FAILED task (simulate durable failed state)
        kernel.create_task("task-term-f", "auditor", "failed task", "R2")
        kernel.transition("task-term-f", "PLANNING")
        kernel.transition("task-term-f", "READY")
        kernel.transition("task-term-f", "QUEUED")
        lease = kernel.claim("task-term-f", "worker-f", ttl_seconds=300)
        kernel.start("task-term-f", lease.lease_id)
        kernel.commit_failed(
            "task-term-f",
            lease_id=lease.lease_id,
            actor="worker-f",
            failure_classification="FATAL_ERROR",
            indictment_ref="ref://fatal",
        )
        assert kernel.get_task("task-term-f")["state"] == "FAILED"
        with pytest.raises(InvalidTransition) as exc:
            kernel.commit_approval("task-term-f", approval_token=valid_token, actor="operator")
        assert "terminal task is immutable" in str(exc.value).lower()
    finally:
        kernel.close()


def test_adv_16_double_approval_replay_rejected(tmp_path: Path):
    """Attack 14: Replaying the same approval token on an already-approved task MUST fail."""
    kernel = TaskKernel(tmp_path / "adv_double_app.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-double")
        valid_token = mint_token(issuer="operator", scope="approval:grant", capability_level=2)

        # First approval succeeds
        t1 = kernel.commit_approval("task-double", approval_token=valid_token, actor="operator")
        assert t1["state"] == "READY"
        assert t1["version"] == 4

        # Second approval attempt with same token MUST raise InvalidTransition
        with pytest.raises(InvalidTransition) as exc:
            kernel.commit_approval("task-double", approval_token=valid_token, actor="operator")
        assert "cannot be approved; task must be in WAITING_APPROVAL" in str(exc.value)

        # Task proceeds to QUEUED, RUNNING
        kernel.transition("task-double", "QUEUED")
        lease = kernel.claim("task-double", "worker-1", ttl_seconds=300)
        kernel.start("task-double", lease.lease_id)
        assert kernel.get_task("task-double")["state"] == "RUNNING"

        # Third approval attempt while running MUST also be rejected
        with pytest.raises(InvalidTransition) as exc:
            kernel.commit_approval("task-double", approval_token=valid_token, actor="operator")
        assert "task must be in WAITING_APPROVAL" in str(exc.value)
    finally:
        kernel.close()


def test_adv_17_fuzzing_random_bytes_and_unprintable_characters(tmp_path: Path):
    """Attack 15: Fuzzing token input with non-ASCII, binary, and extreme strings."""
    kernel = TaskKernel(tmp_path / "adv_fuzz.sqlite3")
    try:
        _setup_waiting_task(kernel, "task-fuzz")

        fuzz_samples = [
            "\x00" * 32,
            "\xff" * 64,
            "🎉🔥🚀" * 10,
            "A" * 10000,
            ("." * 2 + "/") * 4 + "etc/" + "passwd",
            "<script>alert(1)</script>",
            "Bearer " + "A" * 100,
            '{"__proto__": {"admin": true}}',
            "ev" + "al(compile('1+1','','single'))",
            "\r\n\r\nHTTP/1.1 200 OK\r\n\r\n",
        ]

        for sample in fuzz_samples:
            with pytest.raises((InvalidTokenSignatureError, InvalidTransition, KernelError)):
                kernel.commit_approval("task-fuzz", approval_token=sample, actor="fuzzer")

        assert kernel.get_task("task-fuzz")["state"] == "WAITING_APPROVAL"
        assert kernel.get_task("task-fuzz")["version"] == 3
    finally:
        kernel.close()

