# Auto-extracted from cross_func_taint_scanner.py
from __future__ import annotations

import ast

from scp.autofix.scanners.taint_flow_scanner import (
    _MARSHAL_FUNCS,
    _PICKLE_FUNCS,
    _SQL_EXECUTE_NAMES,
    _SUBPROCESS_FUNCS,
    _XSS_BUILDERS,
)


def _classify_sink_xfunc(node: ast.Call) -> tuple[str, str] | None:
    """Like V10's _classify_sink, but SQL execute calls are ALWAYS classified
    as sinks (V10 only flags dynamic SQL strings).

    Rationale: in cross-function mode, the question is "does a param reach
    this sink?" — if `cursor.execute(query)` is called and `query` is a
    param, then any caller passing tainted data to this function creates a
    SQL injection path, REGARDLESS of how `query` was built inside the
    function (the caller controls it).
    """
    func = node.func
    if isinstance(func, ast.Attribute):
        recv = func.value
        attr = func.attr
        if isinstance(recv, ast.Name) and recv.id == 'os':
            if attr in ('system', 'popen'):
                return ('CWE-78', f'os.{attr}')
        if isinstance(recv, ast.Name) and recv.id == 'subprocess':
            if attr in _SUBPROCESS_FUNCS:
                return ('CWE-78', f'subprocess.{attr}')
        if isinstance(recv, ast.Name) and recv.id == 'pickle':
            if attr in _PICKLE_FUNCS:
                return ('CWE-502', f'pickle.{attr}')
        if isinstance(recv, ast.Name) and recv.id == 'marshal':
            if attr in _MARSHAL_FUNCS:
                return ('CWE-502', f'marshal.{attr}')
        if isinstance(recv, ast.Name) and recv.id == 'yaml':
            if attr == 'load':
                has_safe_loader = False
                for kw in node.keywords:
                    if kw.arg == 'Loader':
                        if isinstance(kw.value, ast.Name) and 'Safe' in kw.value.id:
                            has_safe_loader = True
                        elif isinstance(kw.value, ast.Attribute) and 'Safe' in kw.value.attr:
                            has_safe_loader = True
                if not has_safe_loader:
                    return ('CWE-502', 'yaml.load')
        if attr in _SQL_EXECUTE_NAMES:
            return ('CWE-89', attr)
        if attr in _XSS_BUILDERS:
            return ('CWE-79', attr)
    if isinstance(func, ast.Name):
        if func.id in ('eval', 'exec'):
            return ('CWE-94', func.id)
        if func.id == 'compile':
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and (arg.value == 'exec'):
                    return ('CWE-94', 'compile')
            for kw in node.keywords:
                if kw.arg == 'mode' and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str) and (kw.value.value == 'exec'):
                    return ('CWE-94', 'compile')
        if func.id in _XSS_BUILDERS:
            return ('CWE-79', func.id)
    return None
