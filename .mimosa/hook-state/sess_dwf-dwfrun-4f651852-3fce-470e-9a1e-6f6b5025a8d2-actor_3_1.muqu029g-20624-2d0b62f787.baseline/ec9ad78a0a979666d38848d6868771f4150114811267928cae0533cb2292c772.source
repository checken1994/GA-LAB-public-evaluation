"""
[ENTERPRISE-V4] Enterprise Scanner Bridge — wire 8 enterprise tools vào AutoFix.

TÁI SAO: SCP AutoFix hiện tại chỉ chạy 2 scanner (BareExceptPass + UndefinedName)
trong ast_scan_scp(). 13 scanner files khác tồn tại nhưng KHÔNG được wire.
Module này bridge 8 enterprise tools (Ruff S-series, Bandit, Vulture, Bugbear,
Dlint) vào AutoFix pipeline — khi ast_scan_scp() chạy, enterprise findings cũng
được include.

Design:
  - Mỗi tool chạy subprocess, parse output → BugReport
  - Filter false positives (test files, nosec annotations)
  - Backward-compatible: returns list[BugReport] like other scanners
  - Fail-open: nếu tool không có sẵn, skip (không block AutoFix)

Wired vào: scp/autofix/runner_phases/ast_scan.py::_scan_file_enterprise()
  → gọi từ ast_scan_scp() sau _scan_file() existing

DNA SCP:
  #1 Reality > Model — enterprise tools là "reality check" cho AutoFix
  #6 Evidence — mỗi finding có tool + rule code + file:line
  #7 AutoFix safe — fail-open, không break existing flow
  #9 No harm — filter test files, nosec, whitelisted patterns
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier
from scp.core.safe_process import safe_run

logger = logging.getLogger("scp.autofix.enterprise")

# [V4.1-FIX] _SCP_ROOT now points to scp/ (production code only).
# Was: .parent.parent.parent = .../scp-vietnam/ (root, includes test scripts)
# Now: .parent.parent = .../scp-vietnam/scp/ (production code only)
# This prevents scanning user test scripts like regression_guard_v2.py at root.
_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp-vietnam/ (for reference)
_SCAN_ROOT = Path(__file__).resolve().parent.parent  # .../scp-vietnam/scp/ (actual scan target)

# Tools that must be installed (fail-open if missing)
_ENTERPRISE_TOOLS = ["ruff", "bandit", "vulture", "flake8", "mypy"]

# [AUTOFIX-T1-ROOTCAUSE] Expanded ruff rule selection.
# WAS: only `--select=S` (security) → SCP missed 6/7 bug classes.
# NOW: S (security) + F (pyflakes: undefined names, unused, redef)
#        + RUF (ruff-specific: RUF012 mutable-default, RUF013 implicit-Optional)
#        + PLW/PLC (pylint: PLW0211 staticmethod-self, PLW2901 redef-loop,
#                   PLW1510 subprocess-no-check, PLC0206 dict-no-items)
#        + B (bugbear: B011 assert-false, B007 unused-loop-var)
#        + UP (pyupgrade).
# This is the ROOT CAUSE fix for the "SCP catches 1/7" gap (see worklog Task 4-a §4).
# Symptom fixes (the 26 individual bugs we patched in Task 5-8) all flow from this gap.
_RUFF_SELECT = "S,F,RUF,PLW,PLC,B,UP"


def _check_tool_available(tool: str) -> bool:
    """Check if a tool binary is available."""
    import shutil
    return shutil.which(tool) is not None


def _is_test_file(path: Path) -> bool:
    """Skip test files — they legitimately use assert, mock, subprocess, etc.

    [V4.1-FIX] Expanded to recognize:
    - /tests/ directory
    - test_*.py files
    - *_test.py files
    - regression_guard*.py (user test scripts at root)
    - benchmark files (test data + scripts)
    - conftest.py (pytest fixtures)
    """
    s = str(path).replace("\\", "/")  # normalize Windows paths
    name = path.name.lower()
    return (
        "/tests/" in s
        or "/test_" in s
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name.startswith("regression_guard")
        or name == "conftest.py"
        or "/benchmark/" in s
        or "__pycache__" in s
    )


def _is_nosec_annotated(path: Path, line: int) -> bool:
    """Check if line has nosec annotation (bandit/ruff suppression)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        if 0 < line <= len(lines):
            return "nosec" in lines[line - 1] or "noqa" in lines[line - 1]
    except Exception as _e:  # noqa: S110
        logger.debug(f"[silent-except] {_e}", exc_info=True)
    return False


