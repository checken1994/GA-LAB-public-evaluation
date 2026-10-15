import base64
import hashlib
import hmac
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

class MissingSecretError(RuntimeError):
    """Raised when SCP_CAPABILITY_SECRET is missing or empty (GAP-09 fail-closed)."""
    pass


class InvalidTokenSignatureError(PermissionError):
    """Raised when a capability token is unsigned, has an invalid signature, or has been tampered with."""
    pass


def compute_token_signature(secret: bytes, subject: str, epoch: int, token_id: str, issued_at: float) -> str:
    """Compute deterministic HMAC-SHA256 signature for a CapabilityToken."""
    canonical = f"{subject}:{epoch}:{token_id}:{issued_at:.6f}".encode()
    return hmac.new(secret, canonical, hashlib.sha256).hexdigest()


def verify_token_signature(secret: bytes, subject: str, epoch: int, token_id: str, issued_at: float, signature: str) -> bool:
    """Verify HMAC-SHA256 signature for a CapabilityToken using constant-time comparison.

    Raises InvalidTokenSignatureError fail-closed if signature is missing, invalid, or tampered.
    """
    if not signature or not str(signature).strip():
        raise InvalidTokenSignatureError("Capability token is unsigned (GAP-08/FA-04)")
    expected = compute_token_signature(secret, subject, epoch, token_id, issued_at)
    if not hmac.compare_digest(str(signature).strip(), expected):
        raise InvalidTokenSignatureError("Capability token signature verification failed (tampered token)")
    return True


def get_capability_secret() -> bytes:
    """Read and return the cryptographic secret for capability tokens.

    Raises MissingSecretError if SCP_CAPABILITY_SECRET is missing or empty.
    """
    secret = os.environ.get("SCP_CAPABILITY_SECRET")
    if not secret or not secret.strip():
        raise MissingSecretError(
            "SCP_CAPABILITY_SECRET environment variable is missing or empty. "
            "A cryptographic secret is required to sign and verify capability tokens (GAP-09)."
        )
    return secret.strip().encode("utf-8")


_SECRET = get_capability_secret()

def mint_token(issuer: str, scope: str, capability_level: int, ttl_seconds: int = 3600) -> str:
    epoch = int(time.time())
    payload = {
        "iss": issuer,
        "scope": scope,
        "cap": capability_level,
        "iat": epoch,
        "exp": epoch + ttl_seconds,
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(_SECRET, payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"

def verify_token(token: str, required_scope: str = "*") -> dict:
    if not token or "." not in token:
        return {"valid": False, "error": "Invalid token format"}
    payload_b64, signature = token.rsplit(".", 1)

    expected_sig = hmac.new(_SECRET, payload_b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        return {"valid": False, "error": "Invalid signature"}

    pad = len(payload_b64) % 4
    if pad:
        payload_b64 += "=" * (4 - pad)

    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
    except Exception:
        logger.debug("verify_token ignored", exc_info=True)
        return {"valid": False, "error": "Invalid payload"}

    if payload.get("exp", 0) < time.time():
        return {"valid": False, "error": "Token expired"}

    scope = payload.get("scope")
    if required_scope != "*" and scope != required_scope and scope != "*":
        return {"valid": False, "error": "Scope mismatch"}

    return {"valid": True, "payload": payload}


def __getattr__(name: str):
    if name == "CapabilityToken":
        from scp.security.capability_epoch import CapabilityToken
        return CapabilityToken
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "MissingSecretError",
    "InvalidTokenSignatureError",
    "get_capability_secret",
    "compute_token_signature",
    "verify_token_signature",
    "mint_token",
    "verify_token",
    # [hygiene F822] CapabilityToken KHÔNG được định nghĩa tĩnh ở module này —
    # nó được lazy-export qua __getattr__ (PEP 562) phía trên để tránh circular
    # import; giữ tên trong __all__ là chủ đích, không phải bug.
    "CapabilityToken",  # noqa: F822  # lazy-export qua __getattr__ (PEP 562) phía trên — chủ đích
]
