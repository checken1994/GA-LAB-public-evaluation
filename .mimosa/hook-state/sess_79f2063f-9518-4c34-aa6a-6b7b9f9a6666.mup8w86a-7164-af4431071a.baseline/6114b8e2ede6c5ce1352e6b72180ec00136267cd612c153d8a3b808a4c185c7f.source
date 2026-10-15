# [V8.0-SCANNER] RaceConditionScanner — detect missing locks on shared mutable state.
#
# TẠI SAO scanner này tồn tại?
#   PATTERN-MAP audit cũ phát hiện: `_SOURCE_HEALTH_LOCK` declared nhưng chưa
#   bao giờ được dùng trong `with self._source_health_lock:`. Code có
#   `self._source_health["src"] = {...}` (mutation) ở nhiều chỗ — async/threaded
#   → race condition: 2 task cùng update dict → 1 update bị lost, hoặc dict
#   resized mid-iteration → RuntimeError.
#
# LOGIC:
#   1. Trong mỗi class (ClassDef), tìm class-attribute init patterns:
#        - `self._X = {}`     (dict literal)
#        - `self._X = []`     (list literal)
#        - `self._X = set()`  (set call)
#        - `self._X = 0`      (int counter)
#        - `self._X = deque()`(deque call)
#      Track {var_name: lineno} của các mutable attrs (skip immutable: str/int/float const).
#   2. Tìm `with self._lock_name:` blocks trong cùng class → collect set của các
#      lock names.
#   3. Tìm mutation patterns trên các tracked attrs:
#        - `self._X[k] = v`            (Subscript assign)
#        - `self._X.append(v)`         (Call .append)
#        - `self._X.pop()`, `.remove()`, `.discard()`, `.add()`, `.extend()`, `.update()`
#        - `self._X += [...]`           (AugAssign)
#        - `self._X = self._X + ...`    (reassignment)
#   4. Mutation BÊN TRONG `with self._lock:` block = SAFE.
#      Mutation NGOÀI lock block (trong async/threaded method) = BUG.
#
# CONSERVATIVE HEURISTICS:
#   - Chỉ flag nếu method có `async def` hoặc method name gợi ý concurrent
#     (verify_, fetch_, process_, update_, increment_, record_, batch_).
#     Pure sync method chạy trong 1 thread = không race.
#   - Skip __init__ (constructor runs in single thread).
#   - Skip test files, scripts.
#   - Skip mutation BÊN TRONG try/except block (mutation thường an toàn hơn
#     vì exception path luôn single-thread).
#   - Nếu class có bất kỳ lock nào (self._*lock), flag mutations không trong
#     lock block. Nếu class KHÔNG có lock nào → skip (conservative — class có
#     thể chạy single-threaded).
#
# RETURNS:
#   list[BugReport] — bug_type="RaceCondition"
from __future__ import annotations

import ast
import logging
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.race_condition")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 500

# [Fix 4-b-007 · Phase 4-A] Lock-name hints expanded beyond "lock"/"mutex" —
# asyncio.Semaphore / asyncio.Event / asyncio.Condition / asyncio.Barrier /
# asyncio.Queue / gate objects are ALL concurrency primitives. Missing them
# caused classes using `self._sem = asyncio.Semaphore(1)` to gate mutations
# to be treated as "no lock declared" and skipped (DNA #19 — scanner blind
# spot, DNA #5 — multiple scanner runs shared the same blind spot).
_LOCK_NAME_HINTS: tuple[str, ...] = (
    "lock", "mutex", "sem", "semaphore", "condition", "event",
    "barrier", "gate", "latch",
)


def _is_lock_name(name: str) -> bool:
    """True if attr name looks like a concurrency primitive (lock/sem/etc.)."""
    n = name.lower()
    return any(hint in n for hint in _LOCK_NAME_HINTS)


# Method name prefixes suggesting concurrent execution.
# Conservative: only flag methods that look like they're called concurrently
# (async method, or method whose name suggests it's invoked from a worker).
_CONCURRENT_PREFIXES = (
    "verify_", "fetch_", "process_", "update_", "increment_", "record_",
    "batch_", "add_", "remove_", "delete_", "schedule_", "run_", "execute_",
    "submit_", "publish_", "consume_", "handle_",
    # Bare method names commonly called from async/threaded contexts
    "record", "add", "remove", "delete", "submit", "publish", "consume",
    "update", "fetch", "process", "verify", "schedule", "increment",
    "register", "append", "track", "log_event", "report",
)