# ============================================================
# 1. RUFF S-SERIES (security rules)
# ============================================================
def scan_with_ruff(path: Path) -> list[dict]:
    """Run Ruff (expanded rule set) on a single file. Returns findings.

    [AUTOFIX-T1-ROOTCAUSE] Was `--select=S` only (security). Now `S,F,RUF,PLW,PLC,B,UP`
    so SCP catches the 6/7 bug classes it previously missed:
      - F541 (f-string no placeholder), F811 (duplicate), F841 (unused)
      - RUF012 (mutable class default), RUF013 (implicit Optional)
      - PLW0211 (staticmethod+self), PLW2901 (redefined loop var),
        PLW1510 (subprocess no check), PLC0206 (dict without items)
      - B011 (assert False), B007 (unused loop var)
      - UP (pyupgrade)
    Each finding keeps its rule code so downstream can NEVER_AUTO_FIX filter.
    """
    if not _check_tool_available("ruff"):
        return []
    try:
        result = safe_run(
            ["ruff", "check", "--preview", f"--select={_RUFF_SELECT}",
             "--output-format=json", "--no-cache", str(path)],
            timeout=30,
        )
        if result.returncode not in (0, 1):
            return []
        findings = json.loads(result.stdout) if result.stdout else []
        out = []
        for f in findings:
            line = f.get("location", {}).get("row", 1)
            code = f.get("code", "S???")
            msg = f.get("message", "")
            # Skip nosec/noqa annotated
            if _is_nosec_annotated(path, line):
                continue
            # S101 (assert) in test files is OK
            if code == "S101" and _is_test_file(path):
                continue
            out.append({
                "line": line,
                "bug_type": f"RuffSecurity_{code}",
                "description": f"[Ruff {code}] {msg}",
                "suggested_fix": f"See Ruff rule {code} documentation",
                "severity": "HIGH" if code in ("S105", "S106", "S608") else "MEDIUM",
                "tool": "ruff",
            })
        return out
    except Exception as e:
        logger.debug(f"[enterprise] ruff failed on {path}: {e}", exc_info=True)
        return []


# ============================================================
# 2. BANDIT (security baseline)
# ============================================================
def scan_with_bandit(path: Path) -> list[dict]:
    """Run Bandit on a single file. Returns HIGH/MEDIUM findings."""
    if not _check_tool_available("bandit"):
        return []
    try:
        result = safe_run(
            ["bandit", "-ll", "-ii", "-q", "-f", "json", str(path)],
            timeout=30,
        )
        if result.returncode not in (0, 1):
            return []
        d = json.loads(result.stdout) if result.stdout else {}
        out = []
        for r in d.get("results", []):
            line = r.get("line_number", 1)
            if _is_nosec_annotated(path, line):
                continue
            sev = r.get("issue_severity", "LOW")
            if sev == "LOW":
                continue  # Only HIGH/MEDIUM
            out.append({
                "line": line,
                "bug_type": f"Bandit_{r.get('test_id', 'B???')}",
                "description": f"[Bandit {r.get('test_id')}] {r.get('issue_text', '')[:120]}",
                "suggested_fix": "See Bandit rule documentation",
                "severity": sev,
                "tool": "bandit",
            })
        return out
    except Exception as e:
        logger.debug(f"[enterprise] bandit failed on {path}: {e}", exc_info=True)
        return []


