"""Regression pin for the T00 pre-commit worktree ENOENT harness bug (2026-10-01).

Git exports its operation context to hook processes — notably
``GIT_INDEX_FILE=".git/index"`` (RELATIVE). ``run_git_cmd`` child commands
used to inherit it, so ``git worktree add`` inside the pre-commit hook
resolved index.lock against the NEW worktree (``<tmp>/.git/index.lock``
where ``.git`` is a file) and failed with ENOENT — blocking EVERY commit
in hook context while standalone T00 runs passed.

Contract: ``run_git_cmd`` must scrub the parent operation's git context
vars from the child subprocess environment. No audit rule is affected.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parents[2] / "tools" / "t00_meta_audit.py"

_GIT_CONTEXT_VARS = (
    "GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR",
    "GIT_PREFIX", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


def _load_tool():
    spec = importlib.util.spec_from_file_location("t00_meta_audit_under_test", _TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # required before exec_module (dataclasses)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("var", _GIT_CONTEXT_VARS)
def test_run_git_cmd_scrubs_parent_git_context_vars(monkeypatch, var):
    """The child subprocess env must never inherit the hook's git context."""
    module = _load_tool()
    for other in _GIT_CONTEXT_VARS:
        monkeypatch.setenv(other, ".git/index" if other == "GIT_INDEX_FILE" else other.lower())

    captured: dict = {}

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(args, **kwargs):
        captured["env"] = kwargs.get("env")
        return _Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module.run_git_cmd(["rev-parse", "HEAD"])

    env = captured["env"]
    assert env is not None, "run_git_cmd must pass an explicit (scrubbed) env"
    assert var not in env, (
        f"{var} leaked into the child git subprocess: hook context must not "
        "poison audit git commands (worktree add ENOENT blocker)"
    )


def test_real_git_worktree_add_survives_hook_env(monkeypatch, tmp_path):
    """End-to-end: with GIT_INDEX_FILE exported exactly like a pre-commit
    hook, run_git_cmd('worktree add') must succeed (the original blocker)."""
    module = _load_tool()
    monkeypatch.setenv("GIT_INDEX_FILE", ".git/index")

    worktree = tmp_path / "baseline-worktree"
    out = module.run_git_cmd(["worktree", "add", "-d", str(worktree), "HEAD"], check=False)
    try:
        assert worktree.exists(), (
            f"worktree add must succeed in hook-like env; stderr tail: {out!r}"
        )
    finally:
        module.run_git_cmd(["worktree", "remove", "-f", str(worktree)], check=False)
