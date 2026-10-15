from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scp.api.route_profile import resolve_api_profile, route_group_enabled

ROOT = Path(__file__).resolve().parents[2]


def test_profile_defaults_and_invalid_value_fail_closed() -> None:
    assert resolve_api_profile({"SCP_PRODUCTION_MODE": "1"}) == "core"
    assert resolve_api_profile({"SCP_PRODUCTION_MODE": "0"}) == "full"
    assert resolve_api_profile(
        {"SCP_PRODUCTION_MODE": "1", "SCP_API_PROFILE": "standard"}
    ) == "standard"
    with pytest.raises(RuntimeError, match="invalid SCP_API_PROFILE"):
        resolve_api_profile({"SCP_API_PROFILE": "everything"})


def test_route_groups_are_monotonic_and_classified() -> None:
    assert not route_group_enabled("chat", "core")
    assert route_group_enabled("chat", "standard")
    assert route_group_enabled("chat", "full")
    assert not route_group_enabled("pc_controller", "standard")
    assert route_group_enabled("pc_controller", "full")
    with pytest.raises(RuntimeError, match="unclassified"):
        route_group_enabled("forgotten_router", "full")


def _loaded_paths(profile: str) -> set[str]:
    env = os.environ.copy()
    env.update(
        {
            "SCP_API_PROFILE": profile,
            "SCP_PRODUCTION_MODE": "0",
            "SCP_SKIP_STARTUP_GATE": "1",
            "SCP_JWT_SECRET": "route-profile-test-secret",
            "SCP_EGRESS_MODE": "deny",
        }
    )
    script = (
        "import json; from scp.api_server import app, _API_PROFILE; "
        "print('ROUTE_PROFILE_JSON=' + json.dumps({'profile': _API_PROFILE, "
        "'paths': sorted({r.path for r in app.routes})}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    marker = next(
        (
            line
            for line in completed.stdout.splitlines()
            if line.startswith("ROUTE_PROFILE_JSON=")
        ),
        None,
    )
    assert marker is not None, completed.stdout
    payload = json.loads(marker.split("=", 1)[1])
    assert payload["profile"] == profile
    return set(payload["paths"])


def test_core_profile_reduces_actual_registered_routes() -> None:
    core = _loaded_paths("core")
    full = _loaded_paths("full")

    assert "/ask" in core
    assert "/health" in core
    assert "/v1/chat/completions" not in core
    assert "/v3/hands/status" not in core
    assert "/v1/chat/completions" in full
    assert "/v3/hands/status" in full
    assert core < full
