"""Unit and regression tests for R3: Cryptographic Verifier Receipt Provenance and Kernel Verification.

Tests verify:
1. VerifierReceipt construction, serialization, and deterministic canonical representation.
2. HMAC-SHA256 signing and constant-time verification using get_verifier_secret.
3. Fail-closed rejection of unsigned, forged, tampered, expired, and future receipts.
4. TaskKernel.commit_verification_result strict cryptographic receipt enforcement.
5. GAP-P1 closure: strict rejection of RUNNING -> COMPLETED state machine bypass.
6. GAP-P2 closure: authentic verifier_id and signature_digest recorded in SQLite event journal.
7. Rejection of cross-task receipt replay.
8. Support for both VerifierReceipt dataclass instances and valid receipt dictionaries.
9. Journal hash-chain integrity preservation across verified completions.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Any

import pytest

from scp.core.verifier_receipt import (
    InvalidReceiptSignatureError,
    MissingSecretError,
    VerifierReceipt,
    canonical_receipt_bytes,
    get_verifier_secret,
    sign_verifier_receipt,
    verify_verifier_receipt,
)
from scp.task_kernel import InvalidTransition, StaleLease, TaskKernel


@pytest.fixture
def fixture_secret(monkeypatch):
    """Ensure a fixed verifier secret is available for deterministic tests."""
    secret = "test-verifier-secret-key-32-bytes-long!"
    monkeypatch.setenv("SCP_VERIFIER_SECRET", secret)
    monkeypatch.setenv("SCP_CAPABILITY_SECRET", secret)
    return secret


def _setup_task_in_verifying(
    kernel: TaskKernel,
    task_id: str,
    owner: str = "test-owner",
    worker: str = "test-worker",
) -> Any:
    """Helper to transition a task to VERIFYING state and return active lease."""
    kernel.create_task(task_id, owner, f"task goal {task_id}")
    kernel.transition(task_id, "PLANNING")
    kernel.transition(task_id, "READY")
    kernel.transition(task_id, "QUEUED")
    lease = kernel.claim(task_id, worker, ttl_seconds=60.0)
    kernel.start(task_id, lease.lease_id)
    kernel.transition(task_id, "VERIFYING")
    return lease


# =========================================================================
# 1. VerifierReceipt Construction and Canonical Serialization Tests
# =========================================================================

def test_verifier_receipt_dataclass_fields_and_defaults():
    """VerifierReceipt maintains immutability and expected field defaults."""
    r = VerifierReceipt(
        task_id="t-1",
        verifier_id="v-reality-1",
        verdict="VERIFIED",
        evidence_ref="evidence://proof-1",
        issued_at=1700000000.123456,
    )
    assert r.task_id == "t-1"
    assert r.verifier_id == "v-reality-1"
    assert r.verdict == "VERIFIED"
    assert r.evidence_ref == "evidence://proof-1"
    assert r.issued_at == 1700000000.123456
    assert r.signature == ""
    assert r.attempt_id is None

    d = r.to_dict()
    assert d["task_id"] == "t-1"
    assert d["signature"] == ""


def test_canonical_receipt_bytes_deterministic():
    """Canonical receipt bytes format: task_id:verifier_id:verdict:evidence_ref:issued_at:.6f."""
    r = VerifierReceipt(
        task_id="task-42",
        verifier_id="verifier-judge-v1",
        verdict="VERIFIED",
        evidence_ref="evidence://sha256-hash",
        issued_at=1700000000.5,
    )
    expected = b"task-42:verifier-judge-v1:VERIFIED:evidence://sha256-hash:1700000000.500000"
    assert canonical_receipt_bytes(r) == expected

    # Also accepts dict representation
    r_dict = r.to_dict()
    assert canonical_receipt_bytes(r_dict) == expected


def test_canonical_receipt_bytes_rejects_missing_fields():
    """Canonical serialization fails closed if mandatory fields are blank."""
    with pytest.raises(InvalidReceiptSignatureError, match="task_id is required"):
        canonical_receipt_bytes({"task_id": "", "verifier_id": "v", "verdict": "VERIFIED", "evidence_ref": "ref", "issued_at": 100})

    with pytest.raises(InvalidReceiptSignatureError, match="verifier_id is required"):
        canonical_receipt_bytes({"task_id": "t", "verifier_id": "", "verdict": "VERIFIED", "evidence_ref": "ref", "issued_at": 100})

    with pytest.raises(InvalidReceiptSignatureError, match="verdict is required"):
        canonical_receipt_bytes({"task_id": "t", "verifier_id": "v", "verdict": "", "evidence_ref": "ref", "issued_at": 100})

    with pytest.raises(InvalidReceiptSignatureError, match="evidence_ref is required"):
        canonical_receipt_bytes({"task_id": "t", "verifier_id": "v", "verdict": "VERIFIED", "evidence_ref": "", "issued_at": 100})


# =========================================================================
# 2. Cryptographic Signing & Verification Roundtrip Tests
# =========================================================================

def test_sign_and_verify_roundtrip(fixture_secret):
    """Authentic signed receipt verifies successfully."""
    r = VerifierReceipt(
        task_id="task-auth-1",
        verifier_id="reality-verifier-v1",
        verdict="VERIFIED",
        evidence_ref="evidence://valid-audit-trail",
        issued_at=time.time(),
    )
    signed = sign_verifier_receipt(r, fixture_secret)
    assert signed.signature != ""
    assert len(signed.signature) == 64  # SHA256 hex string

    # Verification passes
    assert verify_verifier_receipt(signed, fixture_secret, task_id="task-auth-1") is True


def test_sign_and_verify_from_dict(fixture_secret):
    """sign_verifier_receipt accepts dict and returns signed VerifierReceipt."""
    raw = {
        "task_id": "task-dict-1",
        "verifier_id": "rag-verifier",
        "verdict": "VERIFIED",
        "evidence_ref": "evidence://ref-dict",
        "issued_at": time.time(),
    }
    signed = sign_verifier_receipt(raw, fixture_secret)
    assert isinstance(signed, VerifierReceipt)
    assert signed.signature != ""
    assert verify_verifier_receipt(asdict(signed), fixture_secret, task_id="task-dict-1") is True


# =========================================================================
# 3. Forgery & Tampering Rejection Tests (Fail-Closed)
# =========================================================================

def test_unsigned_receipt_rejected(fixture_secret):
    """Receipt with missing or empty signature raises InvalidReceiptSignatureError."""
    r = VerifierReceipt(
        task_id="task-unsig-1",
        verifier_id="rogue-worker",
        verdict="VERIFIED",
        evidence_ref="evidence://fake",
        issued_at=time.time(),
        signature="",
    )
    with pytest.raises(InvalidReceiptSignatureError, match="unsigned"):
        verify_verifier_receipt(r, fixture_secret, task_id="task-unsig-1")


def test_tampered_signature_rejected(fixture_secret):
    """Modified signature bits fail HMAC comparison."""
    r = VerifierReceipt(
        task_id="task-tamp-sig",
        verifier_id="legit-verifier",
        verdict="VERIFIED",
        evidence_ref="evidence://real",
        issued_at=time.time(),
    )
    signed = sign_verifier_receipt(r, fixture_secret)
    # Flip first character of hex signature
    bad_sig = ("0" if signed.signature[0] != "0" else "1") + signed.signature[1:]
    tampered = VerifierReceipt(
        task_id=signed.task_id,
        verifier_id=signed.verifier_id,
        verdict=signed.verdict,
        evidence_ref=signed.evidence_ref,
        issued_at=signed.issued_at,
        signature=bad_sig,
    )
    with pytest.raises(InvalidReceiptSignatureError, match="tampered receipt"):
        verify_verifier_receipt(tampered, fixture_secret, task_id="task-tamp-sig")


def test_tampered_verdict_rejected(fixture_secret):
    """Forging verdict from non-VERIFIED or tampering signed verdict fails verification."""
    r = VerifierReceipt(
        task_id="task-tamp-verd",
        verifier_id="legit-verifier",
        verdict="CONTRADICTED",
        evidence_ref="evidence://real",
        issued_at=time.time(),
    )
    signed = sign_verifier_receipt(r, fixture_secret)
    # Attacker flips verdict to VERIFIED while keeping old signature
    tampered = VerifierReceipt(
        task_id=signed.task_id,
        verifier_id=signed.verifier_id,
        verdict="VERIFIED",
        evidence_ref=signed.evidence_ref,
        issued_at=signed.issued_at,
        signature=signed.signature,
    )
    with pytest.raises(InvalidReceiptSignatureError, match="tampered receipt"):
        verify_verifier_receipt(tampered, fixture_secret, task_id="task-tamp-verd")


def test_tampered_evidence_ref_rejected(fixture_secret):
    """Altering evidence_ref invalidates canonical bytes and signature."""
    r = VerifierReceipt(
        task_id="task-tamp-ev",
        verifier_id="legit-verifier",
        verdict="VERIFIED",
        evidence_ref="evidence://original-good-evidence",
        issued_at=time.time(),
    )
    signed = sign_verifier_receipt(r, fixture_secret)
    tampered = VerifierReceipt(
        task_id=signed.task_id,
        verifier_id=signed.verifier_id,
        verdict=signed.verdict,
        evidence_ref="evidence://fake-tampered-evidence",
        issued_at=signed.issued_at,
        signature=signed.signature,
    )
    with pytest.raises(InvalidReceiptSignatureError, match="tampered receipt"):
        verify_verifier_receipt(tampered, fixture_secret, task_id="task-tamp-ev")


def test_tampered_verifier_id_rejected(fixture_secret):
    """Substituting verifier_id invalidates canonical bytes and signature."""
    r = VerifierReceipt(
        task_id="task-tamp-vid",
        verifier_id="independent-auditor",
        verdict="VERIFIED",
        evidence_ref="evidence://original",
        issued_at=time.time(),
    )
    signed = sign_verifier_receipt(r, fixture_secret)
    tampered = VerifierReceipt(
        task_id=signed.task_id,
        verifier_id="self-appointed-rogue",
        verdict=signed.verdict,
        evidence_ref=signed.evidence_ref,
        issued_at=signed.issued_at,
        signature=signed.signature,
    )
    with pytest.raises(InvalidReceiptSignatureError, match="tampered receipt"):
        verify_verifier_receipt(tampered, fixture_secret, task_id="task-tamp-vid")


def test_cross_task_replay_rejected(fixture_secret):
    """Receipt issued for task-A submitted to verify task-B fails closed."""
    r_task_a = VerifierReceipt(
        task_id="task-A",
        verifier_id="auditor-1",
        verdict="VERIFIED",
        evidence_ref="evidence://task-a-proof",
        issued_at=time.time(),
    )
    signed_a = sign_verifier_receipt(r_task_a, fixture_secret)
    with pytest.raises(InvalidReceiptSignatureError, match="does not match expected task_id"):
        verify_verifier_receipt(signed_a, fixture_secret, task_id="task-B")


def test_expired_and_future_timestamp_rejected(fixture_secret):
    """Receipts with future (>60s) or expired (>max_skew) timestamps are rejected."""
    now = time.time()
    # Future timestamp
    r_future = VerifierReceipt(
        task_id="task-future",
        verifier_id="v1",
        verdict="VERIFIED",
        evidence_ref="evidence://f",
        issued_at=now + 120.0,
    )
    signed_future = sign_verifier_receipt(r_future, fixture_secret)
    with pytest.raises(InvalidReceiptSignatureError, match="in the future"):
        verify_verifier_receipt(signed_future, fixture_secret, task_id="task-future")

    # Expired timestamp (> 300s skew)
    r_expired = VerifierReceipt(
        task_id="task-expired",
        verifier_id="v1",
        verdict="VERIFIED",
        evidence_ref="evidence://e",
        issued_at=now - 500.0,
    )
    signed_expired = sign_verifier_receipt(r_expired, fixture_secret)
    with pytest.raises(InvalidReceiptSignatureError, match="expired"):
        verify_verifier_receipt(signed_expired, fixture_secret, task_id="task-expired", max_skew_seconds=300.0)


def test_missing_secret_fails_closed(monkeypatch):
    """Missing or empty secret environment variables raise MissingSecretError."""
    monkeypatch.delenv("SCP_VERIFIER_SECRET", raising=False)
    monkeypatch.delenv("SCP_CAPABILITY_SECRET", raising=False)
    with pytest.raises(MissingSecretError, match="missing or empty"):
        get_verifier_secret(None)


# =========================================================================
# 4. TaskKernel Enforcement & Journal Provenance Tests
# =========================================================================

def test_kernel_commit_verification_result_authentic_receipt(tmp_path, fixture_secret):
    """TaskKernel accepts an authentic signed receipt and commits task to COMPLETED."""
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        task_id = "task-complete-legit-1"
        lease = _setup_task_in_verifying(kernel, task_id)

        receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id=task_id,
                verifier_id="reality-judge-v2",
                verdict="VERIFIED",
                evidence_ref="evidence://audit/receipt-hash-42",
                issued_at=time.time(),
            ),
            fixture_secret,
        )

        completed = kernel.commit_verification_result(task_id, lease.lease_id, receipt)
        assert completed["state"] == "COMPLETED"
        assert completed["active_lease_id"] is None

        # Verify GAP-P2 journal closure: authentic verifier_id and signature_digest
        events = kernel.get_events(task_id)
        completion_events = [e for e in events if e["type"] == "TASK_COMPLETED"]
        assert len(completion_events) == 1
        comp_event = completion_events[0]
        assert comp_event["actor"] == "reality-judge-v2"
        payload = json.loads(comp_event["payload_json"])
        assert payload["verifier_id"] == "reality-judge-v2"
        assert payload["signature_digest"] == f"sha256:{receipt.signature[:16]}..."
        assert payload["evidence_ref"] == "evidence://audit/receipt-hash-42"
        assert payload["verifier_verdict"] == "VERIFIED"

        # Journal hash chain integrity check
        journal = kernel.verify_journal(task_id)
        assert journal["hash_chain_valid"] is True
    finally:
        kernel.close()


def test_kernel_commit_verification_result_dict_input(tmp_path, fixture_secret):
    """TaskKernel accepts signed receipt passed as a dictionary."""
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        task_id = "task-dict-commit-1"
        lease = _setup_task_in_verifying(kernel, task_id)

        receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id=task_id,
                verifier_id="hands-kernel-result-verifier-v1",
                verdict="VERIFIED",
                evidence_ref="evidence://hands/action-proof",
                issued_at=time.time(),
            ),
            fixture_secret,
        )

        completed = kernel.commit_verification_result(task_id, lease.lease_id, receipt.to_dict())
        assert completed["state"] == "COMPLETED"
    finally:
        kernel.close()


def test_kernel_commit_verification_result_rejects_unsigned_receipt(tmp_path, fixture_secret):
    """TaskKernel strictly rejects unsigned receipt dictionary (closing forgery exploit)."""
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        task_id = "task-forgery-reject-1"
        lease = _setup_task_in_verifying(kernel, task_id)

        # Worker manufactures fake receipt dictionary without cryptographic signature
        forged = {
            "task_id": task_id,
            "verifier_id": "malicious-worker-fake-verifier",
            "verdict": "VERIFIED",
            "evidence_ref": "fake://attacker-controlled-evidence",
        }

        with pytest.raises(InvalidReceiptSignatureError, match="unsigned"):
            kernel.commit_verification_result(task_id, lease.lease_id, forged)

        # Ensure task state was NOT modified
        assert kernel.get_task(task_id)["state"] == "VERIFYING"
        events = kernel.get_events(task_id)
        assert not any(e["type"] == "TASK_COMPLETED" for e in events)
    finally:
        kernel.close()


def test_kernel_commit_verification_result_rejects_tampered_signature(tmp_path, fixture_secret):
    """TaskKernel strictly rejects receipt with forged or modified signature."""
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        task_id = "task-tampered-sig-1"
        lease = _setup_task_in_verifying(kernel, task_id)

        tampered = {
            "task_id": task_id,
            "verifier_id": "trusted-verifier",
            "verdict": "VERIFIED",
            "evidence_ref": "evidence://proof",
            "issued_at": time.time(),
            "signature": "deadbeef" * 8,  # Bogus signature
        }

        with pytest.raises(InvalidReceiptSignatureError, match="tampered receipt"):
            kernel.commit_verification_result(task_id, lease.lease_id, tampered)

        assert kernel.get_task(task_id)["state"] == "VERIFYING"
    finally:
        kernel.close()


def test_kernel_commit_verification_result_rejects_mismatched_task_id(tmp_path, fixture_secret):
    """Receipt generated for task-X cannot be replayed to complete task-Y."""
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        task_a = "task-replay-A"
        task_b = "task-replay-B"
        _lease_a = _setup_task_in_verifying(kernel, task_a)
        lease_b = _setup_task_in_verifying(kernel, task_b)

        # Receipt validly issued for task-A
        receipt_a = sign_verifier_receipt(
            VerifierReceipt(
                task_id=task_a,
                verifier_id="auditor-1",
                verdict="VERIFIED",
                evidence_ref="evidence://proof-a",
                issued_at=time.time(),
            ),
            fixture_secret,
        )

        # Attempt to submit receipt_a to task-B
        with pytest.raises(InvalidReceiptSignatureError, match="does not match expected task_id"):
            kernel.commit_verification_result(task_b, lease_b.lease_id, receipt_a)

        assert kernel.get_task(task_b)["state"] == "VERIFYING"
    finally:
        kernel.close()


# =========================================================================
# 5. GAP-P1 Closure: Reject RUNNING -> COMPLETED State Machine Bypass
# =========================================================================

def test_gap_p1_running_to_completed_bypass_strictly_rejected(tmp_path, fixture_secret):
    """Direct transition from RUNNING -> COMPLETED without VERIFYING raises InvalidTransition."""
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        task_id = "task-gap-p1-bypass"
        kernel.create_task(task_id, "owner-1", "test bypass")
        kernel.transition(task_id, "PLANNING")
        kernel.transition(task_id, "READY")
        kernel.transition(task_id, "QUEUED")
        lease = kernel.claim(task_id, "worker-1", ttl_seconds=60.0)
        kernel.start(task_id, lease.lease_id)
        # Task state is now RUNNING! Not VERIFYING!
        assert kernel.get_task(task_id)["state"] == "RUNNING"

        receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id=task_id,
                verifier_id="verifier-1",
                verdict="VERIFIED",
                evidence_ref="evidence://proof",
                issued_at=time.time(),
            ),
            fixture_secret,
        )

        # Attempt 1: commit_verification_result from RUNNING must fail
        with pytest.raises(InvalidTransition, match="RUNNING->COMPLETED"):
            kernel.commit_verification_result(task_id, lease.lease_id, receipt)

        # Attempt 2: commit_completed from RUNNING must fail
        with pytest.raises(InvalidTransition, match="RUNNING->COMPLETED"):
            kernel.commit_completed(task_id, lease.lease_id, "VERIFIED", "evidence://proof")

        # Task remains safely in RUNNING
        assert kernel.get_task(task_id)["state"] == "RUNNING"
    finally:
        kernel.close()


def test_gap_p1_all_non_verifying_states_reject_completion(tmp_path, fixture_secret):
    """Every state other than VERIFYING must reject commit_completed."""
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        task_id = "task-non-verifying-states"
        kernel.create_task(task_id, "owner-1", "test all states")

        # In CREATED
        with pytest.raises((InvalidTransition, StaleLease)):
            kernel.commit_completed(task_id, "lease-dummy", "VERIFIED", "evidence://ref")

        kernel.transition(task_id, "PLANNING")
        with pytest.raises((InvalidTransition, StaleLease)):
            kernel.commit_completed(task_id, "lease-dummy", "VERIFIED", "evidence://ref")

        kernel.transition(task_id, "READY")
        with pytest.raises((InvalidTransition, StaleLease)):
            kernel.commit_completed(task_id, "lease-dummy", "VERIFIED", "evidence://ref")

        kernel.transition(task_id, "QUEUED")
        with pytest.raises((InvalidTransition, StaleLease)):
            kernel.commit_completed(task_id, "lease-dummy", "VERIFIED", "evidence://ref")
    finally:
        kernel.close()


# =========================================================================
# 6. Direct commit_completed with Receipt & Tamper Detection
# =========================================================================

def test_commit_completed_with_valid_signed_receipt(tmp_path, fixture_secret):
    """commit_completed() called with receipt keyword argument records authentic provenance."""
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        task_id = "task-direct-receipt-1"
        lease = _setup_task_in_verifying(kernel, task_id)

        receipt = sign_verifier_receipt(
            VerifierReceipt(
                task_id=task_id,
                verifier_id="auditor-omega",
                verdict="VERIFIED",
                evidence_ref="evidence://audit-omega-proof",
                issued_at=time.time(),
            ),
            fixture_secret,
        )

        completed = kernel.commit_completed(task_id, lease.lease_id, receipt=receipt)
        assert completed["state"] == "COMPLETED"

        events = kernel.get_events(task_id)
        comp_event = next(e for e in events if e["type"] == "TASK_COMPLETED")
        assert comp_event["actor"] == "auditor-omega"
        payload = json.loads(comp_event["payload_json"])
        assert payload["verifier_id"] == "auditor-omega"
        assert payload["signature_digest"] == f"sha256:{receipt.signature[:16]}..."
    finally:
        kernel.close()


def test_commit_completed_with_tampered_receipt_rejected(tmp_path, fixture_secret):
    """commit_completed() called with tampered receipt fails closed."""
    db_file = tmp_path / "kernel.sqlite3"
    kernel = TaskKernel(db_file)
    try:
        task_id = "task-direct-tampered-1"
        lease = _setup_task_in_verifying(kernel, task_id)

        bad_receipt = {
            "task_id": task_id,
            "verifier_id": "forged-auditor",
            "verdict": "VERIFIED",
            "evidence_ref": "evidence://fake",
            "issued_at": time.time(),
            "signature": "bad_sig_12345",
        }

        with pytest.raises(InvalidReceiptSignatureError, match="tampered receipt"):
            kernel.commit_completed(task_id, lease.lease_id, receipt=bad_receipt)

        assert kernel.get_task(task_id)["state"] == "VERIFYING"
    finally:
        kernel.close()
