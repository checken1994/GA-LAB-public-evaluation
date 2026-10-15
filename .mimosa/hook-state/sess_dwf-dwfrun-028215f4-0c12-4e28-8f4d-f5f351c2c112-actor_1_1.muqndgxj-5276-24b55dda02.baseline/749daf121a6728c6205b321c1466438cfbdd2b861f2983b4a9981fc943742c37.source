"""[IMP-2] Reality Test — exercise the patched module's callables for real.

[M1 hardening + FA-04 remediation] Contract (DNA #22 — PASS ≠ TRUE):
  - Discovers public top-level functions AND class methods (via no-arg
    constructor instantiation) via AST, then invokes them with
    signature-constructed smoke args through a REAL import of the module
    (importlib, not cached in sys.modules).
  - Handles sync + async functions (asyncio.run).
  - Catches BaseException (SystemExit, KeyboardInterrupt) to protect the
    host runner process from target sys.exit() calls.
  - Handles *args, *kwargs, keyword-only params, and positional-only params.
  - A callable that RAISES on the constructed args is NOT counted as
    exercised; the exception is recorded under "exceptions".
  - If 0 callables were exercised successfully → ok=False / UNVERIFIED.
  - If >= 1 callables exercised successfully → ok=True / VERIFIED with
    callables_exercised=N (failed callables listed under "exceptions").
  - A file with no exercisable public callables can never be VERIFIED
    (fail-closed, DNA #22).

Callers: post_fix_verify Phase B, shadow_canary (fail-open), auto_rollback
watcher (treats ok=False as regression → rollback — fail-closed by design).
"""

import ast
import asyncio
import importlib.util
import inspect
import logging
from pathlib import Path

logger = logging.getLogger("scp.autofix.reality_test")


def _build_mock_args(sig: inspect.Signature) -> tuple:
    """Build positional + keyword mock arguments from a signature."""
    positional = []
    keywords = {}
    for name, param in sig.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL,):
            continue  # *args — skip, the defaults will fill in
        if param.kind in (inspect.Parameter.VAR_KEYWORD,):
            keywords[name] = {}  # **kwargs — empty dict
            continue
        # Build a mock value based on annotation or default
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


def _safe_call(func, args: tuple, kwargs: dict):
    """Call func and catch BaseException (SystemExit, KeyboardInterrupt).
    Returns (ok: bool, result_or_error)."""
    try:
        result = func(*args, **kwargs)
        return True, result
    except SystemExit as e:
        return False, f"SystemExit({e.code}) — target function tried to kill the host process"
    except KeyboardInterrupt:
        # silent-by-design: explicit (False, reason) return — host-protection contract, caller fail-closed.
        return False, "KeyboardInterrupt — target function blocked host interruption"
    except BaseException as e:
        logger.debug(f"_safe_call: exception ignored: {e}", exc_info=True)
        return False, f"{type(e).__name__}: {e}"


def _run_async(coro):
    """Run an async callable, managing the event loop safely."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # silent-by-design: documented fallback — no running loop means the
        # caller manages its own loop/executor below.
        logger.debug("reality_test: no running event loop, using managed execution", exc_info=True)
        loop = None
    if loop is not None and loop.is_running():
        # We're inside a running loop — use a task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=30)
    return asyncio.run(coro)


def _exercise_callable(func, name: str) -> dict:
    """Try to exercise a single callable. Returns an exercise record."""
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError) as e:
        return {"callable": name, "exercised": False, "error": f"signature unavailable: {e}"}

    args, kwargs = _build_mock_args(sig)

    if inspect.iscoroutinefunction(func):
        # Async function — wrap in asyncio.run inside a try
        async def _call():
            return await func(*args, **kwargs)
        ok, result = _safe_call(lambda: _run_async(_call()), (), {})
    else:
        ok, result = _safe_call(func, args, kwargs)

    if ok:
        return {"callable": name, "exercised": True}
    return {"callable": name, "exercised": False, "error": str(result)[:200]}


def _discover_callables(tree: ast.Module, module) -> list:
    """Discover all exercisable public callables: top-level functions and
    public class methods (via no-arg or all-default constructor)."""
    callables = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            func = getattr(module, node.name, None)
            if callable(func) and not inspect.isclass(func):
                callables.append(func)
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            cls = getattr(module, node.name, None)
            if cls is None or not inspect.isclass(cls):
                continue
            # Try to instantiate with no args (or all-default)
            try:
                instance = cls()
            except Exception as inst_err:
                # silent-by-design: auto-instantiation probe — classes requiring
                # args are skipped from smoke exercising (documented contract).
                logger.debug("reality_test: %s requires constructor args, skipping: %s", node.name, inst_err, exc_info=True)
                continue  # requires args — cannot auto-instantiate
            for attr_name in dir(instance):
                if attr_name.startswith("_"):
                    continue
                method = getattr(instance, attr_name, None)
                if callable(method) and not inspect.isclass(method):
                    # Only methods defined on this class (not inherited from object/type)
                    if hasattr(cls, attr_name):
                        callables.append(method)
    return callables


def run_reality_test(bug_id: str = None, file_path: str = None, exercise_callables: bool = True, **kwargs):
    if not file_path or not Path(file_path).exists():
        return {"ok": False, "status": "UNVERIFIED", "reason": "file not found"}

    try:
        source = Path(file_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"ok": False, "status": "UNVERIFIED", "reason": f"Syntax error: {e}"}

    callables_exercised = 0
    exceptions: list[dict] = []
    all_exercise_records: list[dict] = []

    if exercise_callables:
        try:
            module_name = Path(file_path).stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            # Do NOT cache in sys.modules to prevent test pollution
            spec.loader.exec_module(module)

            discovered = _discover_callables(tree, module)

            for func in discovered:
                name = getattr(func, "__name__", str(func))
                record = _exercise_callable(func, name)
                all_exercise_records.append(record)
                if record.get("exercised"):
                    callables_exercised += 1
                else:
                    exceptions.append({
                        "callable": record.get("callable", name),
                        "error": record.get("error", "unknown"),
                    })

        except BaseException as e:
            logger.debug(f"run_reality_test: exception ignored: {e}", exc_info=True)
            # Module failed to import/exec or a callable killed the host —
            # nothing was reliably exercised.
            return {
                "ok": False,
                "status": "UNVERIFIED",
                "reason": f"Module load/execution error: {e}",
                "exceptions": exceptions,
            }

    if not exercise_callables:
        # Caller explicitly disabled runtime exercise → there is no runtime
        # evidence to back a VERIFIED claim (fail-closed, DNA #22).
        return {
            "ok": False,
            "status": "UNVERIFIED",
            "reason": "callable exercise disabled — no runtime evidence",
            "callables_exercised": 0,
        }

    if callables_exercised == 0:
        return {
            "ok": False,
            "status": "UNVERIFIED",
            "reason": "0 callables exercised successfully",
            "exceptions": exceptions,
        }

    return {
        "ok": True,
        "status": "VERIFIED",
        "reason": (
            f"reality test passed, exercised {callables_exercised} callables"
            + (f", {len(exceptions)} callable(s) raised" if exceptions else "")
        ),
        "callables_exercised": callables_exercised,
        "exceptions": exceptions,
    }