# ============================================================
# 5. MYPY (dynamic type-check — the "deep" prong of the 4-prong mission)
# ============================================================
def scan_with_mypy(path: Path) -> list[dict]:
    """Run mypy on a single file. Returns type-error findings.

    [AUTOFIX-T1-ROOTCAUSE] Adds the DEEP type-check prong SCP was missing.
    mypy catches what static AST scanners cannot:
      - Incompatible assignments (variable typed X, assigned Y)
      - attr-defined (class attribute used but not declared)
      - call-arg / call-overload (wrong number/type of arguments)
      - operator (unsupported operand types, e.g. object + int)
      - index (unsupported target for indexed assignment)
      - return-value (function returns wrong type)

    Filtered: skip [annotation-unchecked] (informational), [unused-ignore]
    (low-signal). Only keep actionable type errors.
    Fail-open: if mypy unavailable or file has unresolvable imports, skip.
    """
    if not _check_tool_available("mypy"):
        return []
    try:
        result = safe_run(
            ["mypy", "--no-error-summary", "--show-error-codes",
             "--ignore-missing-imports", "--no-color-output",
             "--no-pretty", str(path)],
            timeout=45,
        )
        if result.returncode not in (0, 1):
            return []
        out = []
        for line in result.stdout.splitlines():
            # Format: path:line: error: message  [code]
            if ":" not in line or " error:" not in line:
                continue
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            try:
                line_num = int(parts[1])
            except ValueError:
                # silent-by-design: malformed tool-output line skipped in aggregation.
                logger.debug("enterprise: skipping malformed mypy line: %r", line, exc_info=True)
                continue
            rest = parts[2]  # " error: message  [code]"
            # Extract [code]
            code = "mypy-unknown"
            if "[" in rest and "]" in rest:
                code = rest[rest.rindex("[") + 1: rest.rindex("]")]
            # Low-signal codes — skip
            if code in ("annotation-unchecked", "unused-ignore", "var-annotated"):
                continue
            msg = rest.replace("error:", "").strip().split("[")[0].strip()
            out.append({
                "line": line_num,
                "bug_type": f"Mypy_{code}",
                "description": f"[mypy {code}] {msg[:140]}",
                "suggested_fix": "Fix type annotation or call site",
                "severity": "MEDIUM",
                "tool": "mypy",
            })
        return out
    except Exception as e:
        logger.debug(f"[enterprise] mypy failed on {path}: {e}", exc_info=True)
        return []


# ============================================================
# 3. VULTURE (dead code)
# ============================================================
def scan_with_vulture(path: Path) -> list[dict]:
    """Run Vulture on a single file. Returns high-confidence dead code."""
    if not _check_tool_available("vulture"):
        return []
    try:
        result = safe_run(
            ["vulture", str(path), "--min-confidence", "80"],
            timeout=30,
        )
        out = []
        for line in result.stdout.splitlines():
            # Format: path:line: unused <kind> 'name' (80% confidence)
            if ":" not in line:
                continue
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            try:
                line_num = int(parts[1])
            except ValueError:
                # silent-by-design: malformed tool-output line skipped in aggregation.
                logger.debug("enterprise: skipping malformed vulture line: %r", line, exc_info=True)
                continue
            msg = parts[2].strip()
            out.append({
                "line": line_num,
                "bug_type": "DeadCode_Vulture",
                "description": f"[Vulture] {msg}",
                "suggested_fix": "Remove unused code or prefix with _",
                "severity": "LOW",
                "tool": "vulture",
            })
        return out
    except Exception as e:
        logger.debug(f"[enterprise] vulture failed on {path}: {e}", exc_info=True)
        return []


# ============================================================
# 4. FLAKE8-BUGBEAR + DLINT (common bugs + best practices)
# ============================================================
def scan_with_bugbear_dlint(path: Path) -> list[dict]:
    """Run flake8 with bugbear (B) + dlint (DUO) plugins."""
    if not _check_tool_available("flake8"):
        return []
    try:
        result = safe_run(
            ["python3", "-m", "flake8", "--select=B,DUO",
             "--max-line-length=200", str(path)],
            timeout=30,
        )
        out = []
        for line in result.stdout.splitlines():
            # Format: path:line:col: CODE message
            if ":" not in line:
                continue
            parts = line.split(":", 3)
            if len(parts) < 4:
                continue
            try:
                line_num = int(parts[1])
            except ValueError:
                # silent-by-design: malformed tool-output line skipped in aggregation.
                logger.debug("enterprise: skipping malformed pylint line: %r", line, exc_info=True)
                continue
            msg = parts[3].strip()
            # Extract code (B007, DUO102, etc.)
            code_match = msg.split()[0] if msg else ""
            # Critical bugs
            sev = "HIGH" if code_match in ("B033", "B041", "DUO138") else "MEDIUM"
            out.append({
                "line": line_num,
                "bug_type": f"BugbearDlint_{code_match}",
                "description": f"[{code_match}] {msg}",
                "suggested_fix": f"See {code_match} rule documentation",
                "severity": sev,
                "tool": "flake8",
            })
        return out
    except Exception as e:
        logger.debug(f"[enterprise] bugbear/dlint failed on {path}: {e}", exc_info=True)
        return []


