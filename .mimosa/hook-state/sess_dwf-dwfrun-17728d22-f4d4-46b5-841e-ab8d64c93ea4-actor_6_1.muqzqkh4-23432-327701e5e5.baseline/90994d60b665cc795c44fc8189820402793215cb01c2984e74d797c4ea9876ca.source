from pathlib import Path
from unittest.mock import patch

from scp.autofix.classifier import BugReport, BugTier
from scp.autofix.runner import run_once
from scp.autofix.runner_phases.ast_scan import _is_protected_path


class DummyWhyResult:
    allowed = True

@patch("scp.meta.why_gate.WhyGate.gate")
def test_autofix_protected_path_blocked(mock_gate):
    mock_gate.return_value = DummyWhyResult()

    bug = BugReport(
        file='scp/autofix/policy_gate.py',
        line=1,
        bug_type='test_bug',
        description='Test bug',
        suggested_fix='<<<<<<< SEARCH\nfoo\n=======\nbar\n>>>>>>> REPLACE',
        tier=BugTier.TIER_1_AUTO_FIX
    )
    summary = run_once(bugs=[bug], deterministic_only=False)

    assert len(summary['details']) == 1
    assert summary['details'][0]['result']['action'] == 'protected_path_blocked'


# =========================================================================
# [PERM-03 FIX] Path normalization regression tests.
#
# Probe BEFORE the fix (Windows):
#   _is_protected_path(r"D:\scp\scp\autofix\engine.py") -> False
# The gate was vacuous for absolute Windows paths (backslash separators
# never substring-matched the POSIX-style PROTECTED_PATHS entries), so
# autofix could rewrite its own security files.
# =========================================================================

class TestIsProtectedPathNormalization:
    def _native_abs(self, module) -> str:
        """Native absolute path (backslashes on Windows, slashes on POSIX)."""
        return str(Path(module.__file__).resolve())

    def test_windows_absolute_path_of_protected_file_is_blocked(self):
        import scp.autofix.engine as engine_mod
        assert _is_protected_path(self._native_abs(engine_mod)) is True

    def test_posix_absolute_form_is_blocked(self):
        import scp.autofix.engine as engine_mod
        posix_abs = Path(engine_mod.__file__).resolve().as_posix()
        assert _is_protected_path(posix_abs) is True

    def test_relative_posix_form_is_blocked(self):
        assert _is_protected_path("scp/autofix/engine.py") is True

    def test_benign_autofix_file_is_not_blocked(self):
        import scp.autofix.monitor as monitor_mod
        assert _is_protected_path(self._native_abs(monitor_mod)) is False
        assert _is_protected_path("scp/autofix/monitor.py") is False

    def test_repo_tests_dir_protected_via_absolute_windows_path(self):
        tests_root = Path(__file__).resolve().parent
        candidate = str(tests_root / "some_helper_module.py")
        assert _is_protected_path(candidate) is True
