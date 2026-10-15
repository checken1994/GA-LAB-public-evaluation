"""
[OPT-26] Patch validation — check patch before applying.

DNA SCP #7 AutoFix safe: validate BEFORE write, not after.
Checks:
  1. SEARCH block exists in target file
  2. REPLACE block is valid Python (ast.parse — supports fragments)
  3. REPLACE doesn't contain dangerous patterns (os.system, eval, exec, subprocess)
  4. SEARCH != REPLACE (actually changes something)
"""
from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("scp.autofix.validate_patch")


@dataclass
class ValidationResult:
    valid: bool
    reason: str
    search_found: bool = False
    syntax_ok: bool = False
    no_dangerous: bool = False
    has_change: bool = False


DANGEROUS_PATTERNS = [
    r'\bos\.system\s*\(',
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'\bsubprocess\.',
    r'\b__import__\s*\(',
    r'\bpopen\s*\(',
    r'\bpty\.spawn\s*\(',
    r'\bcommands\.getoutput\s*\(',
]


def _try_parse_fragment(code: str) -> bool:
    """Try parsing code as a Python fragment.

    REPLACE blocks are often code fragments (e.g., `except Exception as e:`)
    that are not valid standalone Python modules. We try multiple parse
    strategies to recognize syntactically valid fragments:
      1. As-is (standalone module)
      2. Indented inside a function body (wraps in `def _chk():\n    <code>`)
      3. Indented inside a try block (wraps in `try:\n    <code>`)
      4. Single expression (wraps in `_ = (<code>)`)

    [OPT-30] Bug fix: real LLM-generated REPLACE blocks are usually INDENTED
    (e.g. `    except Exception as e:\n        logger.warning(repr(e))`).
    Without dedent, strategies 1-4 all fail on indented except blocks because:
      - As-is: indented `except` at top level → SyntaxError
      - Wrap in def: `    except` inside function body without `try` → SyntaxError
      - Wrap in try: `    except` doesn't align with `try` → SyntaxError
    Fix: textwrap.dedent() the code first to strip common leading whitespace.
    This is safe (no-op for already top-level code) and makes the strategies
    work on real LLM output.

    Returns True if any parse strategy succeeds.
    """
    if not code.strip():
        return False

    # [OPT-30] Dedent first so indented fragments (real LLM output) work.
    import textwrap
    code = textwrap.dedent(code)

    # Strategy 1: as-is
    try:
        ast.parse(code)
        return True
    except SyntaxError as e:
        logger.warning(f"Silent except: {e}")

    # Strategy 2: wrap in function body (handles indented fragments like
    # `if x:\n    y()` or `for i in x:\n    y()`)
    try:
        indented = "\n".join("    " + line if line.strip() else line
                              for line in code.split("\n"))
        ast.parse(f"def _autofix_chk_():\n{indented}\n")
        return True
    except SyntaxError as e:
        logger.warning(f"Silent except: {e}")

    # Strategy 3: wrap after a try block (handles `except ...:` fragments —
    # the except clause must align with the try, NOT be indented further)
    try:
        ast.parse(f"try:\n    pass\n{code}\n")
        return True
    except SyntaxError as e:
        logger.warning(f"Silent except: {e}")

    # Strategy 4: single expression
    try:
        ast.parse(f"_ = ({code})")
        return True
    except SyntaxError as e:
        logger.warning(f"Silent except: {e}")

    return False


def flexible_replace(source: str, search: str, replace: str) -> str | None:
    """
    Attempts strict replacement. If it fails, attempts flexible replacement 
    ignoring leading/trailing whitespaces per line.
    Returns the new string if replaced, else None.
    """  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim
    if search in source:
        return source.replace(search, replace, 1)

    search_lines = search.splitlines()
    if not search_lines:
        return None

    # Flexible matching
    source_lines = source.splitlines(keepends=True)
    source_lines_stripped = [line.strip() for line in source_lines]
    search_lines_stripped = [line.strip() for line in search_lines]

    search_len = len(search_lines_stripped)
    source_len = len(source_lines_stripped)

    for i in range(source_len - search_len + 1):
        match = True
        for j in range(search_len):
            if source_lines_stripped[i + j] != search_lines_stripped[j]:
                match = False
                break

        if match:
            # We found a match! We should replace source_lines[i:i+search_len] with replace
            prefix = "".join(source_lines[:i])
            suffix = "".join(source_lines[i + search_len :])

            res = prefix + replace
            # If the original block had a trailing newline but replace doesn't, append it
            # Or simpler: just ensure we don't accidentally lose newlines between replace and suffix
            if suffix and not res.endswith('\n') and not suffix.startswith('\n'):
                res += '\n'

            return res + suffix

    return None


def validate_patch(file_path: str, search: str, replace: str) -> ValidationResult:
    """Validate a search-replace patch before applying.

    Args:
        file_path: Target file path
        search: SEARCH block (code to find)
        replace: REPLACE block (new code)

    Returns:
        ValidationResult with details
    """
    result = ValidationResult(valid=False, reason="")

    # 1. Check SEARCH exists in file
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        result.search_found = flexible_replace(content, search, replace) is not None
        if not result.search_found:
            result.reason = f"SEARCH block not found in {file_path}"
            return result
    except Exception as e:
        logger.debug(f"validate_patch: exception ignored: {e}", exc_info=True)
        # silent-by-design: explicit invalid result carrying the error reason is returned to the caller.
        result.reason = f"Cannot read file: {e}"
        return result

    # 2. Check SEARCH != REPLACE
    result.has_change = search.strip() != replace.strip()
    if not result.has_change:
        result.reason = "SEARCH and REPLACE are identical — no change"
        return result

    # 3. Check REPLACE syntax (supports code fragments)
    if _try_parse_fragment(replace):
        result.syntax_ok = True
    else:
        result.reason = "REPLACE has syntax error (not valid standalone nor fragment)"
        return result

    # 4. Check no dangerous patterns
    result.no_dangerous = True
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, replace):
            result.no_dangerous = False
            result.reason = f"Dangerous pattern detected: {pattern}"
            return result

    # All checks passed
    result.valid = True
    result.reason = "All validation checks passed"
    return result


def validate_patch_safety_only(replace: str) -> ValidationResult:
    """Validate only REPLACE block (for pre-check before file read)."""
    result = ValidationResult(valid=False, reason="")
    if not _try_parse_fragment(replace):
        result.reason = "REPLACE has syntax error (not valid standalone nor fragment)"
        return result
    result.syntax_ok = True
    result.no_dangerous = True
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, replace):
            result.no_dangerous = False
            result.reason = f"Dangerous pattern: {pattern}"
            return result
    result.valid = True
    result.reason = "Safety checks passed"
    return result


__all__ = ["validate_patch", "validate_patch_safety_only", "ValidationResult", "flexible_replace"]
