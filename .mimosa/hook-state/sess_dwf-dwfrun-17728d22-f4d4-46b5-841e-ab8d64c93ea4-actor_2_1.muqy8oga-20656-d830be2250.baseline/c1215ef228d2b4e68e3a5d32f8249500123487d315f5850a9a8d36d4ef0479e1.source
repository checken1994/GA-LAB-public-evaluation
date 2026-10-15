"""
[SCP-DNA-FIX R9 v4 IMP-20] Cross-File Type-Flow Verification.

TẠI SAO file này tồn tại?
  IMP-15 (semantic_equiv) chỉ so sánh signature của 1 hàm. IMP-16 (blast_radius)
  chỉ đếm số caller. Nhưng KHÔNG có module nào kiểm tra: "nếu fix đổi return
  type từ `Optional[X]` thành `X`, các caller `if result is None: ...` sẽ có
  dead branch — code không crash nhưng logic sai (DNA #22: PASS ≠ TRUE)".

  Ví dụ thực tế SCP:
    - Fix `def get_user(uid) -> Optional[User]` → `def get_user(uid) -> User`
      (loại bỏ None để đơn giản hóa). Nhưng 5 caller làm `if user is None:
      return 404`. Sau fix, branch `is None` không bao giờ True → 5 endpoint
      "trả 500 thay vì 404" vì code tiếp theo giả định None đã được xử lý.
    - Fix `def parse(s: Any) -> ...` → `def parse(s: str) -> ...` (narrowing).
      Caller `parse(request.json)` truyền dict → TypeError runtime.

  v4 IMP-20 thêm cross-file type-flow verification:
    1. Caller cung cấp orig_signature + new_signature (return type + arg types).
    2. Engine walk caller graph (shallow — own implementation, standalone).
    3. Với mỗi caller, check compatibility:
       - Return narrowing (Optional → X): caller có `if x is None` branch?
       - Return widening (X → Optional[X]): caller unwrap x.__attr__ mà không
         check None?
       - Arg narrowing (Any → int): caller truyền giá trị có thể không phải int?
    4. Trả về TypeFlowResult{compatible, breaking_callers, incompatible_sites}.

  Inspired by:
    - pyright strict mode (Microsoft, type-flow analysis)
    - mypy --strict + mypyc (drop-in runtime type check)
    - CodeQL type-flow taint tracking
    - TypeScript language server "find all references" + type compatibility

Flow:
  result = verify_type_flow(
      target_file="runtime/judge.py",
      target_function="ingestion_decision",
      orig_signature=Signature(args=["ctx"], returns="Optional[Decision]"),
      new_signature=Signature(args=["ctx"], returns="Decision"),
      scp_root="<GA-LAB_ROOT>/scp",
  )
  if not result.compatible:
      for site in result.incompatible_sites:
          log(f"Dead branch at {site.file}:{site.line}: {site.reason}")

DNA principles applied:
  #9  (No harm)         — type-flow breakage = silent regression
  #22 (PASS ≠ TRUE)     — fix "compiles + reality-tests OK" ≠ doesn't break callers
  #19 (Reality multi-source)— type signature + caller usage = 2 sources
  #7  (Autofix safe)    — fail-open: parse error / no callers → compatible=True

Light-touch: NO modification to any v2/v3 file. Standalone module.

[SCP-DNA-FIX R12-14] Integration status: WIRED in engine.py:1330-1410 (R10 IMP-20, fail-open). R12-13 REAL signature extraction (no longer empty).
  Wire in `runner_phases/post_fix_verify.py:run_full_post_fix_verify()`
  AFTER IMP-15 semantic_equiv. If `result.compatible == False` → cap fix
  confidence at 0.49 in IMP-14 (force human review per DNA #4/#17).

Smoke test (DNA #22 — verify it actually works, not just parses):
  $ python3 -c "
  from type_flow_verifier import verify_type_flow, Signature
  # No real scp_root needed — fail-open returns compatible=True
  r = verify_type_flow('fake.py', 'foo',
      Signature(args=['x'], returns='Optional[int]'),
      Signature(args=['x'], returns='int'),
      scp_root='/nonexistent')
  print(r.compatible, r.reason)
  "
  → True skip — no callers found (fail-open)
"""
from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.autofix.type_flow_verifier")


