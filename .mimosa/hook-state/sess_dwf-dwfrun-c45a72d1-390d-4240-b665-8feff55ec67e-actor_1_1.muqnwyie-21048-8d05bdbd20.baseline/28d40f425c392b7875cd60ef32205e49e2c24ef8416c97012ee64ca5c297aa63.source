# Auto-extracted from cross_func_taint_scanner.py
from __future__ import annotations

from collections import defaultdict


def _run_fixpoint(funcs_by_qualname: dict[str, FunctionInfo]) -> None:  # noqa: F821  # [hygiene-keep] FunctionInfo injected by cross_func_taint_scanner.py rebind/wire
    """Iterate taint propagation through the call graph until fixpoint.

    Expands each function's `propagating_params` and `sink_consuming_params`
    based on callee behavior:
      - If F calls G with F's param `p` at arg position `i`, and G's param
        at position `i` is in G.sink_consuming_params, then `p` is added to
        F.sink_consuming_params (transitive sink).
      - If F returns the result of calling G with F's param `p` at position
        `i`, and G's param at position `i` is in G.propagating_params (or
        G.returns_source), then `p` is added to F.propagating_params.

    Iterates until no changes (or _MAX_FIXPOINT_ROUNDS reached).
    """
    funcs_by_name: dict[str, list[FunctionInfo]] = defaultdict(list)  # noqa: F821  # [hygiene-keep] FunctionInfo injected by cross_func_taint_scanner.py rebind/wire
    for f in funcs_by_qualname.values():
        funcs_by_name[f.name].append(f)
    for f in funcs_by_qualname.values():
        f.propagating_params = set(f.returns_param)
        f.sink_consuming_params = set(f.param_sinks.keys())
        f.transitive_sinks = {p: list(hits) for p, hits in f.param_sinks.items()}
    for round_num in range(_MAX_FIXPOINT_ROUNDS):  # noqa: F821  # [hygiene-keep] _MAX_FIXPOINT_ROUNDS injected by cross_func_taint_scanner.py rebind/wire
        changed = False
        for f in funcs_by_qualname.values():
            for edge in f.outgoing_calls:
                candidates = funcs_by_name.get(edge.callee_name, [])
                if not candidates:
                    continue
                for g in candidates:
                    if edge.arg_pos >= len(g.params):
                        continue
                    g_param = g.params[edge.arg_pos]
                    if g_param in g.sink_consuming_params:
                        if edge.arg_param not in f.sink_consuming_params:
                            f.sink_consuming_params.add(edge.arg_param)
                            changed = True
                        existing_keys = {(h.cwe, h.sink_name, h.sink_line, h.via_callee) for h in f.transitive_sinks.get(edge.arg_param, [])}
                        for h in g.transitive_sinks.get(g_param, []):
                            key = (h.cwe, h.sink_name, h.sink_line, h.via_callee)
                            if key in existing_keys:
                                continue
                            transitive = SinkHit(cwe=h.cwe, sink_name=h.sink_name, sink_line=h.sink_line, via_callee=g.qualname, via_callee_file=g.file, via_callee_param=g_param)  # noqa: F821  # [hygiene-keep] SinkHit injected by cross_func_taint_scanner.py rebind/wire
                            f.transitive_sinks.setdefault(edge.arg_param, []).append(transitive)
                            existing_keys.add(key)
                            changed = True
                    if edge.in_return and (g_param in g.propagating_params or g.returns_source):
                        if edge.arg_param not in f.propagating_params:
                            f.propagating_params.add(edge.arg_param)
                            changed = True
        if not changed:
            logger.debug(f'[CrossFuncTaint] fixpoint reached at round {round_num + 1} ({len(funcs_by_qualname)} functions)')  # noqa: F821  # [hygiene-keep] logger injected by cross_func_taint_scanner.py rebind/wire
            return
    logger.debug(f'[CrossFuncTaint] fixpoint maxed out at {_MAX_FIXPOINT_ROUNDS} rounds ({len(funcs_by_qualname)} functions)')  # noqa: F821  # [hygiene-keep] logger injected by cross_func_taint_scanner.py rebind/wire
