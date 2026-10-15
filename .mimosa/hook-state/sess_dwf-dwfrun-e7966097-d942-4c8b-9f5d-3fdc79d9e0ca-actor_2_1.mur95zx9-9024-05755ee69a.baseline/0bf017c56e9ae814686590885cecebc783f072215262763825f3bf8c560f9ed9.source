"""[W1-c1 2026-10-02] /ask fact-check fire-and-forget contract (static).

Causal chain of the bug:
  _ask_impl (rebound against scp.api_server globals) scheduled the fact-check
  via ``asyncio.create_task(...)`` + done-callback bookkeeping. The task kept
  running AFTER the handler returned its response and the run ledger was
  committed COMPLETED — a fire-and-forget auxiliary branch escaping the
  finalize boundary: no guarantee any task survives finalize.

The contract pinned here has two layers:
  1. STATIC: every call to ``_async_fact_check`` in
     scp/api_server_parts/_ask_impl.py must sit under an ``ast.Await`` node
     and must never be an argument of ``asyncio.create_task`` — no
     scheduling, only awaiting. Await is an expression node, so an ancestor
     Await proves the call lives inside an awaited expression (direct await
     or an awaited wrapper such as ``asyncio.wait_for(...)``); scheduling via
     create_task/ensure_future never has one.
  2. REBIND SEAM: the awaited call and the wait bound must resolve through
     the production binding (``api_server._ask_impl.__globals__ is
     api_server.__dict__``) — the same namespace-export contract as the
     history-evidence hook (F-RUN-02, test_ask_history_evidence_hook.py).

Hermetic: no env, no network.
"""
from __future__ import annotations

import ast
from pathlib import Path

_ASK_IMPL_PATH = (
    Path(__file__).resolve().parents[2] / "scp" / "api_server_parts" / "_ask_impl.py"
)


def _parse_ask_impl() -> ast.Module:
    return ast.parse(
        _ASK_IMPL_PATH.read_text(encoding="utf-8"), filename=str(_ASK_IMPL_PATH)
    )


def _is_asyncio_create_task(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "create_task"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "asyncio"
    )


def _is_async_fact_check_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "_async_fact_check"
    if isinstance(func, ast.Attribute):
        return func.attr == "_async_fact_check"
    return False


def _factcheck_calls_with_ancestors(tree: ast.Module) -> list[tuple[ast.Call, tuple]]:
    """Return (call_node, ancestor_chain_including_self) for every call that
    spells ``_async_fact_check`` anywhere in the module (any accessor form)."""
    stack: list[ast.AST] = []
    results: list[tuple[ast.Call, tuple]] = []

    def _visit(node: ast.AST) -> None:
        stack.append(node)
        if _is_async_fact_check_call(node):
            results.append((node, tuple(stack)))
        for child in ast.iter_child_nodes(node):
            _visit(child)
        stack.pop()

    _visit(tree)
    return results


def test_factcheck_call_is_awaited_not_scheduled():
    """Mọi Call tới ``_async_fact_check`` phải nằm dưới ast.Await và không bao
    giờ là arg của ``asyncio.create_task``.

    Trước fix: call nằm trong ``asyncio.create_task(...)`` (fire-and-forget,
    task sống sót sau finalize) → FAIL. Sau fix:
    ``await asyncio.wait_for(_async_fact_check(...), timeout=...)`` → PASS.
    """
    tree = _parse_ask_impl()
    calls = _factcheck_calls_with_ancestors(tree)
    assert calls, "contract vô nghĩa nếu _ask_impl không còn gọi _async_fact_check"

    scheduled: list[str] = []
    unawaited: list[str] = []
    for call, ancestors in calls:
        ancestors_without_self = ancestors[:-1]
        # (a) never an argument of asyncio.create_task
        if any(_is_asyncio_create_task(a) for a in ancestors_without_self):
            scheduled.append(ast.dump(call)[:120])
        # (b) must sit under an Await node — Await là expression node, nên
        #     ancestor Await chứng minh call nằm trong biểu thức được await.
        if not any(isinstance(a, ast.Await) for a in ancestors_without_self):
            unawaited.append(ast.dump(call)[:120])

    assert not scheduled, (
        f"fact-check call scheduled via create_task (fire-and-forget): {scheduled}"
    )
    assert not unawaited, f"fact-check call not under any await: {unawaited}"


def test_factcheck_wait_bound_resolves_through_rebind_seam():
    """[rebind-seam] ``_ask_impl`` rebind với globals() của scp.api_server
    (composition root, scp/api_server.py:386). Tên mà body tham chiếu sau fix
    (``_async_fact_check``, ``_FACTCHECK_AWAIT_TIMEOUT_S``) phải resolve được
    trong globals của hàm đã rebind — nếu thiếu, LOAD_GLOBAL raise NameError
    mỗi /ask có PASS-verdict (cùng class bug F-RUN-02 deep-audit boot).

    Bound phải bằng timeout per-request nội bộ của StreamingFactChecker
    (scp/core/streaming_factcheck.py: safe_urlopen timeout=10).
    """
    from scp import api_server

    assert api_server._ask_impl.__globals__ is api_server.__dict__
    assert "_async_fact_check" in api_server._ask_impl.__globals__
    assert "_FACTCHECK_AWAIT_TIMEOUT_S" in api_server._ask_impl.__globals__
    # Namespace export phải là CÙNG object với bản trong part module
    # (namespace export, không phải copy — behavior không thể drift).
    from scp.api_server_parts import _ask_impl as ask_part

    assert (
        api_server._ask_impl.__globals__["_FACTCHECK_AWAIT_TIMEOUT_S"]
        is ask_part._FACTCHECK_AWAIT_TIMEOUT_S
    )
    assert api_server._ask_impl.__globals__["_FACTCHECK_AWAIT_TIMEOUT_S"] == 10.0
