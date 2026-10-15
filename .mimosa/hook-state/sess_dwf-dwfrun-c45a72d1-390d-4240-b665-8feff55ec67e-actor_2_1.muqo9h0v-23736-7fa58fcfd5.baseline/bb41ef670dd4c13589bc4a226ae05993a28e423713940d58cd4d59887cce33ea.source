from __future__ import annotations

import base64
import hashlib
import hmac
import json

from scp.core import capability_token


def _payload(token: str) -> dict:
    encoded = token.split(".", 1)[0]
    encoded += "=" * (-len(encoded) % 4)
    return json.loads(base64.urlsafe_b64decode(encoded).decode("utf-8"))


def _signed_payload(payload_bytes: bytes) -> str:
    encoded = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    signature = hmac.new(
        capability_token._SECRET,
        encoded.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded}.{signature}"


def test_default_token_ttl_is_exact(monkeypatch) -> None:
    monkeypatch.setattr(capability_token.time, "time", lambda: 1_000.0)

    payload = _payload(capability_token.mint_token("issuer", "read", 1))

    assert payload["iat"] == 1_000
    assert payload["exp"] == 4_600


def test_invalid_formats_and_signature_fail_closed() -> None:
    assert capability_token.verify_token("")["valid"] is False
    assert capability_token.verify_token("no-separator")["valid"] is False
    assert capability_token.verify_token("a.b.c")["valid"] is False

    token = capability_token.mint_token("issuer", "read", 1, ttl_seconds=60)
    payload, _signature = token.rsplit(".", 1)
    result = capability_token.verify_token(f"{payload}.tampered")
    assert result["valid"] is False
    assert result["error"] == "Invalid signature"


def test_valid_token_round_trip_requires_padding_and_positive_verdict(monkeypatch) -> None:
    monkeypatch.setattr(capability_token.time, "time", lambda: 1_000.0)
    token = capability_token.mint_token("xxx", "read", 7, ttl_seconds=60)
    encoded, _signature = token.rsplit(".", 1)

    # This payload deliberately needs two '=' characters restored by verify_token.
    assert len(encoded) % 4 == 2

    result = capability_token.verify_token(token, required_scope="read")
    assert result["valid"] is True
    assert result["payload"]["iss"] == "xxx"
    assert result["payload"]["scope"] == "read"
    assert result["payload"]["cap"] == 7
    assert result["payload"]["iat"] == 1_000
    assert result["payload"]["exp"] == 1_060


def test_correctly_signed_malformed_payload_fails_closed() -> None:
    token = _signed_payload(b'{"iss":"issuer","scope":"read"')

    result = capability_token.verify_token(token)

    assert result["valid"] is False
    assert result["error"] == "Invalid payload"


def test_expired_token_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(capability_token.time, "time", lambda: 1_000.0)
    token = capability_token.mint_token("issuer", "read", 1, ttl_seconds=60)
    monkeypatch.setattr(capability_token.time, "time", lambda: 1_061.0)

    result = capability_token.verify_token(token)

    assert result["valid"] is False
    assert result["error"] == "Token expired"


def test_missing_exp_claim_fails_closed_at_subsecond_boundary(monkeypatch) -> None:
    token = _signed_payload(
        json.dumps(
            {"iss": "issuer", "scope": "read", "cap": 1, "iat": 0}
        ).encode("utf-8")
    )
    monkeypatch.setattr(capability_token.time, "time", lambda: 0.5)

    result = capability_token.verify_token(token)

    assert result["valid"] is False
    assert result["error"] == "Token expired"


def test_scope_mismatch_fails_closed_while_wildcard_requirement_allows(monkeypatch) -> None:
    monkeypatch.setattr(capability_token.time, "time", lambda: 1_000.0)
    token = capability_token.mint_token("issuer", "read", 1, ttl_seconds=60)

    denied = capability_token.verify_token(token, required_scope="write")
    allowed = capability_token.verify_token(token, required_scope="*")

    assert denied["valid"] is False
    assert denied["error"] == "Scope mismatch"
    assert allowed["valid"] is True
    assert allowed["payload"]["scope"] == "read"
