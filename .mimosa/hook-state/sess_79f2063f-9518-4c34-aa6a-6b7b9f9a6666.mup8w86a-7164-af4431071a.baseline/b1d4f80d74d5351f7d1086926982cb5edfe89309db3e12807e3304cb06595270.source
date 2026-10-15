"""SCP canonical admin-auth verifier.

[Fix 4-a-006 / Phase 3-A — DNA #5, #14, #19, #25]
TẠI SAO this module exists:
  Before this fix, TWO divergent `verify_admin` functions lived in the codebase:
    1. `scp.api_server_parts.helpers.verify_admin` — HTTPBearer-based,
       NO rate limiting, raises HTTPException(401) on no-config. Dead code
       (no callers — confirmed by grep `from scp.api_server_parts.helpers
       import.*verify_admin` returns 0 matches).
    2. `scp.api._shared.verify_admin` — Header-based, HAS rate limiting
       (5 failures / 60s per IP), raises HTTPException(503) on no-config
       (WRONG status code — should be 401 Unauthorized, not 503 Service
       Unavailable). All route modules imported this one.

  DNA #5 (ảo giác đồng thuận): same name `verify_admin` ≠ same auth posture.
  DNA #14 (đồng thuận ≠ đúng): both passed basic tests; only the rate-limit
  + 503-vs-401 differences mattered under attack. DNA #19: scanner didn't
  cross-check the two definitions. DNA #25 (missing piece): no comment in
  either file pointing to the other as canonical.

  Fix: ONE canonical `verify_admin` lives HERE in `scp/security/auth.py`
  (security is the right home for auth). It has:
    - Rate limiting (max 5 failed attempts / 60s per IP → 429 Too Many Requests)
    - 401 Unauthorized on no-config (was 503 in the old _shared version)
    - 401 Unauthorized on missing/invalid token
    - Timing-safe `secrets.compare_digest` (no early short-circuit)
    - NO dev-mode bypass (deny by default if no token configured)

  `scp/api/_shared.py` and `scp/api_server_parts/helpers.py` BOTH re-export
  this function — so existing `from scp.api._shared import verify_admin`
  imports keep working, but there is now ONE implementation. If you need to
  change admin auth behavior, edit THIS file only.
"""
from __future__ import annotations

import logging
import secrets
import threading
import time
from typing import Any

logger = logging.getLogger("scp.security.auth")
from scp.security.auth_config import AuthConfigError, load_auth_config

# [G5-FIX] Header + Request imports — both are FastAPI dependency markers.
try:
    from fastapi import Header, Request
except ImportError:  # pragma: no cover — fastapi is a hard dep of the API server
    logger.debug('<module>: ImportError ignored', exc_info=True)
    Header = None  # type: ignore
    Request = Any  # type: ignore[misc,assignment]

# [AUTOFIX-T2-SEC] Rate limiting for auth endpoints — prevents brute-force.
# Simple in-memory sliding-window limiter: max 5 failed attempts per IP per 60s.
# DNA SCP #12: "Không tăng quyền chỉ vì lập luận tăng" — rate limit là capability
# control, không phải logic change. Fail-closed (block) on threshold.
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX_FAILURES = 5
_MAX_AUTH_FAILURE_IPS = 5000
_auth_failures_lock = threading.Lock()
_auth_failures: dict[str, list[float]] = {}

# KNOWN LIMITATION (documented, do NOT "fix" by trusting headers):
#   - Buckets are keyed by the TCP peer (request.client.host). Behind a reverse
#     proxy every client shares ONE bucket, so a burst of failures from one
#     client can 429 others. X-Forwarded-For is NOT used on purpose — it is
#     client-spoofable and would let an attacker rotate fake IPs to bypass the
#     limiter entirely. Deployments needing per-client granularity must
#     terminate the limiter at the proxy itself.
#   - When the ASGI server does not populate request.client (Unix sockets,
#     some test clients), all such requests share the literal "unknown" bucket.
#     This is fail-closed (shared throttling), not a bypass.
def _evict_oldest_failure_bucket_locked() -> None:
    """[SEC-FIX auth-eviction 2026-09-26] Drop the least-recently-active bucket.

    Eviction used to pop `next(iter(_auth_failures))` — pure INSERTION order.
    A bucket's position never changes once created (setdefault keeps the slot),
    so the FIRST attacker to appear could be evicted over and over while
    carrying the most recent failures, resetting their throttle budget, while
    stale one-failure buckets (never re-checked) lingered forever. Eviction is
    now by oldest most-recent-failure timestamp: the bucket whose latest
    failure is furthest in the past is dropped first.
    Must be called with _auth_failures_lock held.
    """
    if len(_auth_failures) <= _MAX_AUTH_FAILURE_IPS:
        return
    oldest_ip = min(
        _auth_failures,
        key=lambda ip: _auth_failures[ip][-1] if _auth_failures[ip] else 0.0,
    )
    _auth_failures.pop(oldest_ip, None)