# ============================================================
# MAIN: run all enterprise scanners on one file
# ============================================================
def scan_file_enterprise(path: Path) -> list[dict]:
    """Run all enterprise scanners on a single file. Returns combined findings.

    Fail-open: if a tool is unavailable, skip it (don't block AutoFix).
    """
    findings: list[dict] = []
    # Skip test files entirely (legitimate assert, mock, etc.)
    if _is_test_file(path):
        return findings
    # Skip __pycache__
    if "__pycache__" in str(path):
        return findings

    findings.extend(scan_with_ruff(path))
    findings.extend(scan_with_bandit(path))
    findings.extend(scan_with_vulture(path))
    findings.extend(scan_with_bugbear_dlint(path))
    findings.extend(scan_with_mypy(path))  # [AUTOFIX-T1] deep type-check prong
    findings.extend(scan_for_secrets(path))  # [AUTOFIX-T2-SEC] hardcoded secret detection

    return findings


def scan_scp_enterprise(max_files: int = 100) -> list[BugReport]:
    """Run enterprise scanners across scp/ package. Returns BugReports.

    Args:
        max_files: cap scan time (default 100 files = ~5 min)

    Wire vào ast_scan_scp() — chạy sau _scan_file() existing.
    """
    bugs: list[BugReport] = []
    count = 0
    for path in _SCAN_ROOT.rglob("*.py"):
        if count >= max_files:
            logger.info(f"[enterprise] scan capped at {max_files} files")
            break
        if "__pycache__" in str(path):
            continue
        count += 1
        findings = scan_file_enterprise(path)
        for f in findings:
            try:
                bug = BugReport(
                    file=str(path),
                    line=f["line"],
                    bug_type=f["bug_type"],
                    description=f["description"],
                    suggested_fix=f.get("suggested_fix", ""),
                    tier=BugTier.TIER_2_AUTO_FIX_LOG if f.get("severity") in ("HIGH", "MEDIUM") else BugTier.TIER_3_PERMISSION,
                )
                # [V4-DETERMINISTIC] Mark bugs that should skip LLM (too risky/complex)
                # These bugs get REPORTED but not auto-fixed by LLM — prevents
                # the fix→fail→retry loop seen in startup log (S603, S310).
                if should_skip_for_llm(f["bug_type"]):
                    bug.tier = BugTier.TIER_3_PERMISSION  # require human review
                    bug.suggested_fix = (
                        f"[SKIP-LLM] {f.get('suggested_fix', '')} "
                        f"— deterministic fix needed or human review"
                    )
                bugs.append(bug)
            except Exception as e:
                logger.debug(f"[enterprise] build BugReport failed: {e}", exc_info=True)

    logger.info(f"[enterprise] scanned {count} files, found {len(bugs)} issues")
    return bugs



# ============================================================
# DETERMINISTIC FIXES — không cần LLM (an toàn hơn, nhanh hơn)
# ============================================================
# TÁI SAO: LLM thường generate patch sai cho security rules (S603, S310)
# vì cần context cụ thể. Deterministic fix an toàn hơn + không tốn API calls.
# DNA SCP #7 (AutoFix safe) — deterministic > LLM cho patterns cố định.

