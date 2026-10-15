import json
import time

import pytest

from scp.core.capability_token import (
    CapabilityToken,
    InvalidTokenSignatureError,
    compute_token_signature,
    verify_token_signature,
)
from scp.security.capability_epoch import (
    CapabilityAuthority,
    parse_capability_token,
)

# ==============================================================================
# T03 - GAP-08: CAPABILITY TOKEN HMAC-SHA256 SIGNING & ANTI-FORGERY VERIFICATION
# ==============================================================================
# Verifies that CapabilityTokens are cryptographically signed with HMAC-SHA256,
# validated in constant-time, and that unsigned, forged, tampered, or wrong-key
# tokens are rejected fail-closed with InvalidTokenSignatureError (FA-04 / FA-09).
# ==============================================================================


@pytest.fixture
def fixture_secret() -> bytes:
    return b"test-secret-32-chars-long-abcdef012345"


@pytest.fixture
def authority(tmp_path, fixture_secret) -> CapabilityAuthority:
    state_file = tmp_path / "capability_state.json"
    return CapabilityAuthority(state_path=state_file, secret=fixture_secret)


def test_invalid_token_signature_error_inherits_permission_error():
    """InvalidTokenSignatureError must inherit from PermissionError for PEP contract compliance."""
    assert issubclass(InvalidTokenSignatureError, PermissionError)
    err = InvalidTokenSignatureError("test signature error")
    assert isinstance(err, PermissionError)


def test_capability_token_reexported_from_core_and_security():
    """CapabilityToken must be accessible and identical from both modules."""
    from scp.core.capability_token import CapabilityToken as CoreToken
    from scp.security.capability_epoch import CapabilityToken as SecurityToken

    assert CoreToken is SecurityToken


def test_compute_token_signature_deterministic(fixture_secret):
    """Canonical signature computation must be strictly deterministic across calls."""
    sig1 = compute_token_signature(fixture_secret, "hands:pc.read_file", 0, "tid-100", 1700000000.123456)
    sig2 = compute_token_signature(fixture_secret, "hands:pc.read_file", 0, "tid-100", 1700000000.123456)
    assert sig1 == sig2
    assert len(sig1) == 64  # SHA256 hex digest length

    # Altering any field must yield a distinct signature
    sig_diff_subject = compute_token_signature(fixture_secret, "hands:pc.write_file", 0, "tid-100", 1700000000.123456)
    assert sig1 != sig_diff_subject

    sig_diff_epoch = compute_token_signature(fixture_secret, "hands:pc.read_file", 1, "tid-100", 1700000000.123456)
    assert sig1 != sig_diff_epoch

    sig_diff_id = compute_token_signature(fixture_secret, "hands:pc.read_file", 0, "tid-101", 1700000000.123456)
    assert sig1 != sig_diff_id

    sig_diff_time = compute_token_signature(fixture_secret, "hands:pc.read_file", 0, "tid-100", 1700000000.123457)
    assert sig1 != sig_diff_time


def test_verify_token_signature_direct_contract(fixture_secret):
    """verify_token_signature must return True for valid signatures and raise InvalidTokenSignatureError."""
    sig = compute_token_signature(fixture_secret, "hands:pc.read_file", 0, "tid-1", 1700000000.0)
    assert verify_token_signature(fixture_secret, "hands:pc.read_file", 0, "tid-1", 1700000000.0, sig) is True

    # Empty or missing signature -> fail-closed InvalidTokenSignatureError
    with pytest.raises(InvalidTokenSignatureError) as exc_info:
        verify_token_signature(fixture_secret, "hands:pc.read_file", 0, "tid-1", 1700000000.0, "")
    assert "unsigned" in str(exc_info.value).lower()

    with pytest.raises(InvalidTokenSignatureError) as exc_info:
        verify_token_signature(fixture_secret, "hands:pc.read_file", 0, "tid-1", 1700000000.0, "   ")
    assert "unsigned" in str(exc_info.value).lower()

    # Tampered signature -> fail-closed InvalidTokenSignatureError
    bad_sig = "0" * 64
    with pytest.raises(InvalidTokenSignatureError) as exc_info:
        verify_token_signature(fixture_secret, "hands:pc.read_file", 0, "tid-1", 1700000000.0, bad_sig)
    assert "verification failed" in str(exc_info.value).lower() or "tampered" in str(exc_info.value).lower()


