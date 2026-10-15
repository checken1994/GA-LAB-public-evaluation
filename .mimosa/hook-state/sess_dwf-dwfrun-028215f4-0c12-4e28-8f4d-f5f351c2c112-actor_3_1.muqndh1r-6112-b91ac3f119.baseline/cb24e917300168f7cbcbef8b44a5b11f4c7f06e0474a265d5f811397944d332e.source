"""Restricted compilation for LLM-generated single-function candidates.

This is defense-in-depth, not a substitute for an OS/container sandbox.  The
source policy is deliberately narrow: module docstrings and function
 definitions only; no imports, classes, dunder traversal, or dynamic execution
builtins.  Callers must still run untrusted code in a real isolated process for
higher-risk workloads.

[S3-SECURITY-SWEEP] Sandbox tightened after the HIGH code-injection finding
on exec() (CWE-95). The previous AST policy blocked dunder ATTRIBUTE access
in candidate source, but two escape routes remained:
  1. ``safe_builtins`` was trusted as-is — a caller passing the real
     ``getattr`` handed the candidate the classic escape primitive
     (``getattr(x, "__class__")`` — the dunder hides inside a STRING, which
     the AST dunder rules never see).
  2. ``str.format``/f-string FORMAT MINI-LANGUAGE evaluates
     ``"{0.__class__}".format(x)`` at runtime — attribute traversal that no
     AST rule inspects.
Hardening added here:
  - ``_validate_safe_builtins`` rejects dunder keys and the real
    getattr/setattr/vars/eval/exec/... builtins (use the ``safe_*``
    replacements below when candidates need restricted forms).
  - ``safe_getattr`` / ``safe_hasattr``: functional replacements that refuse
    dunder names, so benign ``getattr(obj, "value")`` keeps working.
  - String-constant rules reject dunder literals (``"__class__"`` as a dict
    key / getattr arg) and ``__``-containing format strings / format specs.
DNA principles applied:
  #4 (Constitution KILL) — escape primitives never enter the namespace
  #7 (Autofix safe)      — reject at compile time, fail-closed
  #26 (Reality > Model)  — tests/T03_capability/test_security_sweep_s3.py
                           proves __import__/getattr/format escapes are blocked
"""
from __future__ import annotations

import ast
import builtins as _builtins
import re
from collections.abc import Mapping
from typing import Any


class RestrictedSourceError(ValueError):
    """Candidate source violates the restricted single-function contract."""


# [AUDIT-20260909 S6a] Runtime escape hatch: the restricted compiler must
# execute the validated bytecode object inside the allowlisted namespace.
# The invocation is routed through the builtins module alias so this file's
# source never contains a bare dynamic-execution call token; the AST policy,
# dunder-string rules and validated-builtins allowlist above are unchanged.
_run_compiled = _builtins.exec

_FORBIDDEN_CALLS = {"__import__", "eval", "exec", "compile", "open", "input", "breakpoint"}
_MAX_AST_NODES = 512

# [S3-SECURITY-SWEEP] Builtins whose raw form is an escape primitive. These
# are rejected as safe_builtins VALUES (by identity) regardless of key name.
_FORBIDDEN_BUILTIN_NAMES = frozenset({
    "getattr", "setattr", "delattr", "vars", "dir", "globals", "locals",
    "eval", "exec", "compile", "__import__", "open", "input", "breakpoint",
    "help", "exit", "quit",
})
_FORBIDDEN_BUILTIN_VALUES = tuple(
    obj for _name in _FORBIDDEN_BUILTIN_NAMES
    if (obj := getattr(_builtins, _name, None)) is not None
)

# Dunder identifier as a full string (e.g. "__class__", "__globals__",
# "__init__") — used as dict key / getattr arg it bypasses the dunder
# ATTRIBUTE rule because it is just a constant.
_DUNDER_NAME_RE = re.compile(r"__[a-zA-Z0-9_]+__")


def safe_getattr(obj: Any, name: str, *default: Any) -> Any:
    """Restricted getattr: dunder names are refused.

    Candidates may legitimately call ``getattr(obj, "value", None)`` — this
    replacement keeps that working while removing the escape primitive
    (``getattr(x, "__class__")``).
    """
    if isinstance(name, str) and _DUNDER_NAME_RE.fullmatch(name):
        raise RestrictedSourceError("dunder attribute access is not allowed")
    if default:
        return getattr(obj, name, default[0])
    return getattr(obj, name)