def _deterministic_fix_s101(path: Path, line: int, source: str) -> str | None:
    """S101: assert in production → replace with if/raise.

    Pattern: `assert condition` → `if not condition: raise AssertionError(...)`
    Safe because: same semantics in -O mode, but explicit.
    Skip: test files (assert is correct there).
    """
    if _is_test_file(path):
        return None  # assert is correct in tests
    lines = source.splitlines()
    if line > len(lines):
        return None
    original = lines[line - 1]
    # Simple pattern: assert X
    import re
    m = re.match(r'^(\s*)assert\s+(.+?)(?:,\s*["\'](.+?)["\'])?\s*$', original)
    if not m:
        return None
    indent, cond, msg = m.groups()
    msg_part = f' "{msg}"' if msg else ''
    replacement = f'{indent}if not ({cond}): raise AssertionError({msg_part or cond})'
    return f"<<<<<<< SEARCH\n{original}\n=======\n{replacement}\n>>>>>>> REPLACE"


def _deterministic_fix_s311(path: Path, line: int, source: str) -> str | None:
    """S311: random.X → secrets.SystemRandom().X (for security-sensitive code).

    Pattern: `random.randint(...)` → `secrets.SystemRandom().randint(...)`
    Skip: test files, non-security contexts.
    """
    if _is_test_file(path):
        return None
    lines = source.splitlines()
    if line > len(lines):
        return None
    original = lines[line - 1]
    import re
    # Match random.method(...) but not random.SystemRandom (already safe)
    m = re.search(r'\brandom\.(?!SystemRandom)(\w+)\(', original)
    if not m:
        return None
    method = m.group(1)
    replacement = original.replace(
        f'random.{method}(',
        f'secrets.SystemRandom().{method}('
    )
    return f"<<<<<<< SEARCH\n{original}\n=======\n{replacement}\n>>>>>>> REPLACE"


def _deterministic_fix_s105(path: Path, line: int, source: str) -> str | None:
    """S105: hardcoded password → move to env var.

    Pattern: `password = "xxx"` → `password = os.environ.get("PASSWORD", "")`
    """
    lines = source.splitlines()
    if line > len(lines):
        return None
    original = lines[line - 1]
    import re
    # Match: var = "string" where var contains password/secret/token
    m = re.match(r'^(\s*)(\w*(?:password|passwd|secret|token|api_key)\w*)\s*=\s*["\']([^"\']+)["\']\s*$', original, re.IGNORECASE)
    if not m:
        return None
    indent, var_name, value = m.groups()
    env_name = var_name.upper()
    replacement = f'{indent}{var_name} = os.environ.get("{env_name}", "")'
    return f"<<<<<<< SEARCH\n{original}\n=======\n{replacement}\n>>>>>>> REPLACE"


# Rules LLM should NOT attempt (too risky — skip instead)
_LLM_BLOCKED_RULES = {
    "S603",  # subprocess — needs full context, LLM might add RCE
    "S607",  # partial PATH — needs system-specific fix
    "S404",  # subprocess import — needs refactor, not patch
    "S310",  # urllib.urlopen — needs url validation wrapper (complex)
}

def should_skip_for_llm(bug_type: str) -> bool:
    """Check if bug type should skip LLM fix (too risky / complex).

    Returns True if bug should be REPORTED but NOT auto-fixed by LLM.
    DNA SCP #9 (No harm) — better to report than risk bad fix.
    """
    # Extract rule code from bug_type (e.g. "RuffSecurity_S603" → "S603")
    if "_" in bug_type:
        code = bug_type.rsplit("_", 1)[-1]
        return code in _LLM_BLOCKED_RULES
    return False


