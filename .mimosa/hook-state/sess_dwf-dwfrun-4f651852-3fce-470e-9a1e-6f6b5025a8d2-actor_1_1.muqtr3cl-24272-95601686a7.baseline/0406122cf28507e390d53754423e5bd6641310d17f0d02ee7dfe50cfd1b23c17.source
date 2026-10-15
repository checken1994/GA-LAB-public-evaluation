"""Canonical early environment loading for SCP server entrypoints."""
from __future__ import annotations

import os
from pathlib import Path


def load_selected_env() -> None:
    """Load the explicit env boundary before importing modules that read env.

    When SCP_ENV_FILE is set, its keys override the parent process environment.
    When it is absent, the repository .env is a compatibility fallback and does
    not override already-present parent variables. Values are never logged.
    """
    override = os.environ.get("SCP_ENV_FILE")
    if override:
        env_path = Path(override).expanduser()
        if not env_path.is_absolute():
            env_path = Path.cwd() / env_path
    else:
        # env_loader.py lives at <repo>/scp/security/ — parents[2] is the repo
        # root where the canonical .env lives. parents[1] pointed at the
        # package dir (scp/.env) which does not exist, silently loading nothing.
        env_path = Path(__file__).resolve().parents[2] / ".env"

    if not env_path.is_file():
        return

    text = env_path.read_text(encoding="utf-8-sig")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip(chr(34)).strip(chr(39))
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value


__all__ = ["load_selected_env"]