# ============================================================
# Bounded walk limits.
# ============================================================

MAX_FILES_TO_SCAN = 1000
MAX_NODES_PER_FILE = 5000
MAX_CALLERS_RECORDED = 100
MAX_BREAKING_SITES = 50


# ============================================================
# Type representation — parsed from annotation strings.
# ============================================================

@dataclass
class TypeNode:
    """A parsed type, e.g. Optional[int] -> TypeNode('Optional', [TypeNode('int')]).

    The `name` is the type constructor (e.g. 'int', 'str', 'Optional',
    'Union', 'List', 'Dict', 'Tuple', 'None'). The `args` are type params.
    """
    name: str
    args: list[TypeNode] = field(default_factory=list)

    def is_optional(self) -> bool:
        """True if this type is Optional[X] (i.e. Union[X, None])."""
        if self.name == "Optional" and len(self.args) == 1:
            return True
        if self.name == "Union":
            return any(a.name == "None" for a in self.args)
        if self.name == "None":
            return True
        return False

    def unwrap_optional(self) -> TypeNode:
        """Return X if self is Optional[X], else self."""
        if self.name == "Optional" and len(self.args) == 1:
            return self.args[0]
        if self.name == "Union":
            non_none = [a for a in self.args if a.name != "None"]
            if len(non_none) == 1:
                return non_none[0]
        return self

    def to_str(self) -> str:
        if not self.args:
            return self.name
        inner = ", ".join(a.to_str() for a in self.args)
        return f"{self.name}[{inner}]"


def parse_type(ann: str | None) -> TypeNode | None:
    """Parse a Python type annotation string into a TypeNode.

    Handles: int, str, Optional[X], List[X], Dict[K,V], Tuple[X,...],
    Union[X, Y, ...], None, 'X | Y' (PEP 604). Returns None on parse error.

    Fail-open: any error → None (caller treats as "unknown type, skip").
    """
    if not ann:
        return None
    try:
        s = ann.strip()
        if not s:
            return None
        # Strip quotes (forward-ref annotations).
        if s.startswith("'") and s.endswith("'"):
            s = s[1:-1]
        if s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
        # PEP 604: X | Y → Union[X, Y]
        if "|" in s and "[" not in s:
            parts = [p.strip() for p in s.split("|") if p.strip()]
            if len(parts) > 1:
                return TypeNode("Union", [parse_type(p) or TypeNode(p) for p in parts])
        # No bracket → primitive or class name.
        if "[" not in s:
            return TypeNode(s)
        # Has bracket: extract name + inner.
        idx = s.index("[")
        name = s[:idx].strip()
        inner = s[idx + 1: s.rindex("]")].strip()
        args = _split_top_level(inner)
        return TypeNode(name, [parse_type(a) or TypeNode(a.strip()) for a in args])
    except Exception as e:  # noqa: BLE001 — fail-open
        logger.debug(f"[IMP-20] parse_type error on {ann!r}: {e}")
        return None


def _split_top_level(s: str) -> list[str]:
    """Split 'X, Y, Dict[A, B]' → ['X', 'Y', 'Dict[A, B]'] (top-level commas only)."""
    out: list[str] = []
    depth = 0
    cur: list[str] = []
    for ch in s:
        if ch == "[":
            depth += 1
            cur.append(ch)
        elif ch == "]":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur).strip())
    return [x for x in out if x]


# ============================================================
# Signature dataclass.
# ============================================================

@dataclass
class Signature:
    """A function signature used for type-flow analysis.

    Attributes:
        args: List of arg type strings (positional). E.g. ['int', 'str'].
        returns: Return type string. E.g. 'Optional[User]'.
        arg_names: Optional list of arg names (for keyword-call detection).
    """
    args: list[str] = field(default_factory=list)
    returns: str = ""
    arg_names: list[str] = field(default_factory=list)


# ============================================================
# Caller / Site dataclasses.
# ============================================================

