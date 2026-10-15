"""Generate a failing reproduction test for the autofix loop.

[S3-SECURITY-SWEEP] Hardening (HIGH path-traversal fix + code-injection
hygiene): ``issue_desc`` is external finding text — line breaks and control
characters are stripped so it cannot escape the generated ``#`` comment into
executable code — and the write target is resolved + contained inside the
current working directory before any write.
"""
import os
from pathlib import Path

from scp.autofix.path_guard import ensure_within, sanitize_comment_text


def generate_repro_test(issue_desc: str):
    test_code = f"""import pytest

def test_reproduction():
    # Issue: {sanitize_comment_text(issue_desc, 100)}
    assert False, "Failing test generated from issue for autofix loop"
"""
    target = ensure_within(os.getcwd(), "tests/test_dynamic_repro.py")
    if target is None:
        raise ValueError("repro test path escapes the working directory")
    with Path(target).open("w", encoding="utf-8") as f:
        f.write(test_code)
    return "tests/test_dynamic_repro.py"
