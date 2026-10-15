"""[FA-13 containment] Fixed subprocess runner for BSG-VA behavior probes.

TẠI SAO file này tồn tại:
  scp/autofix/evidence_replay.probe_module_behavior() phải NẠP và GỌI các
  callable của source CHƯA kiểm chứng (candidate / buggy pre-fix source).
  Trước đây việc này dùng exec() TRỰC TIẾP trong host process của AutoFix —
  containment weakness (HIGH: code-injection surface): module độc hại có thể
  đọc state/secrets/connection trong bộ nhớ host hoặc monkeypatch host.
  Fix: source được nạp trong một SUBPROCESS riêng (cwd = throwaway tmp dir,
  env tối thiểu, timeout bounded). File runner này là STATIC: không sinh code
  động, không eval/exec chuỗi động, và chỉ nạp ĐÚNG file path được truyền qua
  argv thông qua importlib.

Protocol (parent ↔ runner):
  argv[1] — đường dẫn file module cần nạp
  argv[2] — JSON array các tên public top-level cần exercise
  stdout  — đúng MỘT JSON document:
    {"ok": bool, "reason": str, "records": [record...],
     "exercised": int, "pinnable": int}
  record: {callable, exercised, pinnable, result_repr, error, async, args_expr}

Fail-closed contract: crash, exit != 0, stdout không parse được, hoặc timeout
→ parent coi probe FAILED (no records) — không bao giờ im lặng coi là pass.
stdout của module bị nạp được redirect vào bộ nhớ đệm nên stdout của runner
luôn sạch để parse (chính xác một JSON document).
"""
from __future__ import annotations

import asyncio
import inspect
import io
import json
import logging
import os
import sys
from contextlib import redirect_stdout
from importlib.util import module_from_spec, spec_from_file_location

logger = logging.getLogger(__name__)

_MAX_PINNED_REPR_LEN = 300


class ModuleExecError(Exception):
    """The untrusted module raised while importing/exercising."""


def _repr_is_pinnable(repr_text) -> bool:
    """Same stability rule as evidence_replay._repr_is_stable (parent recomputes)."""
    if not isinstance(repr_text, str):
        return False
    if len(repr_text) > _MAX_PINNED_REPR_LEN:
        return False
    return " at 0x" not in repr_text


def _build_mock_args(sig):
    """Deterministic smoke args — same strategy as runner_phases.reality_test.

    Must stay byte-for-byte equivalent in decision order to the in-process
    helper so probe results are identical between the two implementations.
    """
    positional = []
    keywords = {}
    for name, param in sig.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL,):
            continue  # *args — skip, the defaults will fill in
        if param.kind in (inspect.Parameter.VAR_KEYWORD,):
            keywords[name] = {}  # **kwargs — empty dict
            continue
        ann = param.annotation
        if param.default is not inspect.Parameter.empty:
            val = param.default
        elif ann is str or (isinstance(ann, type) and ann is str):
            val = "test"
        elif ann is int or (isinstance(ann, type) and ann is int):
            val = 1
        elif ann is bool or (isinstance(ann, type) and ann is bool):
            val = True
        elif isinstance(ann, type) and ann in (dict,):
            val = {}
        elif isinstance(ann, type) and ann in (list, tuple):
            val = []
        elif ann is float or (isinstance(ann, type) and ann is float):
            val = 1.0
        else:
            val = "test"  # generic fallback
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            positional.append(val)
        else:
            keywords[name] = val
    return tuple(positional), keywords


def _safe_call(func, args, kwargs):
    """Call func, catching BaseException (SystemExit/KeyboardInterrupt included)."""
    try:
        result = func(*args, **kwargs)
        return True, result
    except SystemExit as e:
        return False, f"SystemExit({e.code}) — target function tried to kill the probe process"
    except KeyboardInterrupt:
        return False, "KeyboardInterrupt — target function blocked probe interruption"
    except BaseException as e:
        logger.debug(f"_safe_call: exception ignored: {e}", exc_info=True)
        return False, f"{type(e).__name__}: {e}"


def _exercise(func, name):
    """Exercise one callable; returns the record dict (same schema as parent)."""
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError) as exc:
        return {"callable": name, "exercised": False, "pinnable": False,
                "result_repr": None, "error": f"signature unavailable: {exc}",
                "async": False, "args_expr": ""}
    args, kwargs = _build_mock_args(sig)
    args_expr = ", ".join(
        [repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()]
    )
    is_async = inspect.iscoroutinefunction(func)
    if is_async:
        async def _call():
            return await func(*args, **kwargs)
        ok, call_result = _safe_call(lambda: asyncio.run(_call()), (), {})
    else:
        ok, call_result = _safe_call(func, args, kwargs)

    record = {"callable": name, "exercised": bool(ok), "pinnable": False,
              "result_repr": None, "error": None if ok else str(call_result)[:200],
              "async": is_async, "args_expr": args_expr}
    if ok:
        try:
            record["result_repr"] = repr(call_result)
        except Exception as repr_err:  # noqa: BLE001 — un-repr-able result
            record["result_repr"] = f"<unrepr-able {type(call_result).__name__}: {repr_err}>"
        record["pinnable"] = _repr_is_pinnable(record["result_repr"])
    return record


def main() -> None:
    out = {"ok": False, "reason": "", "records": [], "exercised": 0, "pinnable": 0}
    real_stdout = sys.stdout
    try:
        if len(sys.argv) != 3:
            raise ValueError("usage: replay_probe_runner.py <module_path> <names_json>")
        module_path = sys.argv[1]
        public_names = json.loads(sys.argv[2])
        if not isinstance(public_names, list) or not all(isinstance(n, str) for n in public_names):
            raise ValueError("argv[2] must be a JSON array of callable names")

        stem = os.path.splitext(os.path.basename(module_path))[0]
        spec = spec_from_file_location(stem, module_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"no importable spec for {module_path}")
        module = module_from_spec(spec)

        # Module stdout is buffered away so the runner's stdout carries
        # EXACTLY one JSON document regardless of what the target prints.
        captured = io.StringIO()
        with redirect_stdout(captured):
            try:
                spec.loader.exec_module(module)
            except BaseException as exec_err:  # noqa: BLE001 — untrusted source
                raise ModuleExecError(
                    f"module exec failed: {type(exec_err).__name__}: {exec_err}"
                ) from exec_err
            records = []
            for name in public_names:
                func = getattr(module, name, None)
                if func is None or not callable(func) or inspect.isclass(func):
                    records.append({
                        "callable": name, "exercised": False, "pinnable": False,
                        "result_repr": None,
                        "error": "name is not callable at module level",
                        "async": False, "args_expr": "",
                    })
                    continue
                records.append(_exercise(func, name))

        out["records"] = records
        out["exercised"] = sum(1 for r in records if r["exercised"])
        out["pinnable"] = sum(1 for r in records if r["pinnable"])
        out["ok"] = True
    except ModuleExecError as exc:
        out["ok"] = False
        out["records"] = []
        out["exercised"] = 0
        out["pinnable"] = 0
        out["reason"] = str(exc)
    except BaseException as exc:  # noqa: BLE001 — the probe must always answer in JSON
        out["ok"] = False
        out["records"] = []
        out["exercised"] = 0
        out["pinnable"] = 0
        out["reason"] = f"probe harness error: {type(exc).__name__}: {exc}"
    finally:
        print(json.dumps(out, ensure_ascii=False), file=real_stdout)
        real_stdout.flush()
        # Non-daemon threads spawned by the target source must not wedge the
        # parent's bounded timeout — exit hard once the answer is on stdout.
        os._exit(0)


if __name__ == "__main__":
    main()
