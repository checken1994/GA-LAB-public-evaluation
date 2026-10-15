"""Canonical, fail-closed authentication configuration.

This module centralizes file/env precedence for backend and packaged runs. It
never logs or returns credential values in diagnostics.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class AuthConfigError(RuntimeError):
    """Authentication configuration is unsafe or unreadable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _clean(value: str | None) -> str:
    value = (value or "").lstrip("\ufeff").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def _file_value(file_env: str, raw_path: str) -> tuple[str, str]:
    path_text = _clean(raw_path)
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        value = path.read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        raise AuthConfigError(f"{file_env}_UNREADABLE") from exc
    value = _clean(value)
    if not value:
        raise AuthConfigError(f"{file_env}_EMPTY")
    return value, "file"


def _resolve_value(env_name: str, file_env: str) -> tuple[str, str]:
    direct = _clean(os.environ.get(env_name))
    file_ref = _clean(os.environ.get(file_env))
    if file_ref:
        from_file, source = _file_value(file_env, file_ref)
        if direct and direct != from_file:
            raise AuthConfigError(f"{env_name}_FILE_CONFLICT")
        return from_file, source
    if direct:
        return direct, "env"
    return "", "none"


@dataclass(frozen=True)
class AuthConfig:
    token: str
    password: str
    token_source: str
    password_source: str

    @property
    def configured(self) -> bool:
        return bool(self.token or self.password)

    # [SEC-FIX no-secret-oracle 2026-09-26] `config_digest` (sha256 over the
    # RAW token|password material) and `diagnostics()` were DELETED. They had
    # zero callers in the repo (AST sweep, probe-confirmed), and config_digest
    # was a deterministic offline brute-force oracle: anyone who ever saw the
    # digest could verify token guesses offline at sha256 speed, no live
    # system required. Diagnostics that need to identify a config must use
    # token_source/password_source and lengths only — never a digest of the
    # secret material.


def load_auth_config() -> AuthConfig:
    token, token_source = _resolve_value(
        "SCP_AUTH_TOKEN_SECRET", "SCP_AUTH_TOKEN_SECRET_FILE"
    )
    password, password_source = _resolve_value(
        "SCP_AUTH_PASSWORD", "SCP_AUTH_PASSWORD_FILE"
    )
    return AuthConfig(
        token=token,
        password=password,
        token_source=token_source,
        password_source=password_source,
    )


__all__ = ["AuthConfig", "AuthConfigError", "load_auth_config"]
