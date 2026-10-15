"""SCP Code Evolution Agent — bounded self-improvement production path.

P0 hardening:
- LLM generation uses the canonical LLMGateway; no direct OpenRouter transport.
- Gateway Z2/Z3 therefore provides the exact-$0 PEP and free-only routing.
- Candidate source changes pass DriftGuard before any write.
- Tests run on the actually modified source; failure restores the backup.
- AUTO mode remains opt-in and manual mode never auto-commits.
"""
from __future__ import annotations

import ast
import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from scp.core.pending_fix_review import ensure_review_guide
from scp.core.safe_process import safe_run
from scp.governance import DriftDecision, DriftGuard

logger = logging.getLogger("scp.evolution")

SCP_ROOT = Path(__file__).parent.parent.parent
MAX_FIXES_PER_DAY = int(os.environ.get("SCP_EVOLUTION_MAX_DAILY", "10"))
AUTO_MODE = os.environ.get("SCP_EVOLUTION_AUTO", "0") == "1"  # compatibility snapshot


def _auto_mode_enabled() -> bool:
    return os.environ.get("SCP_EVOLUTION_AUTO", "0").strip().lower() in {"1", "true", "yes", "on"}


class CodeEvolutionAgent:
    """Scan -> propose -> guarded patch -> Reality test -> commit/rollback."""

    def __init__(self):
        self.scp_dir = SCP_ROOT / "scp"
        self.tests_dir = SCP_ROOT / "tests"
        self.log_file = SCP_ROOT / "data" / "evolution_log.jsonl"
        self._fixes_today = 0
        self._last_reset = time.time()
        # Kept for diagnostics/backward compatibility only. They are not used
        # as transport credentials/model authority by this agent anymore.
        self._or_key = os.environ.get("OPENROUTER_API_KEY", "")
        self._or_model = os.environ.get("OPENROUTER_MODEL_AUTOFIX", os.environ.get("OPENROUTER_MODEL", "openrouter/free"))
        self._fixes_applied = 0
        self._fixes_rolled_back = 0
        self._fixes_skipped = 0
        self._drift_guard = DriftGuard(SCP_ROOT / "spec" / "protected_invariants.yaml")

    def _get_drift_guard(self):
        # [P0-REGFIX] _drift_guard is initialized in __init__, but the
        # engine composes agents via CodeEvolutionAgent.__new__(...) with
        # minimal attrs (production autofix path) - so the guard must be
        # lazily bound or every fix attempt crashes with AttributeError.
        guard = getattr(self, "_drift_guard", None)
        if guard is None:
            guard = DriftGuard(SCP_ROOT / "spec" / "protected_invariants.yaml")
            self._drift_guard = guard
        return guard

    def _reset_daily_if_needed(self) -> None:
        if time.time() - self._last_reset > 86400:
            self._fixes_today = 0
            self._last_reset = time.time()

    async def run_cycle(self) -> dict:
        self._reset_daily_if_needed()
        if self._fixes_today >= MAX_FIXES_PER_DAY:
            return {"status": "rate_limited", "fixes_today": self._fixes_today}
        result = {
            "started_at": datetime.now().astimezone().isoformat(),
            "bugs_found": 0,
            "fixes_attempted": 0,
            "fixes_applied": 0,
            "fixes_rolled_back": 0,
        }
        bugs = self._scan_bugs()
        result["bugs_found"] = len(bugs)
        if not bugs:
            result["status"] = "no_bugs_found"
            return result
        bug = bugs[0]
        result["fixes_attempted"] = 1
        fix = await self._generate_fix(bug)
        if not fix:
            result["status"] = "fix_generation_failed"
            self._fixes_skipped += 1
            return result

        filepath = SCP_ROOT / bug["file"]
        backup = self._backup_file(filepath)
        actually_patched = self._apply_fix(filepath, fix)
        if not actually_patched:
            self._fixes_skipped += 1
            result["status"] = "fix_queued_for_review"
            result["fixes_skipped"] = 1
            self._log_evolution(
                bug,
                fix,
                {"passed": False, "output": "", "failures": "not patched — queued/rejected for review"},
                applied=False,
            )
            result["ended_at"] = datetime.now().astimezone().isoformat()
            return result

        test_result = self._run_tests()
        if test_result["passed"]:
            if _auto_mode_enabled():
                self._commit_fix(bug, fix, test_result)
                self._fixes_applied += 1
                self._fixes_today += 1
                result["fixes_applied"] = 1
                result["status"] = "fix_applied"
            else:
                self._fixes_applied += 1
                result["status"] = "fix_applied_pending_commit"
                result["note"] = "AUTO_MODE=0 — patch on disk, awaiting manual git commit"
            self._log_evolution(bug, fix, test_result, applied=True)
        else:
            self._restore_backup(filepath, backup)
            self._fixes_rolled_back += 1
            result["fixes_rolled_back"] = 1
            result["status"] = "fix_rolled_back"
            result["test_failures"] = test_result.get("failures", [])
            self._log_evolution(bug, fix, test_result, applied=False)
        result["ended_at"] = datetime.now().astimezone().isoformat()
        return result

    def _scan_bugs(self) -> list[dict]:
        bugs: list[dict] = []
        try:
            from scp.autofix.runner_phases.report import run_full_scan

            scan_summary = run_full_scan(include_ast=True)
            for br in scan_summary.get("bugs", []):
                try:
                    tier = int(getattr(br, "tier", 1) or 1)
                except (TypeError, ValueError) as exc:
                    # silent-by-design: unparseable tier falls back to documented default 1.
                    logger.debug("code_evolution_agent: bug tier unparseable, defaulting to 1: %s", exc, exc_info=True)
                    tier = 1
                if tier < 2:
                    continue
                bugs.append({
                    "file": str(getattr(br, "file", "")),
                    "line": int(getattr(br, "line", 0) or 0),
                    "pattern": str(getattr(br, "bug_type", "unknown")),
                    "severity": "CRITICAL" if tier >= 3 else "HIGH",
                    "why": str(getattr(br, "description", "")),
                    "fix_hint": str(getattr(br, "suggested_fix", "")),
                    "match": "",
                })
        except Exception as exc:
            logger.error("Evolution scan failed (self-evolution disabled): %s", exc, exc_info=True)
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        bugs.sort(key=lambda item: order.get(item["severity"], 9))
        return bugs

    async def _generate_fix(self, bug: dict) -> str | None:
        filepath = SCP_ROOT / bug["file"]
        try:
            original = filepath.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("code_evolution_agent: cannot read bug file %s — fix skipped: %s", filepath, exc, exc_info=True)
            return None
        prompt = f"""Fix this Python bug with the smallest safe change.

BUG:
File: {bug['file']}:{bug['line']}
Pattern: {bug['pattern']}
Problem: {bug['why']}
Suggested fix: {bug['fix_hint']}
Matched code: {bug['match']}

FILE CONTEXT:
{self._get_context(original, bug['line'], description=str(bug.get('description', '')))}

Return ONLY one or more canonical blocks:
<<<<<<< SEARCH
<exact current code>
=======
<replacement code>
>>>>>>> REPLACE

If no safe fix exists, return CANNOT_FIX."""
        try:
            # Canonical gateway owns provider routing + egress + P0 Z2/Z3.
            from scp.llm_gateway import get_gateway

            answer, provider = await get_gateway().chat(
                prompt,
                task="autofix",
                system_prompt=(
                    "You are a bounded Python code fixer. Do not weaken tests, "
                    "security, evidence, rollback, capability, or zero-cost invariants."
                ),
            )
            if not answer:
                logger.info("Evolution fix generation unavailable: %s", provider)
                return None
            if "CANNOT_FIX" in answer:
                return None
            return answer
        except Exception as exc:
            logger.warning("Evolution guarded LLM generation failed: %s", exc, exc_info=True)
            return None

    async def _ask_openrouter(self, prompt: str) -> str | None:
        """Backward-compatible name; now routes through the canonical gateway."""
        try:
            from scp.llm_gateway import get_gateway

            answer, _provider = await get_gateway().chat(
                prompt,
                task="autofix",
                system_prompt="Return only a minimal SEARCH/REPLACE patch or CANNOT_FIX.",
            )
            return answer
        except Exception as exc:
            logger.debug("Guarded fix generation failed: %s", exc, exc_info=True)
            return None

    def _get_context(self, content: str, line: int, radius: int = 50, description: str = "") -> str:
        try:
            from scp.core.context_pruner import prune_source

            pruned = prune_source(content, line or 0, description)
            if pruned.strip():
                return pruned
        except Exception as exc:
            # silent-by-design: context pruning is an optional refinement; the raw
            # line-window fallback below is the documented behavior.
            logger.debug("code_evolution_agent: prune_source failed, using raw window: %s", exc, exc_info=True)
        lines = content.split("\n")
        start = max(0, line - radius)
        end = min(len(lines), line + radius)
        return "\n".join(f"{i+1}: {lines[i]}" for i in range(start, end))

    @staticmethod
    def _backup_file(filepath: Path) -> str:
        return filepath.read_text(encoding="utf-8")

    def _relative_repo_path(self, filepath: Path) -> str:
        try:
            return filepath.resolve().relative_to(SCP_ROOT.resolve()).as_posix()
        except ValueError as exc:
            # silent-by-design: paths outside the repo root are reported verbatim.
            logger.debug("code_evolution_agent: path outside SCP_ROOT, using as_posix: %s", exc, exc_info=True)
            return filepath.as_posix()

    def _drift_allows(self, filepath: Path, original: str, patched: str) -> bool:
        result = self._get_drift_guard().inspect_change(
            path=self._relative_repo_path(filepath),
            old_text=original,
            new_text=patched,
            governance_authorized=False,
        )
        if result.decision is DriftDecision.ALLOW:
            return True
        logger.warning(
            "Evolution patch blocked by DriftGuard: decision=%s path=%s reasons=%s",
            result.decision.value,
            filepath,
            "; ".join(result.reasons),
        )
        return False

    def _write_if_safe(self, filepath: Path, original: str, patched: str) -> bool:
        if patched == original:
            return False
        try:
            ast.parse(patched, filename=str(filepath))
        except SyntaxError as exc:
            logger.warning("Patched %s has syntax error: %s", filepath.name, exc)
            return False
        if not self._drift_allows(filepath, original, patched):
            return False
        filepath.write_text(patched, encoding="utf-8")
        # Postflight checks the exact bytes that landed on disk, not merely the
        # proposed string. Any protected semantic drift remains blocked.
        landed = filepath.read_text(encoding="utf-8")
        post = self._get_drift_guard().inspect_change(
            path=self._relative_repo_path(filepath),
            old_text=original,
            new_text=landed,
            governance_authorized=False,
        )
        if post.decision is not DriftDecision.ALLOW:
            filepath.write_text(original, encoding="utf-8")
            logger.error("DriftGuard postflight rejected landed patch; restored original")
            return False
        return True

    def _apply_fix(self, filepath: Path, fix: str) -> bool:
        original = filepath.read_text(encoding="utf-8")
        search_patterns = (
            re.compile(r"<<<<<<<\s*SEARCH\s*\n(.*?)\n={5,7}\s*\n(.*?)\n>>>>>>>\s*(?:REPLACE)?\s*", re.DOTALL),
            re.compile(r"<<<<<<<\s*OLD\s*\n(.*?)\n={5,7}\s*\n(.*?)\n>>>>>>>\s*(?:NEW)?\s*", re.DOTALL),
        )
        matches = []
        for pattern in search_patterns:
            matches = list(pattern.finditer(fix))
            if matches:
                break
        if matches:
            patched = original
            changed = False
            for match in matches:
                old_text, new_text = match.group(1), match.group(2)
                if old_text in patched:
                    patched = patched.replace(old_text, new_text, 1)
                    changed = True
                else:
                    logger.warning("SEARCH/OLD block not found in %s", filepath.name)
            if changed and self._write_if_safe(filepath, original, patched):
                logger.info("Applied drift-guarded search/replace patch to %s", filepath.name)
                return True

        fenced = re.search(r"```(?:python)?\s*\n(.*?)\n```", fix, re.DOTALL)
        if fenced:
            code_block = fenced.group(1).strip()
            first_line = code_block.split("\n", 1)[0]
            if first_line.startswith(("def ", "class ", "async def ")):
                name_match = re.match(r"(?:async\s+)?(?:def|class)\s+(\w+)", first_line)
                if name_match:
                    def_name = name_match.group(1)
                    existing_pattern = re.compile(
                        rf"((?:async\s+)?(?:def|class)\s+{re.escape(def_name)}\b[^\n]*\n(?:(?:[ \t]+[^\n]*\n)*))",
                        re.MULTILINE,
                    )
                    existing = existing_pattern.search(original)
                    if existing:
                        orig_first = existing.group(1).split("\n", 1)[0]
                        indent = len(orig_first) - len(orig_first.lstrip())
                        indented = "\n".join(
                            (" " * indent + line) if line and not line.startswith(" " * indent) else line
                            for line in code_block.split("\n")
                        )
                        patched = original[: existing.start()] + indented + "\n" + original[existing.end() :]
                        if self._write_if_safe(filepath, original, patched):
                            logger.info("Applied drift-guarded function patch to %s (%s)", filepath.name, def_name)
                            return True

        self._queue_pending_fix(filepath, fix)
        return False

    @staticmethod
    def _queue_pending_fix(filepath: Path, fix: str) -> None:
        import hashlib

        pending_dir = SCP_ROOT / "pending_fixes"
        pending_dir.mkdir(parents=True, exist_ok=True)
        stamp = int(time.time())
        digest = hashlib.sha256(f"{filepath}:{stamp}:{id(fix)}".encode()).hexdigest()[:8]
        pending_file = pending_dir / f"{filepath.stem}_pending_{stamp}_{digest}.py"
        review_content = (
            f"# Pending fix for {filepath.name} — HUMAN review required.\n"
            f"# Suggested fix:\n# " + fix[:2000].replace("\n", "\n# ") + "\n"
        )
        pending_file.write_text(review_content, encoding="utf-8")
        ensure_review_guide(pending_dir)
        logger.info("Fix queued for human review: %s", pending_file)

    @staticmethod
    def _restore_backup(filepath: Path, backup: str) -> None:
        filepath.write_text(backup, encoding="utf-8")

    def _run_tests(self) -> dict:
        try:
            result = safe_run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(self.tests_dir),
                    "-q",
                    "--tb=line",
                    "--deselect",
                    "tests/test_v1041_matrix.py::test_full_matrix_coverage_70",
                    "--deselect",
                    "tests/test_v1042_fast_learning.py::test_compounding_l2",
                ],
                timeout=120,
                cwd=str(SCP_ROOT),
                env={**os.environ, "SCP_DEV_MODE": "1"},
            )
            return {
                "passed": result.returncode == 0,
                "output": result.stdout[-500:] if result.stdout else "",
                "failures": result.stderr[-500:] if result.stderr else "",
            }
        except Exception as exc:
            logger.debug(f"_run_tests ignored: {exc}", exc_info=True)
            return {"passed": False, "output": "", "failures": str(exc)}

    @staticmethod
    def _commit_fix(bug: dict, fix: str, test_result: dict) -> None:
        del fix
        try:
            safe_run(["git", "add", "-A"], cwd=str(SCP_ROOT))
            safe_run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"[AUTO] Fix {bug['pattern']} in {bug['file']}:{bug['line']}\n"
                    f"Bug: {bug['why'][:100]}\n"
                    f"Tests: {'PASS' if test_result['passed'] else 'FAIL'}",
                ],
                cwd=str(SCP_ROOT),
            )
        except Exception as exc:
            logger.warning("git commit unavailable: %s", exc, exc_info=True)

    def _log_evolution(self, bug: dict, fix: str, test_result: dict, applied: bool) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "bug": bug,
            "fix_preview": fix[:200],
            "test_passed": test_result["passed"],
            "applied": applied,
        }
        with open(self.log_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_stats(self) -> dict:
        return {
            "fixes_applied": self._fixes_applied,
            "fixes_rolled_back": self._fixes_rolled_back,
            "fixes_skipped": self._fixes_skipped,
            "fixes_today": self._fixes_today,
            "max_per_day": MAX_FIXES_PER_DAY,
            "auto_mode": _auto_mode_enabled(),
            "llm_transport": "canonical_gateway_egress_guarded",
        }


_evolution_agent: CodeEvolutionAgent | None = None


def get_evolution_agent() -> CodeEvolutionAgent:
    global _evolution_agent
    if _evolution_agent is None:
        _evolution_agent = CodeEvolutionAgent()
    return _evolution_agent


async def start_evolution_loop(interval: int = 3600):
    agent = get_evolution_agent()
    logger.info("Code Evolution Agent started (interval=%ss auto=%s)", interval, _auto_mode_enabled())
    while True:
        try:
            result = await agent.run_cycle()
            if result.get("status") == "fix_applied":
                logger.info("Evolution: fix applied")
            elif result.get("status") == "fix_rolled_back":
                logger.warning("Evolution: fix rolled back (tests failed)")
        except Exception as exc:
            logger.warning("Evolution error: %s", exc, exc_info=True)
        await asyncio.sleep(interval)


def run_evolution_cycle_once() -> dict:
    agent = get_evolution_agent()
    try:
        coro = agent.run_cycle()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as exc:
            # silent-by-design: no running loop is the expected sync-context case.
            logger.debug("code_evolution_agent: no running asyncio loop: %s", exc, exc_info=True)
            loop = None
        if loop is not None:
            import concurrent.futures as futures

            with futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(lambda: asyncio.run(coro)).result()
        return asyncio.run(coro)
    except Exception as exc:
        logger.error("run_evolution_cycle_once failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}