def test_legitimate_token_issue_and_validate_roundtrip(authority):
    """Legitimately issued token must possess a valid HMAC signature and pass validation."""
    token = authority.issue("hands:pc.read_file")
    assert isinstance(token, CapabilityToken)
    assert token.subject == "hands:pc.read_file"
    assert token.epoch == 0
    assert len(token.signature) == 64

    # Validation with matching subject
    assert authority.validate(token, required_subject="hands:pc.read_file") is True
    # Validation without subject check
    assert authority.validate(token) is True


def test_token_dictionary_and_json_roundtrip_preserves_signature(authority):
    """Token serialized to dict or JSON and parsed back must retain valid signature."""
    token = authority.issue("hands:pc.write_file")
    d = token.to_dict()
    assert d["signature"] == token.signature

    # Parse from dict
    parsed_dict = parse_capability_token(d)
    assert parsed_dict is not None
    assert parsed_dict.signature == token.signature
    assert authority.validate(parsed_dict, required_subject="hands:pc.write_file") is True

    # Parse from JSON str
    json_str = json.dumps(d)
    parsed_json = parse_capability_token(json_str)
    assert parsed_json is not None
    assert parsed_json.signature == token.signature
    assert authority.validate(parsed_json, required_subject="hands:pc.write_file") is True


def test_unsigned_token_rejected_fail_closed(authority):
    """Unsigned token must be rejected fail-closed with InvalidTokenSignatureError (FA-04)."""
    unsigned_token = CapabilityToken(
        subject="hands:pc.write_file",
        epoch=0,
        token_id="forged-id-1",
        issued_at=time.time(),
        signature="",
    )
    with pytest.raises(InvalidTokenSignatureError) as exc_info:
        authority.validate(unsigned_token, required_subject="hands:pc.write_file")
    assert "unsigned" in str(exc_info.value).lower()


def test_none_signature_rejected_fail_closed(authority):
    """Token with None signature must be rejected fail-closed with InvalidTokenSignatureError."""
    token_none_sig = CapabilityToken(
        subject="hands:pc.write_file",
        epoch=0,
        token_id="forged-id-2",
        issued_at=time.time(),
        signature=None,  # type: ignore[arg-type]
    )
    with pytest.raises(InvalidTokenSignatureError):
        authority.validate(token_none_sig, required_subject="hands:pc.write_file")


def test_tampered_signature_rejected(authority):
    """Token with a corrupted or forged signature must be rejected with InvalidTokenSignatureError."""
    token = authority.issue("hands:pc.write_file")
    # Flip last character of signature
    corrupted_sig = token.signature[:-1] + ("0" if token.signature[-1] != "0" else "1")
    tampered_token = CapabilityToken(
        subject=token.subject,
        epoch=token.epoch,
        token_id=token.token_id,
        issued_at=token.issued_at,
        signature=corrupted_sig,
    )
    with pytest.raises(InvalidTokenSignatureError) as exc_info:
        authority.validate(tampered_token, required_subject="hands:pc.write_file")
    assert "verification failed" in str(exc_info.value).lower() or "tampered" in str(exc_info.value).lower()


def test_tampered_subject_rejected(authority):
    """Token with tampered subject must fail signature verification."""
    token = authority.issue("hands:pc.read_file")
    tampered_token = CapabilityToken(
        subject="hands:pc.write_file",  # escalated privilege
        epoch=token.epoch,
        token_id=token.token_id,
        issued_at=token.issued_at,
        signature=token.signature,
    )
    with pytest.raises(InvalidTokenSignatureError):
        authority.validate(tampered_token, required_subject="hands:pc.write_file")


def test_tampered_epoch_rejected(authority):
    """Token with forged future epoch must fail signature verification."""
    token = authority.issue("hands:pc.read_file")
    tampered_token = CapabilityToken(
        subject=token.subject,
        epoch=token.epoch + 10,  # attempt to bypass upcoming revocations
        token_id=token.token_id,
        issued_at=token.issued_at,
        signature=token.signature,
    )
    with pytest.raises(InvalidTokenSignatureError):
        authority.validate(tampered_token)


