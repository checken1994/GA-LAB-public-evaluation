"""[A8] Sandbox evaluator argv-injection gate pins — audit remediation round 2.

Lỗ hổng đã chứng minh (script B5): ``_safe_relpath("--version")`` trả
``"--version"`` (relative path hợp lệ) -> key của ``test_files`` chảy thẳng
vào pytest argv -> ``pytest --version`` exit 0 -> **PASS với 0 test**.

Fail-closed contract sau fix:
  - key test_files bắt đầu ``-`` (argv-flag-shaped) -> FAIL setup;
  - key không kết thúc ``.py`` -> FAIL setup;
  - key traversal/absolute -> FAIL setup (guard _safe_relpath/_contained_path
    GIỮ NGUYÊN — chỉ thêm gate trước argv);
  - pytest exit 0 nhưng output không chứng minh >=1 test chạy -> FAIL
    ``no_tests_reported`` (``no tests ran`` không phải PASS — Reality Verifier);
  - 1 test benign -> PASS như cũ.
"""
from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from scp.sandbox_evaluator import evaluator
from scp.sandbox_evaluator.evaluator import _count_tests_reported, _test_key_reject_reason, evaluate


# ---------------------------------------------------------------
# Unit: key rejection (A8 gate)
# ---------------------------------------------------------------

@pytest.mark.parametrize("key", ["--version", "-x", "--collect-only", "-k test_a", "--rootdir=."])
def test_flag_shaped_keys_rejected(key):
    assert _test_key_reject_reason(key) == "argv_flag_shaped"


@pytest.mark.parametrize("key", ["test_ok.txt", "conftest.cfg", "helper"])
def test_non_python_keys_rejected(key):
    assert _test_key_reject_reason(key) == "not_python_file"


def test_benign_key_accepted():
    assert _test_key_reject_reason("test_calc.py") is None
    assert _test_key_reject_reason("tests/test_x.py") is None


# ---------------------------------------------------------------
# Integration: evaluate() fail-closed tại boundary setup
# ---------------------------------------------------------------

def _patch_with_test_key(key: str, test_body: str = "def test_a(): assert True\n") -> dict:
    return {
        "files": {"calc.py": "def add(a, b):\n    return a + b\n"},
        "test_files": {key: test_body},
        "timeout_seconds": 20,
    }


@pytest.mark.parametrize("key", ["--version", "-x", "--collect-only"])
def test_evaluate_flag_key_fails_setup(key):
    """Key argv-flag phải FAIL TRƯỚC khi pytest được spawn (returncode None)."""
    result = evaluate(_patch_with_test_key(key))
    assert result.verdict == "FAIL"
    assert result.returncode is None  # pytest KHÔNG hề được chạy
    assert result.reason.startswith("setup:test_file_rejected:argv_flag_shaped")


def test_evaluate_non_py_key_fails_setup():
    result = evaluate(_patch_with_test_key("test_ok.txt"))
    assert result.verdict == "FAIL"
    assert result.returncode is None
    assert result.reason.startswith("setup:test_file_rejected:not_python_file")


def test_evaluate_traversal_key_fails_setup():
    result = evaluate(_patch_with_test_key("../traversal_test.py"))
    assert result.verdict == "FAIL"
    assert result.returncode is None
    assert result.reason.startswith("setup:")


def test_evaluate_absolute_key_fails_setup():
    result = evaluate(_patch_with_test_key("C:/evil/test_abs.py"))
    assert result.verdict == "FAIL"
    assert result.returncode is None
    assert result.reason.startswith("setup:")


def test_evaluate_benign_single_test_still_passes():
    """Regression guard: fix KHÔNG được hạ khả năng PASS của test benign."""
    result = evaluate(_patch_with_test_key("test_calc.py"))
    assert result.verdict == "PASS"
    assert result.returncode == 0
    assert _count_tests_reported(result.stdout) >= 1


# ---------------------------------------------------------------
# A8 hardening: exit 0 nhưng 0 test chạy được chứng minh -> FAIL
# ---------------------------------------------------------------

def _fake_completed(returncode: int, stdout: str):
    return SimpleNamespace(returncode=returncode, stdout=stdout.encode("utf-8"),
                           stderr=b"", args=["pytest"])


def test_exit0_without_test_report_fails_closed(monkeypatch):
    """pytest exit 0 + stdout không có summary 'N passed' -> FAIL no_tests_reported.

    Đây là lá chắn thứ hai: kể cả khi argv đã sạch, PASS vẫn chỉ hợp lệ khi
    pytest CHỨNG MINH được đã chạy ít nhất 1 test (Reality Verifier:
    ``no tests ran`` không phải PASS).
    """
    def _fake_run(*args, **kwargs):
        return _fake_completed(0, "no tests ran in 0.01s\n")
    monkeypatch.setattr(evaluator.subprocess, "run", _fake_run)
    result = evaluate(_patch_with_test_key("test_calc.py"))
    assert result.verdict == "FAIL"
    assert result.reason == "no_tests_reported"


def test_count_tests_reported_semantics():
    assert _count_tests_reported("") == 0
    assert _count_tests_reported("no tests ran in 0.01s") == 0
    assert _count_tests_reported("1 passed in 0.02s") == 1
    assert _count_tests_reported("3 passed, 2 skipped in 0.1s") == 5
    assert _count_tests_reported("1 failed in 0.02s") == 1
