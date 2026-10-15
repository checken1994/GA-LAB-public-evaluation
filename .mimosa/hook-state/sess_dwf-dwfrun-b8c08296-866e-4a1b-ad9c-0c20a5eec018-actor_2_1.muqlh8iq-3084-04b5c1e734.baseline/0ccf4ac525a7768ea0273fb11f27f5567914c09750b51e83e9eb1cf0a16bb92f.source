"""Secret loading with optional file-backed injection and no value logging."""
from __future__ import annotations

import os
from pathlib import Path


def read_secret(env_name: str, file_env_name: str) -> str:
    path_value = os.environ.get(file_env_name, "").strip()
    if path_value:
        p = Path(path_value).expanduser()
        if not p.is_file():
            raise RuntimeError(f"{file_env_name} points to a missing secret file")
        value = p.read_text(encoding="utf-8").strip()
        if not value:
            raise RuntimeError(f"{file_env_name} points to an empty secret file")
        return value
    return os.environ.get(env_name, "").strip()