@dataclass
class CallerSite:
    """A single call site to the target function."""
    file: str
    line: int
    col: int = 0
    context: str = ""       # short source snippet for audit
    # Pattern flags (caller-usage patterns that may conflict with new type):
    checks_none: bool = False        # caller has `if result is None`
    unwraps_attr: bool = False       # caller does `result.attr` (without None check)
    passes_arg_index: int = -1       # which positional arg the call passes
    passes_arg_repr: str = ""        # short repr of the arg expression
    # [SCP-DNA-FIX R13-6] Bug #2: previously _check_arg_compat used
    # `"int" in passes_arg_repr` (substring matching) which caused both
    # false positives (string "winter" contains "int" as substring →
    # flagged as int) and false negatives (string "hello" passed to int
    # arg → not flagged because "int" not in "hello"). We now store the
    # literal's *type tag* (resolved from the AST node at scan time),
    # so compatibility can be decided by isinstance-equivalent.
    passes_arg_literal_type: str = ""  # "int"|"str"|"float"|"bool"|"None"|
                                       # "list"|"dict"|"tuple"|"set"|"name"|
                                       # "call"|"attr"|"<other>"|""


@dataclass
class IncompatibleSite:
    """A caller site that breaks under the new signature."""
    caller: CallerSite
    reason: str
    severity: str = "warning"   # "warning" | "error"


@dataclass
class TypeFlowResult:
    """Outcome of verify_type_flow()."""
    compatible: bool = True
    breaking_callers: list[str] = field(default_factory=list)
    incompatible_sites: list[IncompatibleSite] = field(default_factory=list)
    caller_count: int = 0
    reason: str = ""
    bounded: bool = False   # True if any cap was hit

    def to_dict(self) -> dict[str, Any]:
        return {
            "compatible": self.compatible,
            "breaking_callers_count": len(self.breaking_callers),
            "incompatible_sites_count": len(self.incompatible_sites),
            "caller_count": self.caller_count,
            "reason": self.reason,
            "bounded": self.bounded,
            "incompatible_sites": [
                {
                    "file": s.caller.file,
                    "line": s.caller.line,
                    "reason": s.reason,
                    "severity": s.severity,
                    "context": s.caller.context,
                }
                for s in self.incompatible_sites
            ],
        }


# ============================================================
# Call-site collector — AST visitor.
# ============================================================

