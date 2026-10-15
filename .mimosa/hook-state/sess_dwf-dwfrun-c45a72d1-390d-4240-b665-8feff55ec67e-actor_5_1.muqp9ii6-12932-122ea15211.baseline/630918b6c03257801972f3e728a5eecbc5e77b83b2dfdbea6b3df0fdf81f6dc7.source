"""Tests verifying fail-closed handling of SCP_CAPABILITY_SECRET (GAP-09).

Ensures that the capability token subsystem strictly requires a cryptographic
secret and fails closed (raising MissingSecretError) whenever the secret is
unset, empty, or whitespace-only, with no insecure fallback secret.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from scp.core import capability_token
from scp.core.capability_token import MissingSecretError, get_capability_secret


def test_missing_secret_error_is_runtime_error() -> None:
    """MissingSecretError must inherit from RuntimeError for fail-closed safety."""
    assert issubclass(MissingSecretError, RuntimeError)
    err = MissingSecretError("test message")
    assert isinstance(err, RuntimeError)
    assert str(err) == "test message"


def test_get_capability_secret_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """When SCP_CAPABILITY_SECRET is set, get_capability_secret() returns UTF-8 bytes."""
    test_secret = "super-secret-cryptographic-key-1234567890"
    monkeypatch.setenv("SCP_CAPABILITY_SECRET", test_secret)

    secret_bytes = get_capability_secret()
    assert secret_bytes == test_secret.encode("utf-8")
    assert isinstance(secret_bytes, bytes)


def test_get_capability_secret_strips_surrounding_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Surrounding whitespace should be trimmed from the secret."""
    test_secret = "key-with-padding"
    monkeypatch.setenv("SCP_CAPABILITY_SECRET", f"  {test_secret}  \n")

    assert get_capability_secret() == test_secret.encode("utf-8")


def test_get_capability_secret_missing_raises_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """When SCP_CAPABILITY_SECRET is unset, get_capability_secret() raises MissingSecretError."""
    monkeypatch.delenv("SCP_CAPABILITY_SECRET", raising=False)

    with pytest.raises(MissingSecretError) as exc_info:
        get_capability_secret()

    expected_msg = (
        "SCP_CAPABILITY_SECRET environment variable is missing or empty. "
        "A cryptographic secret is required to sign and verify capability tokens (GAP-09)."
    )
    assert expected_msg in str(exc_info.value)


@pytest.mark.parametrize("empty_val", ["", "   ", "\t", "\n", "  \r\n  "])
def test_get_capability_secret_empty_or_whitespace_raises_fail_closed(
    monkeypatch: pytest.MonkeyPatch, empty_val: str
) -> None:
    """Empty or whitespace-only SCP_CAPABILITY_SECRET must raise MissingSecretError."""
    monkeypatch.setenv("SCP_CAPABILITY_SECRET", empty_val)

    with pytest.raises(MissingSecretError) as exc_info:
        get_capability_secret()

    assert "SCP_CAPABILITY_SECRET environment variable is missing or empty" in str(exc_info.value)


def test_module_import_fails_closed_in_clean_subprocess_when_unset() -> None:
    """In a clean Python subprocess where SCP_CAPABILITY_SECRET is unset, importing capability_token must fail."""
    env = {k: v for k, v in os.environ.items() if k != "SCP_CAPABILITY_SECRET"}
    code = "import scp.core.capability_token"

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "MissingSecretError" in result.stderr
    assert "SCP_CAPABILITY_SECRET environment variable is missing or empty" in result.stderr


def test_module_import_fails_closed_in_clean_subprocess_when_empty() -> None:
    """In a clean Python subprocess where SCP_CAPABILITY_SECRET='', importing capability_token must fail."""
    env = dict(os.environ)
    env["SCP_CAPABILITY_SECRET"] = ""
    code = "import scp.core.capability_token"

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "MissingSecretError" in result.stderr
    assert "SCP_CAPABILITY_SECRET environment variable is missing or empty" in result.stderr


def test_module_import_succeeds_in_clean_subprocess_when_set() -> None:
    """In a clean Python subprocess where SCP_CAPABILITY_SECRET is valid, import succeeds and exposes correct _SECRET."""
    env = dict(os.environ)
    test_secret = "isolated-test-secret-value-abcdef123456"
    env["SCP_CAPABILITY_SECRET"] = test_secret
    code = (
        "import scp.core.capability_token as ct; "
        f"assert ct._SECRET == b'{test_secret}'; "
        "token = ct.mint_token('sub-test', 'read', 1); "
        "verified = ct.verify_token(token); "
        "assert verified['valid'] is True; "
        "print('SUBPROCESS_PASS')"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "SUBPROCESS_PASS" in result.stdout


def test_no_hardcoded_fallback_secret_remains() -> None:
    """Verify that the insecure dev fallback secret b'dev-secret-do-not-use-in-prod-12345' is purged."""
    fallback = b"dev-secret-do-not-use-in-prod-12345"
    assert capability_token._SECRET != fallback

    # Check source file content directly to ensure fallback string literal does not exist in code
    source_file = os.path.abspath(capability_token.__file__)
    with open(source_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "dev-secret-do-not-use-in-prod-12345" not in content
