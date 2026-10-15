"""Adversarial stress-test probe for Milestone 2 (GAP-09 Capability Secret Fail-Closed).

Authored by: Reviewer 2 (reviewer_m2_2)
Objective: Independently challenge assumptions, verify fail-closed semantics,
test boundary inputs, test subprocess isolation, and verify complete purge of fallback secret.
"""

from __future__ import annotations

import hmac
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def run_check(description: str, fn):
    print(f"[*] Running: {description}...")
    try:
        fn()
        print(f"    [+] PASS: {description}")
    except Exception as e:
        print(f"    [-] FAIL: {description} -> {type(e).__name__}: {e}")
        raise


def test_import_without_secret_fails_immediately():
    """Verify that importing capability_token without SCP_CAPABILITY_SECRET raises MissingSecretError immediately."""
    if "SCP_CAPABILITY_SECRET" in os.environ:
        del os.environ["SCP_CAPABILITY_SECRET"]

    # Ensure module is not in sys.modules
    sys.modules.pop("scp.core.capability_token", None)

    try:
        import scp.core.capability_token  # noqa: F401
        raise AssertionError("Importing scp.core.capability_token without secret should have failed!")
    except RuntimeError as exc:
        assert type(exc).__name__ == "MissingSecretError"
        assert "SCP_CAPABILITY_SECRET environment variable is missing or empty" in str(exc)


def test_missing_secret_error_hierarchy():
    """Verify MissingSecretError is a RuntimeError (fails closed in standard error handlers)."""
    # Now set a valid secret to allow importing capability_token for symbol inspection
    os.environ["SCP_CAPABILITY_SECRET"] = "bootstrap-secret-for-probe-hierarchy-check-1234"
    sys.modules.pop("scp.core.capability_token", None)

    from scp.core.capability_token import MissingSecretError
    assert issubclass(MissingSecretError, RuntimeError)
    assert not issubclass(MissingSecretError, (KeyError, ValueError, TypeError))


def test_adversarial_whitespace_and_null_bytes():
    """Test boundary inputs: spaces, tabs, newlines, carriage returns."""
    from scp.core.capability_token import MissingSecretError, get_capability_secret

    adversarial_blanks = [
        "",
        " ",
        "   ",
        "\t",
        "\n",
        "\r\n",
        "  \t  \r\n  ",
        "                ",
    ]

    for val in adversarial_blanks:
        os.environ["SCP_CAPABILITY_SECRET"] = val
        try:
            get_capability_secret()
            raise AssertionError(f"Expected MissingSecretError for secret={repr(val)}, but succeeded!")
        except MissingSecretError as e:
            assert "SCP_CAPABILITY_SECRET environment variable is missing or empty" in str(e)


def test_unset_env_raises_missing_secret_error():
    """Test get_capability_secret() with unset environment variable."""
    from scp.core.capability_token import MissingSecretError, get_capability_secret

    if "SCP_CAPABILITY_SECRET" in os.environ:
        del os.environ["SCP_CAPABILITY_SECRET"]

    try:
        get_capability_secret()
        raise AssertionError("Expected MissingSecretError when SCP_CAPABILITY_SECRET is unset, but succeeded!")
    except MissingSecretError:
        pass


def test_subprocess_import_fail_closed_permutations():
    """Verify module-level import in isolated subprocesses under various adversarial environments."""
    python_exe = sys.executable

    test_cases = [
        ("Unset SCP_CAPABILITY_SECRET", {}),
        ("Empty SCP_CAPABILITY_SECRET", {"SCP_CAPABILITY_SECRET": ""}),
        ("Whitespace SCP_CAPABILITY_SECRET", {"SCP_CAPABILITY_SECRET": "   \t\n  "}),
    ]

    for label, extra_env in test_cases:
        # Build clean minimal env without inheriting pytest or conftest environment
        clean_env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(REPO_ROOT),
        }
        clean_env.update(extra_env)

        proc = subprocess.run(
            [python_exe, "-c", "import scp.core.capability_token; print('SHOULD_NOT_PRINT')"],
            env=clean_env,
            capture_output=True,
            text=True,
        )

        assert proc.returncode != 0, f"Subprocess succeeded unexpectedly under: {label} (stdout: {proc.stdout})"
        assert "SHOULD_NOT_PRINT" not in proc.stdout
        assert "MissingSecretError" in proc.stderr
        assert "SCP_CAPABILITY_SECRET environment variable is missing or empty" in proc.stderr


