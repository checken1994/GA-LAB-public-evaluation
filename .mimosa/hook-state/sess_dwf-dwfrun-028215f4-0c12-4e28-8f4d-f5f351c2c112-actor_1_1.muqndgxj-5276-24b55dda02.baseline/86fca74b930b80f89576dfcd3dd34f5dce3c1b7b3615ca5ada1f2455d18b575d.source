# Auto-extracted from cross_func_taint_scanner.py
from __future__ import annotations

from scp.autofix.scanners.taint_flow_scanner import (
    _iter_python_files,
)


def _get_scp_call_graph() -> _CrossFuncScanner:  # noqa: F821  # [hygiene-keep] _CrossFuncScanner injected by cross_func_taint_scanner.py rebind/wire
    """Build (once) and return the scp/ call graph.

    Subsequent calls return the cached call graph. Used by scan_file() to
    avoid rebuilding the scp/ call graph for every file scan.
    """
    global _SCP_CALL_GRAPH_CACHE
    if _SCP_CALL_GRAPH_CACHE is not None:
        return _SCP_CALL_GRAPH_CACHE
    scanner = _CrossFuncScanner()  # noqa: F821  # [hygiene-keep] _CrossFuncScanner injected by cross_func_taint_scanner.py rebind/wire
    files_added = 0
    for path in _iter_python_files(_SCP_ROOT, limit=_MAX_FILES):  # noqa: F821  # [hygiene-keep] _SCP_ROOT injected by cross_func_taint_scanner.py rebind/wire
        scanner.add_file(path)
        files_added += 1
    scanner.run_fixpoint()
    logger.info(f'[CrossFuncTaint] built scp/ call graph: {len(scanner.funcs_by_qualname)} functions across {files_added} files')  # noqa: F821  # [hygiene-keep] logger injected by cross_func_taint_scanner.py rebind/wire
    _SCP_CALL_GRAPH_CACHE = scanner
    return scanner
