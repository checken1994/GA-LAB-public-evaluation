"""Pytest configuration for external audit tests.

RC-10 fix — break circular self-audit by providing an INDEPENDENT test harness.

Notes:
- These tests intentionally do NOT import SCP modules (avoid circular trust).
- They shell out to external tools (ruff, bandit, grep) and assert on output.
- If ruff/bandit/grep is not installed, the test is skipped (not failed) —
  this keeps CI green on minimal environments, but a production CI MUST
  install all three.
"""
import os
import shutil
import sys

import pytest

# Make the SCP package importable when these tests need to inspect source paths.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCP_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _SCP_ROOT not in sys.path:
    sys.path.insert(0, _SCP_ROOT)


def pytest_collection_modifyitems(config, items):
    """Mark tests that need external tools — skip if tool missing."""
    for item in items:
        # Tests named test_no_*_via_<tool> require that tool on PATH.
        if "via_ruff" in item.nodeid and shutil.which("ruff") is None:
            item.add_marker(pytest.mark.skip(reason="ruff not installed"))
        if "via_bandit" in item.nodeid and shutil.which("bandit") is None:
            item.add_marker(pytest.mark.skip(reason="bandit not installed"))
        if "via_grep" in item.nodeid and shutil.which("grep") is None:
            item.add_marker(pytest.mark.skip(reason="grep not installed"))