# Async dispatch marker (set in visit_FunctionDef)
_ASYNC_MARKER = "__async__"

# [Fix 4-b-007] `asyncio` (and alias) module names whose `.gather(...)` call
# without `return_exceptions=True` silently swallows the first exception and
# cancels/loses the rest. DNA #19: scanner previously could not see this
# class of silent error-swallowing race.
_ASYNCIO_MODULE_NAMES: frozenset[str] = frozenset({"asyncio", "asyncio_compat"})

# Mutation methods on list/dict/set
_MUTATING_METHODS = {
    "append", "extend", "insert", "remove", "pop", "clear", "update",
    "add", "discard", "setdefault", "popitem", "sort", "reverse",
    "appendleft", "popleft", "extendleft", "rotate",
}


def _is_mutable_init(node: ast.AST) -> bool:
    """True if RHS is `[]`, `{}`, `set()`, `deque()`, `defaultdict()`, `Counter()`."""
    # List/dict/set literal
    if isinstance(node, (ast.List, ast.Dict, ast.Set)):
        return True
    # Constructor call: set(), deque(), defaultdict(), Counter()
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id in {"set", "deque", "defaultdict", "Counter", "OrderedDict"}
    # self._x: dict = {} (already handled by literal)
    # int counter
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return True
    return False


