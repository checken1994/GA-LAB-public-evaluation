# [V9.0-SCANNER] StaticMethodSelfScanner — detect `@staticmethod` on methods using `self`.
#
# TẠI SAO scanner này tồn tại?
#   Python runtime raises TypeError khi gọi `obj.method()` nếu method bị gắn
#   `@staticmethod` nhưng body dùng `self.` (truy cập instance attrs). Đây là
#   LỖI RUNTIME THẬT — không bắt được bởi ruff `--select=S` (chỉ security),
#   chỉ bắt được bởi PLW0211 (pylint rule mà SCP không wire cho tới mission này).
#
#   Concretely: scp/runtime/judge.py:691 đã từng bị — `_get_exp_policies(self)`
#   `@staticmethod` nhưng body `self._exp_policies` → crash TypeError khi gọi
#   từ judgecore_mixin.py:514,873. Mission 1 (Task 5-8) đã fix thủ công.
#   Scanner này đảm bảo SCP TỰ BẮT được lớp lỗi này trong tương lai.
#
# LOGIC:
#   - Duyệt AST, tìm FunctionDef có decorator `staticmethod`.
#   - Nếu first arg tên là `self` HOẶC body có `ast.Attribute(value=Name('self'))`
#     → flag PLW0211.
#   - Chỉ flag trong class body (không phải module-level function).
#
# CONSERVATIVE:
#   - Chỉ flag `self` (không flag `cls` — `@staticmethod` với `cls` cũng sai nhưng
#     hiếm và thường là staticmethod本当 không nên có arg đầu).
#   - Skip nếu method rỗng hoặc chỉ có docstring (pass) — không đủ evidence.
#
# RETURNS:
#   list[BugReport] — bug_type="Ruff_PLW0211" (mapping với rule code ruff)
from __future__ import annotations

import ast
import logging
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.staticmethod_self")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 500


class _StaticMethodSelfFinder(ast.NodeVisitor):
    """Visit class bodies; flag @staticmethod methods that use `self`."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.bugs: list[BugReport] = []
        self._class_depth = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_depth += 1
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._check_method(item)
        self.generic_visit(node)
        self._class_depth -= 1

    def _check_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check if a @staticmethod method uses self."""
        # Only inside a class
        if self._class_depth < 1:
            return
        # Check decorators for @staticmethod (plain, no args)
        is_static = False
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name) and dec.id == "staticmethod":
                is_static = True
                break
        if not is_static:
            return

        # Check 1: first arg named `self` (immediate red flag)
        args = node.args
        first_arg_is_self = (
            args.args
            and args.args[0].arg == "self"
        )

        # Check 2: body references `self.X` (Attribute on Name('self'))
        uses_self_attr = False
        for child in ast.walk(node):
            if (isinstance(child, ast.Attribute)
                    and isinstance(child.value, ast.Name)
                    and child.value.id == "self"):
                uses_self_attr = True
                break

        if not (first_arg_is_self or uses_self_attr):
            return

        # Skip empty methods (just docstring + pass) — not enough evidence
        real_stmts = [s for s in node.body if not isinstance(s, ast.Expr)]
        if not real_stmts:
            return

        reason_parts = []
        if first_arg_is_self:
            reason_parts.append("first arg named `self`")
        if uses_self_attr:
            reason_parts.append("body uses `self.attr`")
        reason = " + ".join(reason_parts)

        self.bugs.append(BugReport(
            file=self.filepath,
            line=node.lineno,
            bug_type="Ruff_PLW0211",
            description=(
                f"PLW0211: `@staticmethod` on method `{node.name}` but {reason} — "
                f"calling `obj.{node.name}()` will raise TypeError at runtime. "
                f"Fix: remove `@staticmethod` (method is instance-bound)."
            ),
            suggested_fix=(
                f"Remove `@staticmethod` decorator from `{node.name}` — it uses "
                f"instance state and must be a regular instance method."
            ),
            tier=BugTier.TIER_3_PERMISSION,  # NEVER_AUTO_FIX: needs human judgment
            affects_logic=False,  # HOW not WHAT, but classified Tier-3 for safety
        ))


def scan_file(path: Path) -> list[BugReport]:
    """Scan a single file for @staticmethod+self bugs."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError, OSError) as e:
        logger.debug(f"[staticmethod_self] parse failed {path}: {e}")
        return []
    finder = _StaticMethodSelfFinder(str(path))
    finder.visit(tree)
    return finder.bugs


def scan_scp() -> list[BugReport]:
    """Scan entire scp/ package for @staticmethod+self bugs."""
    bugs: list[BugReport] = []
    count = 0
    for path in _SCP_ROOT.rglob("*.py"):
        if count >= _MAX_FILES:
            break
        if "__pycache__" in str(path):
            continue
        count += 1
        bugs.extend(scan_file(path))
    if bugs:
        logger.info(f"[staticmethod_self] scanned {count} files, found {len(bugs)} PLW0211 bugs")
    return bugs


__all__ = ["scan_file", "scan_scp"]
