"""Cryptographic Verifier Receipt infrastructure for TaskKernel verification provenance (R3/GAP-14)."""
from __future__ import annotations

import dataclasses
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Any

from scp.task_kernel import KernelError


class MissingSecretError(RuntimeError):
    """Raised when neither SCP_VERIFIER_SECRET nor SCP_CAPABILITY_SECRET is configured."""
    pass


class InvalidReceiptSignatureError(KernelError, PermissionError):
    """Raised when a verifier receipt signature is missing, forged, tampered, or invalid."""
    pass


@dataclass(frozen=True)
class VerifierReceipt:
    task_id: str
    verifier_id: str
    verdict: str
    evidence_ref: str
    issued_at: float
    signature: str = ""
    attempt_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "verifier_id": self.verifier_id,
            "verdict": self.verdict,
            "evidence_ref": self.evidence_ref,
            "issued_at": self.issued_at,
            "signature": self.signature,
            "attempt_id": self.attempt_id,
        }


def get_verifier_secret(secret: str | bytes | None = None) -> bytes:
    """Resolve and return cryptographic secret bytes for verifier receipts.

    Priority:
    1. Explicit secret argument (if provided and non-empty)
    2. SCP_VERIFIER_SECRET environment variable
    3. SCP_CAPABILITY_SECRET environment variable
    Raises MissingSecretError if none is set or if empty.
    """
    if secret is not None:
        if isinstance(secret, bytes):
            if not secret:
                raise MissingSecretError("Provided secret bytes must not be empty.")
            return secret
        val = str(secret).strip()
        if not val:
            raise MissingSecretError("Provided secret string must not be empty.")
        return val.encode()

    env_secret = os.environ.get("SCP_VERIFIER_SECRET") or os.environ.get("SCP_CAPABILITY_SECRET")
    if not env_secret or not env_secret.strip():
        raise MissingSecretError(
            "SCP_VERIFIER_SECRET or SCP_CAPABILITY_SECRET environment variable is missing or empty. "
            "A cryptographic secret is required to sign and verify receipts (R3/GAP-14)."
        )
    return env_secret.strip().encode()


def canonical_receipt_bytes(receipt: VerifierReceipt | dict[str, Any]) -> bytes:
    """Construct deterministic canonical bytes for signing and verifying a receipt.

    Format: task_id:verifier_id:verdict:evidence_ref:issued_at:.6f
    """
    if isinstance(receipt, dict):
        task_id = str(receipt.get("task_id", "")).strip()
        verifier_id = str(receipt.get("verifier_id", "")).strip()
        verdict = str(receipt.get("verdict", "")).strip()
        evidence_ref = str(receipt.get("evidence_ref", "")).strip()
        try:
            issued_at = float(receipt.get("issued_at", 0.0))
        except (TypeError, ValueError):
            raise InvalidReceiptSignatureError("Invalid issued_at timestamp in receipt") from None
    elif isinstance(receipt, VerifierReceipt):
        task_id = str(receipt.task_id).strip()
        verifier_id = str(receipt.verifier_id).strip()
        verdict = str(receipt.verdict).strip()
        evidence_ref = str(receipt.evidence_ref).strip()
        try:
            issued_at = float(receipt.issued_at)
        except (TypeError, ValueError):
            raise InvalidReceiptSignatureError("Invalid issued_at timestamp in receipt") from None
    else:
        raise InvalidReceiptSignatureError("receipt must be a VerifierReceipt or dict")

    if not task_id:
        raise InvalidReceiptSignatureError("receipt task_id is required")
    if not verifier_id:
        raise InvalidReceiptSignatureError("receipt verifier_id is required")
    if not verdict:
        raise InvalidReceiptSignatureError("receipt verdict is required")
    if not evidence_ref:
        raise InvalidReceiptSignatureError("receipt evidence_ref is required")

    return f"{task_id}:{verifier_id}:{verdict}:{evidence_ref}:{issued_at:.6f}".encode()