def _is_self_attr(node) -> tuple[bool, str]:
    """If node is `self.NAME`, return (True, NAME). Else (False, '')."""
    if (isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"):
        return True, node.attr
    return False, ""


def _is_lock_with(node: ast.With) -> list[str]:
    """Return list of `self.X` lock names used as context managers in this With.

    [Fix 4-b-007] Recognize asyncio.Semaphore/Event/Condition/Barrier (and
    any name with sem/mutex/lock/condition/event/barrier/gate/latch substring)
    as a lock. Previously only `lock`/`mutex` were detected → asyncio.Lock
    + asyncio.Semaphore were treated as "no lock declared" → class skipped.
    """
    lock_names: list[str] = []
    for item in node.items:
        ctx = item.context_expr
        # `with self._lock:` — ctx is Attribute
        is_self, name = _is_self_attr(ctx)
        if is_self and _is_lock_name(name):
            lock_names.append(name)
        # [Fix 4-b-007] Also accept `async with asyncio.Lock():` (module-level
        # call result used directly as context manager, not stored on self).
        # We don't track this as a named attr, but its presence means the
        # method has a lock scope — represent it with a synthetic name.
        if isinstance(ctx, ast.Call):
            func = ctx.func
            if (isinstance(func, ast.Attribute)
                    and func.attr in {"Lock", "RLock", "Semaphore",
                                      "Condition", "Event", "Barrier",
                                      "BoundedSemaphore", "Queue"}):
                lock_names.append("__asyncio_primitive__")
    return lock_names


class _ClassRaceFinder(ast.NodeVisitor):
    """Walk one ClassDef, collect mutable attrs + lock usages + unsafe mutations."""

    def __init__(self, filepath: str, class_name: str, class_start_line: int):
        self.filepath = filepath
        self.class_name = class_name
        self.class_start_line = class_start_line
        self.findings: list[dict] = []
        # Mutable attrs: {name: init_lineno}
        self._mutable_attrs: dict[str, int] = {}
        # All lock attrs declared in class (self._lock, self._mutex, etc.)
        self._lock_attrs: set[str] = set()
        # Current lock scope stack: list of sets of lock names
        self._lock_stack: list[set[str]] = []
        # Current method name (for concurrent-method check)
        self._cur_method: str = ""
        # [Fix 4-b-007] Track async-ness of current method. An `async def`
        # method is concurrent BY DEFINITION (it runs on the event loop and
        # can be interleaved at any `await`). Treating it as concurrent
        # regardless of name (e.g. `async def calculate_metrics` was
        # previously NOT detected as concurrent because "calculate_metrics"
        # doesn't match _CONCURRENT_PREFIXES) closes blind spot #2.
        self._cur_method_is_async: bool = False
        # [Fix 4-b-007] Track whether the class has ANY async method. Used
        # to decide whether to skip the class entirely if no lock is declared
        # (blind spot #3: previously classes with `async def` + shared state
        # + NO lock attr were skipped at line 237).
        self._class_has_async: bool = False

    def _in_lock(self) -> bool:
        return any(bool(s) for s in self._lock_stack)

    def _is_concurrent_method(self) -> bool:
        # [Fix 4-b-007] An async method is concurrent by definition (event
        # loop interleaves coroutines at every `await`). Name prefix is no
        # longer required — `async def calculate_metrics(self)` is concurrent
        # even though "calculate_metrics" matches no _CONCURRENT_PREFIXES.
        if self._cur_method_is_async:
            return True
        if not self._cur_method:
            return False
        if self._cur_method.startswith("__"):
            return False  # __init__, __enter__, etc — usually single-thread
        # Exact match OR prefix match
        for p in _CONCURRENT_PREFIXES:
            if self._cur_method == p or self._cur_method.startswith(p):
                return True
        return False

    def visit_FunctionDef(self, node):
        # Enter method scope
        saved_method = self._cur_method
        saved_async = self._cur_method_is_async
        self._cur_method = node.name
        # Check if async
        is_async = isinstance(node, ast.AsyncFunctionDef)
        self._cur_method_is_async = is_async
        if is_async:
            self._class_has_async = True
        for stmt in node.body:
            self.visit(stmt)
        # Restore
        self._cur_method = saved_method
        self._cur_method_is_async = saved_async
        # Tag this finding set if any method was async — we don't track that
        # per-finding, so let's add it as a flag.
        if is_async and self._is_concurrent_method():
            for f in self.findings:
                if "method" not in f:
                    f["method"] = node.name
                    f["async"] = True

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node):
        # Detect `self._X = {}` or `self._X = []` etc. AND subscript assigns
        for tgt in node.targets:
            is_self, name = _is_self_attr(tgt)
            if not is_self:
                # Still check subscript assign below
                if (isinstance(tgt, ast.Subscript)
                        and isinstance(tgt.value, ast.Attribute)):
                    is_self2, name2 = _is_self_attr(tgt.value)
                    if is_self2 and name2 in self._mutable_attrs:
                        self._check_unsafe_mutation(node.lineno, name2, "subscript_assign")
                continue
            # [Fix 4-b-007] Use expanded lock-name hint set (_is_lock_name)
            # so asyncio.Semaphore / Condition / Event / Barrier are recognized.
            if _is_lock_name(name):
                self._lock_attrs.add(name)
                # Lock attrs themselves are not "mutable" in the race sense
                continue
            # Otherwise, check if it's a mutable init
            if _is_mutable_init(node.value):
                self._mutable_attrs[name] = node.lineno
            # Detect Subscript assign on mutable attr: self._X[k] = v
            if (isinstance(tgt, ast.Subscript)
                    and isinstance(tgt.value, ast.Attribute)):
                is_self3, name3 = _is_self_attr(tgt.value)
                if is_self3 and name3 in self._mutable_attrs:
                    self._check_unsafe_mutation(node.lineno, name3, "subscript_assign")
        # Visit RHS
        self.visit(node.value)

    def visit_With(self, node: ast.With):
        lock_names = _is_lock_with(node)
        self._lock_stack.append(set(lock_names))
        for stmt in node.body:
            self.visit(stmt)
        self._lock_stack.pop()
        # Visit context expressions (in case they have their own attrs)
        for item in node.items:
            self.visit(item.context_expr)

    visit_AsyncWith = visit_With

    def visit_AugAssign(self, node):
        # self._X += ...  or self._X[k] += ...
        if isinstance(node.target, ast.Attribute):
            is_self, name = _is_self_attr(node.target)
            if is_self and name in self._mutable_attrs:
                self._check_unsafe_mutation(node.lineno, name, "aug_assign")
        elif isinstance(node.target, ast.Subscript):
            is_self, name = _is_self_attr(node.target.value)
            if is_self and name in self._mutable_attrs:
                self._check_unsafe_mutation(node.lineno, name, "aug_assign_subscript")
        self.visit(node.value)

    def visit_Call(self, node: ast.Call):
        # self._X.append(...) / .pop() / .update() / .add() / etc.
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr in _MUTATING_METHODS):
            is_self, name = _is_self_attr(node.func.value)
            if is_self and name in self._mutable_attrs:
                self._check_unsafe_mutation(node.lineno, name, f"call_{node.func.attr}")
        self.generic_visit(node)

    def _check_unsafe_mutation(self, lineno: int, attr: str, kind: str):
        # If mutation is inside a `with self._lock:` block → safe
        if self._in_lock():
            return
        # [Fix 4-b-007] Old logic: `if not self._lock_attrs: return` — this
        # skipped ENTIRELY any class without a "lock"/"mutex" attr, even if
        # it had async methods mutating shared state. DNA #19: blind spot
        # = the scanner could not see the very class of race it was supposed
        # to detect (asyncio-based classes that forget to declare a lock).
        # New logic: only skip if the class has NEITHER a lock NOR any async
        # method (i.e. it's plausibly single-threaded). If the class has an
        # async method + shared mutable state + no lock, that's the bug
        # itself — flag it (kind="async_mutation_no_lock").
        if not self._lock_attrs and not self._cur_method_is_async:
            return
        if not self._is_concurrent_method():
            return
        # Distinguish "no lock at all + async" from "has lock but mutation
        # outside lock block" — the former is a stronger signal (class
        # designer forgot to add ANY concurrency primitive).
        if not self._lock_attrs and self._cur_method_is_async:
            kind = f"{kind}+async_no_lock"
        self.findings.append({
            "line": lineno,
            "class": self.class_name,
            "attr": attr,
            "kind": kind,
            "class_line": self.class_start_line,
            "method": self._cur_method,
        })


