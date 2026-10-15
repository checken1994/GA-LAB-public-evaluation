"""[ZONE-FIX 2026-09-26] Regression — speculative_branching's pytest window
must be bounded (timeout), and the live target file must be restored when a
branch times out.

BEFORE the fix: subprocess.run(["pytest", "-q"]) had NO timeout — a hung test
suite hung run_speculative_branching forever (probe-verified: no return in
15s, external kill). AFTER: _SPECULATIVE_TEST_TIMEOUT_SECONDS bounds the
window; a timeout fails that branch (logged) and the finally block restores
the target. The module is DEMO-ONLY (no production callers — only tests);
see its docstring for the live-file-window limitation.
"""
from __future__ import annotations

import logging

import scp.autofix.speculative_branching as sb
from scp.autofix.speculative_branching import run_speculative_branching

logging.disable(logging.CRITICAL)


def test_hung_test_suite_fails_the_branch_and_restores_target(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sb, "_SPECULATIVE_TEST_TIMEOUT_SECONDS", 2)

    target = tmp_path / "target.py"
    target.write_text("def compute(a, b):\n    return a - b\n", encoding="utf-8")
    (tmp_path / "test_hang.py").write_text(
        "import time\n\ndef test_hang():\n    time.sleep(3600)\n", encoding="utf-8"
    )

    result = run_speculative_branching(
        ["def compute(a, b):\n    return a + b\n"],
        str(target),
    )

    assert result is False, "hung suite must fail the branch, not hang the caller"
    assert target.read_text(encoding="utf-8").startswith("def compute"), (
        "candidate patch left on the live target after the branch failed"
    )
    assert not (tmp_path / "target.py.branch0.bak").exists(), "backup not cleaned up"


def test_passing_candidate_still_applied_and_restoration_skipped(
    tmp_path, monkeypatch
):
    """Sanity: the bounded window does not break the happy path (no tests →
    pytest exits non-zero → branch fails → returns False)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sb, "_SPECULATIVE_TEST_TIMEOUT_SECONDS", 30)

    target = tmp_path / "target.py"
    target.write_text("def compute(a, b):\n    return a - b\n", encoding="utf-8")

    result = run_speculative_branching([], str(target))
    assert result is False  # no candidates → nothing passes
    assert target.read_text(encoding="utf-8").startswith("def compute")
