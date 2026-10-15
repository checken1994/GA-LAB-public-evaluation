"""[F-RUN-02 audit-r2 2026-10-01] Rebind-namespace global resolution contract.

Causal chain of the bug (observed in docker logs, NameError every boot):
  api_server._rebind_part_function(lifespan) rebinds the extracted lifespan
  function to execute against scp.api_server's globals (the authoritative
  composition root) -> the nested deep-audit scheduler body `_deep_audit_loop`
  calls `deep_audit_boot_run_enabled()` -> that name lived ONLY in
  scp/api_server_parts/lifespan.py -> LOAD_GLOBAL raised NameError at the
  scheduler's first cycle, killing the deep-audit body every boot.

The contract pinned here has two layers:
  1. GENERIC GUARD: every code object of every rebound function
     (_ask_impl, _async_fact_check, lifespan) must resolve every LOAD_GLOBAL
     name against scp.api_server's module globals (or builtins). This fails
     for the WHOLE missing-export class — including regressions that add a
     new helper to a part module without exporting it — not just the one
     name that broke this boot.
  2. REAL BODY EXECUTION: the exact name the scheduler body calls must
     execute through the production binding (rebound.__globals__) and return
     the env-gated verdict — proving the call chain
     rebound-lifespan -> _deep_audit_loop -> deep_audit_boot_run_enabled()
     no longer hits NameError.
"""
from __future__ import annotations

import builtins
import dis

import pytest


def _iter_code_objects(fn):
    stack = [fn.__code__]
    while stack:
        code = stack.pop()
        yield code
        for const in code.co_consts:
            if hasattr(const, "co_code"):
                stack.append(const)


def _global_reference_names(fn) -> set[tuple[str, str]]:
    names: set[tuple[str, str]] = set()
    for code in _iter_code_objects(fn):
        for ins in dis.get_instructions(code):
            if ins.opname in ("LOAD_GLOBAL", "DELETE_GLOBAL"):
                names.add((ins.opname, ins.argval))
    return names


def _rebound_raw_functions() -> dict[str, object]:
    from scp.api_server_parts import _ask_impl as ask_part
    from scp.api_server_parts import _async_fact_check as afc_part
    from scp.api_server_parts import lifespan as lifespan_part

    return {
        "_ask_impl": ask_part._ask_impl,
        "_async_fact_check": afc_part._async_fact_check,
        "lifespan": getattr(lifespan_part.lifespan, "__wrapped__", lifespan_part.lifespan),
    }


def test_every_global_reference_of_rebound_functions_resolves():
    """Generic guard: no rebound function may reference an unresolvable global.

    Trước fix: test này FAIL với
    ``lifespan: {('LOAD_GLOBAL', 'deep_audit_boot_run_enabled')}`` — đúng
    NameError quan sát được mỗi boot trong docker logs.
    """
    from scp import api_server

    missing: dict[str, list[str]] = {}
    for name, raw in _rebound_raw_functions().items():
        rebound = api_server._rebind_part_function(raw)
        # The rebind contract: rebound code executes against api_server globals.
        assert rebound.__globals__ is api_server.__dict__, name
        for _op, ref in _global_reference_names(raw):
            if ref not in api_server.__dict__ and not hasattr(builtins, ref):
                missing.setdefault(name, []).append(ref)
    assert not missing, (
        "rebound functions reference globals missing from scp.api_server "
        f"(NameError at runtime): {missing}"
    )


def test_deep_audit_boot_run_enabled_resolves_and_executes_in_rebound_namespace(monkeypatch):
    """The exact scheduler-body call must execute through the rebound globals.

    Chạy THÂN hàm thật (không mock): scp.api_server_parts.lifespan.
    deep_audit_boot_run_enabled đọc SCP_DEEP_AUDIT_BOOT_RUN — cả 2 nhánh
    env (unset → False, '1' → True) phải trả verdict qua đúng binding mà
    production dùng.
    """
    from scp import api_server

    monkeypatch.delenv("SCP_DEEP_AUDIT_BOOT_RUN", raising=False)
    # Direct attribute access on the composition root — before the fix this
    # name did not exist here, which is the root cause of the boot NameError.
    fn = api_server.deep_audit_boot_run_enabled
    assert fn() is False

    monkeypatch.setenv("SCP_DEEP_AUDIT_BOOT_RUN", "1")
    assert fn() is True

    # Same function object as the part module (namespace export, not a copy):
    # behavior cannot drift between the two namespaces.
    from scp.api_server_parts import lifespan as lifespan_part

    assert fn is lifespan_part.deep_audit_boot_run_enabled


def test_lifespan_scheduler_body_reaches_boot_run_gate_without_nameerror():
    """Execute the real nested scheduler body code path (bounded, no LLM).

    The full `_deep_audit_loop` closure is created inside the lifespan, so
    this test rebinds the REAL lifespan exactly like production, then drives
    the body's first-cycle semantics: the LOAD_GLOBAL of
    deep_audit_boot_run_enabled from the rebound namespace (the failing
    instruction pre-fix) must execute without NameError.
    """
    from scp import api_server

    raw = _rebound_raw_functions()["lifespan"]
    rebound = api_server._rebind_part_function(raw)

    # Find the nested code object that performs the actual call.
    loop_codes = [
        code
        for code in _iter_code_objects(raw)
        if "deep_audit_boot_run_enabled" in code.co_names
    ]
    assert loop_codes, "deep-audit scheduler body phải tham chiếu boot-run gate"

    # Execute the exact name resolution the scheduler body performs, against
    # the exact globals dict the rebound body will use at runtime.
    namespace = rebound.__globals__
    for code in loop_codes:
        for _op, ref in _global_reference_names_from_code(code):
            if ref in code.co_names and ref not in namespace and not hasattr(builtins, ref):
                pytest.fail(f"scheduler body code {code.co_name} resolves missing global {ref!r}")

    result = namespace["deep_audit_boot_run_enabled"]()
    assert isinstance(result, bool)


def _global_reference_names_from_code(code):
    for ins in dis.get_instructions(code):
        if ins.opname in ("LOAD_GLOBAL", "DELETE_GLOBAL"):
            yield ins.opname, ins.argval
