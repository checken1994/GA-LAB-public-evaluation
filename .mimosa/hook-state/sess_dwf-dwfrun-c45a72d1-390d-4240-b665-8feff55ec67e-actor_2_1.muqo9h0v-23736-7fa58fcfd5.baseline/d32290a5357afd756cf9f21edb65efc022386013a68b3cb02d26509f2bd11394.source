# Auto-extracted from cross_func_taint_scanner.py
from __future__ import annotations

import logging

from scp.autofix.classifier import BugReport
from scp.autofix.scanners.taint_flow_scanner import (
    _iter_python_files,
)

logger = logging.getLogger(__name__)

def scan_scp() -> list[BugReport]:
    """Scan the entire SCP package for CROSS-FUNCTION taint bugs.

    Walks `scp/` recursively (up to _MAX_FILES=500 files), skipping tests,
    __pycache__, examples, scripts, attack_payloads, and benchmark dirs.

    Returns:
        List of BugReports with bug_type="CrossFuncTaint_CWE-XXX". Each
        report captures a confirmed source→callee→sink dataflow across
        two or more functions (the intra-function scanner misses these).
    """
    scanner = _CrossFuncScanner()  # noqa: F821  # [hygiene-keep] _CrossFuncScanner injected by cross_func_taint_scanner.py rebind/wire
    files_scanned = 0
    for path in _iter_python_files(_SCP_ROOT, limit=_MAX_FILES):  # noqa: F821  # [hygiene-keep] _SCP_ROOT injected by cross_func_taint_scanner.py rebind/wire
        files_scanned += 1
        try:
            scanner.add_file(path)
        except Exception as e:
            logger.warning(f'Error adding {path} to call graph: {e}', exc_info=True)
    scanner.run_fixpoint()
    bugs = scanner.detect_bugs()
    logger.info(f'[CrossFuncTaintScanner] found {len(bugs)} cross-function taint bug(s) across {len(scanner.funcs_by_qualname)} functions (scanned {files_scanned} files)')
    return bugs