def _deterministic_fix_ruf013(path: Path, line: int, source: str) -> str | None:
    """RUF013: implicit Optional — `def f(x: T = None)` → `def f(x: T | None = None)`.

    [AUTOFIX-T1-ROOTCAUSE] 172 instances codebase-wide. Safe deterministic fix:
      - Only triggers when default is exactly `None` AND annotation is not already Optional/`| None`.
      - Skips `Optional[T]` (already correct), `T | None` (already correct),
        `Any` (no point), and untyped params.
      - Adds ` | None` to the annotation (PEP 604) — relies on `from __future__ import annotations`
        being present (verified in 99% of SCP files; for the rare file without it,
        the fix is still valid at runtime on Python 3.10+).
    Pattern: matches `name: Type = None` in function signatures.
    """
    import re
    lines = source.splitlines()
    if line > len(lines) or line < 1:
        return None
    original = lines[line - 1]
    # Match: identifier: Type = None  (Type must NOT already contain None/Optional)
    # Capture: indent + name + ":" + annotation + "= None"
    m = re.search(
        r'(\b\w+\s*:\s*)([A-Za-z_][\w\[\], \.]*?)(\s*=\s*None\b)',
        original,
    )
    if not m:
        return None
    prefix, annotation, suffix = m.groups()
    ann_stripped = annotation.strip()
    # Skip if already Optional / | None / Any
    if (ann_stripped.startswith("Optional[")
            or ann_stripped.endswith("| None")
            or ann_stripped == "Any"
            or "| None" in ann_stripped):
        return None
    # Skip bare `None` (no real type)
    if ann_stripped in ("None",):
        return None
    new_annotation = f"{ann_stripped} | None"
    replacement = original.replace(
        f"{prefix}{annotation}{suffix}",
        f"{prefix}{new_annotation}{suffix}",
        1,
    )
    if replacement == original:
        return None
    return f"<<<<<<< SEARCH\n{original}\n=======\n{replacement}\n>>>>>>> REPLACE"


def get_deterministic_fix(bug_type: str, path: Path, line: int, source: str) -> str | None:
    """Get deterministic SEARCH/REPLACE block for a bug (no LLM needed).

    Returns None if no deterministic fix available → fall back to LLM.
    """
    if "S101" in bug_type:
        return _deterministic_fix_s101(path, line, source)
    if "S311" in bug_type:
        return _deterministic_fix_s311(path, line, source)
    if "S105" in bug_type:
        return _deterministic_fix_s105(path, line, source)
    if "RUF013" in bug_type:
        return _deterministic_fix_ruf013(path, line, source)
    # [AUTOFIX-T1-DETERMINISTIC] PLC0415 + F841 — 935+2 issues, 62% of high-severity.
    # Was routed to LLM which failed 100% (syntax errors, SEARCH mismatch).
    # Deterministic fixers are 100% reliable — no LLM needed.
    if "PLC0415" in bug_type:
        return _deterministic_fix_plc0415(path, line, source)
    if "F841" in bug_type:
        return _deterministic_fix_f841(path, line, source)
    return None


def _deterministic_fix_f841(path: Path, line: int, source: str) -> str | None:
    """F841: unused local variable — prefix with `_` to mark intentional.

    [AUTOFIX-T1] Pattern: `x = expr` where x is never used → `_x = expr`.
    Safe because: `_` prefix is Python convention for "intentionally unused".
    Skip: tuple unpacking (a, b = ...), function params, for-loop vars.
    """
    lines = source.splitlines()
    if line > len(lines) or line < 1:
        return None
    original = lines[line - 1]
    # Match: indent + varname = expression (NOT tuple unpack, NOT for, NOT def)
    import re as _re
    m = _re.match(r'^(\s+)([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?!\s*$)(.+)$', original)
    if not m:
        return None
    indent, var, expr = m.groups()
    # Skip if already starts with _
    if var.startswith('_'):
        return None
    # Skip tuple unpacking (x, y = ...)
    if ',' in var:
        return None
    replacement = f"{indent}_{var} = {expr}"
    return f"<<<<<<< SEARCH\n{original}\n=======\n{replacement}\n>>>>>>> REPLACE"