class _CallSiteCollector(ast.NodeVisitor):
    """Walks an AST tree, collects all call sites of `target_function`.

    For each call site, also detects:
        - Whether the result is checked for None (`if x is None`).
        - Whether the result is unwrapped via attribute access (`x.attr`).
    """

    def __init__(self, target_function: str, target_file: str) -> None:
        self.target = target_function
        self.target_file = target_file
        self.sites: list[CallerSite] = []
        self._node_count = 0
        # Track names currently bound to a fresh call result (within ~5 stmts).
        # Mapping: var name → CallerSite of the assignment.
        self._recent_bindings: dict[str, CallerSite] = {}
        # Pending assign target: when visit_Assign detects `name = <call to target>`,
        # it sets this name so visit_Call (called next via generic_visit) can
        # bind the freshly-created site to it.
        self._pending_target_name: str | None = None

    def _bump_node(self) -> bool:
        """Return True if we should keep walking (under cap)."""
        self._node_count += 1
        return self._node_count <= MAX_NODES_PER_FILE

    def _is_target_call(self, func_node: ast.expr) -> bool:
        """True if func_node is a call to self.target."""
        if isinstance(func_node, ast.Name) and func_node.id == self.target:
            return True
        if isinstance(func_node, ast.Attribute) and func_node.attr == self.target:
            return True
        return False

    def visit_Call(self, node: ast.Call) -> Any:  # noqa: N802
        if not self._bump_node():
            return
        # Detect call to target_function.
        target_hit = self._is_target_call(node.func)

        if target_hit and len(self.sites) < MAX_CALLERS_RECORDED:
            site = CallerSite(
                file=self.target_file,
                line=getattr(node, "lineno", 0),
                col=getattr(node, "col_offset", 0),
                context=self._snippet(node),
                passes_arg_index=0,
                passes_arg_repr=self._arg_repr(node),
                # [SCP-DNA-FIX R13-6] Bug #2: capture the literal type
                # via isinstance() at scan time, so _check_arg_compat
                # can do real type matching instead of substring matching.
                passes_arg_literal_type=self._arg_literal_type(node),
            )
            self.sites.append(site)
            # If this call is the RHS of an assignment we just entered,
            # bind the LHS name to this site.
            if self._pending_target_name is not None:
                self._recent_bindings[self._pending_target_name] = site
                self._pending_target_name = None

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> Any:  # noqa: N802
        if not self._bump_node():
            return
        # If RHS is a Call to target, set pending_target_name so visit_Call
        # (invoked next via generic_visit on node.value) can bind the site.
        saved_pending = self._pending_target_name
        if isinstance(node.value, ast.Call) and self._is_target_call(node.value.func):
            # Only support single-Name target (e.g. `t = get_thing()`).
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                self._pending_target_name = node.targets[0].id
        self.generic_visit(node)
        # Restore (in case visit_Call didn't fire / wasn't a target).
        self._pending_target_name = saved_pending

    def visit_If(self, node: ast.If) -> Any:  # noqa: N802
        if not self._bump_node():
            return
        # Detect `if <name> is None` or `if <name> is not None`.
        name = self._is_none_check(node.test)
        if name and name in self._recent_bindings:
            site = self._recent_bindings[name]
            site.checks_none = True
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> Any:  # noqa: N802
        if not self._bump_node():
            return
        # If `name.attr` and name is a recent binding → unwrap.
        if isinstance(node.value, ast.Name):
            name = node.value.id
            if name in self._recent_bindings:
                self._recent_bindings[name].unwraps_attr = True
        self.generic_visit(node)

    # --- Helpers ---

    def _is_none_check(self, test: ast.expr) -> str | None:
        """Return the var name if `test` is `name is None` / `name is not None`."""
        try:
            if isinstance(test, ast.Compare):
                if len(test.ops) == 1 and len(test.comparators) == 1 and isinstance(test.ops[0], (ast.Is, ast.IsNot)):
                    # Left is variable name, comparator is None constant
                    if isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value is None:
                        return test.left.id
                    # Left is None constant, comparator is variable name (e.g. None is x)
                    if isinstance(test.left, ast.Constant) and test.left.value is None and isinstance(test.comparators[0], ast.Name):
                        return test.comparators[0].id
            return None
        except Exception:  # noqa: BLE001
            return None  # silent-by-design: analysis probe — None means "no none-check detected" per the helper contract

    def _snippet(self, node: ast.Call) -> str:
        """Return a short source snippet for the call (best-effort)."""
        try:
            if isinstance(node.func, ast.Name):
                return f"{node.func.id}(...)"
            if isinstance(node.func, ast.Attribute):
                return f"...{node.func.attr}(...)"
            return "<call>"
        except Exception:  # noqa: BLE001
            return "<call>"  # silent-by-design: best-effort snippet — placeholder marks the failed formatting (documented in docstring)

    def _arg_repr(self, node: ast.Call) -> str:
        """Return a short repr of the first positional arg."""
        try:
            if node.args:
                a = node.args[0]
                if isinstance(a, ast.Name):
                    return f"Name({a.id})"
                if isinstance(a, ast.Constant):
                    return f"Const({a.value!r})"
                if isinstance(a, ast.Call):
                    return "Call(...)"
                if isinstance(a, ast.Attribute):
                    return f"Attr(.{a.attr})"
                return f"{type(a).__name__}"
            return "<no-args>"
        except Exception:  # noqa: BLE001
            return "<err>"

    # [SCP-DNA-FIX R13-6] Bug #2: companion to passes_arg_literal_type.
    # Returns a stable type tag for the first positional arg literal,
    # decided by isinstance() on the AST node (not substring matching).
    def _arg_literal_type(self, node: ast.Call) -> str:
        """Return a type tag for the first positional arg, or "" if unknown.

        Uses isinstance on the AST node — equivalent to type matching at
        runtime, NOT substring matching on the repr (which was buggy).
        """
        try:
            if not node.args:
                return ""
            a = node.args[0]
            # ast.Constant covers Python 3.8+ (replaces ast.Num/ast.Str/
            # ast.NameConstant which are deprecated aliases).
            if isinstance(a, ast.Constant):
                v = a.value
                # IMPORTANT: bool is a subclass of int — check bool FIRST.
                if isinstance(v, bool):
                    return "bool"
                if isinstance(v, int):
                    return "int"
                if isinstance(v, float):
                    return "float"
                if isinstance(v, str):
                    return "str"
                if v is None:
                    return "None"
                if isinstance(v, bytes):
                    return "bytes"
                return "Const<other>"
            if isinstance(a, ast.Name):
                return "name"
            if isinstance(a, ast.Call):
                return "call"
            if isinstance(a, ast.Attribute):
                return "attr"
            if isinstance(a, (ast.List,)):
                return "list"
            if isinstance(a, (ast.Dict,)):
                return "dict"
            if isinstance(a, (ast.Tuple,)):
                return "tuple"
            if isinstance(a, (ast.Set,)):
                return "set"
            return "<other>"
        except Exception:  # noqa: BLE001
            return ""  # silent-by-design: literal-type probe — empty tag means "unknown literal type" per the helper contract