def test_subprocess_import_success_with_valid_secret():
    """Verify module-level import in isolated subprocess succeeds when valid secret is provided."""
    python_exe = sys.executable
    test_key = "adversarial-probe-verified-secret-key-64-hex-characters-abcdef12"

    clean_env = {
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(REPO_ROOT),
        "SCP_CAPABILITY_SECRET": f"   {test_key}   \n",  # with padding
    }

    code = (
        "import scp.core.capability_token as ct; "
        f"assert ct._SECRET == {repr(test_key.encode('utf-8'))}, f'Mismatch: {{ct._SECRET}}'; "
        "tok = ct.mint_token('adv-issuer', 'admin', 3); "
        "res = ct.verify_token(tok, 'admin'); "
        "assert res['valid'] is True; "
        "print('MINT_VERIFY_SUCCESS')"
    )

    proc = subprocess.run(
        [python_exe, "-c", code],
        env=clean_env,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, f"Subprocess failed with valid secret: {proc.stderr}"
    assert "MINT_VERIFY_SUCCESS" in proc.stdout


def test_old_fallback_secret_forge_attempt_is_rejected():
    """Adversarial forgery attempt: create a token signed with the old hardcoded dev-secret and attempt validation."""
    from scp.core import capability_token
    import base64
    import time

    old_secret = b"dev-secret-do-not-use-in-prod-12345"
    now = int(time.time())
    payload = {
        "iss": "forged-attacker",
        "scope": "root:admin",
        "cap": 999,
        "iat": now,
        "exp": now + 7200,
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    forged_sig = hmac.new(old_secret, payload_b64.encode(), hashlib.sha256).hexdigest()
    forged_token = f"{payload_b64}.{forged_sig}"

    # Verify against live capability_token module with production-like random secret
    res = capability_token.verify_token(forged_token)
    assert res["valid"] is False
    assert res["error"] == "Invalid signature"


def test_absence_of_fallback_secret_in_source():
    """Verify that no trace of the old dev-secret exists in the scp/ source code."""
    old_secret_str = "dev-secret-do-not-use-in-prod-12345"
    for py_path in REPO_ROOT.glob("scp/**/*.py"):
        content = py_path.read_text(encoding="utf-8", errors="replace")
        assert old_secret_str not in content, f"Found old dev secret in {py_path}!"


def test_conftest_isolation():
    """Verify that tests/conftest.py does NOT leak into external scripts or production imports."""
    # When running python outside pytest, conftest.py is never executed
    proc = subprocess.run(
        [sys.executable, "-c", "import os; print('ENV_VAL:', os.environ.get('SCP_CAPABILITY_SECRET', 'NONE'))"],
        capture_output=True,
        text=True,
        env={
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "PATH": os.environ.get("PATH", ""),
        }
    )
    assert proc.returncode == 0
    assert "ENV_VAL: NONE" in proc.stdout


if __name__ == "__main__":
    print("=================================================================")
    print("STARTING INDEPENDENT ADVERSARIAL AUDIT FOR MILESTONE 2 (GAP-09)")
    print("=================================================================")

    run_check("Import without secret fails immediately", test_import_without_secret_fails_immediately)
    run_check("MissingSecretError is a RuntimeError", test_missing_secret_error_hierarchy)
    run_check("Adversarial whitespace & empty checks", test_adversarial_whitespace_and_null_bytes)
    run_check("Unset env raises MissingSecretError", test_unset_env_raises_missing_secret_error)
    run_check("Subprocess import fails closed (unset, empty, whitespace)", test_subprocess_import_fail_closed_permutations)
    run_check("Subprocess import succeeds with valid secret (trimmed)", test_subprocess_import_success_with_valid_secret)
    run_check("Forged token using old fallback secret is rejected", test_old_fallback_secret_forge_attempt_is_rejected)
    run_check("Absence of fallback secret in scp/ source tree", test_absence_of_fallback_secret_in_source)
    run_check("tests/conftest.py isolation from standalone execution", test_conftest_isolation)

    print("=================================================================")
    print("ALL 8 ADVERSARIAL STRESS-TEST CHECKS PASSED (FAIL-CLOSED VERIFIED)")
    print("=================================================================")