# [Fix 4-b-007] Module-level scan for asyncio.gather(...) without
# return_exceptions=True. This is a different class of bug from class-level
# race conditions: when gather() raises on the first exception, all other
# tasks are cancelled and their results (or exceptions) are lost. Caller
# cannot distinguish "1 of N failed" from "all N failed". DNA #19: scanner
# previously had no detection for this pattern — multiple scanner runs all
# agreed "no race found" because they shared this blind spot (DNA #5).
def _is_asyncio_gather_call(node: ast.Call) -> bool:
    """True if node is `asyncio.gather(...)` or `<asyncio_alias>.gather(...)`."""
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr == "gather"):
        return False
    # `asyncio.gather(...)` — direct module attribute access
    if isinstance(func.value, ast.Name) and func.value.id in _ASYNCIO_MODULE_NAMES:
        return True
    # `import asyncio as aio` then `aio.gather(...)` — caller alias. We can't
    # track import aliases without a symbol table, so accept any `*.gather`
    # call as a candidate (the kwarg check below is the real filter).
    # Conservative: require the receiver to be a Name (not e.g. `obj.gather()`
    # which would be a method on a user class).
    if isinstance(func.value, ast.Name):
        return True
    return False


def _gather_has_return_exceptions_true(node: ast.Call) -> bool:
    """True if call has `return_exceptions=True` (or any truthy literal)."""
    for kw in node.keywords:
        if kw.arg != "return_exceptions":
            continue
        v = kw.value
        if isinstance(v, ast.Constant) and v.value:
            return True
        if isinstance(v, ast.NameConstant) and v.value:  # py<3.8 compat
            return True
        if isinstance(v, ast.Name) and v.id == "True":
            return True
        # Any other expression (e.g. return_exceptions=some_var) — treat as
        # present (caller opted in) so we don't false-positive.
        return True
    return False


def _find_gather_without_return_exceptions(tree, filepath: str) -> list[dict]:
    """Walk module-level AST and find unsafe asyncio.gather(...) calls.

    Returns list of {line, kind="gather_no_return_exceptions"} dicts.
    """
    findings: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_asyncio_gather_call(node):
            continue
        if _gather_has_return_exceptions_true(node):
            continue
        findings.append({
            "line": node.lineno,
            "kind": "gather_no_return_exceptions",
            "filepath": filepath,
        })
    return findings


def _iter_python_files(root: Path, limit: int = _MAX_FILES):
    count = 0
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if "tests" in path.parts:
            continue
        if path.name.startswith("test_"):
            continue
        if any(part in ("examples", "scripts", "attack_payloads") for part in path.parts):
            continue
        if count >= limit:
            break
        yield path
        count += 1


