# Auto-extracted from cross_func_taint_scanner.py
from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    """Per-function summary used by the whole-program taint analysis.

    Pass 1 fields are populated by `_CallGraphBuilder` from AST:
      - params, is_static_or_class
      - returns_source: True if any return statement returns a SOURCE call
      - returns_param: params that flow to RETURN (without sanitization)
      - param_sinks: params that flow to a SINK in this function's body
      - outgoing_calls: edges to other scp/ functions (for fixpoint)
      - func_node: the AST FunctionDef node (for Pass 3 detector walk)

    Pass 2 fields are populated by `_run_fixpoint`:
      - propagating_params: subset of params whose taint propagates to RETURN
        (initially = returns_param; expanded by fixpoint when a callee
        propagates taint back through F's return)
      - sink_consuming_params: subset of params whose taint reaches a SINK
        (initially = param_sinks.keys(); expanded by fixpoint transitively
        through callee chains)
      - transitive_sinks: per-param list of SinkHit objects (including
        transitive hits via callees) — used to build the call chain in
        the bug description
    """
    qualname: str
    file: str
    lineno: int
    name: str
    params: list[str]
    is_static_or_class: bool
    func_node: ast.AST | None = field(default=None, repr=False)
    returns_source: bool = False
    source_return_line: int = 0
    source_return_desc: str = ''
    returns_param: set[str] = field(default_factory=set)
    param_sinks: dict[str, list[SinkHit]] = field(default_factory=dict)  # noqa: F821  # [hygiene-keep] SinkHit injected by cross_func_taint_scanner.py rebind/wire
    outgoing_calls: list[CallEdge] = field(default_factory=list)  # noqa: F821  # [hygiene-keep] CallEdge injected by cross_func_taint_scanner.py rebind/wire
    propagating_params: set[str] = field(default_factory=set)
    sink_consuming_params: set[str] = field(default_factory=set)
    transitive_sinks: dict[str, list[SinkHit]] = field(default_factory=dict)  # noqa: F821  # [hygiene-keep] SinkHit injected by cross_func_taint_scanner.py rebind/wire