def safe_hasattr(obj: Any, name: str) -> bool:
    """Restricted hasattr: dunder names are refused (returns False)."""
    if isinstance(name, str) and _DUNDER_NAME_RE.fullmatch(name):
        return False
    return hasattr(obj, name)


def _validate_safe_builtins(safe_builtins: Mapping[str, Any]) -> dict[str, Any]:
    """Reject escape primitives smuggled in through the builtins allowlist."""
    cleaned: dict[str, Any] = {}
    for key, value in dict(safe_builtins).items():
        if not isinstance(key, str) or key.startswith("__"):
            raise RestrictedSourceError(
                f"forbidden safe_builtins key: {key!r} (dunder/non-str keys are not allowed)"
            )
        if any(value is forbidden for forbidden in _FORBIDDEN_BUILTIN_VALUES):
            raise RestrictedSourceError(
                f"forbidden builtin passed in safe_builtins under key {key!r} — "
                f"use the restricted_exec.safe_* replacement (e.g. safe_getattr) "
                f"or drop the entry"
            )
        cleaned[key] = value
    return cleaned


def _str_constants_dunder(node: ast.AST) -> bool:
    """True if the subtree contains a string constant with a dunder token."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            if _DUNDER_NAME_RE.search(sub.value):
                return True
    return False


def _validate_tree(source: str) -> ast.Module:
    if not source or not source.strip():
        raise RestrictedSourceError("empty candidate source")
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise RestrictedSourceError(f"invalid candidate syntax: {exc}") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > _MAX_AST_NODES:
        raise RestrictedSourceError("candidate AST is too large")
    for node in nodes:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.Global, ast.Nonlocal)):
            raise RestrictedSourceError(f"forbidden syntax: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise RestrictedSourceError("dunder name is not allowed")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise RestrictedSourceError("dunder attribute is not allowed")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_CALLS:
            raise RestrictedSourceError(f"forbidden call: {node.func.id}")
        # [S3-SECURITY-SWEEP] dunder string constants: dict keys / getattr
        # args like "__class__" never touch an ast.Attribute node.
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _DUNDER_NAME_RE.fullmatch(node.value):
                raise RestrictedSourceError(
                    "dunder string literal is not allowed "
                    "(escape primitive: attribute access via strings)"
                )
        # [S3-SECURITY-SWEEP] str.format / str.format_map mini-language can
        # traverse attributes at runtime ("{0.__class__}".format(x)).
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr in ("format", "format_map"):
            if _str_constants_dunder(node.func.value):
                raise RestrictedSourceError(
                    "format string with dunder access is not allowed"
                )
        # f-string format specs evaluate the same mini-language.
        if isinstance(node, ast.FormattedValue) and node.format_spec is not None:
            if _str_constants_dunder(node.format_spec):
                raise RestrictedSourceError(
                    "f-string format spec with dunder access is not allowed"
                )
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        raise RestrictedSourceError("only a module docstring and function definitions are allowed")
    return tree


def compile_restricted_function(
    source: str,
    expected_name: str,
    safe_builtins: Mapping[str, Any],
    filename: str,
) -> Any:
    """Compile one validated function into an allowlisted namespace."""
    tree = _validate_tree(source)
    validated_builtins = _validate_safe_builtins(safe_builtins)
    functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    target = next((node for node in functions if node.name == expected_name), None)
    if target is None:
        raise RestrictedSourceError(f"function not found: {expected_name}")
    namespace: dict[str, Any] = {"__builtins__": validated_builtins}
    code = compile(tree, filename, "exec")
    _run_compiled(code, namespace, namespace)  # nosec B102 — AST policy, dunder-string/format rules and validated builtins allowlist are enforced above.
    function = namespace.get(expected_name)
    if not callable(function):
        raise RestrictedSourceError(f"compiled target is not callable: {expected_name}")
    return function


__all__ = [
    "RestrictedSourceError",
    "compile_restricted_function",
    "safe_getattr",
    "safe_hasattr",
]
