# Auto-extracted from cross_func_taint_scanner.py
from __future__ import annotations

import ast
from pathlib import Path

from scp.autofix.scanners.taint_flow_scanner import (
    _collect_names,
    _is_sanitizer_call,
)


class _CallGraphBuilder(ast.NodeVisitor):
    """Walk a file's AST and build a FunctionInfo for every function def.

    Tracks current class scope so qualnames include the class prefix
    (e.g., "scp/core/foo.py::MyClass.my_method").
    """

    def __init__(self, file: Path, relpath: str):
        self.file = file
        self.relpath = relpath
        self.class_stack: list[str] = []
        self.funcs: list[FunctionInfo] = []  # noqa: F821  # [hygiene-keep] FunctionInfo injected by cross_func_taint_scanner.py rebind/wire

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_stack.append(node.name)
        for child in node.body:
            self.visit(child)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_func(node)

    def _handle_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        prefix = '.'.join(self.class_stack) if self.class_stack else ''
        qualname = f'{self.relpath}::{prefix}.{node.name}' if prefix else f'{self.relpath}::{node.name}'
        info = FunctionInfo(qualname=qualname, file=str(self.file), lineno=node.lineno, name=node.name, params=self._extract_params(node), is_static_or_class=self._is_static_or_class(node), func_node=node)  # noqa: F821  # [hygiene-keep] FunctionInfo injected by cross_func_taint_scanner.py rebind/wire
        self._analyze_body(node, info)
        self.funcs.append(info)
        for child in node.body:
            self.visit(child)

    @staticmethod
    def _extract_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        """Return positional + posonly + kwonly param names (skip *args/**kwargs)."""
        a = node.args
        params: list[str] = []
        params.extend(arg.arg for arg in a.posonlyargs)
        params.extend(arg.arg for arg in a.args)
        params.extend(arg.arg for arg in a.kwonlyargs)
        return params

    @staticmethod
    def _is_static_or_class(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        return any(isinstance(d, ast.Name) and d.id in ('staticmethod', 'classmethod') or (isinstance(d, ast.Attribute) and d.attr in ('staticmethod', 'classmethod')) for d in node.decorator_list)

    def _analyze_body(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef, info: FunctionInfo) -> None:  # noqa: F821  # [hygiene-keep] FunctionInfo injected by cross_func_taint_scanner.py rebind/wire
        """Walk function body (NOT descending into nested funcs) to extract:
        - isinstance-sanitized params
        - return-statement analysis (source returns, param returns)
        - sink calls (which params reach them)
        - outgoing calls to other scp/ functions (with params as args)
        """
        sanitized: set[str] = set()
        for n in self._walk_in_scope(func_node):
            if isinstance(n, ast.If):
                for sub in ast.walk(n.test):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and (sub.func.id == 'isinstance'):
                        if sub.args and isinstance(sub.args[0], ast.Name) and (sub.args[0].id in info.params):
                            sanitized.add(sub.args[0].id)
        return_call_ids: set[int] = set()
        for n in self._walk_in_scope(func_node):
            if isinstance(n, ast.Return) and n.value is not None:
                for sub in ast.walk(n.value):
                    if isinstance(sub, ast.Call):
                        return_call_ids.add(id(sub))
        for n in self._walk_in_scope(func_node):
            if isinstance(n, ast.Return) and n.value is not None:
                self._analyze_return_value(n.value, info, sanitized)
            if isinstance(n, ast.Call):
                self._analyze_call_node(n, info, sanitized, in_return=id(n) in return_call_ids)

    @staticmethod
    def _walk_in_scope(node: ast.AST):
        """Yield all descendants of `node` EXCEPT nested FunctionDef /
        AsyncFunctionDef / ClassDef bodies (those have their own scope)."""
        for child in ast.iter_child_nodes(node):
            yield from _CallGraphBuilder._walk_in_scope_helper(child)

    @staticmethod
    def _walk_in_scope_helper(node: ast.AST):
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return
        for child in ast.iter_child_nodes(node):
            yield from _CallGraphBuilder._walk_in_scope_helper(child)

    def _analyze_return_value(self, value: ast.AST, info: FunctionInfo, sanitized: set[str]) -> None:  # noqa: F821  # [hygiene-keep] FunctionInfo injected by cross_func_taint_scanner.py rebind/wire
        """Inspect a return expression: does it return a SOURCE? a param? a
        sanitized value? Updates info.returns_source / returns_param."""
        if _is_sanitizer_call(value):
            return
        src = _xfunc_is_source(value)  # noqa: F821  # [hygiene-keep] _xfunc_is_source injected by cross_func_taint_scanner.py rebind/wire
        if src is not None:
            info.returns_source = True
            if info.source_return_line == 0:
                info.source_return_line = getattr(value, 'lineno', 0)
                _, info.source_return_desc = src
        if isinstance(value, ast.Name) and value.id in info.params:
            if value.id not in sanitized:
                info.returns_param.add(value.id)
            return
        names = _collect_names(value)
        for n in names:
            if n in info.params and n not in sanitized:
                info.returns_param.add(n)

    def _analyze_call_node(self, call_node: ast.Call, info: FunctionInfo, sanitized: set[str], in_return: bool) -> None:  # noqa: F821  # [hygiene-keep] FunctionInfo injected by cross_func_taint_scanner.py rebind/wire
        """Inspect a Call node: is it a SINK that consumes a param? is it an
        outgoing call to another scp/ function with a param as arg?"""
        sink = _classify_sink_xfunc(call_node)  # noqa: F821  # [hygiene-keep] _classify_sink_xfunc injected by cross_func_taint_scanner.py rebind/wire
        if sink is not None:
            cwe, sink_name = sink
            for arg in call_node.args:
                if _is_sanitizer_call(arg):
                    continue
                arg_names = _collect_names(arg)
                for n in arg_names:
                    if n in info.params and n not in sanitized:
                        hit = SinkHit(cwe=cwe, sink_name=sink_name, sink_line=call_node.lineno)  # noqa: F821  # [hygiene-keep] SinkHit injected by cross_func_taint_scanner.py rebind/wire
                        info.param_sinks.setdefault(n, []).append(hit)
            for kw in call_node.keywords:
                if kw.value is None or _is_sanitizer_call(kw.value):
                    continue
                arg_names = _collect_names(kw.value)
                for n in arg_names:
                    if n in info.params and n not in sanitized:
                        hit = SinkHit(cwe=cwe, sink_name=sink_name, sink_line=call_node.lineno)  # noqa: F821  # [hygiene-keep] SinkHit injected by cross_func_taint_scanner.py rebind/wire
                        info.param_sinks.setdefault(n, []).append(hit)
        callee_name = self._callee_simple_name(call_node)
        if callee_name is not None:
            for i, arg in enumerate(call_node.args):
                if _is_sanitizer_call(arg):
                    continue
                if isinstance(arg, ast.Name) and arg.id in info.params and (arg.id not in sanitized):
                    info.outgoing_calls.append(CallEdge(callee_name=callee_name, arg_param=arg.id, call_line=call_node.lineno, arg_pos=i, in_return=in_return))  # noqa: F821  # [hygiene-keep] CallEdge injected by cross_func_taint_scanner.py rebind/wire

    @staticmethod
    def _callee_simple_name(call_node: ast.Call) -> str | None:
        """Return the simple name of the callee for bare-name calls only.

        `foo(x)` → "foo"
        `obj.method(x)` / `self.method(x)` / `module.func(x)` → None
            (attribute calls are NOT resolved in v1 — would need import/scope
             analysis to know which `obj.method` is meant)
        """
        func = call_node.func
        if isinstance(func, ast.Name):
            return func.id
        return None
