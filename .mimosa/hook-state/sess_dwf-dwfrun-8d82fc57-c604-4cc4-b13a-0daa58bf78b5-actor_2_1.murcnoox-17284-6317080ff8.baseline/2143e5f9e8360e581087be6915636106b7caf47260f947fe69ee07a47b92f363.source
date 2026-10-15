"""Canonical OpenRouter credential resolution for Python providers.

The loader accepts direct values or per-key secret-file references for the
three supported OpenRouter slots. It never logs or returns diagnostics that
contain credential values. Direct/file conflicts fail closed instead of
silently selecting one credential.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path

logger = logging.getLogger(__name__)



_OPENROUTER_SLOTS = (
    "OPENROUTER_API_KEY",
    "OPENROUTER_API_KEY_2",
    "OPENROUTER_API_KEY_3",
    "OPENROUTER_API_KEY_4",
    "OPENROUTER_API_KEY_5",
    "OPENROUTER_API_KEY_6",
    "OPENROUTER_API_KEY_7",
    "OPENROUTER_API_KEY_8",
    "OPENROUTER_API_KEY_9",
    "OPENROUTER_API_KEY_10",
)
_PLACEHOLDERS = {"your-key-here", "change-me", "changeme"}


class ProviderCredentialError(RuntimeError):
    """Raised when provider credential configuration is unsafe or unreadable."""


def _read_file_value(file_env: str, file_ref: str) -> str:
    path = Path(file_ref).expanduser()
    if not path.is_file():
        raise ProviderCredentialError(f"{file_env} points to a missing file")
    try:
        value = path.read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        raise ProviderCredentialError(
            f"{file_env} cannot be read ({type(exc).__name__})"
        ) from exc
    if not value:
        raise ProviderCredentialError(f"{file_env} is empty")
    return value


def load_openrouter_keys(environ: Mapping[str, str] | None = None) -> list[str]:
    """Return configured OpenRouter keys in deterministic slot order.

    A slot may use either ``OPENROUTER_API_KEY[_N]`` or its matching
    ``*_FILE`` variable. If both are present they must be byte-equivalent
    after UTF-8 BOM/newline normalization. Placeholder values are ignored.
    """
    env = os.environ if environ is None else environ
    keys: list[str] = []
    for slot in _OPENROUTER_SLOTS:
        direct = str(env.get(slot, "") or "").strip()
        file_env = f"{slot}_FILE"
        file_ref = str(env.get(file_env, "") or "").strip()
        from_file = _read_file_value(file_env, file_ref) if file_ref else ""
        if direct and from_file and direct != from_file:
            raise ProviderCredentialError(f"{slot} conflicts with {file_env}")
        value = from_file or direct
        if value and value.lower() not in _PLACEHOLDERS:
            keys.append(value)
    return keys


def provider_key_status(environ: Mapping[str, str] | None = None) -> dict[str, int | bool]:
    """Return sanitized provider readiness metadata without secret values."""
    try:
        keys = load_openrouter_keys(environ)
    except ProviderCredentialError:
        logger.debug('provider_key_status: ProviderCredentialError ignored', exc_info=True)
        return {"configured": False, "key_count": 0, "config_error": True}
    return {"configured": bool(keys), "key_count": len(keys), "config_error": False}
