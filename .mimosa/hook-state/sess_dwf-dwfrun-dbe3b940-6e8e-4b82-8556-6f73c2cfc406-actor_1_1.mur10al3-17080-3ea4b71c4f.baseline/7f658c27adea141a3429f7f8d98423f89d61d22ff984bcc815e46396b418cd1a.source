"""Explicit API-surface profiles for the monolithic SCP FastAPI process."""
from __future__ import annotations

import os
from collections.abc import Mapping

PROFILE_LEVEL = {"core": 0, "standard": 1, "full": 2}

# A group is registered only when the selected profile reaches this level.
GROUP_MINIMUM = {
    "trace": "core",
    "chat": "standard",
    "openai_compat": "standard",
    "evaluation": "standard",
    "control": "standard",
    "hands": "standard",
    "agent": "standard",
    "versioned_admin": "full",
    "import": "full",
    "stream": "full",
    "threat": "full",
    "audit": "full",
    "prediction": "full",
    "webhook": "full",
    "pc_controller": "full",
    "web_control": "full",
    "batch_benchmark": "full",
    "call": "full",
    # Restored subsystems
    "risk_intelligence": "full",
    "world_state": "full",
    "calibration": "full",
    "forecast": "full",
    "history": "full",
}


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def resolve_api_profile(environ: Mapping[str, str] | None = None) -> str:
    """Resolve the profile, defaulting production to the least surface."""
    env = os.environ if environ is None else environ
    configured = str(env.get("SCP_API_PROFILE", "")).strip().lower()
    if not configured:
        return "core" if _truthy(env.get("SCP_PRODUCTION_MODE")) else "full"
    if configured not in PROFILE_LEVEL:
        allowed = ", ".join(PROFILE_LEVEL)
        raise RuntimeError(f"invalid SCP_API_PROFILE={configured!r}; expected one of: {allowed}")
    return configured


def route_group_enabled(group: str, profile: str) -> bool:
    if profile not in PROFILE_LEVEL:
        raise RuntimeError(f"unknown API profile: {profile}")
    minimum = GROUP_MINIMUM.get(group)
    if minimum is None:
        raise RuntimeError(f"unclassified API route group: {group}")
    return PROFILE_LEVEL[profile] >= PROFILE_LEVEL[minimum]
