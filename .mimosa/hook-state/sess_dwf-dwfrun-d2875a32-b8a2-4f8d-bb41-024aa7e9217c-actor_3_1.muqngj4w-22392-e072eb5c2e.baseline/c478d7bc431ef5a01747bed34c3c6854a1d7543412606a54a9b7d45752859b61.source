# Auto-extracted from cross_func_taint_scanner.py
from __future__ import annotations

from pathlib import Path

from scp.autofix.classifier import BugReport


def scan_file(path: Path) -> list[BugReport]:
    """Scan a single Python file for CROSS-FUNCTION taint bugs.

    Builds a call graph from scp/ + the target file, then walks the target
    file's functions with cross-function awareness. Reports bugs whose
    CALLER is in the target file.

    NOTE: this scanner ONLY reports cross-function bugs (source and sink in
    DIFFERENT functions). Intra-function bugs are reported by
    taint_flow_scanner.py's scan_file().

    Args:
        path: Path to a .py file.

    Returns:
        List of BugReports with bug_type="CrossFuncTaint_CWE-XXX".
    """
    path = Path(path)
    base = _get_scp_call_graph()  # noqa: F821  # [hygiene-keep] _get_scp_call_graph injected by cross_func_taint_scanner.py rebind/wire
    scanner = _clone_call_graph(base)  # noqa: F821  # [hygiene-keep] _clone_call_graph injected by cross_func_taint_scanner.py rebind/wire
    scanner.add_file(path)
    scanner.run_fixpoint()
    return scanner.detect_bugs(only_in_files={str(path)})
