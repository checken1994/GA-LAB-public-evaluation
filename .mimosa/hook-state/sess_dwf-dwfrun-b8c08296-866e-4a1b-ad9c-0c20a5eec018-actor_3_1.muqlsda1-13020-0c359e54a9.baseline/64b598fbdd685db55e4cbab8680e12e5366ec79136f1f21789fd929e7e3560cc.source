"""Mutable context passed across AutoFix split phases."""
from __future__ import annotations

from pathlib import Path
from typing import Any


class FixContext:
    """Preserve the historical per-fix working namespace across mixin phases.

    The monolithic engine used local variables that later phases populated as
    work progressed.  The split uses this mutable object as the explicit
    equivalent; only the four construction-time fields are required.
    """

    def __init__(self, *, bug: Any, filepath: Path, report: bool, attack_mode: bool):
        self.bug = bug
        self.filepath = filepath
        self.report = report
        self.attack_mode = attack_mode
