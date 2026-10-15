# [V5.9-SCANNER] APIWiringScanner — detect API keys in .env but unused in code.
#
# TẠI SAO scanner này tồn tại?
#   .env có 8+ *_API_KEY vars (OPENROUTER x3, PUBMED, NCBI, GROQ, EIA, USDA,
#   NVD, CASE_LAW, NASA, GOOGLE_FACT_CHECK). Một số có value (active key),
#   một số trống (chưa register).
#
#   Vấn đề: API_KEY có value nhưng KHÔNG BAO GIỜ được reference trong
#   data_sources/*.py → phí. Hoặc ngược lại: data_source gọi os.environ["X"]
#   nhưng .env không có X → KeyError runtime.
#
#   VÍ DỤ (từ audit):
#     .env: PUBMED_API_KEY=2b49d86d...  (active)
#     medical.py:58: os.environ.get("PUBMED_API_KEY", "")  ✅ wired
#     biology.py:42: os.environ.get("NCBI_API_KEY", "") or "PUBMED_API_KEY"  ✅ wired
#
#     .env: GOOGLE_FACT_CHECK_API_KEY=  (empty)
#     → no data_source references it → gap (but key is empty so low priority)
#
# LOGIC:
#   1. Parse .env → extract all *_API_KEY vars (skip empty values for "gap"
#      reporting but still list them as "not wired")
#   2. Walk scp/data_sources/*.py — find `os.environ.get("X")` / `os.environ["X"]`
#      / `os.getenv("X")` references
#   3. For each .env API_KEY:
#      a. NOT referenced in any data_source → bug "APIWiringGap"
#      b. Referenced but value is empty → bug "APIKeyMissing" (different severity)
#   4. For each data_source reference:
#      a. NOT in .env → bug "APIKeyNotConfigured" (KeyError at runtime)
#
# RETURNS:
#   list[BugReport] — bug_type="APIWiringGap" / "APIKeyMissing" / "APIKeyNotConfigured"
from __future__ import annotations

import logging
import re
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.api_wiring")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_REPO_ROOT = _SCP_ROOT.parent  # .../scp-vietnam/
_ENV_PATH = _REPO_ROOT / ".env"
_DATA_SOURCES_DIR = _SCP_ROOT / "data_sources"

# [SCP-DNA-FIX R15] Fix META-BUG 2: scanner only checked scp/data_sources/*.py
# but API keys are also referenced in llm_gateway/, meta/why_sources/, prediction/,
# security/, core/, capabilities/. Result: 3/4 findings were false positives
# (flagged OPENROUTER, GROQ, NASA as unused — but they're used in other dirs).
# Fix: scan ALL Python directories under scp/, not just data_sources/.
_SCAN_DIRS = [
    _SCP_ROOT / "data_sources",
    _SCP_ROOT / "llm_gateway",
    _SCP_ROOT / "meta" / "why_sources",
    _SCP_ROOT / "prediction",
    _SCP_ROOT / "security",
    _SCP_ROOT / "core",
    _SCP_ROOT / "capabilities",
    _SCP_ROOT / "knowledge",
    _SCP_ROOT / "api",
    _SCP_ROOT / "runtime",
]

# Pattern: VAR_NAME=value (skip comments and empty lines)
# [V5.9-SCANNER] Capture the FULL var name INCLUDING the _API_KEY suffix
# so it matches code references like os.environ.get("OPENROUTER_API_KEY").
# Old regex `([A-Z][A-Z0-9_]*)_API_KEY` captured only "OPENROUTER" — wrong.
_ENV_VAR_PATTERN = re.compile(
    r"^\s*([A-Z][A-Z0-9_]*_API_KEY)\s*=\s*(.*?)\s*$"
)

# Pattern: os.environ.get("X", ...) / os.environ["X"] / os.getenv("X", ...)
# We use regex on source code — simpler than AST for this use case.
_ENV_REF_PATTERN = re.compile(
    r"os\.environ\.get\(\s*['\"]([A-Z][A-Z0-9_]+)['\"]"
    r"|os\.environ\[\s*['\"]([A-Z][A-Z0-9_]+)['\"]"
    r"|os\.getenv\(\s*['\"]([A-Z][A-Z0-9_]+)['\"]"
)


