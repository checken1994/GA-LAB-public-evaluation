"""[IMP-15] Semantic Equivalence Verification — REAL AST-based oracle.

TẠI SAO file này tồn tại (and why the old stub was a blocker):
  The previous implementation was ``def verify_semantic_equiv(...): return
  Result()`` — an unconditional ok=True stub. Phase IMP-15 (wired in
  runner_phases/post_fix_verify.py) therefore proved NOTHING: any patch,
  including one that silently rewrote unrelated behavior, was reported
  "semantically equivalent". Worse, the caller built
  ``_V3_SE_BugLoc(function_name=...)`` which raised TypeError (file_path and
  line are required fields) and the phase's ``except Exception`` swallowed it
  into "semantic equivalence failed" → spurious rollback whenever a backup +
  method_name existed. Vacuous when it ran, harmful when it didn't.

REAL contract implemented here (fail-closed oracle):
  - The TARGET function (bug_location.function_name) is extracted from both
    sources. Comparison = ``ast.dump`` of the function after normalization
    (docstrings stripped; comments never reach an AST; line/col attributes
    excluded via include_attributes=False).
      * identical  -> ok=True,  equivalent=True
      * different  -> ok=False, equivalent=False, diff reason recorded
    The honest ok=False is the ORACLE's answer ("the target function changed");
    the phase consumer decides what escalates (critical/over_broad drive
    all_ok in post_fix_verify.py — a target-function change is exactly what a
    real fix does, so it is reported but does not fail the phase gate).
  - Target function GONE from the fixed source -> critical=True, ok=False
    (existing phase contract: rollback — callers will break).
  - Target function unchanged but OTHER module statements changed ->
    over_broad=True, ok=False (the phase's documented purpose: catch fixes
    that reach outside bug_location).
  - Target function not found in the ORIGINAL source -> ok=False (cannot
    anchor the comparison; never claim equivalence without evidence).
  - Parse error on either side -> ok=False, equivalent=False (fail-closed).

The no-backup SKIP branch lives in post_fix_verify.py and is labeled
SKIPPED_NOT_IMPLEMENTED — a skipped phase is never counted as a pass.
"""
from __future__ import annotations

import ast
import copy
import dataclasses
import logging

logger = logging.getLogger("scp.autofix.semantic_equiv")

_MAX_DIFF_SUMMARIES = 5
_DIFF_SNIPPET_LEN = 80


@dataclasses.dataclass
class BugLocation:
    file_path: str
    line: int
    function_name: str | None = None
    class_name: str | None = None


class Result:
    def __init__(self) -> None:
        self.ok: bool = True
        self.equivalent: bool = True
        self.over_broad: bool = False
        self.critical: bool = False
        self.changed_statements: list = []
        self.reason: str = "ok"