def sign_verifier_receipt(
    receipt: VerifierReceipt | dict[str, Any],
    secret: str | bytes | None = None,
) -> VerifierReceipt:
    """Compute HMAC-SHA256 signature for VerifierReceipt and return signed VerifierReceipt."""
    sec = get_verifier_secret(secret)
    if isinstance(receipt, dict):
        task_id = str(receipt.get("task_id", "")).strip()
        verifier_id = str(receipt.get("verifier_id", "")).strip()
        verdict = str(receipt.get("verdict", "")).strip()
        evidence_ref = str(receipt.get("evidence_ref", "")).strip()
        issued_at = float(receipt.get("issued_at", 0.0)) if receipt.get("issued_at") else time.time()
        attempt_id = receipt.get("attempt_id")
        receipt_obj = VerifierReceipt(
            task_id=task_id,
            verifier_id=verifier_id,
            verdict=verdict,
            evidence_ref=evidence_ref,
            issued_at=issued_at,
            attempt_id=attempt_id,
        )
    elif isinstance(receipt, VerifierReceipt):
        issued_at = receipt.issued_at if receipt.issued_at else time.time()
        if issued_at != receipt.issued_at:
            receipt_obj = dataclasses.replace(receipt, issued_at=issued_at)
        else:
            receipt_obj = receipt
    else:
        raise InvalidReceiptSignatureError("receipt must be a VerifierReceipt or dict")

    canonical = canonical_receipt_bytes(receipt_obj)
    signature = hmac.new(sec, canonical, hashlib.sha256).hexdigest()
    return dataclasses.replace(receipt_obj, signature=signature)


def verify_verifier_receipt(
    receipt: VerifierReceipt | dict[str, Any],
    secret: str | bytes | None = None,
    *,
    task_id: str | None = None,
    max_skew_seconds: float = 300.0,
) -> bool:
    """Verify HMAC-SHA256 signature of a receipt using constant-time comparison.

    Raises InvalidReceiptSignatureError fail-closed if:
    - receipt is missing, empty, or invalid type
    - task_id is mismatched (if task_id provided)
    - verifier_id or evidence_ref is missing
    - verdict != 'VERIFIED'
    - signature is missing or empty
    - timestamp is invalid, in future (>60s), or expired (>max_skew_seconds)
    - signature does not match computed HMAC
    Returns True on valid receipt.
    """
    if receipt is None:
        raise InvalidReceiptSignatureError("Verifier receipt is missing or empty (R3/FA-04)")

    if isinstance(receipt, dict):
        rcpt_task_id = str(receipt.get("task_id", "")).strip()
        verifier_id = str(receipt.get("verifier_id", "")).strip()
        verdict = str(receipt.get("verdict", "")).strip()
        evidence_ref = str(receipt.get("evidence_ref", "")).strip()
        signature = str(receipt.get("signature", "")).strip()
        ts_raw = receipt.get("issued_at")
    elif isinstance(receipt, VerifierReceipt):
        rcpt_task_id = str(receipt.task_id).strip()
        verifier_id = str(receipt.verifier_id).strip()
        verdict = str(receipt.verdict).strip()
        evidence_ref = str(receipt.evidence_ref).strip()
        signature = str(receipt.signature).strip()
        ts_raw = receipt.issued_at
    else:
        raise InvalidReceiptSignatureError("Verifier receipt must be a VerifierReceipt or dict")

    if not rcpt_task_id:
        raise InvalidReceiptSignatureError("Verifier receipt missing task_id")
    if task_id is not None and str(task_id).strip() != rcpt_task_id:
        raise InvalidReceiptSignatureError(
            f"Receipt task_id '{rcpt_task_id}' does not match expected task_id '{str(task_id).strip()}'"
        )
    if not verifier_id:
        raise InvalidReceiptSignatureError("Verifier receipt missing verifier_id")
    if verdict != "VERIFIED":
        raise InvalidReceiptSignatureError(
            f"Completion requires verifier verdict 'VERIFIED', got '{verdict}'"
        )
    if not evidence_ref:
        raise InvalidReceiptSignatureError("Verifier receipt missing evidence_ref")
    if not signature:
        raise InvalidReceiptSignatureError("Verifier receipt is unsigned (R3/FA-04)")

    try:
        issued_at = float(ts_raw)
    except (TypeError, ValueError):
        raise InvalidReceiptSignatureError("Invalid timestamp in verifier receipt") from None

    now = time.time()
    if issued_at > now + 60.0:
        raise InvalidReceiptSignatureError("Verifier receipt issued_at is in the future")
    if max_skew_seconds > 0 and (now - issued_at) > max_skew_seconds:
        raise InvalidReceiptSignatureError("Verifier receipt has expired")

    canonical = canonical_receipt_bytes(receipt)
    sec = get_verifier_secret(secret)
    expected_sig = hmac.new(sec, canonical, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        raise InvalidReceiptSignatureError(
            "Verifier receipt signature verification failed (tampered receipt)"
        )

    return True


__all__ = [
    "VerifierReceipt",
    "MissingSecretError",
    "InvalidReceiptSignatureError",
    "get_verifier_secret",
    "canonical_receipt_bytes",
    "sign_verifier_receipt",
    "verify_verifier_receipt",
]