class APIWiringScanner:
    """Detect API keys in .env that are unused, or referenced but not configured."""

    name: str = "APIWiringScanner"

    def __init__(
        self,
        env_path: Path | None = None,
        data_sources_dir: Path | None = None,
    ):
        self.env_path = env_path or _ENV_PATH
        self.data_sources_dir = data_sources_dir or _DATA_SOURCES_DIR
        # [SCP-DNA-FIX R15] Enable multi-directory scanning (META-BUG 2 fix)
        self._use_multi_dir = True

    def _parse_env(self) -> dict[str, str]:
        """Parse .env, return dict of *_API_KEY var → value (value may be empty)."""
        env: dict[str, str] = {}
        if not self.env_path.exists():
            logger.warning(f"[APIWiringScanner] .env not found at {self.env_path}")
            return env
        try:
            for line in self.env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = _ENV_VAR_PATTERN.match(line)
                if m:
                    var_name = m.group(1)
                    # Strip surrounding quotes if any
                    value = m.group(2).strip().strip('"').strip("'")
                    env[var_name] = value
        except Exception as e:
            logger.error(f"[APIWiringScanner] .env parse failed: {e}", exc_info=True)
        return env

    def _scan_data_sources(self) -> dict[str, list[str]]:
        """[SCP-DNA-FIX R15] Walk ALL Python dirs under scp/ — find API_KEY references.

        Was: only scp/data_sources/*.py (META-BUG 2 — missed llm_gateway/, meta/, etc.)
        Now: scans _SCAN_DIRS (10 directories) for os.environ.get/[]/getenv references.

        Returns dict {API_KEY_NAME: [list of file paths that reference it]}.
        """
        refs: dict[str, list[str]] = {}
        # [R15] Scan ALL directories, not just data_sources
        scan_dirs = _SCAN_DIRS if hasattr(self, '_use_multi_dir') else [self.data_sources_dir]
        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
            # Use rglob to find .py files recursively
            for py_file in scan_dir.rglob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                # Skip __pycache__, tests, venv
                if "__pycache__" in str(py_file) or "venv" in str(py_file):
                    continue
                try:
                    source = py_file.read_text(encoding="utf-8", errors="replace")
                except Exception as read_err:  # noqa: S112
                    # silent-by-design: best-effort file read inside scan loop.
                    logger.debug("api_wiring_scanner: skipping unreadable file %s: %s", py_file, read_err, exc_info=True)
                    continue
                for m in _ENV_REF_PATTERN.finditer(source):
                    var_name = m.group(1) or m.group(2) or m.group(3)
                    if var_name:
                        refs.setdefault(var_name, [])
                    if str(py_file) not in refs[var_name]:
                        refs[var_name].append(str(py_file))
        return refs

    def scan(self) -> list[BugReport]:
        """Run the scanner."""
        env_keys = self._parse_env()
        code_refs = self._scan_data_sources()

        bugs: list[BugReport] = []

        # Bug type 1: API key in .env (with value) but NOT referenced anywhere
        for var_name, value in env_keys.items():
            if var_name in code_refs:
                continue  # wired
            if value:
                # Active key but no code uses it → real gap
                bugs.append(BugReport(
                    file=str(self.env_path),
                    line=0,
                    bug_type="APIWiringGap",
                    description=(
                        f"APIWiringGap: {var_name}={value[:8]}... is configured "
                        f"in .env but NOT referenced in any scp/data_sources/*.py. "
                        f"Either remove the key from .env, or wire it into a "
                        f"data_source."
                    ),
                    suggested_fix=(
                        f"Add a method in the appropriate data_source that "
                        f"calls the API: e.g. add `fetch_from_xxx()` using "
                        f"os.environ.get({var_name!r}, ''). Then wire it "
                        f"into the SLM's verify path."
                    ),
                    tier=BugTier.TIER_2_AUTO_FIX_LOG,
                ))
            else:
                # Empty value + no code reference → informational only
                bugs.append(BugReport(
                    file=str(self.env_path),
                    line=0,
                    bug_type="APIKeyMissing",
                    description=(
                        f"APIKeyMissing: {var_name} is in .env but empty "
                        f"AND not referenced in any data_source. "
                        f"Register for the API + wire it in, or remove."
                    ),
                    suggested_fix=(
                        "Register at the API provider, fill in .env, then "
                        "add a fetch_from_xxx() method in the matching "
                        "data_source."
                    ),
                    tier=BugTier.TIER_2_AUTO_FIX_LOG,
                ))

        # Bug type 2: data_source references API_KEY but .env doesn't have it
        for var_name, files in code_refs.items():
            if var_name in env_keys:
                continue  # configured (may be empty — handled above)
            # Reference exists but .env has no such var → KeyError at runtime
            files_str = ", ".join(Path(f).name for f in files[:3])
            bugs.append(BugReport(
                file=files[0] if files else str(self.env_path),
                line=0,
                bug_type="APIKeyNotConfigured",
                description=(
                    f"APIKeyNotConfigured: code references {var_name} "
                    f"(in {files_str}) but .env has no such var. "
                    f"os.environ.get() will return None/empty — silent "
                    f"failure when the data_source tries to call the API."
                ),
                suggested_fix=(
                    f"Either add {var_name}=... to .env (after registering), "
                    f"or remove the dead code path that references it."
                ),
                tier=BugTier.TIER_2_AUTO_FIX_LOG,
            ))

        logger.info(
            f"[APIWiringScanner] found {len(bugs)} wiring gap(s) "
            f"(env_keys={len(env_keys)}, code_refs={len(code_refs)})"
        )
        return bugs