class RaceConditionScanner:
    """Detect mutations on mutable class attrs outside lock blocks in concurrent methods.

    [Fix 4-b-007 · Phase 4-A] Now also detects:
      * asyncio primitives (Lock / Semaphore / Condition / Event / Barrier) via
        expanded lock-name hint set — previously only `lock`/`mutex` matched.
      * Any `async def` method as concurrent — previously only methods whose
        name matched `_CONCURRENT_PREFIXES` (so `async def calculate_metrics`
        was treated as single-threaded).
      * Classes with async methods + shared state + NO lock (previously
        skipped entirely at `if not self._lock_attrs: return`).
      * Module-level `asyncio.gather(...)` calls without `return_exceptions=True`
        (silent error-swallowing race — first exception cancels all siblings).

    Property-based reality test (`tests/reality-tests/reality_4-b-007.py`)
    feeds the scanner 4 race samples + 2 safe samples; the scanner MUST
    flag every race sample and pass every safe sample. Failure to do so
    means the scanner has a new blind spot (DNA #5 — ảo giác đồng thuận).
    """

    name: str = "RaceConditionScanner"
    bug_type: str = "RaceCondition"

    def __init__(self, scp_root: Path | None = None, max_files: int = _MAX_FILES):
        self.scp_root = scp_root or _SCP_ROOT
        self.max_files = max_files

    def scan(self) -> list[BugReport]:
        bugs: list[BugReport] = []
        files_scanned = 0
        for path in _iter_python_files(self.scp_root, limit=self.max_files):
            files_scanned += 1
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as parse_err:
                # silent-by-design: parse probe — unparseable file is skipped by this scan by design.
                logger.debug("race_condition_scanner: skipping unparseable file %s: %s", path, parse_err, exc_info=True)
                continue
            except Exception as read_err:  # noqa: S112
                logger.debug("race_condition_scanner: skipping unreadable file %s: %s", path, read_err, exc_info=True)
                continue

            # [Fix 4-b-007] Module-level pass: asyncio.gather without
            # return_exceptions=True. Independent of ClassDef pass.
            for f in _find_gather_without_return_exceptions(tree, str(path)):
                bugs.append(BugReport(
                    file=f["filepath"],
                    line=f["line"],
                    bug_type=self.bug_type,
                    description=(
                        f"RaceCondition: `asyncio.gather(...)` at line {f['line']} "
                        f"WITHOUT `return_exceptions=True` — the first raised "
                        f"exception will propagate, all other tasks are cancelled "
                        f"and their results/exceptions LOST. Caller cannot "
                        f"distinguish '1 of N failed' from 'all N failed'. "
                        f"(DNA #19 — scanner previously blind to this pattern.)"
                    ),
                    suggested_fix=(
                        "Pass `return_exceptions=True` to asyncio.gather() and "
                        "inspect each result for Exception instances, OR wrap each "
                        "task in try/except and aggregate errors explicitly."
                    ),
                    tier=BugTier.TIER_3_PERMISSION,  # silent error swallowing
                    affects_logic=True,
                ))

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                finder = _ClassRaceFinder(str(path), node.name, node.lineno)
                finder.visit(node)
                for f in finder.findings:
                    is_async_no_lock = "async_no_lock" in f["kind"]
                    bugs.append(BugReport(
                        file=str(path),
                        line=f["line"],
                        bug_type=self.bug_type,
                        description=(
                            f"RaceCondition: mutation `{f['kind']}` on mutable attr "
                            f"`self.{f['attr']}` (defined in class `{f['class']}` at "
                            f"line {f['class_line']}) at line {f['line']} in method "
                            f"`{f.get('method', '?')}` is NOT inside any "
                            f"`with self._lock:` block. Class declares lock(s) "
                            f"{sorted(finder._lock_attrs) if finder._lock_attrs else 'N/A'} "
                            f"→ concurrent calls may corrupt state."
                            + (
                                " [Fix 4-b-007] Method is `async def` — concurrent "
                                "by definition (event loop interleaves at every await). "
                                "Class declares NO concurrency primitive at all."
                                if is_async_no_lock else ""
                            )
                        ),
                        suggested_fix=(
                            "Wrap the mutation in `async with self._<lock>:` block, OR "
                            "document that the method is single-threaded only, OR "
                            "move the mutation into a method that already holds the lock."
                        ),
                        tier=BugTier.TIER_3_PERMISSION,  # concurrency changes semantics
                        affects_logic=True,
                    ))

        logger.info(
            f"[RaceConditionScanner] found {len(bugs)} race-risk mutation(s) "
            f"(scanned {files_scanned} files)"
        )
        return bugs
