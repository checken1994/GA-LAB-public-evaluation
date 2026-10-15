"""Shared storage configuration; resolving a path performs no filesystem writes."""
from __future__ import annotations

import os
from pathlib import Path


def runtime_data_dir() -> Path:
    configured = os.environ.get("SCP_DATA_DIR", "").strip()
    return (Path(configured).expanduser() if configured else
            Path(__file__).resolve().parents[2] / "data").resolve()


def runtime_path(env_key: str, filename: str) -> Path:
    """An explicit component path wins; otherwise use the configured data root."""
    configured = os.environ.get(env_key, "").strip()
    return (Path(configured).expanduser() if configured else
            runtime_data_dir() / filename).resolve()