def _check_rate_limit(ip: str) -> bool:
    """Return True if IP is within rate limit, False if blocked.

    See the KNOWN LIMITATION note above `_evict_oldest_failure_bucket_locked`
    for the shared-bucket semantics behind proxies and unknown clients.
    """
    now = time.time()
    with _auth_failures_lock:
        failures = [t for t in _auth_failures.get(ip, []) if now - t < _RATE_LIMIT_WINDOW]
        if failures:
            _auth_failures[ip] = failures
        else:
            _auth_failures.pop(ip, None)  # Delete empty IP key
        _evict_oldest_failure_bucket_locked()
        return len(failures) < _RATE_LIMIT_MAX_FAILURES


def _record_auth_failure(ip: str) -> None:
    """Record a failed auth attempt for rate limiting.

    See the KNOWN LIMITATION note above `_evict_oldest_failure_bucket_locked`
    for the shared-bucket semantics behind proxies and unknown clients.
    """
    with _auth_failures_lock:
        _auth_failures.setdefault(ip, []).append(time.time())
        _evict_oldest_failure_bucket_locked()


# [FIX-A P0-3] Log-once flag: warn when admin token is empty (deny-by-default).
_admin_no_token_warned: bool = False


def verify_admin(
    authorization: str = Header("", alias="Authorization"),  # noqa: B008 — FastAPI dependency injection idiom
    token: str | None = None,
    *,
    request: Request,
):
    """Verify admin token — timing-safe, NO dev-mode bypass, RAISES on failure.

    [Fix 4-a-006 / Phase 3-A] This is the CANONICAL `verify_admin` for the
    SCP system. Previously, TWO divergent impls existed (helpers.py + _shared.py)
    with different signatures, different rate-limit behavior, and different
    failure status codes (401 vs 503). Now both re-export THIS function —
    ONE source of truth. Do NOT add a second impl.

    Behavior:
      - 429 Too Many Requests if IP exceeds 5 failed attempts / 60s (rate limit)
      - 401 Unauthorized if no SCP_AUTH_PASSWORD / SCP_AUTH_TOKEN_SECRET
        configured (was 503 in old _shared.py — 503 is "service unavailable",
        which is semantically WRONG for "auth not configured")
      - 401 Unauthorized on missing or invalid token (timing-safe compare)
      - Returns True on success
    """
    from fastapi import HTTPException

    # Extract client IP for rate limiting. The Request annotation is essential:
    # FastAPI injects the actual connection only for a Request-typed parameter.
    client_ip = "unknown"
    if request is not None and hasattr(request, "client") and request.client:
        client_ip = request.client.host or "unknown"

    # Rate limit check BEFORE auth (don't leak whether token is valid)
    if not _check_rate_limit(client_ip):
        logger.warning(f"[RATE-LIMIT] IP {client_ip} blocked — too many auth failures")
        raise HTTPException(
            status_code=429,
            detail="Too many auth attempts — try again later",
        )

    try:
        auth_config = load_auth_config()
    except AuthConfigError as exc:
        logger.error("verify_admin: invalid auth configuration (%s)", exc.code)
        raise HTTPException(status_code=503, detail="Authentication configuration unavailable") from exc
    auth_password = auth_config.password
    auth_token = auth_config.token
    # Deny by default if NEITHER is configured (no dev-mode bypass).
    # [Fix 4-a-006] 503 → 401: "Auth not configured" is an authorization
    # failure (caller's credentials don't match the empty config), NOT a
    # service-availability issue. Per RFC 7235, 401 is correct.
    if not auth_password and not auth_token:
        global _admin_no_token_warned
        if not _admin_no_token_warned:
            logger.warning(
                "verify_admin: SCP_AUTH_PASSWORD/SCP_AUTH_TOKEN_SECRET not set — "
                "denying admin request (configure a real token in .env; "
                "SCP_DEV_MODE bypass was removed in RC-2 fix)"
            )
            _admin_no_token_warned = True
        raise HTTPException(
            status_code=401,
            detail="Unauthorized — set SCP_AUTH_PASSWORD / SCP_AUTH_TOKEN_SECRET in .env",
        )

    provided = token or ""
    # [G5-FIX] Extract from Authorization header (FastAPI populates `authorization` param)
    # [REAUDIT-FIX] When called directly (not via Depends), authorization may be Header object
    if not provided and isinstance(authorization, str) and authorization:
        if authorization.lower().startswith("bearer "):
            provided = authorization[7:].strip()
        else:
            provided = authorization.strip()
    if not provided:
        _record_auth_failure(client_ip)
        raise HTTPException(status_code=401, detail="Missing auth token")

    # Timing-safe comparison — no short-circuit on first differing byte.
    ok = False
    if auth_token:
        try:
            ok = ok or secrets.compare_digest(provided, auth_token)
        except (TypeError, ValueError) as e:
            logger.warning(f"Silent except: {e}")
    if auth_password and not ok:
        try:
            ok = ok or secrets.compare_digest(provided, auth_password)
        except (TypeError, ValueError) as e:
            logger.warning(f"Silent except: {e}")
    if not ok:
        _record_auth_failure(client_ip)
        raise HTTPException(status_code=401, detail="Invalid auth token")
    return True


__all__ = [
    "verify_admin",
    "_check_rate_limit",
    "_record_auth_failure",
    "_auth_failures",
    "_RATE_LIMIT_WINDOW",
    "_RATE_LIMIT_MAX_FAILURES",
    "_admin_no_token_warned",
]
