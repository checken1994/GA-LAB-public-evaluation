"""Deterministic, AST-aware patch recipes for the out-of-loop AutoFix worker.

The recipes in this module are deliberately conservative. They return a complete
candidate source and never mutate the target file or call a provider. A separate
worker owns policy evaluation, atomic write, verification, rollback and ledger
transitions.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("scp.autofix.deterministic_patches")


@dataclass(frozen=True)
class PatchCandidate:
    patch_id: str
    bug_type: str
    file: str
    risk: str
    source_hash_before: str
    source_after: str
    reason: str
    verify_after: Callable[[str], tuple[bool, str]]

    @property
    def after_hash(self) -> str:
        return hashlib.sha256(self.source_after.encode("utf-8")).hexdigest()

    @property
    def diff(self) -> str:
        before = self._source_before_for_diff
        return "".join(difflib.unified_diff(
            before.splitlines(keepends=True),
            self.source_after.splitlines(keepends=True),
            fromfile=self.file,
            tofile=f"{self.file} (deterministic candidate)",
        ))

    # The worker sets this private field after construction. Keeping it out of
    # the public constructor prevents recipes from accidentally using a stale
    # source when they are composed.
    _source_before_for_diff: str = ""


def _sha(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _candidate(
    *, patch_id: str, bug_type: str, file: str, risk: str,
    before: str, after: str, reason: str,
    verify_after: Callable[[str], tuple[bool, str]],
) -> PatchCandidate:
    c = PatchCandidate(
        patch_id=patch_id,
        bug_type=bug_type,
        file=file,
        risk=risk,
        source_hash_before=_sha(before),
        source_after=after,
        reason=reason,
        verify_after=verify_after,
    )
    object.__setattr__(c, "_source_before_for_diff", before)
    return c


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for match in re.finditer("\\n", source):
        offsets.append(match.end())
    return offsets


def _replace_node(source: str, node: ast.AST, replacement: str) -> str | None:
    lineno = getattr(node, "lineno", None)
    end_lineno = getattr(node, "end_lineno", None)
    col = getattr(node, "col_offset", None)
    end_col = getattr(node, "end_col_offset", None)
    if None in (lineno, end_lineno, col, end_col):
        return None
    offsets = _line_offsets(source)
    try:
        start = offsets[int(lineno) - 1] + int(col)
        end = offsets[int(end_lineno) - 1] + int(end_col)
    except (IndexError, TypeError) as offset_err:
        # silent-by-design: offset probe — None means "no snippet replaceable"
        # per the patch-builder contract.
        # [hygiene F821-fix] `bug` không tồn tại trong scope _replace_node()
        # (NameError trong except handler) — bỏ tham chiếu, log đủ ngữ cảnh.
        logger.debug("deterministic_patches: line offsets unusable: %s", offset_err, exc_info=True)
        return None
    if start < 0 or end < start or end > len(source):
        return None
    return source[:start] + replacement + source[end:]


def _has_logger_binding(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname == "logger" or (alias.name == "logger" and not alias.asname):
                    return True
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.asname == "logger" or (alias.name == "logger" and not alias.asname):
                    return True
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id == "logger":
                    return True
    return False


def _bare_except_candidate(bug, source: str, tree: ast.Module) -> PatchCandidate | None:
    if bug.bug_type not in {"BareExceptPass", "Ruff_BLE001", "BLE001"}:
        return None
    if not _has_logger_binding(tree):
        return None
    target: ast.ExceptHandler | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if int(getattr(node, "lineno", 0) or 0) != int(getattr(bug, "line", 0) or 0):
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Pass):
            continue
        target = node
        break
    if target is None:
        return None

    pass_node = target.body[0]
    pass_line_start = _line_offsets(source)[pass_node.lineno - 1]
    pass_line_end = source.find("\n", pass_line_start)
    if pass_line_end < 0:
        pass_line_end = len(source)
    pass_line = source[pass_line_start:pass_line_end]
    indent = pass_line[: len(pass_line) - len(pass_line.lstrip())]
    if target.name:
        exc_name = target.name
        handler_source = source
    else:
        exc_name = "_scp_exc"
        handler_start = _line_offsets(source)[target.lineno - 1]
        handler_end = source.find("\n", handler_start)
        if handler_end < 0:
            handler_end = len(source)
        handler_line = source[handler_start:handler_end]
        colon = handler_line.rfind(":")
        if colon < 0:
            return None
        new_handler_line = handler_line[:colon] + f" as {exc_name}" + handler_line[colon:]
        handler_source = source[:handler_start] + new_handler_line + source[handler_end:]
        # The pass node offset moved only when a newline was introduced. No
        # newline is introduced, so its location remains valid.
    # Recompute the pass-line offset after the optional handler-line edit;
    # adding `as _scp_exc` changes the byte offset of every later line.
    pass_line_start = _line_offsets(handler_source)[pass_node.lineno - 1]
    pass_line_end = handler_source.find("\n", pass_line_start)
    if pass_line_end < 0:
        pass_line_end = len(handler_source)
    pass_line = handler_source[pass_line_start:pass_line_end]
    indent = pass_line[: len(pass_line) - len(pass_line.lstrip())]
    new_pass = f'{indent}logger.debug(f"[SCP deterministic autofix] silenced exception: {{{exc_name}!r}}")'
    new_source = handler_source[:pass_line_start] + new_pass + handler_source[pass_line_end:]

    def verify(after: str) -> tuple[bool, str]:
        try:
            parsed = ast.parse(after)
        except SyntaxError as exc:
            return False, f"syntax error after BareExcept patch: {exc}"
        for node in ast.walk(parsed):
            if isinstance(node, ast.ExceptHandler) and node.lineno == target.lineno:
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    return False, "BareExcept handler still contains pass"
        return True, "BareExcept pass removed and logger call present"

    return _candidate(
        patch_id="bare_except_pass_ast_v1",
        bug_type=bug.bug_type,
        file=str(bug.file),
        risk="low",
        before=source,
        after=new_source,
        reason="AST matched one ExceptHandler with a single Pass and an existing logger binding",
        verify_after=verify,
    )


def _sql_text_parts(joined: ast.JoinedStr) -> tuple[str, list[str]] | None:
    sql_parts: list[str] = []
    names: list[str] = []
    for value in joined.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            sql_parts.append(value.value)
        elif isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name):
            sql_parts.append("?")
            names.append(value.value.id)
        else:
            return None
    sql = "".join(sql_parts)
    if not names or len(names) > 4:
        return None
    if ";" in sql:
        return None
    # Do not parameterize identifiers. Only values in a simple WHERE/VALUES
    # region are accepted; table/column/order interpolation is ambiguous.
    lowered = sql.lower()
    if re.search(r"\b(from|join|into|update|order\s+by|group\s+by)\s+\?", lowered):
        return None
    if " where " not in f" {lowered} " and " values " not in f" {lowered} ":
        return None
    return sql, names


def _sql_candidate(bug, source: str, tree: ast.Module) -> PatchCandidate | None:
    if bug.bug_type not in {"SQLInjection", "SQLInjectionVulnerability", "Sqli", "B608"}:
        return None
    target: ast.Call | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if int(getattr(node, "lineno", 0) or 0) != int(getattr(bug, "line", 0) or 0):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "execute":
            continue
        if not isinstance(node.args[0], ast.JoinedStr):
            continue
        target = node
        break
    if target is None:
        return None
    parts = _sql_text_parts(target.args[0])
    if parts is None:
        return None
    sql, names = parts
    func_source = ast.get_source_segment(source, target.func)
    if not func_source or not re.fullmatch(r"[A-Za-z_][\w.]*", func_source):
        return None
    sql_literal = json.dumps(sql, ensure_ascii=False)
    tuple_values = ", ".join(names) + ("," if len(names) == 1 else "")
    replacement = f"{func_source}({sql_literal}, ({tuple_values}))"
    new_source = _replace_node(source, target, replacement)
    if new_source is None:
        return None

    def verify(after: str) -> tuple[bool, str]:
        try:
            parsed = ast.parse(after)
        except SyntaxError as exc:
            return False, f"syntax error after SQL patch: {exc}"
        for node in ast.walk(parsed):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "execute":
                if node.lineno == target.lineno and node.args and isinstance(node.args[0], ast.JoinedStr):
                    return False, "SQL execute call still uses an f-string"
        return True, "SQL execute call uses a literal query plus bound parameters"

    return _candidate(
        patch_id="sql_parameterize_ast_v1",
        bug_type=bug.bug_type,
        file=str(bug.file),
        risk="medium",
        before=source,
        after=new_source,
        reason="AST matched cursor.execute with a simple WHERE/VALUES f-string and name-only values",
        verify_after=verify,
    )


def _missing_encoding_candidate(bug, source: str, tree: ast.Module) -> PatchCandidate | None:
    if bug.bug_type not in {"MissingEncoding", "MissingEncodingOpen", "Ruff_MissingEncoding"}:
        return None
    target: ast.Call | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "open":
            continue
        if int(getattr(node, "lineno", 0) or 0) != int(getattr(bug, "line", 0) or 0):
            continue
        if any(keyword.arg == "encoding" for keyword in node.keywords):
            continue
        mode = None
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
            mode = node.args[1].value
        if mode and "b" in mode:
            continue
        if any(keyword.arg in {"opener", "errors", "newline"} for keyword in node.keywords):
            continue
        target = node
        break
    if target is None:
        return None
    call_source = ast.get_source_segment(source, target)
    if not call_source or not call_source.endswith(")"):
        return None
    replacement = call_source[:-1] + (", " if len(target.args) or target.keywords else "") + 'encoding="utf-8")'
    new_source = _replace_node(source, target, replacement)
    if new_source is None:
        return None

    def verify(after: str) -> tuple[bool, str]:
        try:
            parsed = ast.parse(after)
        except SyntaxError as exc:
            return False, f"syntax error after encoding patch: {exc}"
        for node in ast.walk(parsed):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open" and node.lineno == target.lineno:
                if not any(k.arg == "encoding" for k in node.keywords):
                    return False, "open() still lacks encoding"
        return True, "text open() now has explicit UTF-8 encoding"

    return _candidate(
        patch_id="open_encoding_ast_v1",
        bug_type=bug.bug_type,
        file=str(bug.file),
        risk="low",
        before=source,
        after=new_source,
        reason="AST matched text open() without encoding, binary mode, opener or ambiguous keyword handling",
        verify_after=verify,
    )


def build_candidate(bug) -> PatchCandidate | None:
    """Return the first conservative candidate for a finding, or ``None``.

    This function is pure with respect to the target file: it reads and parses
    source but never writes it. The worker is the only component allowed to
    mutate files.
    """
    path = Path(str(getattr(bug, "file", "")))
    if not path.exists() or not path.is_file():
        return None
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as read_err:
        # silent-by-design: read/parse probe — None means "no patch candidate
        # extractable from this file".
        logger.debug("deterministic_patches: source read/parse failed for %s: %s", path, read_err, exc_info=True)
        return None
    for recipe in (_bare_except_candidate, _sql_candidate, _missing_encoding_candidate):
        try:
            candidate = recipe(bug, source, tree)
        except Exception as exc:  # recipes are isolated; no provider fallback
            logger.debug("deterministic recipe %s failed: %s", recipe.__name__, exc, exc_info=True)
            candidate = None
        if candidate is not None:
            return candidate
    return None


def candidate_patch_text(candidate: PatchCandidate) -> str:
    """Return a human-readable unified diff used by policy/audit records."""
    return candidate.diff


def candidate_search_replace(candidate: PatchCandidate) -> str:
    """Adapt a full-source candidate to the legacy engine patch contract."""
    return (
        f"<<<<<<< SEARCH\n{candidate._source_before_for_diff}\n"
        f"=======\n{candidate.source_after}\n>>>>>>> REPLACE"
    )


__all__ = [
    "PatchCandidate",
    "build_candidate",
    "candidate_patch_text",
    "candidate_search_replace",
]
