#!/usr/bin/env python3
"""Fail closed if importing required SCP modules mutates the checkout source tree."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("scp", "scp.llm_gateway", "scp.task_kernel", "scp.api_server")


def _status() -> tuple[str, ...]:
    output = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    return tuple(line for line in output.splitlines() if line.strip())


def _print_delta(before: tuple[str, ...], after: tuple[str, ...]) -> None:
    before_set = set(before)
    new_entries = [line for line in after if line not in before_set]
    print("new checkout mutations:")
    for line in new_entries:
        print(f"  {line}")
    diff = subprocess.run(
        ["git", "diff", "--", "scp", "scripts", "tools", "tests"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    ).stdout
    if diff.strip():
        print("tracked source diff:")
        print(diff[:30000])
    for line in new_entries:
        if not line.startswith("?? "):
            continue
        rel = line[3:].strip()
        path = ROOT / rel
        if path.suffix != ".py" or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        print(f"untracked Python preview: {rel}")
        print("\n".join(text.splitlines()[:120]))


def main() -> int:
    baseline = _status()
    print(f"baseline status entries: {len(baseline)}")
    for module in MODULES:
        print(f"IMPORT_CHECK {module}")
        proc = subprocess.run(
            [sys.executable, "-c", f"import {module}; print('IMPORT_OK {module}')"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        print(proc.stdout, end="")
        if proc.returncode != 0:
            print(f"FAIL: import {module} exited {proc.returncode}")
            return proc.returncode or 1
        current = _status()
        if current != baseline:
            print(f"FAIL: import {module} mutated the checkout")
            _print_delta(baseline, current)
            return 1
    print("PASS: required imports are source-tree pure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
