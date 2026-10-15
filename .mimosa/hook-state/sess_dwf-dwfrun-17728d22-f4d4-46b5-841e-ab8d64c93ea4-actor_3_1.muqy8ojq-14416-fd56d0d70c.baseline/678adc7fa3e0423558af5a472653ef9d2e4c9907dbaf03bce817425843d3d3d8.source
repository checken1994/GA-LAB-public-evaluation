"""Shared functions for API routes — breaks circular import.

Route modules import from here instead of api_server.py.
"""
import logging
from typing import Any

# [hygiene F821-fix] logger phải định nghĩa TRƯỚC khối try bên dưới: nhánh
# except dùng logger.debug — trước đây logger nằm sau khối try nên ImportError
# sẽ bị NameError(logger) che mất trong chính except handler.
logger = logging.getLogger("scp.api")

# [G5-FIX] Header import at module level — verify_admin uses it in signature
try:
    from fastapi import Header
except ImportError:
    logger.debug('<module>: ImportError ignored', exc_info=True)
    Header = None  # type: ignore


# Default value for authorization header (used if Header not available)
_AUTH_DEFAULT = Header("", alias="Authorization") if Header else ""


# [Fix 4-a-006 / Phase 3-A — DNA #5, #14, #19]
# TẠI SAO verify_admin + rate-limit helpers are now IMPORTED from
# scp.security.auth (not defined here):
#   Before: TWO divergent `verify_admin` functions existed:
#     - helpers.py: HTTPBearer-based, NO rate limiting, 401 on no-config (dead code).
#     - _shared.py (HERE): Header-based, HAS rate limiting, 503 on no-config (WRONG).
#   After: ONE canonical impl in scp.security.auth (with rate limiting + 401 on
#   no-config — best of both). _shared.py re-exports it so existing
#   `from scp.api._shared import verify_admin` imports keep working. If you
#   need to change auth behavior, edit scp.security.auth — not this file.
from scp.security.auth import (  # noqa: E402,F401  (re-exported for backward-compat)
    _RATE_LIMIT_MAX_FAILURES,
    _RATE_LIMIT_WINDOW,
    _auth_failures,
    _check_rate_limit,
    _record_auth_failure,
    verify_admin,
)


def get_judge():
    """Return the canonical process-local RealityJudge singleton.

    Route modules import this compatibility helper, while the main API owns
    the double-checked-locking singleton in ``api_server_parts.helpers``.
    Delegating keeps every route on the same judge instance and avoids
    reinitializing the full SLM/security stack per request.
    """
    from scp.api_server_parts.helpers import get_judge as _get_canonical_judge

    return _get_canonical_judge()


def _extract_v98_context(request) -> dict[str, Any]:
    """Extract bounded V98 request metadata without secret header values."""
    from scp.security.request_context import safe_header_metadata

    metadata = safe_header_metadata(request.headers)
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": metadata["headers"].get("user-agent", ""),
        "headers": metadata["headers"],
        "header_names": metadata["header_names"],
        "sensitive_headers_present": metadata["sensitive_headers_present"],
        "user_agent_present": metadata["user_agent_present"],
    }


# [FIX] Stubs for route imports — delegate to api_server at runtime

from typing import Any

from pydantic import BaseModel, Field


class SessionAnalyzeRequest(BaseModel):
    session_logs: list[dict[str, Any]] = []
    model_responses: list[dict[str, Any]] = []


class SimulationRequest(BaseModel):
    count: int = Field(50, ge=1, le=500)

# [SCP-DNA-FIX] Replace 12 broken shim functions with a PEP 562 module __getattr__.
#
# TẠI SAO (Reality > Model): the previous shims were defined as
#     def _multi_turn_tracker(*args, **kwargs):
#         from scp.api_server import _multi_turn_tracker as _impl
#         return _impl(*args, **kwargs)
# but `api_server._multi_turn_tracker` is a SINGLETON INSTANCE
# (`_multi_turn_tracker = MultiTurnTracker()`), NOT a callable. So:
#   - calling the shim `_multi_turn_tracker()` -> TypeError (instance not callable)
#   - not calling it `_multi_turn_tracker.stats()` -> AttributeError
#     ('function' object has no attribute 'stats')
# Every /v104/* and /v103/* route that touched these names was broken at
# runtime. pylint E1102/E1101 flagged 27 sites; ruff is blind to it
# (no cross-module type inference). The bug passed 3 audit rounds because
# the routes were never exercised in the test transcript (PowerShell.txt
# has zero HTTP request logs) and SCP's defensive try/except swallowed
# the errors. PASS != TRUE.
#
# Fix: __getattr__ returns the api_server attribute DIRECTLY (the instance /
# bool / function — whatever it actually is). Routes' `_multi_turn_tracker.stats()`
# then resolves `.stats` on the real instance. Zero callers invoked the old
# shims with parens (verified by grep across scp/), so this is backward-
# compatible. Circular-import safety: api_server.py defines these singletons
# at module level (lines 176-188) BEFORE it imports the route modules inside
# create_app() (lines 494+). By the time any route does
# `from scp.api._shared import X`, api_server is fully loaded.
_DELEGATED_NAMES = frozenset({
    "_SCP_VERSION", "_V1042_AVAILABLE", "_attack_crawler",
    "_cross_language_learner", "_fact_checker", "_fast_learning",
    "_image_detector", "_multi_turn_tracker", "_real_learning",
    "_safe_fetch_url", "_simple_explainer", "_voice_detector",
})


def __getattr__(name: str):
    """PEP 562 — lazily delegate singleton/function lookups to api_server.

    Fires only for names NOT already defined on this module (i.e. the
    delegated singletons listed in _DELEGATED_NAMES). Returns the real
    attribute from scp.api_server (instance, bool, or function — as-is),
    so route code like `_multi_turn_tracker.stats()` resolves `.stats` on
    the real singleton instance rather than on a broken shim function.
    """
    if name in _DELEGATED_NAMES:
        from scp import api_server
        try:
            return getattr(api_server, name)
        except AttributeError:
            # api_server mid-import or attr genuinely missing — surface a
            # clear error rather than a silent None (DNA: never silent).
            raise AttributeError(
                f"module 'scp.api._shared' cannot resolve '{name}' — "
                f"'scp.api_server' has no such attribute (circular import or missing singleton)"
            ) from None
    raise AttributeError(f"module 'scp.api._shared' has no attribute {name!r}")


def __dir__():
    """Make the delegated names discoverable (tab-completion, pydoc)."""
    return sorted(set(globals().keys()) | set(_DELEGATED_NAMES))