def test_tampered_token_id_rejected(authority):
    """Token with altered token_id must fail signature verification."""
    token = authority.issue("hands:pc.read_file")
    tampered_token = CapabilityToken(
        subject=token.subject,
        epoch=token.epoch,
        token_id="substitute-id",
        issued_at=token.issued_at,
        signature=token.signature,
    )
    with pytest.raises(InvalidTokenSignatureError):
        authority.validate(tampered_token)


def test_tampered_issued_at_rejected(authority):
    """Token with altered issued_at timestamp must fail signature verification."""
    token = authority.issue("hands:pc.read_file")
    tampered_token = CapabilityToken(
        subject=token.subject,
        epoch=token.epoch,
        token_id=token.token_id,
        issued_at=token.issued_at + 10.0,
        signature=token.signature,
    )
    with pytest.raises(InvalidTokenSignatureError):
        authority.validate(tampered_token)


def test_token_signed_with_wrong_secret_rejected(tmp_path):
    """Token signed by Authority A must be rejected by Authority B with different secret."""
    auth_a = CapabilityAuthority(
        state_path=tmp_path / "caps_a.json",
        secret=b"secret-authority-aaaa-32-bytes-long",
    )
    auth_b = CapabilityAuthority(
        state_path=tmp_path / "caps_b.json",
        secret=b"secret-authority-bbbb-32-bytes-long",
    )

    token_a = auth_a.issue("hands:pc.status")
    # Valid on authority A
    assert auth_a.validate(token_a, required_subject="hands:pc.status") is True

    # Strictly rejected on authority B
    with pytest.raises(InvalidTokenSignatureError):
        auth_b.validate(token_a, required_subject="hands:pc.status")


def test_legacy_unsigned_token_dict_strictly_rejected(authority):
    """Legacy token dictionary without signature must be parsed without signature and rejected fail-closed."""
    legacy_payload = {
        "subject": "hands:pc.write_file",
        "epoch": 0,
        "token_id": "legacy-token-id-12345",
        "issued_at": 1700000000.0,
    }
    parsed = parse_capability_token(legacy_payload)
    assert parsed is not None
    assert parsed.signature == ""

    with pytest.raises(InvalidTokenSignatureError) as exc_info:
        authority.validate(parsed, required_subject="hands:pc.write_file")
    assert "unsigned" in str(exc_info.value).lower()


def test_legacy_unsigned_token_json_strictly_rejected(authority):
    """Legacy JSON string payload without signature must be rejected fail-closed."""
    legacy_json = json.dumps({
        "subject": "hands:pc.write_file",
        "epoch": 0,
        "token_id": "legacy-token-id-67890",
        "issued_at": 1700000000.0,
    })
    parsed = parse_capability_token(legacy_json)
    assert parsed is not None
    assert parsed.signature == ""

    with pytest.raises(InvalidTokenSignatureError) as exc_info:
        authority.validate(parsed, required_subject="hands:pc.write_file")
    assert "unsigned" in str(exc_info.value).lower()


def test_revoked_epoch_with_valid_signature_returns_false(authority):
    """When a signed token is valid but its epoch is revoked, validate returns False (not error)."""
    token = authority.issue("hands:pc.read_file")
    assert authority.validate(token) is True

    authority.revoke(reason="security incident", actor="sec_admin")
    # Signature is valid, but epoch is obsolete: returns False
    assert authority.validate(token) is False


def test_subject_mismatch_with_valid_signature_returns_false(authority):
    """When a signed token is valid but subject does not match required_subject, returns False."""
    token = authority.issue("hands:pc.read_file")
    assert authority.validate(token, required_subject="hands:pc.write_file") is False


def test_none_token_returns_false(authority):
    """validate(None) must return False fail-closed without raising."""
    assert authority.validate(None) is False


def test_invalid_object_returns_false(authority):
    """validate() on arbitrary non-token object must return False fail-closed."""
    assert authority.validate(object()) is False  # type: ignore[arg-type]