# ============================================================
# Compatibility logic.
# ============================================================

def _is_narrowing(orig: TypeNode | None, new: TypeNode | None) -> bool:
    """True if `new` is narrower than `orig` (a stricter type).

    Heuristics:
        - Optional[X] → X: narrowing (removed None from union).
        - Any → X: narrowing (Any is universal).
        - X → Optional[X]: NOT narrowing (widening).
        - List[Any] → List[int]: narrowing (element type stricter).
    """
    if orig is None or new is None:
        return False
    # Optional[X] → X
    if orig.is_optional() and not new.is_optional():
        return True
    # Any → anything
    if orig.name == "Any" and new.name != "Any":
        return True
    # List[Any] → List[X]
    if orig.name == new.name and len(orig.args) == len(new.args) and orig.args:
        return any(_is_narrowing(o, n) for o, n in zip(orig.args, new.args))
    return False


def _is_widening(orig: TypeNode | None, new: TypeNode | None) -> bool:
    """True if `new` is wider than `orig` (less strict)."""
    if orig is None or new is None:
        return False
    if not orig.is_optional() and new.is_optional():
        return True
    if orig.name != "Any" and new.name == "Any":
        return True
    return False


def _check_return_compat(
    site: CallerSite,
    orig_ret: TypeNode | None,
    new_ret: TypeNode | None,
) -> str | None:
    """Return a reason string if the return-type change breaks this caller."""
    if orig_ret is None or new_ret is None:
        return None
    # Narrowing Optional[X] → X: caller's `is None` check is now dead branch.
    if _is_narrowing(orig_ret, new_ret) and orig_ret.is_optional():
        if site.checks_none:
            return (
                "return narrowed Optional→X but caller has dead `is None` branch "
                "(DNA #22: PASS ≠ TRUE — runtime may not crash but logic is wrong)"
            )
    # Widening X → Optional[X]: caller's `result.attr` may AttributeError on None.
    if _is_widening(orig_ret, new_ret) and new_ret.is_optional():
        if site.unwraps_attr and not site.checks_none:
            return (
                "return widened X→Optional[X] but caller unwraps attribute "
                "without None check (will AttributeError on None)"
            )
    return None


def _check_arg_compat(
    site: CallerSite,
    orig_args: list[TypeNode | None],
    new_args: list[TypeNode | None],
) -> str | None:
    """Return reason if any arg type narrows incompatibly with what caller passes."""
    # We don't actually parse caller-side arg expressions (too noisy).
    # Heuristic: if arg type narrowed from Any → specific, and caller passes
    # something that looks like a literal of a different type, flag.
    # In practice, we only flag if narrowing is dramatic (Any → int) AND
    # caller passes a non-int literal (Const str/dict/list).
    try:
        idx = site.passes_arg_index
        if idx < 0 or idx >= len(new_args):
            return None
        orig_t = orig_args[idx] if idx < len(orig_args) else None
        new_t = new_args[idx]
        if not _is_narrowing(orig_t, new_t):
            return None
        # [SCP-DNA-FIX R13-6] Bug #2: previously this used substring
        # matching against site.passes_arg_repr (e.g. `"int" in repr_`).
        # That caused:
        #   - FALSE POSITIVE: caller passes "winter" (string) to a str-typed
        #     arg → flagged as "passes an int literal" because "int" is a
        #     substring of "winter".
        #   - FALSE NEGATIVE: caller passes "hello" (string) to an int-typed
        #     arg → NOT flagged because "int" not in "hello".
        # Now we use site.passes_arg_literal_type, which is decided by
        # isinstance() on the AST node at scan time (real type matching).
        arg_type = site.passes_arg_literal_type
        if not arg_type:
            # Unknown arg shape (e.g. operator expression, starred arg) —
            # can't decide, fail-open (don't flag).
            return None
        if new_t and new_t.name == "int":
            # Anything that's NOT "int" / "bool" / "name" / "call" / "attr"
            # (we can't be sure about name/call/attr — they might be int).
            # We DO flag strings, lists, dicts, tuples, sets, floats, None.
            if arg_type in {"str", "list", "dict", "tuple", "set", "float", "None", "bytes"}:
                return (
                    f"arg[{idx}] narrowed Any→int but caller passes a {arg_type} literal"
                )
            return None
        if new_t and new_t.name == "str":
            # Caller passes a non-string literal → flag.
            if arg_type in {"int", "bool", "float", "list", "dict", "tuple", "set", "None", "bytes"}:
                return (
                    f"arg[{idx}] narrowed Any→str but caller passes a {arg_type} literal"
                )
            return None
        return None
    except Exception as narrowing_err:  # noqa: BLE001
        # silent-by-design: narrowing-analysis probe — None means "no narrowing
        # violation detected"; a crash here must not flag a false incompatibility.
        logger.debug("type_flow_verifier: Any-narrowing analysis crashed, no verdict: %s", narrowing_err, exc_info=True)
        return None


