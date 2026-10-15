"""Speculative branching: race N patch candidates against the test suite.

[S3-SECURITY-SWEEP] Hardening (HIGH path-traversal fix): the target file
flows into copy/write sinks, so it is validated (no parent-directory
components, must be an existing file) and resolved to an absolute path
before use. The per-branch backup name is derived from the resolved target,
so no traversal is possible through the backup path either.

STATUS (2026-09-26): DEMO-ONLY / NOT WIRED into the autofix engine — the only
callers are tests (tests/T03_capability/test_security_sweep_s3.py). Known
limitations that keep it out of production wiring:
  1. The candidate patch is written into the LIVE target file while pytest
     runs, so concurrent readers observe uncommitted content during the test
     window. A production integration must race candidates in an isolated
     worktree/sandbox copy instead of the live file.
  2. `pytest` inherits the current working directory and runs whatever suite
     it finds there.
Do NOT delete this module (it is the reference implementation for the
speculative-branching concept and is regression-covered); wire it only after
fixing limitation 1.

[XPROC-TIMEOUT 2026-09-26] The pytest subprocess is bounded by
_SPECULATIVE_TEST_TIMEOUT_SECONDS: a hung suite fails that branch (logged,
file restored by the finally block) instead of hanging the caller forever.
"""
import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Bounded test window per candidate branch (DoS guard: a hung/slow test suite
# used to block run_speculative_branching forever).
_SPECULATIVE_TEST_TIMEOUT_SECONDS = 120


def run_speculative_branching(patch_candidates: list[str], target_file: str):
    # Cơ chế Speculative Branching: chạy đua N giải pháp trong N container tạm
    # [S3-SECURITY-SWEEP] validate + resolve target before any write.
    target = Path(target_file)
    if ".." in target.parts:
        raise ValueError(
            f"target_file contains traversal components: {target_file!r}"
        )
    if not target.is_file():
        raise ValueError(f"target_file does not exist: {target_file!r}")
    resolved_target = target.resolve()
    best_patch = None
    best_rc = 1

    for i, patch in enumerate(patch_candidates):
        backup = str(resolved_target) + f".branch{i}.bak"
        shutil.copy(str(resolved_target), backup)
        try:
            with resolved_target.open("w") as f:
                f.write(patch)

            # Chạy tests trên nhánh spec (bounded — see _SPECULATIVE_TEST_TIMEOUT_SECONDS)
            try:
                result = subprocess.run(
                    ["pytest", "-q"],
                    capture_output=True,
                    timeout=_SPECULATIVE_TEST_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired:
                # Hung/slow suite → this branch FAILS (restore happens in the
                # finally below); the caller must never hang forever.
                logger.warning(
                    "speculative_branching: pytest exceeded %ss on branch %d — "
                    "branch failed, target restored",
                    _SPECULATIVE_TEST_TIMEOUT_SECONDS, i,
                )
                continue
            if result.returncode == 0:
                best_patch = patch
                best_rc = 0
                break # Found a passing patch
        finally:
            shutil.copy(backup, str(resolved_target))
            os.remove(backup)

    if best_rc == 0:
        with resolved_target.open("w") as f:
            f.write(best_patch)
        return True
    return False
