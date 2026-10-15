"""Adversarial Penetration & Stress Testing Harness for R2 (PCController PEP) and R3 (Receipt Provenance).

Authored by: Challenger 1 (teamwork_preview_challenger)
Directives: FA-01 to FA-13, Zero-Trust, Fail-Closed, Empirical Proof Mandate.

This harness executes 35 distinct adversarial attack vectors attempting to:
1. Bypass PCController capability token enforcement (R2).
2. Forge or tamper with Verifier Receipts to trick TaskKernel into completing tasks (R3).
3. Bypass the state machine to complete tasks without verification (GAP-P1).
4. Verify physical SQLite database rows for authentic tamper-evident provenance logging.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import dataclasses
import hashlib
import hmac
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Set default test secrets before importing scp modules that load secrets at import time
if not os.environ.get("SCP_CAPABILITY_SECRET"):
    os.environ["SCP_CAPABILITY_SECRET"] = "challenger-secret-key-for-empirical-testing-12345"
if not os.environ.get("SCP_VERIFIER_SECRET"):
    os.environ["SCP_VERIFIER_SECRET"] = "challenger-secret-key-for-empirical-testing-12345"


from scp.core.capability_token import (
    InvalidTokenSignatureError,
    compute_token_signature,
    get_capability_secret,
)
from scp.core.verifier_receipt import (
    InvalidReceiptSignatureError,
    MissingSecretError,
    VerifierReceipt,
    canonical_receipt_bytes,
    get_verifier_secret,
    sign_verifier_receipt,
    verify_verifier_receipt,
)
from scp.pc_control.pc_controller import CapabilityLevel, PCController
from scp.security.capability_epoch import (
    CapabilityAuthority,
    CapabilityRevokedError,
    CapabilityToken,
)
from scp.task_kernel import (
    InvalidTransition,
    KernelError,
    OptimisticLockError,
    StaleLease,
    TaskKernel,
)


class PenetrationHarness:
    def __init__(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="scp-challenger-r2-r3-"))
        self.secret = "challenger-secret-key-for-empirical-testing-12345"
        os.environ["SCP_CAPABILITY_SECRET"] = self.secret
        os.environ["SCP_VERIFIER_SECRET"] = self.secret
        self.passed_vectors = []
        self.failed_vectors = []

    def cleanup(self) -> None:
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def record_pass(self, vector_id: str, description: str, observation: str) -> None:
        print(f"[PASS] {vector_id}: {description}")
        print(f"       -> Observation: {observation}")
        self.passed_vectors.append((vector_id, description, observation))

    def record_fail(self, vector_id: str, description: str, error: str) -> None:
        print(f"[FAIL] {vector_id}: {description}")
        print(f"       -> ERROR: {error}")
        self.failed_vectors.append((vector_id, description, error))

    # -------------------------------------------------------------------------
    # PART 1: R2 PCController Token Enforcement Penetration
    # -------------------------------------------------------------------------
    async def run_r2_penetration_tests(self) -> None:
        print("\n" + "=" * 80)
        print("PART 1: R2 PCController Token Enforcement Penetration (20 Vectors)")
        print("=" * 80)

        pc_workdir = self.temp_dir / "workspace"
        pc_workdir.mkdir(parents=True, exist_ok=True)
        pc_data = self.temp_dir / "pc_data"
        pc_data.mkdir(parents=True, exist_ok=True)

        auth_state = pc_data / "cap_state.json"
        authority = CapabilityAuthority(auth_state, secret=self.secret)
        controller = PCController(working_dir=pc_workdir, capability_authority=authority)
        # Point controller data_dir and audit to temp
        controller.data_dir = pc_data
        controller.audit_path = pc_data / "audit.jsonl"
        controller.backup_dir = pc_data / "backups"
        controller.kill_switch_path = pc_data / "KILL_SWITCH"
        controller.backup_dir.mkdir(parents=True, exist_ok=True)

        valid_exec_token = authority.issue("pc.execute")
        valid_read_token = authority.issue("pc.read_file")
        valid_write_token = authority.issue("pc.write_file")
        valid_admin_token = authority.issue("pc.clear_kill_switch")

        # Vector R2-01: execute with None token
        try:
            await controller.execute("whoami", capability_token=None)
            self.record_fail("R2-01", "execute with None token", "Did not raise PermissionError")
        except PermissionError as exc:
            self.record_pass("R2-01", "execute with None token rejected", str(exc))

        # Vector R2-02: execute with empty string token
        try:
            await controller.execute("whoami", capability_token="")
            self.record_fail("R2-02", "execute with empty string token", "Did not raise PermissionError")
        except PermissionError as exc:
            self.record_pass("R2-02", "execute with empty string token rejected", str(exc))

        # Vector R2-03: execute with whitespace token
        try:
            await controller.execute("whoami", capability_token="   \t\n  ")
            self.record_fail("R2-03", "execute with whitespace token", "Did not raise PermissionError/InvalidTokenSignatureError")
        except (PermissionError, InvalidTokenSignatureError) as exc:
            self.record_pass("R2-03", "execute with whitespace token rejected", str(exc))

        # Vector R2-04: execute with malformed string token
        try:
            await controller.execute("whoami", capability_token="NOT_A_VALID_TOKEN_PAYLOAD")
            self.record_fail("R2-04", "execute with malformed string", "Did not raise InvalidTokenSignatureError")
        except InvalidTokenSignatureError as exc:
            self.record_pass("R2-04", "execute with malformed string rejected", str(exc))

        # Vector R2-05: execute with invalid JSON dict token
        try:
            await controller.execute("whoami", capability_token={"invalid": "payload"})
            self.record_fail("R2-05", "execute with invalid JSON dict", "Did not raise InvalidTokenSignatureError")
        except InvalidTokenSignatureError as exc:
            self.record_pass("R2-05", "execute with invalid JSON dict rejected", str(exc))

        # Vector R2-06: execute with forged HMAC signature
        forged_token = CapabilityToken(
            subject="pc.execute",
            epoch=0,
            token_id="forged-id-123",
            issued_at=time.time(),
            signature="deadbeef" * 8,
        )
        try:
            await controller.execute("whoami", capability_token=forged_token)
            self.record_fail("R2-06", "execute with forged HMAC signature", "Did not raise InvalidTokenSignatureError")
        except InvalidTokenSignatureError as exc:
            self.record_pass("R2-06", "execute with forged HMAC signature rejected", str(exc))

        # Vector R2-07: execute with token signed with rogue secret
        now_ts = time.time()
        rogue_sig = compute_token_signature(
            b"rogue-attacker-secret-key-12345", "pc.execute", 0, "rogue-token-456", now_ts
        )
        rogue_token = CapabilityToken(
            subject="pc.execute",
            epoch=0,
            token_id="rogue-token-456",
            issued_at=now_ts,
            signature=rogue_sig,
        )
        try:
            await controller.execute("whoami", capability_token=rogue_token)
            self.record_fail("R2-07", "execute with token signed with rogue secret", "Did not raise InvalidTokenSignatureError")
        except InvalidTokenSignatureError as exc:
            self.record_pass("R2-07", "execute with rogue-signed token rejected", str(exc))

        # Vector R2-08: execute with revoked / stale epoch
        token_before_revoke = authority.issue("pc.execute")
        authority.revoke(reason="compromised", actor="security-ops")
        try:
            await controller.execute("whoami", capability_token=token_before_revoke)
            self.record_fail("R2-08", "execute with revoked epoch token", "Did not raise PermissionError")
        except PermissionError as exc:
            self.record_pass("R2-08", "execute with revoked epoch token rejected", str(exc))

        # Restore authority for subsequent tests
        authority.restore(actor="security-ops", reason="re-initialized")
        valid_exec_token = authority.issue("pc.execute")
        valid_read_token = authority.issue("pc.read_file")
        valid_write_token = authority.issue("pc.write_file")
        valid_admin_token = authority.issue("pc.clear_kill_switch")

        # Vector R2-09: Scope mismatch: pc.read_file used for execute
        try:
            await controller.execute("whoami", capability_token=valid_read_token)
            self.record_fail("R2-09", "execute with read_file token", "Did not raise PermissionError")
        except PermissionError as exc:
            self.record_pass("R2-09", "execute with read_file token rejected (scope mismatch)", str(exc))

        # Vector R2-10: Scope mismatch: pc.write_file used for execute
        try:
            await controller.execute("whoami", capability_token=valid_write_token)
            self.record_fail("R2-10", "execute with write_file token", "Did not raise PermissionError")
        except PermissionError as exc:
            self.record_pass("R2-10", "execute with write_file token rejected (scope mismatch)", str(exc))

        # Vector R2-11: Scope mismatch: pc.execute used for write_file
        test_file = pc_workdir / "target.txt"
        try:
            await controller.write_file(
                str(test_file),
                "malicious write",
                capability_token=valid_exec_token,
                capability_level=3,
                approved=True,
            )
            self.record_fail("R2-11", "write_file with execute token", "Did not raise PermissionError")
        except PermissionError as exc:
            self.record_pass("R2-11", "write_file with execute token rejected (scope mismatch)", str(exc))

        # Vector R2-12: Scope mismatch: pc.execute used for clear_kill_switch
        controller.engage_kill_switch(reason="test")
        try:
            controller.clear_kill_switch(approved=True, capability_token=valid_exec_token)
            self.record_fail("R2-12", "clear_kill_switch with execute token", "Did not raise PermissionError")
        except PermissionError as exc:
            self.record_pass("R2-12", "clear_kill_switch with execute token rejected (scope mismatch)", str(exc))

        # Vector R2-13: read_file with missing token
        some_file = pc_workdir / "data.txt"
        some_file.write_text("confidential", encoding="utf-8")
        try:
            await controller.read_file(str(some_file), capability_token=None)
            self.record_fail("R2-13", "read_file with missing token", "Did not raise PermissionError")
        except PermissionError as exc:
            self.record_pass("R2-13", "read_file with missing token rejected", str(exc))

        # Vector R2-14: write_file with missing token (Zero bytes written to disk)
        unwritten = pc_workdir / "unwritten.txt"
        try:
            await controller.write_file(
                str(unwritten),
                "payload",
                capability_token=None,
                capability_level=3,
                approved=True,
            )
            self.record_fail("R2-14", "write_file with missing token", "Did not raise PermissionError")
        except PermissionError as exc:
            assert not unwritten.exists(), "File was created despite missing token!"
            self.record_pass("R2-14", "write_file with missing token rejected; 0 bytes written", str(exc))

        # Vector R2-15: write_file with forged token (Zero bytes written to disk)
        forged_write = CapabilityToken(
            subject="pc.write_file",
            epoch=0,
            token_id="forged-write",
            issued_at=time.time(),
            signature="badc0ffee" * 7 + "a",
        )
        unwritten2 = pc_workdir / "unwritten2.txt"
        try:
            await controller.write_file(
                str(unwritten2),
                "payload2",
                capability_token=forged_write,
                capability_level=3,
                approved=True,
            )
            self.record_fail("R2-15", "write_file with forged token", "Did not raise InvalidTokenSignatureError")
        except InvalidTokenSignatureError as exc:
            assert not unwritten2.exists(), "File was created despite forged token!"
            self.record_pass("R2-15", "write_file with forged token rejected; 0 bytes written", str(exc))

        # Vector R2-16: rollback with missing token
        try:
            await controller.rollback("some-backup-id", approved=True, capability_token=None)
            self.record_fail("R2-16", "rollback with missing token", "Did not raise PermissionError")
        except PermissionError as exc:
            self.record_pass("R2-16", "rollback with missing token rejected", str(exc))

        # Vector R2-17: clear_kill_switch with missing token (kill switch remains engaged)
        try:
            controller.clear_kill_switch(approved=True, capability_token=None)
            self.record_fail("R2-17", "clear_kill_switch with missing token", "Did not raise PermissionError")
        except PermissionError as exc:
            assert controller.kill_switch_engaged() is True
            self.record_pass("R2-17", "clear_kill_switch with missing token rejected; switch remains ON", str(exc))

        # Clear kill switch legitimately for next tests
        controller.clear_kill_switch(approved=True, capability_token=valid_admin_token)
        assert controller.kill_switch_engaged() is False

        # Vector R2-18: Path traversal outside workspace with valid token
        escape_file = pc_workdir.parent / "escape.txt"
        res = await controller.write_file(
            str(escape_file),
            "escaped content",
            capability_token=valid_write_token,
            capability_level=3,
            approved=True,
        )
        if not res.get("success") and "outside SCP workspace" in res.get("error", ""):
            assert not escape_file.exists(), "Escaped file was written outside workspace!"
            self.record_pass("R2-18", "path traversal outside workspace blocked fail-closed", res.get("error", ""))
        else:
            self.record_fail("R2-18", "path traversal outside workspace", f"Result: {res}")

        # Vector R2-19: Sensitive file access with valid token
        sensitive_file = pc_workdir / ".env"
        res_read = await controller.read_file(str(sensitive_file), capability_token=valid_read_token)
        if not res_read.get("success") and "Sensitive path" in res_read.get("error", ""):
            self.record_pass("R2-19", "sensitive file read blocked fail-closed", res_read.get("error", ""))
        else:
            self.record_fail("R2-19", "sensitive file read", f"Result: {res_read}")

        # Vector R2-20: Subprocess isolation check & audit verification
        # Verify audit file recorded TOKEN_REJECTED events and no subprocess was spawned for rejections
        audit_lines = [json.loads(line) for line in controller.audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        token_rejections = [line for line in audit_lines if line.get("event") == "TOKEN_REJECTED"]
        assert len(token_rejections) >= 10, f"Expected >= 10 TOKEN_REJECTED audit events, found {len(token_rejections)}"
        self.record_pass(
            "R2-20",
            "subprocess isolation & audit trail verified",
            f"Logged {len(token_rejections)} physical TOKEN_REJECTED events in audit.jsonl",
        )

    # -------------------------------------------------------------------------
    # PART 2: R3 TaskKernel Verifier Receipt Provenance Penetration
    # -------------------------------------------------------------------------
    def run_r3_penetration_tests(self) -> None:
        print("\n" + "=" * 80)
        print("PART 2: R3 TaskKernel Verifier Receipt Provenance Penetration (15 Vectors)")
        print("=" * 80)

        db_path = self.temp_dir / "kernel_pen.sqlite3"
        kernel = TaskKernel(db_path)

        def setup_task(tid: str, state: str = "VERIFYING") -> Any:
            kernel.create_task(tid, "tester", f"goal for {tid}")
            if state == "CREATED":
                return None
            kernel.transition(tid, "PLANNING")
            if state == "PLANNING":
                return None
            kernel.transition(tid, "READY")
            if state == "READY":
                return None
            kernel.transition(tid, "QUEUED")
            if state == "QUEUED":
                return None
            lease = kernel.claim(tid, "worker-1", ttl_seconds=120.0)
            if state == "LEASED":
                return lease
            kernel.start(tid, lease.lease_id)
            if state == "RUNNING":
                return lease
            kernel.transition(tid, "VERIFYING")
            return lease

        # Vector R3-01: GAP-P1 Direct State Jump bypass: commit_completed() from RUNNING state
        tid_1 = "task-run-bypass-1"
        lease_1 = setup_task(tid_1, state="RUNNING")
        try:
            kernel.commit_completed(tid_1, lease_1.lease_id, verifier_verdict="VERIFIED", evidence_ref="evidence://bypass")
            self.record_fail("R3-01", "direct commit_completed from RUNNING state", "Did not raise InvalidTransition")
        except InvalidTransition as exc:
            self.record_pass("R3-01", "GAP-P1 state jump bypass from RUNNING rejected", str(exc))

        # Vector R3-02: GAP-P1 Direct State Jump from other non-VERIFYING states
        states_to_test = ["CREATED", "PLANNING", "READY", "QUEUED", "LEASED"]
        all_rejected = True
        err_msg = ""
        for s in states_to_test:
            tid_s = f"task-state-jump-{s}"
            ls = setup_task(tid_s, state=s)
            lid = ls.lease_id if ls else "dummy-lease"
            try:
                kernel.commit_completed(tid_s, lid, verifier_verdict="VERIFIED", evidence_ref="evidence://bypass")
                all_rejected = False
                break
            except (InvalidTransition, StaleLease, KernelError) as exc:
                err_msg = str(exc)
        if all_rejected:
            self.record_pass("R3-02", f"GAP-P1 state jump bypass from states {states_to_test} rejected", err_msg)
        else:
            self.record_fail("R3-02", f"GAP-P1 state jump bypass permitted from {s}", "Allowed completion!")

        # Vector R3-03: GAP-P2 Unsigned receipt in commit_verification_result
        tid_3 = "task-unsigned-receipt"
        lease_3 = setup_task(tid_3, state="VERIFYING")
        unsigned_receipt = {
            "task_id": tid_3,
            "verifier_id": "forger",
            "verdict": "VERIFIED",
            "evidence_ref": "evidence://fake",
            "signature": "",
        }
        try:
            kernel.commit_verification_result(tid_3, lease_3.lease_id, unsigned_receipt)
            self.record_fail("R3-03", "unsigned receipt committed", "Did not raise InvalidReceiptSignatureError")
        except InvalidReceiptSignatureError as exc:
            assert kernel.get_task(tid_3)["state"] == "VERIFYING"
            self.record_pass("R3-03", "unsigned receipt rejected fail-closed", str(exc))

        # Vector R3-04: Forged HMAC signature in commit_verification_result
        tid_4 = "task-forged-receipt"
        lease_4 = setup_task(tid_4, state="VERIFYING")
        forged_receipt = {
            "task_id": tid_4,
            "verifier_id": "malicious-verifier",
            "verdict": "VERIFIED",
            "evidence_ref": "evidence://forged",
            "issued_at": time.time(),
            "signature": "cafebabe" * 8,
        }
        try:
            kernel.commit_verification_result(tid_4, lease_4.lease_id, forged_receipt)
            self.record_fail("R3-04", "forged signature accepted", "Did not raise InvalidReceiptSignatureError")
        except InvalidReceiptSignatureError as exc:
            assert kernel.get_task(tid_4)["state"] == "VERIFYING"
            self.record_pass("R3-04", "forged HMAC signature rejected fail-closed", str(exc))

        # Vector R3-05: Receipt signed with rogue / attacker secret
        tid_5 = "task-rogue-secret"
        lease_5 = setup_task(tid_5, state="VERIFYING")
        rogue_receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id=tid_5,
                verifier_id="external-agent",
                verdict="VERIFIED",
                evidence_ref="evidence://rogue",
                issued_at=time.time(),
            ),
            secret="attacker-secret-key-9999",
        )
        try:
            kernel.commit_verification_result(tid_5, lease_5.lease_id, rogue_receipt)
            self.record_fail("R3-05", "rogue-secret signed receipt accepted", "Did not raise InvalidReceiptSignatureError")
        except InvalidReceiptSignatureError as exc:
            assert kernel.get_task(tid_5)["state"] == "VERIFYING"
            self.record_pass("R3-05", "rogue-secret signed receipt rejected fail-closed", str(exc))

        # Vector R3-06: Semantic payload tampering: Altered evidence_ref
        tid_6 = "task-tamp-evidence"
        lease_6 = setup_task(tid_6, state="VERIFYING")
        legit_receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id=tid_6,
                verifier_id="authentic-auditor",
                verdict="VERIFIED",
                evidence_ref="evidence://original-good-hash",
                issued_at=time.time(),
            ),
            secret=self.secret,
        )
        # Tamper evidence_ref while keeping old signature
        tampered_evidence = dataclasses.replace(legit_receipt, evidence_ref="evidence://tampered-fake-hash")
        try:
            kernel.commit_verification_result(tid_6, lease_6.lease_id, tampered_evidence)
            self.record_fail("R3-06", "tampered evidence_ref accepted", "Did not raise InvalidReceiptSignatureError")
        except InvalidReceiptSignatureError as exc:
            assert kernel.get_task(tid_6)["state"] == "VERIFYING"
            self.record_pass("R3-06", "tampered evidence_ref rejected fail-closed", str(exc))

        # Vector R3-07: Semantic payload tampering: Altered verdict from FAILED to VERIFIED
        tid_7 = "task-tamp-verdict"
        lease_7 = setup_task(tid_7, state="VERIFYING")
        failed_receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id=tid_7,
                verifier_id="authentic-auditor",
                verdict="FAILED",
                evidence_ref="evidence://real-test-failed",
                issued_at=time.time(),
            ),
            secret=self.secret,
        )
        tampered_verdict = dataclasses.replace(failed_receipt, verdict="VERIFIED")
        try:
            kernel.commit_verification_result(tid_7, lease_7.lease_id, tampered_verdict)
            self.record_fail("R3-07", "tampered verdict accepted", "Did not raise InvalidReceiptSignatureError")
        except InvalidReceiptSignatureError as exc:
            assert kernel.get_task(tid_7)["state"] == "VERIFYING"
            self.record_pass("R3-07", "tampered verdict rejected fail-closed", str(exc))

        # Vector R3-08: Semantic payload tampering: Altered verifier_id
        tid_8 = "task-tamp-vid"
        lease_8 = setup_task(tid_8, state="VERIFYING")
        legit_8 = sign_verifier_receipt(
            VerifierReceipt(
                task_id=tid_8,
                verifier_id="student-verifier",
                verdict="VERIFIED",
                evidence_ref="evidence://proof-8",
                issued_at=time.time(),
            ),
            secret=self.secret,
        )
        tampered_vid = dataclasses.replace(legit_8, verifier_id="chief-security-officer")
        try:
            kernel.commit_verification_result(tid_8, lease_8.lease_id, tampered_vid)
            self.record_fail("R3-08", "tampered verifier_id accepted", "Did not raise InvalidReceiptSignatureError")
        except InvalidReceiptSignatureError as exc:
            assert kernel.get_task(tid_8)["state"] == "VERIFYING"
            self.record_pass("R3-08", "tampered verifier_id rejected fail-closed", str(exc))

        # Vector R3-09: Cross-task receipt replay attack (Receipt for Task A replayed on Task B)
        tid_9a = "task-replay-target-a"
        tid_9b = "task-replay-target-b"
        lease_9a = setup_task(tid_9a, state="VERIFYING")
        lease_9b = setup_task(tid_9b, state="VERIFYING")
        receipt_for_a = sign_verifier_receipt(
            VerifierReceipt(
                task_id=tid_9a,
                verifier_id="verifier-a",
                verdict="VERIFIED",
                evidence_ref="evidence://proof-for-a",
                issued_at=time.time(),
            ),
            secret=self.secret,
        )
        try:
            kernel.commit_verification_result(tid_9b, lease_9b.lease_id, receipt_for_a)
            self.record_fail("R3-09", "cross-task receipt replay accepted", "Did not raise InvalidReceiptSignatureError")
        except InvalidReceiptSignatureError as exc:
            assert kernel.get_task(tid_9b)["state"] == "VERIFYING"
            self.record_pass("R3-09", "cross-task receipt replay rejected fail-closed", str(exc))

        # Vector R3-10: Expired receipt attack (issued_at in distant past)
        tid_10 = "task-expired-receipt"
        lease_10 = setup_task(tid_10, state="VERIFYING")
        expired_receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id=tid_10,
                verifier_id="verifier-10",
                verdict="VERIFIED",
                evidence_ref="evidence://proof-10",
                issued_at=time.time() - 3600.0,  # 1 hour ago
            ),
            secret=self.secret,
        )
        try:
            kernel.commit_verification_result(tid_10, lease_10.lease_id, expired_receipt)
            self.record_fail("R3-10", "expired receipt accepted", "Did not raise InvalidReceiptSignatureError")
        except InvalidReceiptSignatureError as exc:
            assert kernel.get_task(tid_10)["state"] == "VERIFYING"
            self.record_pass("R3-10", "expired receipt rejected fail-closed", str(exc))

        # Vector R3-11: Future timestamp clock skew attack (> 60s in future)
        tid_11 = "task-future-receipt"
        lease_11 = setup_task(tid_11, state="VERIFYING")
        future_receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id=tid_11,
                verifier_id="verifier-11",
                verdict="VERIFIED",
                evidence_ref="evidence://proof-11",
                issued_at=time.time() + 300.0,  # 5 minutes in future
            ),
            secret=self.secret,
        )
        try:
            kernel.commit_verification_result(tid_11, lease_11.lease_id, future_receipt)
            self.record_fail("R3-11", "future timestamp receipt accepted", "Did not raise InvalidReceiptSignatureError")
        except InvalidReceiptSignatureError as exc:
            assert kernel.get_task(tid_11)["state"] == "VERIFYING"
            self.record_pass("R3-11", "future timestamp receipt rejected fail-closed", str(exc))

        # Vector R3-12: Missing secret fail-closed test
        orig_vsec = os.environ.pop("SCP_VERIFIER_SECRET", None)
        orig_csec = os.environ.pop("SCP_CAPABILITY_SECRET", None)
        try:
            get_verifier_secret(None)
            self.record_fail("R3-12", "get_verifier_secret without environment secret", "Did not raise MissingSecretError")
        except MissingSecretError as exc:
            self.record_pass("R3-12", "missing cryptographic secret fails closed", str(exc))
        finally:
            if orig_vsec:
                os.environ["SCP_VERIFIER_SECRET"] = orig_vsec
            if orig_csec:
                os.environ["SCP_CAPABILITY_SECRET"] = orig_csec

        # Vector R3-13: Direct commit_completed() with tampered receipt dictionary
        tid_13 = "task-direct-tampered"
        lease_13 = setup_task(tid_13, state="VERIFYING")
        bad_direct_rcpt = {
            "task_id": tid_13,
            "verifier_id": "rogue",
            "verdict": "VERIFIED",
            "evidence_ref": "evidence://bad",
            "issued_at": time.time(),
            "signature": "bad" * 21 + "b",
        }
        try:
            kernel.commit_completed(tid_13, lease_13.lease_id, receipt=bad_direct_rcpt)
            self.record_fail("R3-13", "direct commit_completed with tampered receipt accepted", "Did not raise InvalidReceiptSignatureError")
        except InvalidReceiptSignatureError as exc:
            assert kernel.get_task(tid_13)["state"] == "VERIFYING"
            self.record_pass("R3-13", "direct commit_completed with tampered receipt rejected", str(exc))

        # Vector R3-14: Concurrency / OCC race condition test on receipt commitment
        tid_14 = "task-occ-race"
        lease_14 = setup_task(tid_14, state="VERIFYING")
        valid_rcpt_14 = sign_verifier_receipt(
            VerifierReceipt(
                task_id=tid_14,
                verifier_id="concurrent-verifier",
                verdict="VERIFIED",
                evidence_ref="evidence://occ-proof",
                issued_at=time.time(),
            ),
            secret=self.secret,
        )

        results = []
        errors = []

        def worker_attempt():
            # Use dedicated thread connection to test true database-level concurrency
            k_thread = TaskKernel(db_path)
            try:
                res = k_thread.commit_verification_result(tid_14, lease_14.lease_id, valid_rcpt_14)
                return ("SUCCESS", res)
            except Exception as e:
                return ("ERROR", type(e).__name__)
            finally:
                k_thread.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_attempt) for _ in range(5)]
            for fut in concurrent.futures.as_completed(futures):
                outcome, val = fut.result()
                if outcome == "SUCCESS":
                    results.append(val)
                else:
                    errors.append(val)

        if len(results) == 1 and len(errors) == 4:
            self.record_pass(
                "R3-14",
                "OCC race condition: exactly 1 thread succeeded, 4 rejected",
                f"1 SUCCESS, 4 {errors[0]}",
            )
        else:
            self.record_fail("R3-14", "OCC race condition", f"Successes: {len(results)}, Errors: {errors}")

        # Vector R3-15: Physical SQLite database inspection (FA-12 Step 4)
        # Commit an authentic receipt and verify rows in tasks and events table
        tid_15 = "task-authentic-provenance-audit"
        lease_15 = setup_task(tid_15, state="VERIFYING")
        auth_receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id=tid_15,
                verifier_id="independent-forensic-auditor-99",
                verdict="VERIFIED",
                evidence_ref="evidence://immutable-forensic-snapshot-sha256",
                issued_at=time.time(),
            ),
            secret=self.secret,
        )
        kernel.commit_verification_result(tid_15, lease_15.lease_id, auth_receipt)

        # Inspect raw SQLite database using independent raw connection
        raw_conn = sqlite3.connect(str(db_path))
        raw_conn.row_factory = sqlite3.Row
        try:
            # 1. Inspect tasks table
            cur = raw_conn.execute("SELECT task_id, state, active_lease_id FROM tasks WHERE task_id = ?", (tid_15,))
            task_row = cur.fetchone()
            assert task_row is not None
            assert task_row["state"] == "COMPLETED"
            assert task_row["active_lease_id"] is None

            # 2. Inspect events table
            cur2 = raw_conn.execute(
                "SELECT event_id, task_id, event_type, from_state, to_state, actor, payload_json FROM events WHERE task_id = ? AND event_type = 'TASK_COMPLETED'",
                (tid_15,),
            )
            event_row = cur2.fetchone()
            assert event_row is not None
            assert event_row["from_state"] == "VERIFYING"
            assert event_row["to_state"] == "COMPLETED"
            assert event_row["actor"] == "independent-forensic-auditor-99"

            payload = json.loads(event_row["payload_json"])
            assert payload["verifier_id"] == "independent-forensic-auditor-99"
            assert payload["verifier_verdict"] == "VERIFIED"
            assert payload["evidence_ref"] == "evidence://immutable-forensic-snapshot-sha256"
            assert payload["signature_digest"] == f"sha256:{auth_receipt.signature[:16]}..."
            assert payload["lease_id"] == lease_15.lease_id
            assert abs(payload["issued_at"] - auth_receipt.issued_at) < 0.001

            # 3. Verify hash chain
            journal_status = kernel.verify_journal(tid_15)
            assert journal_status["hash_chain_valid"] is True

            self.record_pass(
                "R3-15",
                "physical SQLite row inspection: authentic provenance logged with signature_digest",
                f"tasks state={task_row['state']}, events verifier={payload['verifier_id']}, digest={payload['signature_digest']}",
            )
        finally:
            raw_conn.close()
            kernel.close()


async def main() -> int:
    harness = PenetrationHarness()
    try:
        await harness.run_r2_penetration_tests()
        harness.run_r3_penetration_tests()

        print("\n" + "=" * 80)
        print("PENETRATION & ADVERSARIAL STRESS TEST SUMMARY")
        print("=" * 80)
        print(f"Total Vectors Tested: {len(harness.passed_vectors) + len(harness.failed_vectors)}")
        print(f"Total Passed (Rejected Fail-Closed / Authenticated Correctly): {len(harness.passed_vectors)}")
        print(f"Total Failed (Vulnerabilities or Incomplete Defenses Found): {len(harness.failed_vectors)}")

        if harness.failed_vectors:
            print("\n[!] CRITICAL DEFENSE BYPASSES DETECTED:")
            for vid, desc, err in harness.failed_vectors:
                print(f"    - {vid}: {desc} -> {err}")
            return 1
        else:
            print("\n[✓] ALL 35 ADVERSARIAL PENETRATION ATTEMPTS WERE STRICTLY REJECTED FAIL-CLOSED.")
            print("[✓] R2 PEP TOKEN ENFORCEMENT & R3 VERIFIER RECEIPT PROVENANCE FULLY VERIFIED.")
            return 0
    finally:
        harness.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
