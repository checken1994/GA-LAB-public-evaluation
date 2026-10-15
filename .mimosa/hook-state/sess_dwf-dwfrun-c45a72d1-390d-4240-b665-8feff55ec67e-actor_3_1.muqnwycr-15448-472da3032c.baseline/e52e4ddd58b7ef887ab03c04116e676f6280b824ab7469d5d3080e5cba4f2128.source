"""Root pytest configuration and fixtures for SCP test suite.

Ensures required environment variables (such as SCP_CAPABILITY_SECRET)
are safely defaulted for automated test collection while preserving
fail-closed semantics if intentionally unset during explicit tests.
"""

from __future__ import annotations

import os

os.environ['SCP_API_PROFILE'] = 'full'

# Default capability secret for automated test collection and suites (GAP-09).
# Test cases verifying fail-closed behavior when unset will explicitly remove
# or monkeypatch this variable in subprocesses or isolated scopes.
os.environ.setdefault(
    "SCP_CAPABILITY_SECRET",
    "test-capability-secret-for-automated-suites-only-32bytes",
)

# [EE-G1 / S14] Unit-test determinism against .env import side effects.
# Importing ANY test module that pulls in scp.api_server runs
# scp.security.env_loader.load_selected_env() at collection time, which loads
# the repository .env into os.environ. When that file carries egress keys,
# every test in the session silently ran under the server's egress policy.
# EE-G1 enforcement surfaced this: T03 test_web_browse_requires_token failed
# because .env set SCP_EGRESS_MODE=allowlist for the whole suite. Snapshot the
# parent environment here (before collection imports anything) and restore
# JUST these keys after collection, so test execution starts from the
# caller's environment. Tests that need an explicit mode set their own via
# monkeypatch.setenv — the strict, explicit path (this fix only REMOVES an
# accidental policy source; it never adds one).
_EGRESS_ENV_KEYS = ("SCP_EGRESS_MODE", "SCP_EGRESS_ALLOWLIST", "SCP_PRODUCTION_MODE")
_PARENT_EGRESS_ENV = {k: os.environ.get(k) for k in _EGRESS_ENV_KEYS}


def pytest_collection_finish(session) -> None:
    for key, parent_value in _PARENT_EGRESS_ENV.items():
        current = os.environ.get(key)
        if parent_value is None:
            if current is not None:
                del os.environ[key]
        elif current != parent_value:
            os.environ[key] = parent_value
