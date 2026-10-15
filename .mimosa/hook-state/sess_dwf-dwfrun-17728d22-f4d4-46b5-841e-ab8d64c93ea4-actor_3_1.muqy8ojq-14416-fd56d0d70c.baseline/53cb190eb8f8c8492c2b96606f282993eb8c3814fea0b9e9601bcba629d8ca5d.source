"""
SCP Evolution Modes — 5 deterministic pattern fixers.

[DNA7-FIX] Tạo module thật (trước đây missing → 5 fixers không hoạt động).

5 fixers (gọi TRƯỚC LLM — tiết kiệm credits):
  1. fix_type_mismatch    — type annotation mismatch
  2. add_null_check       — None dereference
  3. add_lock             — race condition (shared mutable)
  4. parameterize_sql     — SQL injection (string concat → parameterized)
  5. add_context_manager  — resource leak (open without close → with statement)

Mỗi fixer trả về SEARCH/REPLACE block hoặc None.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger("scp.autofix.evolution_modes")


def fix_type_mismatch(bug) -> str | None:
    """Fix type mismatch: int + str, list + dict, etc.

    Pattern: x = value + other_type → x = str(value) + other_type
    """
    filepath = Path(bug.file)
    if not filepath.exists():
        return None
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
        idx = bug.line - 1
        if idx >= len(lines):
            return None
        line = lines[idx]
        # Pattern: result = var1 + var2 (potential type mismatch)
        m = re.match(r'^(\s*)(\w+)\s*=\s*(\w+)\s*\+\s*(.+)$', line)
        if m:
            indent = m.group(1)
            result_var = m.group(2)
            left_var = m.group(3)
            right_expr = m.group(4)
            old = line.rstrip()
            new = f"{indent}{result_var} = str({left_var}) + str({right_expr})"
            return f"<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE"
    except Exception as _e:  # noqa: S110
        logger.debug(f"[silent-except] {_e}", exc_info=True)
    return None


def add_null_check(bug) -> str | None:
    """Fix None dereference: obj.attr → if obj is not None: obj.attr

    Pattern: x = obj.attribute → if obj is not None: x = obj.attribute
    """
    filepath = Path(bug.file)
    if not filepath.exists():
        return None
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
        idx = bug.line - 1
        if idx >= len(lines):
            return None
        line = lines[idx]
        # Pattern: var = obj.attr (potential None deref)
        m = re.match(r'^(\s*)(\w+)\s*=\s*(\w+)\.(\w+)$', line)
        if m:
            indent = m.group(1)
            result_var = m.group(2)
            obj_var = m.group(3)
            attr = m.group(4)
            old = line.rstrip()
            new = (
                f"{indent}if {obj_var} is not None:\n"
                f"{indent}    {result_var} = {obj_var}.{attr}\n"
                f"{indent}else:\n"
                f"{indent}    {result_var} = None"
            )
            return f"<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE"
    except Exception as _e:  # noqa: S110
        logger.debug(f"[silent-except] {_e}", exc_info=True)
    return None


def add_lock(bug) -> str | None:
    """Fix race condition: shared mutable without lock → add threading.Lock.

    Pattern: self._data[key] = value → with self._lock: self._data[key] = value
    """
    filepath = Path(bug.file)
    if not filepath.exists():
        return None
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
        idx = bug.line - 1
        if idx >= len(lines):
            return None
        line = lines[idx]
        # Pattern: self._xxx[key] = value (shared dict/list without lock)
        m = re.match(r'^(\s*)self\.(_\w+)\[(.+)\]\s*=\s*(.+)$', line)
        if m:
            indent = m.group(1)
            dict_name = m.group(2)
            key_expr = m.group(3)
            value_expr = m.group(4)
            old = line.rstrip()
            new = (
                f"{indent}with self._lock:\n"
                f"{indent}    self.{dict_name}[{key_expr}] = {value_expr}"
            )
            return f"<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE"
    except Exception as _e:  # noqa: S110
        logger.debug(f"[silent-except] {_e}", exc_info=True)
    return None


def parameterize_sql(bug) -> str | None:
    """Fix SQL injection: string concat → parameterized query.

    Pattern: unsafe inline SQL with interpolated variable → parameterized query.
    """
    filepath = Path(bug.file)
    if not filepath.exists():
        return None
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
        idx = bug.line - 1
        if idx >= len(lines):
            return None
        line = lines[idx]
        # Pattern: interpolated-SQL execute call → parameterized call
        m = re.match(r'^(\s*)(\w+\.execute)\(f["\'](.+)["\']\)$', line)
        if m:
            indent = m.group(1)
            execute_call = m.group(2)
            sql_template = m.group(3)
            # Extract variables from f-string
            vars_found = re.findall(r'\{(\w+)\}', sql_template)
            if vars_found:
                # Replace {var} with ? in SQL.
                # [S3-SECURITY-SWEEP] unwrap quotes around an interpolation
                # first: "'{name}'" -> ? (not "'?'") — a quoted question mark
                # is a string literal, not a bind parameter, so the previous
                # output was still not a truly parameterized query.
                sql_fixed = re.sub(r"(['\"])\{(\w+)\}\1", "?", sql_template)
                sql_fixed = re.sub(r'\{(\w+)\}', '?', sql_fixed)
                params = ", ".join(vars_found)
                old = line.rstrip()
                new = f'{indent}{execute_call}("{sql_fixed}", ({params},))'
                return f"<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE"
    except Exception as _e:  # noqa: S110
        logger.debug(f"[silent-except] {_e}", exc_info=True)
    return None


def add_context_manager(bug) -> str | None:
    """Fix resource leak: open() without close → with statement.

    Pattern: f = open(path) → with open(path) as f:
    """
    filepath = Path(bug.file)
    if not filepath.exists():
        return None
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
        idx = bug.line - 1
        if idx >= len(lines):
            return None
        line = lines[idx]
        # Pattern: var = open(path, mode)
        m = re.match(r'^(\s*)(\w+)\s*=\s*open\((.+)\)$', line)
        if m:
            indent = m.group(1)
            var_name = m.group(2)
            open_args = m.group(3)
            old = line.rstrip()
            new = f"{indent}with open({open_args}) as {var_name}:"
            return f"<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE"
    except Exception as _e:  # noqa: S110
        logger.debug(f"[silent-except] {_e}", exc_info=True)
    return None


# Registry: fixer name → function
FIXERS = {
    "fix_type_mismatch": fix_type_mismatch,
    "add_null_check": add_null_check,
    "add_lock": add_lock,
    "parameterize_sql": parameterize_sql,
    "add_context_manager": add_context_manager,
}


def fix_logic_flow(bug) -> str | None:
    """Fix logic flow bugs: unreachable code, dead branches, etc.

    Pattern: if True: ... else: ... (unreachable else)
    """
    filepath = Path(bug.file)
    if not filepath.exists():
        return None
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
        idx = bug.line - 1
        if idx >= len(lines):
            return None
        line = lines[idx]
        # Pattern: if True: or if False: (dead branch)
        m = re.match(r'^(\s*)if\s+(True|False)\s*:', line)
        if m:
            indent = m.group(1)
            condition = m.group(2)
            old = line.rstrip()
            if condition == "True":
                new = f"{indent}# Always true — else branch is dead code"
            else:
                new = f"{indent}# Always false — this branch is dead code"
            return f"<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE"
    except Exception as _e:  # noqa: S110
        logger.debug(f"[silent-except] {_e}", exc_info=True)
    return None