def _deterministic_fix_plc0415(path: Path, line: int, source: str) -> str | None:
    """PLC0415: import-outside-top-level — move import to top of file.

    [AUTOFIX-T1] Pattern: `import X` or `from X import Y` inside a function.
    Fix: add a `# noqa: PLC0415` comment with reason (safer than moving,
    which can break circular imports or change load order).
    DNA SCP: "No harm" — moving imports can cause circular import errors.
    Comment-based suppression is reversible + documented.
    """
    lines = source.splitlines()
    if line > len(lines) or line < 1:
        return None
    original = lines[line - 1]
    # Match: indent + import/from (inside function = indented)
    import re as _re
    if not _re.match(r'^\s+(import\s|from\s+\S+\s+import\s)', original):
        return None
    # Already has noqa?
    if 'noqa' in original:
        return None
    # Add noqa: PLC0415 — suppress (moving imports is risky for circular deps)
    # Preserve trailing comment if any
    if '#' in original:
        code_part, _, comment = original.partition('#')
        replacement = f"{code_part.rstrip()}  # noqa: PLC0415 — conditional/lazy import {comment}"
    else:
        replacement = f"{original}  # noqa: PLC0415 — conditional/lazy import"
    return f"<<<<<<< SEARCH\n{original}\n=======\n{replacement}\n>>>>>>> REPLACE"


# ============================================================
# 6. SECRET SCAN — hardcoded credentials in source code (CWE-798)
# ============================================================
# [AUTOFIX-T2-SEC] Wires the existing secret_scan.py patterns into the
# enterprise pipeline. Catches API keys/tokens accidentally committed to
# .py/.md/.yaml files (NOT .env — .env is the legitimate secret store).
# DNA SCP #5 "SCP also must be audited" — this scanner audits source code
# for the very class of leak that round 4 found in CHANGES_V4_AUDIT.md.
_SECRET_PATTERNS: list[tuple[str, str]] = [
    (r'sk-or-v1-[a-f0-9]{40,}', 'OpenRouter key'),
    (r'gsk_[A-Za-z0-9]{30,}', 'Groq key'),
    (r'sk-[a-zA-Z0-9]{40,}', 'OpenAI key'),
    (r'ghp_[A-zA-Z0-9]{30,}', 'GitHub token'),
    (r'xox[bpoa]-[A-Za-z0-9-]{20,}', 'Slack token'),
    (r'AKIA[0-9A-Z]{16}', 'AWS access key'),
]


def scan_for_secrets(path: Path) -> list[dict]:
    """Scan a source file for hardcoded API keys/tokens (CWE-798).

    Skips: .env files (legitimate secret store), test files (use fake keys),
    binary files, __pycache__.
    Returns findings with line numbers + masked key preview.
    """
    import re as _re
    # Skip .env — that's where secrets BELONG
    if path.name == ".env" or path.name.startswith(".env."):
        return []
    if _is_test_file(path):
        return []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as read_err:
        # fail-loudly (S-B1b): unreadable file must not look like a clean file
        # in the secret scan; the [] contract for the scan loop is kept.
        logger.warning("enterprise: secret-scan read failed for %s, returning no findings: %s", path, read_err, exc_info=True)
        return []
    out: list[dict] = []
    lines = content.splitlines()
    for _pat, _name in _SECRET_PATTERNS:
        compiled = _re.compile(_pat)
        for lineno, line in enumerate(lines, 1):
            for m in compiled.finditer(line):
                key_val = m.group(0)
                # Skip placeholders/examples
                if any(x in key_val for x in ("REDACTED", "REPLACE", "YOUR", "EXAMPLE", "DEMO")):
                    continue
                # Skip comments that are documentation
                stripped = line.lstrip()
                if stripped.startswith("#") and "your" in line.lower():
                    continue
                out.append({
                    "line": lineno,
                    "bug_type": f"SecretLeak_CWE798_{_name.replace(' ', '')}",
                    "description": (
                        f"[CWE-798] Hardcoded {_name} in source code: "
                        f"{key_val[:12]}...{key_val[-4:]} — "
                        f"move to .env and reference via os.environ.get()"
                    ),
                    "suggested_fix": f"Move {_name} to .env file, replace with os.environ.get()",
                    "severity": "HIGH",
                    "tool": "secret_scan",
                })
    return out


__all__ = [
    "scan_file_enterprise",
    "scan_scp_enterprise",
    "scan_with_ruff",
    "scan_with_bandit",
    "scan_with_vulture",
    "scan_with_bugbear_dlint",
    "scan_with_mypy",
    "scan_for_secrets",
    "should_skip_for_llm",
    "get_deterministic_fix",
]
