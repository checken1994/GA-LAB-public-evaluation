"""Adversarial stress-test probe for Milestone 3 (GAP-08 Capability Token HMAC Signing).

Authored by: Reviewer 1 (reviewer_m3_1)
Objective: Independently stress-test assumptions, probe edge cases, evaluate attack vectors,
and verify fail-closed semantics for HMAC-SHA256 capability token signing.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Ensure valid capability secret for testing
os.environ["SCP_CAPABILITY_SECRET"] = "m3-reviewer-probe-secret-key-64-bytes-0123456789abcdef0123456789abcdef"

from scp.core.capability_token import (
    CapabilityToken,
    InvalidTokenSignatureError,
    compute_token_signature,
    get_capability_secret,
    verify_token_signature,
)
from scp.security.capability_epoch import (
    CapabilityAuthority,
    CapabilityRevokedError,
    parse_capability_token,
)


def run_check(name: str, fn):
    print(f"[*] Testing: {name}...")
    try:
        fn()
        print(f"    [+] PASS: {name}")
    except Exception as e:
        print(f"    [-] FAIL: {name} -> {type(e).__name__}: {e}")
        raise


def test_forged_unsigned_token_rejected():
    """Attack 1: Attacker forges an unsigned CapabilityToken object."""
    secret = get_capability_secret()
    with tempfile.TemporaryDirectory() as tmp:
        auth = CapabilityAuthority(state_path=Path(tmp) / "caps.json", secret=secret)
        forged = CapabilityToken(
            subject="hands:pc.write_file",
            epoch=0,
            token_id="forged-id-123",
            issued_at=time.time(),
            signature="",
        )
        try:
            auth.validate(forged, required_subject="hands:pc.write_file")
            raise AssertionError("Vulnerability: auth.validate accepted unsigned token!")
        except InvalidTokenSignatureError as exc:
            assert "unsigned" in str(exc).lower()


def test_bit_flip_tampering_rejected():
    """Attack 2: Attacker intercepts legitimate token and flips a single bit in signature."""
    secret = get_capability_secret()
    with tempfile.TemporaryDirectory() as tmp:
        auth = CapabilityAuthority(state_path=Path(tmp) / "caps.json", secret=secret)
        legit = auth.issue("hands:pc.read_file")

        # Flip last byte
        last_char = legit.signature[-1]
        corrupt_char = "0" if last_char != "0" else "1"
        tampered_sig = legit.signature[:-1] + corrupt_char

        tampered = CapabilityToken(
            subject=legit.subject,
            epoch=legit.epoch,
            token_id=legit.token_id,
            issued_at=legit.issued_at,
            signature=tampered_sig,
        )

        try:
            auth.validate(tampered, required_subject="hands:pc.read_file")
            raise AssertionError("Vulnerability: auth.validate accepted single-bit flipped signature!")
        except InvalidTokenSignatureError as exc:
            assert "tampered" in str(exc).lower() or "verification failed" in str(exc).lower()


def test_privilege_escalation_rejected():
    """Attack 3: Attacker requests read_file, modifies subject to write_file keeping signature."""
    secret = get_capability_secret()
    with tempfile.TemporaryDirectory() as tmp:
        auth = CapabilityAuthority(state_path=Path(tmp) / "caps.json", secret=secret)
        read_token = auth.issue("hands:pc.read_file")

        escalated_token = CapabilityToken(
            subject="hands:pc.write_file",
            epoch=read_token.epoch,
            token_id=read_token.token_id,
            issued_at=read_token.issued_at,
            signature=read_token.signature,
        )

        try:
            auth.validate(escalated_token, required_subject="hands:pc.write_file")
            raise AssertionError("Vulnerability: Subject tampering was accepted!")
        except InvalidTokenSignatureError:
            pass


def test_epoch_tampering_rejected():
    """Attack 4: Attacker modifies epoch to future epoch to bypass revocation."""
    secret = get_capability_secret()
    with tempfile.TemporaryDirectory() as tmp:
        auth = CapabilityAuthority(state_path=Path(tmp) / "caps.json", secret=secret)
        token = auth.issue("hands:pc.status")

        future_token = CapabilityToken(
            subject=token.subject,
            epoch=token.epoch + 5,
            token_id=token.token_id,
            issued_at=token.issued_at,
            signature=token.signature,
        )

        try:
            auth.validate(future_token, required_subject="hands:pc.status")
            raise AssertionError("Vulnerability: Epoch tampering was accepted!")
        except InvalidTokenSignatureError:
            pass


def test_timestamp_and_id_tampering_rejected():
    """Attack 5: Attacker tampers with issued_at or token_id."""
    secret = get_capability_secret()
    with tempfile.TemporaryDirectory() as tmp:
        auth = CapabilityAuthority(state_path=Path(tmp) / "caps.json", secret=secret)
        token = auth.issue("hands:pc.read_file")

        tampered_time = CapabilityToken(
            subject=token.subject,
            epoch=token.epoch,
            token_id=token.token_id,
            issued_at=token.issued_at + 3600.0,
            signature=token.signature,
        )
        try:
            auth.validate(tampered_time)
            raise AssertionError("Vulnerability: timestamp tampering accepted!")
        except InvalidTokenSignatureError:
            pass

        tampered_id = CapabilityToken(
            subject=token.subject,
            epoch=token.epoch,
            token_id="different-token-id-000",
            issued_at=token.issued_at,
            signature=token.signature,
        )
        try:
            auth.validate(tampered_id)
            raise AssertionError("Vulnerability: token_id tampering accepted!")
        except InvalidTokenSignatureError:
            pass


def test_case_sensitivity_of_signature():
    """Attack 6: Upper-casing hex signature must be rejected."""
    secret = get_capability_secret()
    with tempfile.TemporaryDirectory() as tmp:
        auth = CapabilityAuthority(state_path=Path(tmp) / "caps.json", secret=secret)
        token = auth.issue("hands:pc.status")

        upper_token = CapabilityToken(
            subject=token.subject,
            epoch=token.epoch,
            token_id=token.token_id,
            issued_at=token.issued_at,
            signature=token.signature.upper(),
        )
        try:
            auth.validate(upper_token)
            raise AssertionError("Vulnerability: Uppercase signature accepted!")
        except InvalidTokenSignatureError:
            pass


def test_cross_authority_isolation():
    """Attack 7: Token issued by Authority A rejected by Authority B with different secret."""
    with tempfile.TemporaryDirectory() as tmp:
        auth_a = CapabilityAuthority(Path(tmp) / "auth_a.json", secret=b"secret-authority-a-32-chars-long")
        auth_b = CapabilityAuthority(Path(tmp) / "auth_b.json", secret=b"secret-authority-b-32-chars-long")

        token_a = auth_a.issue("hands:pc.status")
        assert auth_a.validate(token_a, required_subject="hands:pc.status") is True

        try:
            auth_b.validate(token_a, required_subject="hands:pc.status")
            raise AssertionError("Vulnerability: Cross-authority token accepted!")
        except InvalidTokenSignatureError:
            pass


def test_legacy_payload_rejection():
    """Attack 8: Old legacy tokens (no signature field in JSON/dict) are strictly rejected."""
    secret = get_capability_secret()
    with tempfile.TemporaryDirectory() as tmp:
        auth = CapabilityAuthority(state_path=Path(tmp) / "caps.json", secret=secret)
        legacy_dict = {
            "subject": "hands:pc.read_file",
            "epoch": 0,
            "token_id": "legacy-token-12345",
            "issued_at": 1700000000.0,
        }
        parsed = parse_capability_token(legacy_dict)
        assert parsed is not None
        assert parsed.signature == ""

        try:
            auth.validate(parsed)
            raise AssertionError("Vulnerability: Legacy unsigned parsed token accepted!")
        except InvalidTokenSignatureError:
            pass


def test_empty_whitespace_and_null_signature_variants():
    """Attack 9: Various empty/whitespace/null signatures rejected fail-closed."""
    secret = get_capability_secret()
    for bad_sig in ["", " ", "   ", "\t", "\n", "\r\n"]:
        try:
            verify_token_signature(secret, "hands:pc.read_file", 0, "tid-1", 1700000000.0, bad_sig)
            raise AssertionError(f"Vulnerability: bad_sig '{repr(bad_sig)}' accepted!")
        except InvalidTokenSignatureError:
            pass


def test_revocation_lifecycle_with_hmac():
    """Attack 10: Replay after revocation & restoration fails closed even with legitimate HMAC."""
    secret = get_capability_secret()
    with tempfile.TemporaryDirectory() as tmp:
        auth = CapabilityAuthority(state_path=Path(tmp) / "caps.json", secret=secret)
        token0 = auth.issue("hands:pc.read_file")
        assert auth.validate(token0, required_subject="hands:pc.read_file") is True

        # Revoke epoch 0
        auth.revoke(reason="incident", actor="sec_op")
        # Token0 signature is still cryptographically valid, but epoch is obsolete
        assert auth.validate(token0, required_subject="hands:pc.read_file") is False

        # Restore: increments epoch to 2
        auth.restore(reason="restored", actor="sec_op")
        # Token0 remains invalid!
        assert auth.validate(token0, required_subject="hands:pc.read_file") is False

        # Token from epoch 2 works
        token2 = auth.issue("hands:pc.read_file")
        assert token2.epoch == 2
        assert auth.validate(token2, required_subject="hands:pc.read_file") is True


def test_parse_capability_token_adversarial_inputs():
    """Attack 11: Malformed JSON, arrays, primitives, and non-token dicts fail closed to None."""
    assert parse_capability_token(None) is None
    assert parse_capability_token("") is None
    assert parse_capability_token("   ") is None
    assert parse_capability_token("not a json") is None
    assert parse_capability_token("12345") is None
    assert parse_capability_token("true") is None
    assert parse_capability_token("[]") is None
    assert parse_capability_token('{"epoch": "not_an_int"}') is None
    assert parse_capability_token('{"subject": "test"}') is None  # missing epoch -> None
    assert parse_capability_token({"subject": "test", "epoch": "invalid_int"}) is None


def main():
    print("=" * 70)
    print("REVIEWER 1 ADVERSARIAL STRESS-TEST SUITE: GAP-08 HMAC TOKEN SIGNING")
    print("=" * 70)
    checks = [
        ("Forged Unsigned Token Rejection", test_forged_unsigned_token_rejected),
        ("Bit-Flip Tampering Rejection", test_bit_flip_tampering_rejected),
        ("Privilege Escalation Rejection", test_privilege_escalation_rejected),
        ("Epoch Tampering Rejection", test_epoch_tampering_rejected),
        ("Timestamp & ID Tampering Rejection", test_timestamp_and_id_tampering_rejected),
        ("Case Sensitivity of Signature", test_case_sensitivity_of_signature),
        ("Cross-Authority Isolation", test_cross_authority_isolation),
        ("Legacy Payload Rejection", test_legacy_payload_rejection),
        ("Empty/Whitespace Signature Variants", test_empty_whitespace_and_null_signature_variants),
        ("Revocation Lifecycle with HMAC", test_revocation_lifecycle_with_hmac),
        ("Parse Capability Token Adversarial Inputs", test_parse_capability_token_adversarial_inputs),
    ]

    for name, fn in checks:
        run_check(name, fn)

    print("=" * 70)
    print("ALL 11 ADVERSARIAL CHALLENGES PASSED (FAIL-CLOSED VERIFIED).")
    print("=" * 70)


if __name__ == "__main__":
    main()