# ============================================================
# File walking.
# ============================================================

def _iter_python_files(scp_root: str) -> list[Path]:
    """Yield .py files under scp_root, skipping noise dirs.

    [A12 H-1] Deterministic walk: sort theo path TRƯỚC khi cap (thứ tự rglob
    phụ thuộc OS) + WARNING tường minh khi truncation xảy ra — cấm cắt im
    lặng ~20% cây scan."""
    root = Path(scp_root)
    if not root.exists() or not root.is_dir():
        return []
    skip_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}
    try:
        out = sorted(
            p for p in root.rglob("*.py")
            if not any(part in skip_dirs for part in p.parts)
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[IMP-20] file walk error: {e}")
        return []
    if len(out) > MAX_FILES_TO_SCAN:
        logger.warning(
            "[scanner-cap] %s: %d file .py vượt cap %d — cắt còn %d "
            "(nâng MAX_FILES_TO_SCAN nếu cần full coverage)",
            __name__, len(out), MAX_FILES_TO_SCAN, MAX_FILES_TO_SCAN,
        )
        out = out[:MAX_FILES_TO_SCAN]
    return out


def _scan_file_for_calls(
    file_path: Path,
    target_function: str,
) -> tuple[list[CallerSite], bool]:
    """Scan one file for call sites of target_function. Returns (sites, bounded)."""
    sites: list[CallerSite] = []
    bounded = False
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-20] read error {file_path}: {e}")
        return [], False
    # Cheap pre-filter: skip files that don't even mention the name.
    if target_function not in text:
        return [], False
    try:
        tree = ast.parse(text, filename=str(file_path))
    except SyntaxError as e:
        logger.debug(f"[IMP-20] syntax error in {file_path}: {e}")
        return [], False
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-20] parse error in {file_path}: {e}")
        return [], False

    try:
        collector = _CallSiteCollector(target_function, str(file_path))
        collector.visit(tree)
        sites = collector.sites
        if collector._node_count >= MAX_NODES_PER_FILE:
            bounded = True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[IMP-20] collect error in {file_path}: {e}")
    return sites, bounded


# ============================================================
# Public API.
# ============================================================

