"""Cross-function taint scanner public contract with explicit part wiring."""
from __future__ import annotations

import ast
import logging
import types
from collections import defaultdict  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
from dataclasses import dataclass, field  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
from scp.autofix.scanners.taint_flow_scanner import (
    _CWE_TITLES,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    _HEURISTIC_PARAM_NAMES,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    _MARSHAL_FUNCS,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    _PICKLE_FUNCS,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    _SQL_EXECUTE_NAMES,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    _SUBPROCESS_FUNCS,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    _XSS_BUILDERS,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    _collect_names,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    _is_sanitizer_call,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    _is_source,
    _iter_python_files,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
)

logger = logging.getLogger("scp.autofix.scanners.cross_func_taint")
_SCP_ROOT = Path(__file__).resolve().parent.parent.parent
_MAX_FILES = 500
_MAX_FIXPOINT_ROUNDS = 10
_BUILTIN_INPUT_FUNCS: frozenset[str] = frozenset({"input", "raw_input"})


def _xfunc_is_source(node) -> tuple[str, str] | None:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in _BUILTIN_INPUT_FUNCS:
            return ("cli", f"{node.func.id}()")
    return _is_source(node)


@dataclass
class CallEdge:
    callee_name: str
    arg_param: str
    call_line: int
    arg_pos: int
    in_return: bool


@dataclass
class SinkHit:
    cwe: str
    sink_name: str
    sink_line: int
    via_callee: str | None = None
    via_callee_file: str | None = None
    via_callee_param: str | None = None


from .cross_func_taint_scanner_parts import _callgraphbuilder as _p_callgraph
from .cross_func_taint_scanner_parts import _classify_sink_xfunc as _p_classify
from .cross_func_taint_scanner_parts import _crossfuncscanner as _p_scanner
from .cross_func_taint_scanner_parts import _functiondetector as _p_detector
from .cross_func_taint_scanner_parts import _get_scp_call_graph as _p_graph
from .cross_func_taint_scanner_parts import _run_fixpoint as _p_fixpoint
from .cross_func_taint_scanner_parts import functioninfo as _p_functioninfo
from .cross_func_taint_scanner_parts import scan_file as _p_scan_file
from .cross_func_taint_scanner_parts import scan_scp as _p_scan_scp

_PARTS = (
    _p_functioninfo,
    _p_classify,
    _p_callgraph,
    _p_fixpoint,
    _p_detector,
    _p_scanner,
    _p_graph,
    _p_scan_file,
    _p_scan_scp,
)


def _wire_parts() -> None:
    shared = dict(globals())
    for part in _PARTS:
        part.__dict__.update(shared)


def _rebind_part_function(fn):
    """Bind extracted scanner functions to this module's canonical cache/state."""
    rebound = types.FunctionType(fn.__code__, globals(), fn.__name__, fn.__defaults__, fn.__closure__)
    rebound.__kwdefaults__ = fn.__kwdefaults__
    rebound.__annotations__ = dict(getattr(fn, "__annotations__", {}))
    rebound.__doc__ = fn.__doc__
    rebound.__module__ = __name__
    return rebound


_wire_parts()
FunctionInfo = _p_functioninfo.FunctionInfo
_classify_sink_xfunc = _p_classify._classify_sink_xfunc
_CallGraphBuilder = _p_callgraph._CallGraphBuilder
_run_fixpoint = _p_fixpoint._run_fixpoint
_FunctionDetector = _p_detector._FunctionDetector
_CrossFuncScanner = _p_scanner._CrossFuncScanner
_wire_parts()

_SCP_CALL_GRAPH_CACHE: _CrossFuncScanner | None = None


def _clone_call_graph(base: _CrossFuncScanner) -> _CrossFuncScanner:
    new = _CrossFuncScanner()
    for qualname, info in base.funcs_by_qualname.items():
        new.funcs_by_qualname[qualname] = info
    for name, entries in base.funcs_by_name.items():
        new.funcs_by_name[name] = list(entries)
    new._fixpoint_done = True
    return new


_wire_parts()
_get_scp_call_graph = _rebind_part_function(_p_graph._get_scp_call_graph)
scan_file = _rebind_part_function(_p_scan_file.scan_file)
scan_scp = _rebind_part_function(_p_scan_scp.scan_scp)
_wire_parts()

__all__ = ["scan_file", "scan_scp"]