def _find_function(tree: ast.AST, function_name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Find the first function/method node with the given name (BFS walk)."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return node
    return None


def _strip_docstrings(node: ast.AST) -> ast.AST:
    """Deep-copy ``node`` and remove docstring statements.

    A docstring is a leading string-Constant Expr in the body of a Module,
    FunctionDef, AsyncFunctionDef or ClassDef. Comments never appear in an
    AST, so stripping docstrings + dumping without attributes makes the
    comparison insensitive to formatting/comment-only edits while still
    catching ANY executable-structure difference.
    """
    node = copy.deepcopy(node)
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = sub.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                sub.body = body[1:] or [ast.Pass()]
    return node


def _normalized_dump(node: ast.AST) -> str:
    """Stable AST fingerprint: docstrings stripped, no line/col attributes."""
    return ast.dump(_strip_docstrings(node), include_attributes=False)


def _module_dump_without(tree: ast.Module, function_name: str) -> str:
    """Normalized dump of the module with its top-level ``function_name``
    statements removed — used for the over-broad (outside bug_location) check."""
    tree = copy.deepcopy(tree)
    tree.body = [
        stmt
        for stmt in tree.body
        if not (isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name == function_name)
    ]
    return _normalized_dump(tree)


def _changed_statement_summary(
    orig_node: ast.AST,
    fixed_node: ast.AST,
) -> list:
    """Human-readable summary of the first differing body statements.

    Statement indexes are approximate (an insertion shifts everything after
    it) — this is a diff REASON, not the comparison itself; the authoritative
    equivalence decision is the full normalized-dump equality.
    """
    orig_body = _strip_docstrings(orig_node).body
    fixed_body = _strip_docstrings(fixed_node).body
    summaries: list = []
    for idx in range(max(len(orig_body), len(fixed_body))):
        if idx < len(orig_body) and idx < len(fixed_body):
            if ast.dump(orig_body[idx]) == ast.dump(fixed_body[idx]):
                continue
            orig_repr = ast.unparse(orig_body[idx])[:_DIFF_SNIPPET_LEN]
            fixed_repr = ast.unparse(fixed_body[idx])[:_DIFF_SNIPPET_LEN]
            summaries.append(f"stmt#{idx}: {orig_repr!r} -> {fixed_repr!r}")
        elif idx < len(orig_body):
            summaries.append(f"stmt#{idx}: {ast.unparse(orig_body[idx])[:_DIFF_SNIPPET_LEN]!r} -> <absent>")
        else:
            summaries.append(f"stmt#{idx}: <absent> -> {ast.unparse(fixed_body[idx])[:_DIFF_SNIPPET_LEN]!r}")
        if len(summaries) >= _MAX_DIFF_SUMMARIES:
            break
    return summaries


def verify_semantic_equiv(
    original_source: str,
    fixed_source: str,
    bug_location: BugLocation | None,
) -> Result:
    """[IMP-15 REAL] AST-based semantic-equivalence oracle (see module docstring)."""
    result = Result()
    try:
        orig_tree = ast.parse(original_source or "")
        fixed_tree = ast.parse(fixed_source or "")
    except SyntaxError as exc:
        result.ok = False
        result.equivalent = False
        result.reason = f"parse error: {exc}"
        return result

    target_name = getattr(bug_location, "function_name", None) if bug_location is not None else None

    if target_name:
        orig_fn = _find_function(orig_tree, target_name)
        fixed_fn = _find_function(fixed_tree, target_name)
        if orig_fn is None:
            # Cannot anchor the oracle on the requested function — claiming
            # equivalence without evidence would be manufactured green.
            result.ok = False
            result.equivalent = False
            result.reason = (
                f"target function '{target_name}' not found in original source "
                f"— cannot anchor semantic equivalence"
            )
            return result
        if fixed_fn is None:
            result.ok = False
            result.equivalent = False
            result.critical = True
            result.reason = f"target function '{target_name}' GONE from fixed source"
            return result

        # MANDATED CHECK: normalized ast.dump of the target function pre/post.
        if _normalized_dump(orig_fn) != _normalized_dump(fixed_fn):
            result.ok = False
            result.equivalent = False
            result.changed_statements = _changed_statement_summary(orig_fn, fixed_fn)
            result.reason = (
                f"target function '{target_name}' AST changed pre/post "
                f"(normalized ast.dump differs)"
            )
            return result

        # Target function is unchanged — check the REST of the module for
        # over-broad changes (the phase's documented purpose).
        if _module_dump_without(orig_tree, target_name) != _module_dump_without(fixed_tree, target_name):
            result.ok = False
            result.equivalent = False
            result.over_broad = True
            result.changed_statements = _changed_statement_summary(
                _module_without(orig_tree, target_name),
                _module_without(fixed_tree, target_name),
            )
            result.reason = (
                f"changes OUTSIDE target function '{target_name}' detected "
                f"(over-broad fix) — escalating"
            )
            return result

        result.ok = True
        result.equivalent = True
        result.reason = "semantically equivalent (normalized AST identical pre/post)"
        return result

    # No function anchor: whole-module oracle.
    if _normalized_dump(orig_tree) != _normalized_dump(fixed_tree):
        result.ok = False
        result.equivalent = False
        result.changed_statements = _changed_statement_summary(orig_tree, fixed_tree)
        result.reason = "module AST changed pre/post (normalized ast.dump differs)"
        return result
    result.ok = True
    result.equivalent = True
    result.reason = "semantically equivalent (normalized AST identical pre/post)"
    return result


def _module_without(tree: ast.Module, function_name: str) -> ast.Module:
    """Copy of the module with top-level ``function_name`` statements removed."""
    tree = copy.deepcopy(tree)
    tree.body = [
        stmt
        for stmt in tree.body
        if not (isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name == function_name)
    ]
    return tree
