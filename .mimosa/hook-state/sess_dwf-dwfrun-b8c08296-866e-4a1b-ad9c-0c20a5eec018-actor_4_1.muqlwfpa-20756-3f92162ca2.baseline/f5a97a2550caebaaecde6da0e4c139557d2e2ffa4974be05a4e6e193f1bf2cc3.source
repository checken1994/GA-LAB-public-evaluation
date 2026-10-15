"""Verify that the current checkout is the single canonical GA-LAB root."""
from __future__ import annotations

import shutil
import subprocess  # nosec B404 - fixed local git executable, no shell, no user command input
from pathlib import Path

EXPECTED_REMOTE_PARTS = ("github.com/checken1994/GA-LAB", "github.com:checken1994/GA-LAB")
RETIRED_WORKSPACES = {"scp-agent-structure-debt", "scp-structure-debt-worktree"}


def git(*args: str) -> str:
    executable = shutil.which("git")
    if not executable:
        raise OSError("git executable is unavailable")
    return subprocess.check_output([executable, *args], text=True, stderr=subprocess.STDOUT).strip()  # nosec B603


def main() -> int:
    root = Path.cwd()
    problems: list[str] = []
    try:
        if git("rev-parse", "--is-inside-work-tree") != "true":
            problems.append("not inside a git worktree")
        remote = git("remote", "get-url", "origin")
        if not any(part in remote for part in EXPECTED_REMOTE_PARTS):
            problems.append(f"origin is not canonical GA-LAB: {remote}")
        branch = git("branch", "--show-current")
        if not branch:
            problems.append("detached HEAD is not allowed for development")
    except (subprocess.CalledProcessError, OSError) as exc:
        problems.append(f"git identity check failed: {exc}")

    nested_git = [p for p in root.rglob(".git") if p != root / ".git"]
    if nested_git:
        problems.append("nested git metadata found: " + ", ".join(str(p.relative_to(root)) for p in nested_git))
    for retired in sorted(RETIRED_WORKSPACES):
        for path in root.rglob(retired):
            relative = path.relative_to(root)
            # Archived provenance may mention the retired name; only an active
            # workspace outside the archive namespace is a violation.
            if relative.parts[:2] == ("reports", "archived_workspaces_20260826"):
                continue
            problems.append(f"retired workspace reintroduced: {retired}")

    if problems:
        print("canonical root: FAIL")
        print("\n".join(f"- {problem}" for problem in problems))
        return 1
    print("canonical root: PASS")
    print(f"root={root}")
    print(f"remote={git('remote', 'get-url', 'origin')}")
    print(f"branch={git('branch', '--show-current')}")
    print(f"commit={git('rev-parse', 'HEAD')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
