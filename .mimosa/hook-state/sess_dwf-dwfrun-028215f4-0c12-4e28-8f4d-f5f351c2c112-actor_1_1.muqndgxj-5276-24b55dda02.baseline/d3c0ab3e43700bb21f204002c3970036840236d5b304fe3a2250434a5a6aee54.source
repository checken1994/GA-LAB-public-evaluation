#!/usr/bin/env python3
"""Run the P0 test baseline with the active Python environment."""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("baseline_enforcer")
ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    logger.info("Running P0 Baseline Check...")
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "tests/",
        "tests/internal/",
    ]
    logger.info("Running pytest with %s...", sys.executable)
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.error("Pytest infrastructure failed: %s: %s", type(exc).__name__, exc)
        return 2
    if result.returncode != 0:
        logger.error("Pytest failed; baseline is broken (code=%s).", result.returncode)
        if result.stdout:
            logger.error("pytest stdout:\n%s", result.stdout[-8000:])
        if result.stderr:
            logger.error("pytest stderr:\n%s", result.stderr[-8000:])
        return 1
    logger.info("Pytest passed within the configured baseline scope.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