def verify_type_flow(
    target_file: str,
    target_function: str,
    orig_signature: Signature,
    new_signature: Signature,
    scp_root: str,
) -> TypeFlowResult:
    """Verify that changing `target_function`'s signature from
    `orig_signature` to `new_signature` doesn't break any caller.

    Steps:
        1. Walk scp_root for .py files mentioning target_function.
        2. AST-parse each, collect call sites.
        3. For each call site, check:
            - Return type change compatibility (caller checks None / unwraps attr).
            - Arg type change compatibility (caller passes wrong-typed literal).
        4. Aggregate incompatible sites → result.compatible = False.

    Args:
        target_file: File containing the function (for skip-self).
        target_function: Function name (e.g. "ingestion_decision").
        orig_signature: Signature before the fix.
        new_signature: Signature after the fix.
        scp_root: Root of the codebase to walk (e.g. <GA-LAB_ROOT>/scp).

    Returns:
        TypeFlowResult. Fail-open: parse error / no callers found →
        compatible=True with reason="skip — type-flow unverifiable".
    """
    result = TypeFlowResult()
    try:
        if not target_function:
            result.compatible = True
            result.reason = "skip — no target_function (fail-open)"
            return result

        # Parse signatures.
        orig_args = [parse_type(t) for t in orig_signature.args]
        new_args = [parse_type(t) for t in new_signature.args]
        orig_ret = parse_type(orig_signature.returns)
        new_ret = parse_type(new_signature.returns)

        # If we can't parse the new return type, fail-open.
        if new_signature.returns and new_ret is None:
            result.compatible = True
            result.reason = (
                "skip — new return type unparseable "
                f"({new_signature.returns!r}, fail-open)"
            )
            return result

        # Walk files.
        files = _iter_python_files(scp_root)
        if not files:
            result.compatible = True
            result.reason = "skip — no callers found (fail-open)"
            return result

        all_sites: list[CallerSite] = []
        bounded = False
        target_path = Path(target_file).resolve()
        for fp in files:
            try:
                if fp.resolve() == target_path:
                    continue  # don't scan the file itself
            except Exception as _scp_exc:  # noqa: BLE001
                logger.debug(f"[SCP deterministic autofix] silenced exception: {_scp_exc!r}")
            sites, b = _scan_file_for_calls(fp, target_function)
            if b:
                bounded = True
            all_sites.extend(sites)
            if len(all_sites) >= MAX_CALLERS_RECORDED:
                bounded = True
                break

        result.caller_count = len(all_sites)
        result.bounded = bounded

        if not all_sites:
            result.compatible = True
            result.reason = "skip — no callers found (fail-open)"
            return result

        # Check each site.
        for site in all_sites:
            reason = _check_return_compat(site, orig_ret, new_ret)
            if reason:
                result.incompatible_sites.append(IncompatibleSite(
                    caller=site, reason=reason, severity="warning",
                ))
                if site.file not in result.breaking_callers:
                    result.breaking_callers.append(site.file)
                continue
            arg_reason = _check_arg_compat(site, orig_args, new_args)
            if arg_reason:
                result.incompatible_sites.append(IncompatibleSite(
                    caller=site, reason=arg_reason, severity="warning",
                ))
                if site.file not in result.breaking_callers:
                    result.breaking_callers.append(site.file)
            if len(result.incompatible_sites) >= MAX_BREAKING_SITES:
                result.bounded = True
                break

        if result.incompatible_sites:
            result.compatible = False
            result.reason = (
                f"{len(result.incompatible_sites)} incompatible caller site(s) "
                f"across {len(result.breaking_callers)} file(s)"
            )
        else:
            result.compatible = True
            result.reason = (
                f"type-flow compatible across {result.caller_count} caller(s)"
            )

    except Exception as e:  # noqa: BLE001 — fail-open per DNA #7
        logger.warning(f"[IMP-20] verify_type_flow error: {e}")
        result.compatible = True
        result.reason = f"skip — internal error (fail-open): {e}"

    return result


def summarize_type_flow(result: TypeFlowResult) -> str:
    """Return a short human-readable summary for audit log."""
    try:
        if result.compatible:
            return f"OK — {result.reason}"
        sites = result.incompatible_sites[:5]
        lines = [f"INCOMPATIBLE — {result.reason}"]
        for s in sites:
            lines.append(f"  - {s.caller.file}:{s.caller.line} — {s.reason}")
        if len(result.incompatible_sites) > 5:
            lines.append(f"  ... and {len(result.incompatible_sites) - 5} more")
        return "\n".join(lines)
    except Exception as sum_err:  # noqa: BLE001
        # silent-by-design: summary formatting probe — placeholder keeps the audit line alive.
        logger.debug("type_flow_verifier: summary formatting failed: %s", sum_err, exc_info=True)
        return "<summary error>"


__all__ = [
    "TypeNode",
    "parse_type",
    "Signature",
    "CallerSite",
    "IncompatibleSite",
    "TypeFlowResult",
    "verify_type_flow",
    "summarize_type_flow",
]
