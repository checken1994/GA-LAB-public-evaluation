"""
[SCP-DNA-FIX R7-12] Post-Fix Verification Phase — NEW autofix pipeline phase.

TẠI SAO file này tồn tại?
  R5/R6 fix xong NGỪNG. Không verify fix thực sự wire (R6-3 wrapper existed but
  was never called — R7 phát hiện). DNA #26: Reality có quyền cuối cùng — phải
  chạy Reality test SAU fix, không chỉ trước.

  This phase runs AFTER a Tier-2 fix is applied:
    1. Run vulture on WHOLE scp/ directory (cross-file) → assert flagged dead
       method GONE from dead list. If still dead → fix didn't wire → rollback.
    2. Run hypothesis property test (if test exists for the fixed module) →
       assert no TypeError/AttributeError on random inputs.
    3. Import the modified module + call key function with safe input →
       if ImportError/TypeError → rollback + escalate to Tier-3.

  Inspired by: Sentry Autofix (runs test suite after patch, reverts if regression).

Flow:
  Tier-2 fix applied → post_fix_verify.run(bug, patched_file) → {ok: bool, reason: str}
    ok=True → keep fix, log to audit trail
    ok=False → rollback fix (revert file to .tier3bak), escalate to Tier-3

DNA principles applied:
  #26 (Reality > Model) — verify with REAL runtime, not just static analysis
  #9 (No harm) — if verify fails, rollback (non-fatal)
  #7 (Autofix safe) — guard #7: cross-file vulture verify before Tier-2 keeps
  #22 (PASS ≠ TRUE) — fix "applied" ≠ fix "working"
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.autofix.post_fix_verify")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_VERIFY_TIME_S = 30  # don't let verification hang


def _run_vulture_cross_file(method_name: str) -> bool:
    """Run vulture on whole scp/ → check if method_name still flagged as dead.

    Returns True if method is GONE from dead list (fix wired it).
    Returns False if method is STILL dead (fix didn't wire).
    """
    try:
        win_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        result = subprocess.run(
            [sys.executable, "-m", "vulture", str(_SCP_ROOT),
             "--min-confidence", "60"],
            capture_output=True, text=True, timeout=_MAX_VERIFY_TIME_S,
            creationflags=win_flags,
        )
        # If method_name appears in vulture output → still dead
        return method_name not in result.stdout
    except Exception as e:
        logger.warning(" vulture cross-file unavailable; verification is UNVERIFIED: %s", type(e).__name__, exc_info=True)
        return False


def _try_import_module(file_path: str) -> tuple[bool, str]:
    """Import the modified module → catch ImportError/TypeError.

    Returns (ok, message).
    """
    try:
        # Convert file path to module path: scp/runtime/judge.py → scp.runtime.judge
        try:
            rel = Path(file_path).relative_to(_SCP_ROOT.parent)
        except ValueError:
            # [S15 FIX] The patched file lives OUTSIDE the repository tree
            # (tmp verification workspace, as used by the T09 golden task).
            # The import check must still prove the patched module compiles
            # and executes at import time — verify it through its file
            # location under a private, throwaway module name instead of
            # failing the whole base phase with a path arithmetic ValueError.
            return _import_module_by_location(Path(file_path))
        if rel.suffix != ".py":
            return True, "not a .py file, skip import check"
        module_path = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
        if module_path.endswith(".__init__"):
            module_path = module_path[:-9]
        # Try import (force reimport if already loaded)
        if module_path in sys.modules:
            importlib.reload(sys.modules[module_path])
        else:
            importlib.import_module(module_path)
        return True, "import OK"
    except ImportError as e:
        return False, f"ImportError: {e}"
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    except Exception as e:
        # A module-level exception means the patched module was not verified.
        logger.warning(" import check failed; verification is UNVERIFIED: %s", type(e).__name__, exc_info=True)
        return False, f"module import failed: {type(e).__name__}"


def _import_module_by_location(path: Path) -> tuple[bool, str]:
    """Compile+exec a standalone patched module via its file location.

    Used for verification targets outside the repository tree. The module is
    loaded under a private throwaway name and removed afterwards, so repo
    modules and sys.modules state stay untouched. Any load/execution error
    propagates to the caller's fail-closed reporting.
    """
    if path.suffix != ".py":
        return True, "not a .py file, skip import check"
    import uuid as _uuid

    module_name = f"_scp_autofix_verify_{_uuid.uuid4().hex[:12]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return False, f"module import failed: no importable spec for {path.name}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    return True, "import OK (standalone verification target)"


def _try_hypothesis_test(file_path: str) -> tuple[bool, str]:
    """Run hypothesis property test for the fixed module (if test exists).

    Tests live in tests/property/test_<module>.py.
    Returns (ok, message).
    """
    try:
        rel = Path(file_path).relative_to(_SCP_ROOT.parent)
        stem = rel.stem  # e.g. "conversionslm"
        test_file = _SCP_ROOT.parent / "tests" / "property" / f"test_{stem}.py"
        if not test_file.exists():
            return False, f"UNVERIFIED: no property test at {test_file}"
        win_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-x", "--tb=short", "-q"],
            capture_output=True, text=True, timeout=_MAX_VERIFY_TIME_S,
            creationflags=win_flags,
        )
        if result.returncode == 0:
            return True, "hypothesis tests pass"
        return False, f"hypothesis tests failed: {result.stdout[-500:]}"
    except Exception as e:
        logger.warning(" hypothesis test unavailable; verification is UNVERIFIED: %s", type(e).__name__, exc_info=True)
        return False, f"UNVERIFIED: hypothesis test unavailable ({type(e).__name__})"


def run_post_fix_verify(
    bug_id: str,
    file_path: str,
    method_name: str | None = None,
    run_vulture: bool = True,
    run_import: bool = True,
    run_hypothesis: bool = True,
) -> dict:
    """Run post-fix verification on a patched file.

    Args:
        bug_id: Bug identifier (e.g. "R7-1")
        file_path: Path to the patched file
        method_name: If fix wired a dead method, check it's GONE from vulture
        run_vulture: Run cross-file vulture check
        run_import: Run module import check
        run_hypothesis: Run hypothesis property test (if exists)

    Returns:
        {
            "ok": bool,          — True if all checks pass
            "checks": {...},     — per-check results
            "reason": str,       — human-readable summary
            "rollback": bool,    — True if fix should be rolled back
        }
    """
    checks = {}
    all_ok = True

    # Check 1: cross-file vulture (if method_name provided)
    if run_vulture and method_name:
        vulture_ok = _run_vulture_cross_file(method_name)
        checks["vulture"] = {
            "ok": vulture_ok,
            "message": f"method '{method_name}' {'GONE' if vulture_ok else 'STILL DEAD'} from vulture dead list"
        }
        if not vulture_ok:
            all_ok = False

    # Check 2: module import
    if run_import:
        import_ok, import_msg = _try_import_module(file_path)
        checks["import"] = {"ok": import_ok, "message": import_msg}
        if not import_ok:
            all_ok = False

    # Check 3: hypothesis property test
    if run_hypothesis:
        hyp_ok, hyp_msg = _try_hypothesis_test(file_path)
        checks["hypothesis"] = {"ok": hyp_ok, "message": hyp_msg}
        if not hyp_ok:
            all_ok = False

    reason = f" post_fix_verify for {bug_id}: {'ALL PASS' if all_ok else 'FAILED'}"
    logger.info(reason)

    return {
        "ok": all_ok,
        "checks": checks,
        "reason": reason,
        "rollback": not all_ok,  # rollback if any check failed
    }


def rollback_fix(file_path: str, backup_path: str | None = None) -> bool:
    """Rollback a fix by restoring from backup file.

    Args:
        file_path: Path to the patched file (to revert)
        backup_path: Path to backup (if None, look for .tier3bak then
            .audit_fix_backup)

    Returns True if rollback succeeded.

    [SCP-DNA-FIX R13-4] Consolidated canonical rollback-by-backup implementation.
    TẠI SAO: R7-Full added a duplicate `rollback_fix` in `reality_test.py:328`
    with slightly better logic (tries BOTH .tier3bak AND .audit_fix_backup
    fallback, has traceback logging). DeadCodeScanner R13-4 flagged both as
    dead duplicates — engine uses `rollback_fix_by_token` (token-based registry
    lookup) and bypasses both. Fix (Option A — delete dead duplicates):
    - Removed the duplicate from reality_test.py
    - Merged the better logic (multi-extension fallback + traceback) HERE so
      this canonical impl (re-exported as `rollback_fix_post` in
      `runner_phases/__init__.py`) is the single source of truth.
    - Library function for external callers / operators who want to revert
      by file path instead of token.
    """
    try:
        import shutil
        import traceback as _tb
        target = Path(file_path)
        candidates: list[Path] = []
        if backup_path:
            candidates.append(Path(backup_path))
        candidates.append(target.with_suffix(target.suffix + ".tier3bak"))
        candidates.append(target.with_suffix(target.suffix + ".audit_fix_backup"))
        for backup in candidates:
            if backup.exists():
                shutil.copy2(backup, target)
                logger.info(f" Rolled back {file_path} from {backup}")
                return True
        logger.warning(f" No backup found for {file_path}")
        return False
    except Exception as e:
        logger.error(f" Rollback failed: {e}\n{_tb.format_exc()}", exc_info=True)
        return False


# ============================================================
# [IMP-1 enhancement] Full post-fix verification orchestration.
#
# TẠI SAO: R7-Full strengthens IMP-1 to ORCHESTRATE the new reality_test
# (IMP-2) and completeness_check (IMP-3) phases. Instead of 3 separate
# entrypoints, this single function runs ALL 3 verifications in order
# (cheapest first — vulture/import → reality_test exercise → completeness
# re-scan) and aggregates results. If any phase fails, the fix is rolled
# back + escalated to Tier-3.
# ============================================================

def run_full_post_fix_verify(
    bug_id: str,
    file_path: str,
    method_name: str | None = None,
    bug_type: str | None = None,
    run_vulture: bool = True,
    run_import: bool = True,
    run_hypothesis: bool = True,
    run_reality_exercise: bool = True,
    run_completeness: bool = True,
    run_evidence_replay: bool = True,
    buggy_source: str | None = None,
) -> dict:
    """Run ALL post-fix verification phases in order (cheapest first).

    This is the canonical entry point for [IMP-1] post-fix verification.
    It orchestrates:
      1. vulture cross-file (if method_name given)
      2. module import check
      3. hypothesis property test (if test exists)
      4. [IMP-2] reality_test — exercise callables with smoke inputs
      5. [IMP-3] completeness_check — re-run original scanner, verify bug gone
      6. [R12-9 BSG-VA] evidence_replay — replay test on B/S/G code states,
         classify evidence role (gold-aligned / regression-only / misleading /
         candidate-specific / diagnostic-negative).

    Args:
        bug_id: Bug identifier (e.g. "R7-1" or audit log id).
        file_path: Path to patched file.
        method_name: If fix wired a dead method, check it's GONE from vulture.
        bug_type: If provided, run completeness check (re-scan for this type).
        run_vulture / run_import / run_hypothesis: enable/disable base checks.
        run_reality_exercise: enable IMP-2 reality test (callable exercise).
        run_completeness: enable IMP-3 completeness re-scan.
        run_evidence_replay: enable R12-9 BSG-VA evidence replay (B/S/G test).
        buggy_source: Optional pre-fix content of the patched file. For a
            seeded gold entry (first-time bug signature) this gives the B-leg
            of the replay the REAL buggy state, so the generated
            characterization test must genuinely fail on it (FA-04 repair).

    Returns:
        {
            "ok": bool,                — True only if ALL enabled phases pass
            "phases": {...},           — per-phase results
            "rollback": bool,          — True if any phase failed (or evidence_replay flagged)
            "escalate_to_tier3": bool, — True if fix should be re-reviewed
            "reason": str,
        }
    """
    phases: dict[str, Any] = {}
    all_ok = True
    # Explicit flags for evidence_replay (decoupled from all_ok so we can
    # escalate/rollback even when other phases pass).
    _bsgva_escalate = False
    _bsgva_rollback = False
    # Missing or failed oracle evidence is explicitly unverified and blocks
    # promotion; the caller decides whether to rollback or escalate.
    _bsgva_unverified = False

    # Phase A: base post-fix verify (vulture + import + hypothesis)
    base_result = run_post_fix_verify(
        bug_id=bug_id,
        file_path=file_path,
        method_name=method_name,
        run_vulture=run_vulture,
        run_import=run_import,
        run_hypothesis=run_hypothesis,
    )
    phases["base"] = base_result
    if not base_result.get("ok", False):
        all_ok = False

    # Phase B: [IMP-2] reality_test — exercise callables
    if run_reality_exercise:
        try:
            from scp.autofix.runner_phases.reality_test import run_reality_test
            reality_result = run_reality_test(
                bug_id=bug_id,
                file_path=file_path,
                exercise_callables=True,
            )
            phases["reality_test"] = reality_result
            if not reality_result.get("ok", False):
                all_ok = False
        except ImportError as e:
            logger.warning("[IMP-1] reality_test unavailable; verification is UNVERIFIED: %s", type(e).__name__)
            phases["reality_test"] = {"ok": False, "status": "UNVERIFIED", "reason": "reality_test unavailable"}
            all_ok = False
        except Exception as e:  # noqa: BLE001
            logger.warning("[IMP-1] reality_test failed; verification is UNVERIFIED: %s", type(e).__name__)
            phases["reality_test"] = {"ok": False, "status": "UNVERIFIED", "reason": "reality_test failed"}
            all_ok = False

    # Phase C: [IMP-3] completeness_check — re-scan for bug_type
    if run_completeness and bug_type:
        try:
            from scp.autofix.runner_phases.completeness_check import run_completeness_check
            comp_result = run_completeness_check(
                bug_id=bug_id,
                file_path=file_path,
                bug_type=bug_type,
            )
            phases["completeness_check"] = comp_result
            if not comp_result.get("complete", True):
                # Incomplete ≠ rollback-worthy by itself, but DOES escalate.
                # Reason: fix may have partially addressed the bug (good progress)
                # but missed some sites. Tier-3 review decides.
                all_ok = False
        except ImportError as e:
            logger.warning("[IMP-1] completeness_check unavailable; verification is UNVERIFIED: %s", type(e).__name__)
            phases["completeness_check"] = {
                "ok": False, "complete": False, "status": "UNVERIFIED", "reason": "completeness_check unavailable",
            }
            all_ok = False
        except Exception as e:  # noqa: BLE001
            logger.warning("[IMP-1] completeness_check failed; verification is UNVERIFIED: %s", type(e).__name__)
            phases["completeness_check"] = {
                "ok": False, "complete": False, "status": "UNVERIFIED", "reason": "completeness_check failed",
            }
            all_ok = False

    # Phase D: [R12-9 BSG-VA] Evidence Replay — classify test PASS as
    # gold-aligned / regression-only / misleading / candidate-specific /
    # diagnostic-negative, by replaying test_command on Buggy (B) / candidate
    # State (S) / Gold (G) code states. Per BSG-VA paper (arXiv 2607.28871).
    #
    # TẠI SAO: phases A-C trả lời "fix có chạy được không?" nhưng KHÔNG trả lời
    # "test PASS có thực sự chứng minh bug được fix không?". DNA #22
    # (PASS ≠ TRUE): agent có thể "fix" bằng cách làm test vô nghĩa. BSG-VA
    # replay test trên 3 code states (B/S/G) để phân loại evidence.
    #
    # Wire logic:
    #   - Look up gold fix in GoldDataset by bug_signature (sha256 of
    #     bug_type:description). Use bug_id as description proxy.
    #   - If gold entry found → run EvidenceReplay.classify_evidence with
    #     buggy/gold/test_command from gold entry + candidate_source read from
    #     the actual patched file_path.
    #   - role=MISLEADING or REGRESSION_ONLY → escalate_to_tier3 = True
    #     (test evidence is fake or non-discriminative).
    #   - role=DIAGNOSTIC_NEGATIVE → rollback = True (candidate didn't work).
    #   - Missing oracle evidence remains UNVERIFIED and blocks promotion.
    if run_evidence_replay and bug_type:
        try:
            import tempfile as _bsgva_tmpfile

            from scp.autofix import evidence_replay as _bsgva_module
            _BSGVA_Replay = _bsgva_module.EvidenceReplay
            _BSGVA_Role = _bsgva_module.EvidenceRole
            _BSGVA_Dataset = _bsgva_module.GoldDataset
            _bsgva_sig = _bsgva_module.compute_bug_signature

            _bsgva_bug_sig = _bsgva_sig(bug_type, bug_id or "")
            _bsgva_ds = _BSGVA_Dataset()
            _bsgva_entry = _bsgva_ds.get_entry(_bsgva_bug_sig)
            if _bsgva_entry is not None:
                # Read candidate source from actual patched file.
                _bsgva_target = Path(file_path)
                _bsgva_candidate_src = ""
                if _bsgva_target.exists():
                    _bsgva_candidate_src = _bsgva_target.read_text(
                        encoding="utf-8", errors="replace"
                    )
                # Use a temp dir + module.py for replay.
                # [SCP-DNA-FIX R12-15] module-stem substitution — thay "module"
                # trong test_command bằng file stem thật (ví dụ "llm_fix" nếu
                # patch file là scp/autofix/llm_fix.py). Tại sao: Gold dataset
                # test_command dùng `from module import X` (placeholder). Nếu
                # apply nguyên → ImportError → classify DIAGNOSTIC_NEGATIVE →
                # rollback MỌI patch (safe nhưng noisy = sai). Fix: substitute
                # "module" → file stem, ghi vào <stem>.py thay module.py.
                _bsgva_file_stem = Path(file_path).stem if file_path else "module"
                _bsgva_raw_cmd = _bsgva_entry.get("test_command", "")
                if isinstance(_bsgva_raw_cmd, str):
                    _bsgva_test_cmd: str | list[str] = _bsgva_raw_cmd.replace(
                        "module", _bsgva_file_stem
                    )
                else:
                    # argv-list command (seed entries use
                    # [sys.executable, "-m", "pytest"]) — no substitution needed.
                    _bsgva_test_cmd = [str(a) for a in _bsgva_raw_cmd]
                # [FA-04 repair] A seeded entry (first-time bug signature)
                # carries no test. The seed policy must synthesize a REAL
                # discriminating characterization test from observed behavior
                # (evidence_replay.prepare_seed_replay); running bare pytest
                # in the replay workspace collects 0 tests and fails every
                # seeded fix. Fail-closed: no behavior change → UNVERIFIED;
                # candidate regression → rollback.
                _bsgva_seeded = bool(_bsgva_entry.get("seeded"))
                # For seeded entries the caller-provided pre-fix content (the
                # REAL buggy state) feeds the B-leg; dataset entries keep
                # their recorded buggy_source as authoritative.
                _bsgva_seed_buggy_src = _bsgva_entry.get("buggy_source", "")
                if _bsgva_seeded and buggy_source:
                    _bsgva_seed_buggy_src = buggy_source
                with _bsgva_tmpfile.TemporaryDirectory(
                    prefix="bsgva_replay_"
                ) as _bsgva_tmp:
                    _bsgva_seed_reject: dict[str, Any] | None = None
                    _bsgva_seed_rollback = False
                    if _bsgva_seeded:
                        _bsgva_seed_plan = _bsgva_module.prepare_seed_replay(
                            buggy_source=_bsgva_seed_buggy_src,
                            candidate_source=_bsgva_candidate_src,
                            module_stem=_bsgva_file_stem,
                            isolate_cwd=Path(_bsgva_tmp),
                        )
                        if _bsgva_seed_plan.get("ok"):
                            (Path(_bsgva_tmp) / "test_replay_generated.py").write_text(
                                _bsgva_seed_plan["test_source"], encoding="utf-8"
                            )
                        else:
                            _bsgva_seed_reject = _bsgva_seed_plan
                            _bsgva_seed_rollback = bool(_bsgva_seed_plan.get("rollback"))
                    if _bsgva_seed_reject is None:
                        # Write buggy/candidate/gold to <stem>.py (not module.py)
                        _bsgva_replay = _BSGVA_Replay(working_dir=_bsgva_tmp)
                        _bsgva_result = _bsgva_replay.classify_evidence(
                            test_command=_bsgva_test_cmd,
                            buggy_source=_bsgva_seed_buggy_src,
                            candidate_source=_bsgva_candidate_src,
                            gold_source=_bsgva_entry.get("gold_source", ""),
                            file_path=str(Path(_bsgva_tmp) / f"{_bsgva_file_stem}.py"),
                        )
                    else:
                        _bsgva_result = None
                if _bsgva_result is not None:
                    # MISLEADING (passes B+S, fails G) and REGRESSION_ONLY
                    # (passes B+S+G) prove the test evidence does NOT
                    # discriminate the fix — that evidence must never promote
                    # a patch (DNA #22), so they are fail-closed like
                    # DIAGNOSTIC_NEGATIVE, while still escalating to Tier-3.
                    _bsgva_ok = _bsgva_result.role not in (
                        _BSGVA_Role.DIAGNOSTIC_NEGATIVE,
                        _BSGVA_Role.MISLEADING,
                        _BSGVA_Role.REGRESSION_ONLY,
                    )
                    phases["evidence_replay"] = {
                        "ok": _bsgva_ok,
                        "role": _bsgva_result.role.value,
                        "discriminating": _bsgva_result.discriminating,
                        "result": _bsgva_result.to_dict(),
                        "reason": str(_bsgva_result),
                    }
                    if _bsgva_result.role in (
                        _BSGVA_Role.MISLEADING,
                        _BSGVA_Role.REGRESSION_ONLY,
                    ):
                        all_ok = False
                        _bsgva_escalate = True
                        logger.warning(
                            f"[R12-9 BSG-VA] evidence_replay for {bug_id}: "
                            f"role={_bsgva_result.role.value} — test evidence is "
                            f"{'FAKE (passes B+S but fails G)' if _bsgva_result.role == _BSGVA_Role.MISLEADING else 'NON-DISCRIMINATIVE (passes B+S+G)'} "
                            f"— escalating to Tier-3 review"
                        )
                    elif _bsgva_result.role == _BSGVA_Role.DIAGNOSTIC_NEGATIVE:
                        all_ok = False
                        _bsgva_rollback = True
                        logger.error(
                            f"[R12-9 BSG-VA] evidence_replay for {bug_id}: "
                            f"role=DIAGNOSTIC_NEGATIVE — candidate fix failed test "
                            f"on replay (b_pass={_bsgva_result.b_result[0]}, "
                            f"s_pass={_bsgva_result.s_result[0]}, "
                            f"g_pass={_bsgva_result.g_result[0]}) — rolling back"
                        )
                    else:
                        logger.info(
                            f"[R12-9 BSG-VA] evidence_replay for {bug_id}: "
                            f"role={_bsgva_result.role.value} "
                            f"discriminating={_bsgva_result.discriminating}"
                        )
                else:
                    _bsgva_seed_reason = str(_bsgva_seed_reject.get("reason", ""))
                    if _bsgva_seed_rollback:
                        all_ok = False
                        _bsgva_rollback = True
                        phases["evidence_replay"] = {
                            "ok": False,
                            "role": _BSGVA_Role.DIAGNOSTIC_NEGATIVE.value,
                            "discriminating": True,
                            "reason": _bsgva_seed_reason,
                        }
                        logger.error(
                            f"[R12-9 BSG-VA] evidence_replay for {bug_id}: "
                            f"seed replay rejected the candidate — rolling back: "
                            f"{_bsgva_seed_reason}"
                        )
                    else:
                        _bsgva_unverified = True
                        _bsgva_escalate = True
                        phases["evidence_replay"] = {
                            "ok": False,
                            "status": "UNVERIFIED",
                            "reason": _bsgva_seed_reason,
                        }
                        logger.warning(
                            f"[R12-9 BSG-VA] evidence_replay for {bug_id}: "
                            f"seed replay UNVERIFIED — escalating: {_bsgva_seed_reason}"
                        )
            else:
                _bsgva_unverified = True
                _bsgva_escalate = True
                phases["evidence_replay"] = {
                    "ok": False,
                    "status": "UNVERIFIED",
                    "skipped": True,
                    "reason": (
                        f"no gold entry for bug_signature="
                        f"{_bsgva_bug_sig[:16]}... (bug_type={bug_type})"
                    ),
                }
        except ImportError as _bsgva_imp:
            logger.debug(
                f"[R12-9 BSG-VA] evidence_replay unavailable (fail-open): {_bsgva_imp}"
            )
            _bsgva_unverified = True
            _bsgva_escalate = True
            phases["evidence_replay"] = {
                "ok": False,
                "status": "UNVERIFIED",
                "skipped": True,
                "reason": f"import skipped: {_bsgva_imp}",
            }
        except Exception as _bsgva_err:  # noqa: BLE001 — fail-open per DNA #7
            logger.warning(
                f"[R12-9 BSG-VA] evidence_replay error (fail-open): {_bsgva_err}"
            )
            _bsgva_unverified = True
            _bsgva_escalate = True
            phases["evidence_replay"] = {
                "ok": False,
                "status": "UNVERIFIED",
                "skipped": True,
                "reason": f"error: {_bsgva_err}",
            }

    # Phase E: [R10 v3 WIRE — IMP-15] Semantic Equivalence Verification.
    # TẠI SAO: reality_test (Phase B) exercises callables with smoke inputs.
    # completeness_check (Phase C) re-runs the scanner to verify the bug is
    # gone. But NEITHER checks that the fix didn't change behavior OUTSIDE
    # the bug_location — e.g. LLM "fixes" a None-comparison bug but also
    # refactors the return type of an unrelated branch. IMP-15 dumps AST of
    # the target function BEFORE (from .tier3bak backup) vs AFTER (current
    # file), compares. If statements OUTSIDE bug_location differ → over_broad
    # → flag for review. If target function is GONE from fixed_ast → CRITICAL.
    # [IMP-15 FIX] The oracle itself is now REAL (AST compare in
    # semantic_equiv.verify_semantic_equiv) — it was an unconditional ok=True
    # stub, and the BugLocation call below raised TypeError that got swallowed
    # into "semantic equivalence failed" → spurious rollback. No backup →
    # SKIPPED_NOT_IMPLEMENTED, excluded from all_ok (never counted as pass).
    try:
        from scp.autofix.runner_phases import semantic_equiv as _v3_se_module
        _V3_SE_BugLoc = _v3_se_module.BugLocation
        _v3_se_verify = _v3_se_module.verify_semantic_equiv
        # Read pre-fix source.
        # [XSNAP-PHASEE 2026-09-26] The engine no longer writes
        # .tier3bak/.audit_fix_backup files (zero in-tree backups —
        # ShadowSnapshot transactions now). Phase E therefore SKIPPED on
        # every modern run — a fail-open skip of the over_broad/critical
        # oracle. Discovery now mirrors verify_mixin._find_pre_patch_backup:
        # active ShadowSnapshot manifest first, legacy suffix backups next,
        # then the buggy_source parameter the engine already passes
        # (ctx.pre_fix_content).
        _v3_se_target = Path(file_path)
        _v3_se_orig_src: str | None = None
        _v3_se_backup = None
        try:
            from scp.autofix.engine_parts.verify_mixin import (
                _find_pre_patch_backup as _v3_se_find_backup,
            )
            _v3_se_backup = _v3_se_find_backup(_v3_se_target)
        except Exception as _v3_se_bk_err:  # noqa: BLE001 — discovery is best-effort
            logger.debug(
                "[R10 v3 IMP-15] pre-fix backup discovery failed: %s",
                _v3_se_bk_err, exc_info=True,
            )
        if _v3_se_backup is not None and _v3_se_backup.exists():
            _v3_se_orig_src = _v3_se_backup.read_text(encoding="utf-8", errors="replace")
        elif buggy_source:
            _v3_se_orig_src = buggy_source
        if _v3_se_orig_src is not None and _v3_se_target.exists():
            _v3_se_fixed_src = _v3_se_target.read_text(encoding="utf-8", errors="replace")
            # Build BugLocation from method_name (if provided).
            # [IMP-15 FIX] The old call `_V3_SE_BugLoc(function_name=...)`
            # raised TypeError (file_path/line are required fields) which the
            # phase's except Exception swallowed into "semantic equivalence
            # failed" → spurious rollback whenever backup + method_name
            # existed. Pass the full signature; line is unknown here (bug
            # line is not a parameter of this orchestrator), so 0 is honest.
            _v3_se_bug_loc = None
            if method_name:
                _v3_se_bug_loc = _V3_SE_BugLoc(
                    file_path=str(file_path),
                    function_name=method_name,
                    line=0,
                )
            _v3_se_result = _v3_se_verify(
                original_source=_v3_se_orig_src,
                fixed_source=_v3_se_fixed_src,
                bug_location=_v3_se_bug_loc,
            )
            phases["semantic_equiv"] = {
                "ok": _v3_se_result.ok,
                "equivalent": _v3_se_result.equivalent,
                "over_broad": _v3_se_result.over_broad,
                "critical": _v3_se_result.critical,
                "changed_statements": list(_v3_se_result.changed_statements[:10]),
                "reason": _v3_se_result.reason,
            }
            # CRITICAL (function deleted) → rollback immediately.
            if _v3_se_result.critical:
                all_ok = False
                logger.error(
                    f"[R10 v3 IMP-15] CRITICAL: target function '{method_name}' "
                    f"DELETED by fix — rolling back (callers will break)"
                )
            # over_broad (changes outside bug_location) → escalate to Tier 3.
            elif _v3_se_result.over_broad:
                all_ok = False
                logger.warning(
                    f"[R10 v3 IMP-15] over_broad fix detected for {bug_id}: "
                    f"{len(_v3_se_result.changed_statements)} statement(s) changed "
                    f"outside bug_location — escalating to Tier 3 review"
                )
            else:
                logger.info(
                    f"[R10 v3 IMP-15] semantic_equiv OK: "
                    f"equivalent={_v3_se_result.equivalent} "
                    f"reason={_v3_se_result.reason[:80]}"
                )
        else:
            # [SKIP-NOT-PASS FIX] No pre-fix source available (no shadow
            # snapshot, no legacy backup, no buggy_source) → semantic
            # equivalence cannot run. The old branch recorded ok=True
            # "SKIPPED" — a skipped phase counted as a pass (manufactured
            # green, DNA #22). It is now labeled SKIPPED_NOT_IMPLEMENTED with
            # ok=False and EXCLUDED from all_ok: it neither blocks the overall
            # verdict nor masquerades as a pass. (ok=False does NOT trip the
            # rollback scan below — that requires `not p.get("complete",
            # True)`, which skips lack.)
            phases["semantic_equiv"] = {
                "ok": False, "status": "SKIPPED_NOT_IMPLEMENTED", "skipped": True,
                "reason": "no pre-fix source (no shadow snapshot, legacy backup, or buggy_source) "
                          "— semantic equivalence SKIPPED_NOT_IMPLEMENTED "
                          "(excluded from all_ok; a skipped phase is never counted as pass)",
            }
    except ImportError as _v3_se_imp:
        logger.warning(
            "[R10 v3 IMP-15] semantic_equiv unavailable; verification is UNVERIFIED: %s",
            type(_v3_se_imp).__name__,
        )
        phases["semantic_equiv"] = {
            "ok": False, "status": "UNVERIFIED", "skipped": True,
            "reason": "semantic equivalence unavailable",
        }
        all_ok = False
    except Exception as _v3_se_err:
        logger.warning(
            "[R10 v3 IMP-15] semantic_equiv failed; verification is UNVERIFIED: %s",
            type(_v3_se_err).__name__,
        exc_info=True)
        phases["semantic_equiv"] = {
            "ok": False, "status": "UNVERIFIED", "skipped": True,
            "reason": "semantic equivalence failed",
        }
        all_ok = False

    overall_ok = all_ok and not _bsgva_unverified
    escalate = (not all_ok) or _bsgva_escalate or _bsgva_unverified
    reason = (
        f"[IMP-1] run_full_post_fix_verify for {bug_id}: "
        f"{'ALL PASS' if overall_ok else 'FAILED/UNVERIFIED'} "
        f"(phases: {', '.join(phases.keys())})"
    )
    logger.info(reason)

    return {
        "ok": overall_ok,
        "phases": phases,
        "rollback": _bsgva_rollback or (not all_ok and any(
            not p.get("ok", True) and not p.get("complete", True)
            for p in phases.values()
            if "ok" in p or "complete" in p
        )),
        "escalate_to_tier3": escalate,
        "reason": reason,
    }


__all__ = ["run_post_fix_verify", "rollback_fix", "run_full_post_fix_verify"]
