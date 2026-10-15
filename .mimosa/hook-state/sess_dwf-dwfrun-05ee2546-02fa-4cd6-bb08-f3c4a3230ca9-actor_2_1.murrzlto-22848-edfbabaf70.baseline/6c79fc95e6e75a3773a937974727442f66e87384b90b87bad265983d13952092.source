# Auto-extracted from cross_func_taint_scanner.py
from __future__ import annotations

import ast

from scp.autofix.scanners.taint_flow_scanner import (
    _HEURISTIC_PARAM_NAMES,
    _collect_names,
    _is_sanitizer_call,
)


class _FunctionDetector:
    """Per-function cross-function taint detector.

    Walks the function body tracking tainted vars (params + locals), with
    cross-function awareness of callee behavior:
      - When `x = G(...)` and G.returns_source → x is tainted
      - When `x = G(arg)` and arg is tainted and G.propagating_params
        contains the corresponding param → x is tainted
      - When `G(tainted_arg)` is called and G.sink_consuming_params contains
        the corresponding param → flag as cross-function taint bug
    """

    def __init__(self, info: FunctionInfo, funcs_by_name: dict[str, list[FunctionInfo]]):  # noqa: F821  # [hygiene-keep] FunctionInfo injected by cross_func_taint_scanner.py rebind/wire
        self.info = info
        self.funcs_by_name = funcs_by_name
        self.findings: list[dict] = []
        self.tainted: dict[str, tuple[int, str]] = {}
        self.sanitized: set[str] = set()

    def analyze(self) -> None:
        if self.info.func_node is None:
            return
        if not self.info.is_static_or_class:
            for p in self.info.params:
                if p in _HEURISTIC_PARAM_NAMES:
                    self.tainted[p] = (self.info.lineno, f"parameter '{p}' (heuristic user-input name)")
        for stmt in self.info.func_node.body:
            self._walk_in_scope(stmt)

    def _walk_in_scope(self, node: ast.AST) -> None:
        """Walk node + descendants, processing assigns/calls/ifs.

        Does NOT descend into nested FunctionDef / AsyncFunctionDef /
        ClassDef — those have their own scope and get their own analysis.
        """
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return
        if isinstance(node, ast.If):
            self._check_isinstance_in_test(node.test)
        elif isinstance(node, ast.Assign):
            self._handle_assign(node)
        elif isinstance(node, ast.AnnAssign):
            self._handle_annassign(node)
        elif isinstance(node, ast.AugAssign):
            self._handle_augassign(node)
        elif isinstance(node, ast.Call):
            self._handle_call(node)
        for child in ast.iter_child_nodes(node):
            self._walk_in_scope(child)

    def _check_isinstance_in_test(self, test_node: ast.AST) -> None:
        """If test is `isinstance(var, ...)` → mark var sanitized (partial)."""
        for n in ast.walk(test_node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and (n.func.id == 'isinstance'):
                if n.args and isinstance(n.args[0], ast.Name):
                    var_name = n.args[0].id
                    self.sanitized.add(var_name)
                    self.tainted.pop(var_name, None)

    def _handle_assign(self, node: ast.Assign) -> None:
        """Track taint through `x = value`."""
        if isinstance(node.value, ast.Call) and _is_sanitizer_call(node.value):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self.tainted.pop(tgt.id, None)
                    self.sanitized.add(tgt.id)
            return
        src = _xfunc_is_source(node.value)  # noqa: F821  # [hygiene-keep] _xfunc_is_source injected by cross_func_taint_scanner.py rebind/wire
        if src is not None:
            _, desc = src
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self.tainted[tgt.id] = (node.lineno, desc)
                    self.sanitized.discard(tgt.id)
            return
        if isinstance(node.value, ast.Call):
            xfunc_taint = self._check_callee_return_taint(node.value)
            if xfunc_taint is not None:
                src_line, src_desc = xfunc_taint
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        self.tainted[tgt.id] = (src_line, src_desc)
                        self.sanitized.discard(tgt.id)
                return
        rhs_names = _collect_names(node.value)
        tainted_refs = (rhs_names & set(self.tainted.keys())) - self.sanitized
        if tainted_refs:
            src_line, src_desc = min((self.tainted[n] for n in tainted_refs), key=lambda x: x[0])
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self.tainted[tgt.id] = (src_line, f'{src_desc} (propagated)')
                    self.sanitized.discard(tgt.id)
            return
        if isinstance(node.value, ast.Constant):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self.tainted.pop(tgt.id, None)
                    self.sanitized.discard(tgt.id)
        elif isinstance(node.value, ast.Name) and node.value.id not in self.tainted:
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self.tainted.pop(tgt.id, None)
                    self.sanitized.discard(tgt.id)

    def _handle_annassign(self, node: ast.AnnAssign) -> None:
        """Same as _handle_assign but for `x: Type = value` form."""
        if node.value is None:
            return
        if isinstance(node.value, ast.Call) and _is_sanitizer_call(node.value):
            if isinstance(node.target, ast.Name):
                self.tainted.pop(node.target.id, None)
                self.sanitized.add(node.target.id)
            return
        src = _xfunc_is_source(node.value)  # noqa: F821  # [hygiene-keep] _xfunc_is_source injected by cross_func_taint_scanner.py rebind/wire
        if src is not None:
            _, desc = src
            if isinstance(node.target, ast.Name):
                self.tainted[node.target.id] = (node.lineno, desc)
                self.sanitized.discard(node.target.id)
            return
        if isinstance(node.value, ast.Call):
            xfunc_taint = self._check_callee_return_taint(node.value)
            if xfunc_taint is not None and isinstance(node.target, ast.Name):
                src_line, src_desc = xfunc_taint
                self.tainted[node.target.id] = (src_line, src_desc)
                self.sanitized.discard(node.target.id)
                return
        rhs_names = _collect_names(node.value)
        tainted_refs = (rhs_names & set(self.tainted.keys())) - self.sanitized
        if tainted_refs and isinstance(node.target, ast.Name):
            src_line, src_desc = min((self.tainted[n] for n in tainted_refs), key=lambda x: x[0])
            self.tainted[node.target.id] = (src_line, f'{src_desc} (propagated)')
            self.sanitized.discard(node.target.id)
            return
        if isinstance(node.value, ast.Constant):
            if isinstance(node.target, ast.Name):
                self.tainted.pop(node.target.id, None)
                self.sanitized.discard(node.target.id)
        elif isinstance(node.value, ast.Name) and node.value.id not in self.tainted:
            if isinstance(node.target, ast.Name):
                self.tainted.pop(node.target.id, None)
                self.sanitized.discard(node.target.id)

    def _handle_augassign(self, node: ast.AugAssign) -> None:
        """Handle `x += y` — propagate taint from y to x if y is tainted."""
        if not isinstance(node.target, ast.Name):
            return
        rhs_names = _collect_names(node.value)
        tainted_refs = (rhs_names & set(self.tainted.keys())) - self.sanitized
        if tainted_refs:
            src_line, src_desc = min((self.tainted[n] for n in tainted_refs), key=lambda x: x[0])
            self.tainted[node.target.id] = (src_line, f'{src_desc} (propagated via +=)')

    def _check_callee_return_taint(self, call_node: ast.Call) -> tuple[int, str] | None:
        """If call_node is a call to a known scp/ function G, and G's return
        is tainted (returns_source OR G propagates one of the args we pass),
        return (source_line, source_desc) describing the taint origin.

        Returns None if the call's return is not tainted.
        """
        callee_name = _CallGraphBuilder._callee_simple_name(call_node)  # noqa: F821  # [hygiene-keep] _CallGraphBuilder injected by cross_func_taint_scanner.py rebind/wire
        if callee_name is None:
            return None
        candidates = self.funcs_by_name.get(callee_name, [])
        if not candidates:
            return None
        for g in candidates:
            if g.returns_source:
                desc = g.source_return_desc or 'source'
                return (g.source_return_line or call_node.lineno, f'{desc} (returned by {g.name})')
            for i, arg in enumerate(call_node.args):
                if i >= len(g.params):
                    break
                g_param = g.params[i]
                if g_param not in g.propagating_params:
                    continue
                if isinstance(arg, ast.Name) and arg.id in self.tainted and (arg.id not in self.sanitized):
                    src_line, src_desc = self.tainted[arg.id]
                    return (src_line, f'{src_desc} (propagated through {g.name})')
        return None

    def _handle_call(self, node: ast.Call) -> None:
        """Check if this Call passes tainted data to a callee whose
        corresponding param is sink-consuming → flag cross-function bug.

        Also checks intra-function sinks (V10-style) but SKIPS them — those
        are reported by taint_flow_scanner.py, not this scanner.
        """
        callee_name = _CallGraphBuilder._callee_simple_name(node)  # noqa: F821  # [hygiene-keep] _CallGraphBuilder injected by cross_func_taint_scanner.py rebind/wire
        if callee_name is None:
            return
        candidates = self.funcs_by_name.get(callee_name, [])
        if not candidates:
            return
        for i, arg in enumerate(node.args):
            if not (isinstance(arg, ast.Name) and arg.id in self.tainted and (arg.id not in self.sanitized)):
                continue
            tainted_var = arg.id
            src_line, src_desc = self.tainted[tainted_var]
            for g in candidates:
                if i >= len(g.params):
                    continue
                g_param = g.params[i]
                if g_param not in g.sink_consuming_params:
                    continue
                direct_hits = g.param_sinks.get(g_param, [])
                transitive_hits = [h for h in g.transitive_sinks.get(g_param, []) if h not in direct_hits]
                all_hits = direct_hits + transitive_hits
                if not all_hits:
                    continue
                for hit in all_hits:
                    self.findings.append({'call_line': node.lineno, 'callee_qualname': g.qualname, 'callee_name': g.name, 'callee_file': g.file, 'callee_param': g_param, 'tainted_var': tainted_var, 'source_line': src_line, 'source_desc': src_desc, 'cwe': hit.cwe, 'sink_name': hit.sink_name, 'sink_line': hit.sink_line, 'via_callee': hit.via_callee, 'via_callee_file': hit.via_callee_file})
