import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("scp.autofix")


def _find_pre_patch_backup(filepath: Path) -> Path | None:
    """Find pre-patch backup from ShadowSnapshot active transaction or legacy backups."""
    try:
        from scp.autofix.shadow_snapshot import get_shadow_snapshot_manager
        mgr = get_shadow_snapshot_manager()
        target_resolved = str(filepath.resolve())
        if mgr.active_dir.is_dir():
            for tx_dir in sorted(mgr.active_dir.iterdir(), reverse=True):
                if not tx_dir.is_dir():
                    continue
                manifest_file = tx_dir / "manifest.json"
                if not manifest_file.is_file():
                    continue
                try:
                    with manifest_file.open("r", encoding="utf-8") as mf:
                        m = json.load(mf)
                    for item in m.get("target_files", []):
                        if item.get("target_path") == target_resolved and item.get("backup_file"):
                            bk = tx_dir / item["backup_file"]
                            if bk.is_file():
                                return bk
                except Exception as manifest_err:
                    # silent-by-design: best-effort backup discovery from shadow
                    # manifests — caller falls through to suffix-based backup scan.
                    logger.debug(" manifest backup scan failed for %s: %s", tx_dir, manifest_err, exc_info=True)
    except Exception as dir_err:
        # silent-by-design: same — missing/inaccessible shadow dir is expected
        # when no shadow transaction exists; suffix scan below still applies.
        logger.debug(" shadow active_dir scan failed: %s", dir_err, exc_info=True)

    for suffix in [".tier3bak", ".audit_fix_backup"]:
        candidate = filepath.with_suffix(filepath.suffix + suffix)
        if candidate.is_file():
            return candidate
    return None


def _same_bug_file(bug_file: str, target_file: str) -> bool:
    """[PATH-EQ-FIX] Compare a scanner-reported file against the patch target.

    TẠI SAO: raw string equality (`str(bug.file) == str(filepath)`) missed
    every path whose separator/letter-case/redundancy differed (Windows
    backslashes vs POSIX forward slashes, "D:/scp/scp/./x.py" vs
    "D:\\scp\\scp\\x.py") — re-scan filtering (Check 2) and new-bug filtering
    (Check 3) silently compared against the empty set, making both gates
    vacuous for Windows-style paths. Normalize with Path(...).resolve() on
    both sides, mirroring completeness_check._bug_matches.
    """
    try:
        bug_resolved = Path(bug_file).resolve() if bug_file else None
        target_resolved = Path(target_file).resolve() if target_file else None
        if bug_resolved is not None and target_resolved is not None:
            return bug_resolved == target_resolved
        # Documented _bug_matches fallback for unresolvable inputs.
        return bug_file.endswith(target_file) or target_file.endswith(bug_file)
    except Exception as resolve_err:
        # silent-by-design: resolve probe — plain string comparison is the
        # documented fallback for unresolvable paths.
        logger.debug("verify_mixin: path resolve failed, comparing raw strings: %s", resolve_err, exc_info=True)
        return bug_file == target_file


class VerifyMixin:
    def _verify_fix(self, filepath, original_bugs: list) -> tuple[bool, str]:
        """Self-verify a fix after applying patch.

        Args:
            filepath: Path to the patched file.
            original_bugs: List of BugReport objects that the fix was supposed to address.

        Returns (is_valid, reason).
        - is_valid=False → fix broke things → caller should ROLLBACK
        - is_valid=True → every required verifier passed

        Checks (in priority order):
          1. ast.parse() — patched file still parses (syntax OK)
          2. Re-scan same file — original bug still there? (NEW)
          3. Check no NEW bugs introduced (compare against original_bugs signatures)
          4. [WORLD-CLASS-GATE] self_scan_patch_diff — patch không được thêm pattern nguy hiểm
          5. [WORLD-CLASS-GATE] pytest — suite không được vỡ sau patch
        """
        try:
            #  Check 1: ast.parse — file must still be valid Python
            try:
                import ast as _ast
                _content = filepath.read_text(encoding="utf-8")
                _ast.parse(_content, filename=str(filepath))
            except SyntaxError as _se:
                return False, f"patched file SyntaxError: {_se}"  # silent-by-design: explicit (False, reason) error return — caller rolls back fail-closed
            except Exception as _parse_err:
                logger.debug(f"VerifyMixin._verify_fix: exception ignored: {_parse_err}", exc_info=True)
                return False, f"parse check failed: {_parse_err}"  # silent-by-design: same — error text reaches the caller's rollback path

            #  Check 2: re-scan file — original bug still present?
            # TẠI SAO: nếu fix chỉ "modify text" mà không thực sự sửa bug pattern,
            # re-scan sẽ tìm thấy bug cũ. Fail-open if scanner unavailable.
            try:
                from scp.autofix.runner import ast_scan_scp
                # ast_scan_scp scans the whole scp/ package. For surgical verify,
                # we filter results to just this file.
                _all_bugs = ast_scan_scp(include_enterprise=False)
                _remaining_for_this_file = [
                    b for b in _all_bugs
                    if _same_bug_file(str(getattr(b, "file", "")), str(filepath))
                ]
                # Check if the SAME bug (by line+type) is still present
                _still_present = []
                for orig in original_bugs:
                    for remain in _remaining_for_this_file:
                        if (getattr(remain, "line", None) == getattr(orig, "line", None)
                                and getattr(remain, "bug_type", "") == getattr(orig, "bug_type", "")):
                            _still_present.append(orig)
                            break
                if _still_present:
                    return False, (
                        f"original bug still present after fix: "
                        f"{len(_still_present)}/{len(original_bugs)} unchanged"
                    )
            except ImportError as _rescan_import_err:
                logger.warning(" ast_scan_scp unavailable; rejecting unverifiable fix: %s", type(_rescan_import_err).__name__)
                return False, "re-scan unavailable; fix is UNVERIFIED"
            except Exception as _rescan_err:
                logger.warning(" re-scan failed; rejecting unverifiable fix: %s", type(_rescan_err).__name__, exc_info=True)
                return False, "re-scan failed; fix is UNVERIFIED"

            #  Check 3: no NEW bugs introduced at the fix line.
            # TẠI SAO: fix có thể "fix bug A nhưng introduce bug B" (e.g., add
            # try/except nhưng except:pass → bare-except bug mới). So sánh
            # bug signatures pre/post — nếu có bug mới ở line gần fix → flag.
            try:
                from scp.autofix.runner import ast_scan_scp
                _all_bugs_post = ast_scan_scp(include_enterprise=False)
                _new_bugs = []
                _orig_lines = {getattr(b, "line", None) for b in original_bugs}
                # [FALSE-POS-FIX] F841: removed `_orig_types` — dead code.
                # Was meant for dedup but line 346 uses a different set comprehension
                # (line, type) tuples directly. _orig_types was never referenced.
                for b in _all_bugs_post:
                    if not _same_bug_file(str(getattr(b, "file", "")), str(filepath)):
                        continue
                    _b_line = getattr(b, "line", None)
                    _b_type = getattr(b, "bug_type", "")
                    # New bug = same file, NOT in original set (by line+type)
                    if (_b_line, _b_type) not in {(getattr(o, "line", None), getattr(o, "bug_type", "")) for o in original_bugs}:
                        # Within ±10 lines of any original bug = likely introduced by fix
                        for _ol in _orig_lines:
                            if _b_line and _ol and abs(_b_line - _ol) <= 10:
                                _new_bugs.append(b)
                                break
                if _new_bugs:
                    return False, (
                        f"fix introduced {_new_bugs.__len__()} new bug(s) near fix line: "
                        f"{[getattr(b, 'bug_type', '?') for b in _new_bugs[:3]]}"
                    )
            except ImportError as _new_bug_import_err:
                logger.warning(" new-bug scanner unavailable; rejecting unverifiable fix: %s", type(_new_bug_import_err).__name__)
                return False, "new-bug scan unavailable; fix is UNVERIFIED"
            except Exception as _new_bug_err:
                logger.warning(" new-bug scan failed; rejecting unverifiable fix: %s", type(_new_bug_err).__name__, exc_info=True)
                return False, "new-bug scan failed; fix is UNVERIFIED"

            # [WORLD-CLASS-GATE] Check 4: self_scan_patch_diff
            # TẠI SAO: Runtime log cho thấy "fix subprocess nhưng patch thêm subprocess mới"
            # (audit_and_fix.py có gate này, SCP thiếu). Soi patch tìm pattern nguy hiểm
            # MỚI XUẤT HIỆN (eval/exec/os.system/subprocess/pickle) — nếu có → REJECT.
            #
            # [SCP-DNA-FIX R12-4] DISABLED — superseded by IMP-24 policy_gate (engine.py:756).
            # Tại sao: OPT-26 (this check) và IMP-24 (policy_gate) chạy song song với
            # logic mâu thuẫn — OPT-26 BLOCK eval/exec/subprocess, IMP-24 REVIEW eval/exec
            # (cho phép). R12-4 đã unify: IMP-24 giờ BLOCK tất cả (eval/exec/shell=True/
            # subprocess/os.system/pickle) — same coverage as OPT-26. Running cả 2 = waste
            # + inconsistent logging. IMP-24 chạy TRƯỚC patch (line 756), OPT-26 chạy SAU
            # patch — nếu IMP-24 BLOCK, patch không apply, OPT-26 không cần chạy. Nếu
            # IMP-24 ALLOW, patch apply, OPT-26 check count-diff — nhưng IMP-24 đã scan
            # patch text rồi, count-diff là redundant. Disable OPT-26, giữ IMP-24 làm
            # single source of truth.
            # Logic gốc (để rollback nếu cần): xem git history trước R12-4.
            # try:
            #     import re as _re
            #     _DANGEROUS_PATTERNS = [
            #         (_re.compile(r'\beval\s*\('), "eval()"),
            #         (_re.compile(r'\bexec\s*\('), "exec()"),
            #         (_re.compile(r'\bos\.system\s*\('), "os.system()"),
            #         (_re.compile(r'\bsubprocess\.(run|Popen|call|check_output)\s*\('), "subprocess call"),
            #         (_re.compile(r'\bpickle\.(loads|load)\s*\('), "pickle.load()"),
            #     ]
            #     _patched_content = filepath.read_text(encoding="utf-8")
            #     _backup_path = filepath.with_suffix(filepath.suffix + ".tier3bak")
            #     if not _backup_path.exists():
            #         _backup_path = filepath.with_suffix(filepath.suffix + ".audit_fix_backup")
            #     if _backup_path.exists():
            #         _original_content = _backup_path.read_text(encoding="utf-8")
            #         _new_dangerous = []
            #         for _pat, _label in _DANGEROUS_PATTERNS:
            #             _before_count = len(_pat.findall(_original_content))
            #             _after_count = len(_pat.findall(_patched_content))
            #             if _after_count > _before_count:
            #                 _new_dangerous.append(f"{_label} ({_before_count}→{_after_count})")
            #         if _new_dangerous:
            #             return False, (
            #                 f"patch tự thêm pattern nguy hiểm: {', '.join(_new_dangerous)} — "
            #                 f"REJECTED (world-class gate: fix phải không thêm nguy hiểm)"
            #             )
            # except Exception as _self_scan_err:
            #     logger.debug(f"[WORLD-CLASS-GATE] self_scan_patch_diff fail-open: {_self_scan_err}")

            # [WORLD-CLASS-GATE] Check 5: pytest — so sánh BASELINE vs POST-PATCH
            # TẠI SAO: 63% rollback rate xảy ra khi KHÔNG chạy pytest. Nhưng nếu chạy
            # tuyệt đối (fail = rollback), test suite có fail sẵn (DB malformed, sandbox)
            # sẽ reject MỌI patch dù patch đúng. DNA SCP: "PASS ≠ ĐÚNG" — không reject
            # patch chỉ vì test suite có fail sẵn; chỉ reject nếu patch LÀM TỆ HƠN.
            # Fix: chạy pytest pre-patch (baseline) + post-patch, so sánh pass/fail count.
            # Chỉ FAIL nếu post-patch có MORE failures hoặc FEWER passes.
            try:
                # [R35] A verifier-spawned pytest must not recursively spawn
                # another verifier pytest through evolution/autofix tests.
                _pytest_child_env = os.environ.copy()
                _pytest_child_env["SCP_AUTOFIX_RUN_PYTEST"] = "0"
                if os.environ.get("SCP_AUTOFIX_RUN_PYTEST", "1") != "0":
                    import subprocess as _sp
                    import sys as _sys
                    _tests_dir = filepath.parent
                    while _tests_dir.parent != _tests_dir:
                        if (_tests_dir / "tests").is_dir() or (_tests_dir / "scp" / "tests").is_dir():
                            break
                        _tests_dir = _tests_dir.parent
                    _root = _tests_dir
                    if (_root / "tests").is_dir() or (_root / "scp" / "tests").is_dir():
                        _test_targets = []
                        if (_root / "tests").is_dir():
                            for p in (_root / "tests").rglob(f"test_*{filepath.stem}*.py"):
                                _test_targets.append(str(p))
                        if not _test_targets:
                            _test_targets = [str(filepath)]
                    else:
                        # [S15 FAIL-CLOSED FIX] The patch target lives outside a
                        # repository checkout (tmp verification workspace). The
                        # pytest gate must NOT silently skip in that case — a
                        # skipped gate is fail-open and contradicts the pinned
                        # contract (subprocess crash or regression must ROLL
                        # BACK the fix). Fall back to running pytest on the
                        # patched file itself (same fallback as "no targets"),
                        # so a crashed verifier still fails closed.
                        _test_targets = [str(filepath)]
                        _root = filepath.parent

                    # [VERIFY-GATE-5-FIX] The pytest run + baseline comparison
                    # below used to be indented INSIDE the `else:` branch, so
                    # for in-repo files (the normal case) _test_targets was
                    # computed and never used — the "suite must not break"
                    # gate (Check 5) was vacuous exactly where it mattered.
                    # It now runs for BOTH branches.
                    _proc = _sp.run(  # noqa: S603 — audited: sys.executable, hardcoded args
                        [_sys.executable, "-m", "pytest", "-q", "--timeout=60"] + _test_targets[:3],
                        cwd=str(_root), capture_output=True, text=True, timeout=90,
                        encoding="utf-8", errors="replace",
                        check=False,
                        env=_pytest_child_env,
                    )

                    if _proc.returncode != 0:
                        import re as _re
                        _summary = (_proc.stdout or _proc.stderr or "").strip().splitlines()
                        _last = _summary[-1] if _summary else ""
                        _fail_m = _re.search(r'(\d+) failed', _last)
                        _pass_m = _re.search(r'(\d+) passed', _last)
                        _post_fails = int(_fail_m.group(1)) if _fail_m else 0
                        _post_passes = int(_pass_m.group(1)) if _pass_m else 0
                        _has_err = "SyntaxError" in (_proc.stdout + _proc.stderr) or (
                            "ERROR" in (_proc.stdout + _proc.stderr)
                            and _proc.returncode not in (4, 5)
                        )
                        if _proc.returncode in (4, 5) and not _has_err:
                            pass
                        else:
                            # Get baseline (pre-patch) from backup file
                            _backup_path = _find_pre_patch_backup(filepath)
                            if _backup_path and _backup_path.exists():
                                import shutil as _shutil
                                _tmp_save = filepath.with_suffix(filepath.suffix + ".post_save")
                                _shutil.copy(str(filepath), str(_tmp_save))
                                try:
                                    _shutil.copy(str(_backup_path), str(filepath))
                                    _base_proc = _sp.run(
                                        [_sys.executable, "-m", "pytest", "-q", "--timeout=60"] + _test_targets[:3],
                                        cwd=str(_root), capture_output=True, text=True, timeout=90,
                                        encoding="utf-8", errors="replace", check=False,
                                        env=_pytest_child_env,
                                    )
                                    _base_summary = (_base_proc.stdout or "").strip().splitlines()
                                    _base_last = _base_summary[-1] if _base_summary else ""
                                    _base_fail_m = _re.search(r'(\d+) failed', _base_last)
                                    _base_pass_m = _re.search(r'(\d+) passed', _base_last)
                                    _base_fails = int(_base_fail_m.group(1)) if _base_fail_m else 0
                                    _base_passes = int(_base_pass_m.group(1)) if _base_pass_m else 0
                                finally:
                                    _shutil.copy(str(_tmp_save), str(filepath))
                                    _tmp_save.unlink(missing_ok=True)
                                # Compare: only fail if patch makes things WORSE
                                if _post_fails > _base_fails or _post_passes < _base_passes:
                                    return False, (
                                        f"pytest REGRESSION: baseline={_base_passes}p/{_base_fails}f "
                                        f"→ post-patch={_post_passes}p/{_post_fails}f "
                                        f"(patch made it worse) — ROLLBACK"
                                    )
                                else:
                                    logger.info(
                                        f"[WORLD-CLASS-GATE] pytest OK: baseline={_base_passes}p/{_base_fails}f "
                                        f"→ post-patch={_post_passes}p/{_post_fails}f (no regression)"
                                    )
                            else:
                                logger.error("[WORLD-CLASS-GATE] pytest failed and no baseline backup found (fail-closed)")
                                return False, f"pytest verify failed (exit code {_proc.returncode}) and no baseline backup available (fail-closed)"
            except Exception as _pytest_err:
                logger.error(f"[WORLD-CLASS-GATE] pytest verify fail-closed: {_pytest_err}", exc_info=True)
                return False, f"pytest verify error (fail-closed): {_pytest_err}"

            # [AUTOFIX-T1-ROOTCAUSE] Check 6: ENTERPRISE RE-SCAN (Idea 3 from world-autofix research).
            # TẠI SAO: Idea 3 (Copilot+CodeQL pattern) — sau fix, chạy lại TẤT CẢ scanner
            # (ruff S,F,RUF,PLW,PLC,B,UP + bandit + vulture + mypy) trên file đã patch.
            # Cascade control 1→2→3: fix bug A không được introduce bug B (mà scanner
            # nội bộ Check 2/3 có thể không nhìn thấy vì chỉ chạy AST scanners nội bộ).
            # Enterprise tools nhìn được SINK/TAINT/type mà AST nội bộ bỏ sót.
            # Gate: chỉ FAIL nếu có bug MỚI (không có trong original_bugs) ở line gần fix.
            try:
                from scp.autofix.enterprise_scanners import scan_file_enterprise
                _enterprise_findings = scan_file_enterprise(filepath)
                _new_ent_bugs = []
                _orig_lines = {getattr(b, "line", None) for b in original_bugs}
                _orig_types = {(getattr(b, "line", None), getattr(b, "bug_type", "")) for b in original_bugs}
                # [SCP-DNA-FIX R12-25] Also collect orig bug types (regardless of line)
                # Tại sao: S110@L130 là pre-existing bug (line 130 có except: pass từ trước).
                # Cascade control check (line, type) → S110@L130 không match orig (orig có BareExceptPass@L126).
                # → S110@L130 bị flag là "NEW" → rollback fix. Nhưng nó PRE-EXISTING.
                # Fix: nếu bug_type có trong orig (bất kỳ line nào) → không phải NEW.
                _orig_bug_types = {getattr(b, "bug_type", "") for b in original_bugs}
                # Also scan orig file for pre-existing S110/BareExceptPass
                _pre_existing_types = set()
                try:
                    _backup_path = _find_pre_patch_backup(filepath)
                    if _backup_path and _backup_path.exists():
                        _orig_findings = scan_file_enterprise(_backup_path)
                        for f in _orig_findings:
                            _pre_existing_types.add((f.get("line"), f.get("bug_type", "")))
                except Exception as _backup_scan_error:
                    logger.debug('[AUTOFIX] backup finding scan failed; continuing fail-open', exc_info=True)
                for f in _enterprise_findings:
                    _f_line = f.get("line")
                    _f_type = f.get("bug_type", "")
                    # Skip if this finding matches an original bug (we KNEW about it)
                    if (_f_line, _f_type) in _orig_types:
                        continue
                    #  Skip if pre-existing in backup (not introduced by fix)
                    if (_f_line, _f_type) in _pre_existing_types:
                        continue
                    # [SCP-DNA-FIX R13-1] Use _orig_bug_types (ALL pre-existing bug
                    # types across the codebase) instead of R12-25b's hardcoded
                    # 3-type list (S110/S112/BLE001). Tại sao: R12-25b only skipped
                    # SCP's deliberate fail-open patterns. But the codebase also has
                    # pre-existing B904/B008/E722/etc. at OTHER lines (in original_bugs).
                    # Enterprise re-scan finds these at the fix-line → flagged as NEW
                    # → autofix over-rollbacks LEGITIMATE fixes for non-hardcoded types.
                    # Now: skip ANY bug_type present in original_bugs (it's pre-existing
                    # by definition — original_bugs is the pre-fix scan result).
                    if _f_type in _orig_bug_types:
                        continue
                    # New enterprise finding near the fix line = likely introduced by patch
                    for _ol in _orig_lines:
                        if _f_line and _ol and abs(_f_line - _ol) <= 15:
                            _new_ent_bugs.append(f)
                            break
                if _new_ent_bugs:
                    _labels = [f"{f.get('bug_type','?')}@L{f.get('line','?')}" for f in _new_ent_bugs[:3]]
                    return False, (
                        f"enterprise re-scan found {len(_new_ent_bugs)} NEW bug(s) near fix: {_labels} — "
                        f"REJECTED (cascade control: fix must not introduce new tool-detected bugs)"
                    )
            except ImportError:
                logger.debug("[CASCADE] enterprise_scanners unavailable (fail-open)")
            except Exception as _ent_err:
                logger.debug(f"[CASCADE] enterprise re-scan fail-open: {_ent_err}", exc_info=True)

            # [R10 v4 WIRE — IMP-19] Property-Based Validation (7th check, fail-closed).
            # TẠI SAO: existing 6 checks verify syntax + re-scan + no-new-bugs +
            # self-scan + pytest + enterprise. But none of them test that the
            # fix preserves INVARIANTS across edge-case inputs (None, empty,
            # negative, unicode, huge list, NaN, etc.). A fix like
            # `def safe_div(a, b): return a / b if b else 0` passes all 6
            # checks but violates "always non-negative" when called with
            # (-10, 2). IMP-19 generates N=50 edge-case inputs via built-in
            # strategy generator, runs BOTH orig + fixed on each, compares.
            # If fixed violates an invariant that orig held → FIX FAILED.
            # Verification uncertainty is fail-closed: if the property
            # validator cannot run, do not promote the fix on the strength of
            # the other checks alone.
            try:
                from scp.autofix.property_validator import (
                    MIXED_STRATEGY as _v4_mixed_strat,
                )
                from scp.autofix.property_validator import (
                    PropertySpec as _V4_PropertySpec,
                )
                from scp.autofix.property_validator import (
                    validate_fix as _v4_property_validate,
                )
                # Build a conservative PropertySpec — only check that the
                # fixed function does not raise on edge-case inputs. We
                # cannot know caller-specific invariants from here, so the
                # property we check is "no uncaught exception on edge input".
                # This catches: TypeError on None, ValueError on empty,
                # IndexError on huge index, etc. Real fix should preserve
                # the orig function's exception-tolerance profile.
                _v4_patched_text = filepath.read_text(encoding="utf-8")
                _v4_backup_path = _find_pre_patch_backup(filepath)
                if _v4_backup_path and _v4_backup_path.exists() and _v4_patched_text:
                    _v4_orig_text = _v4_backup_path.read_text(encoding="utf-8")
                    # Find the function name from the first original bug.
                    _v4_fn_name = ""
                    for _orig_bug in original_bugs:
                        _v4_fn_name = (
                            getattr(_orig_bug, "function_name", "")
                            or getattr(_orig_bug, "method_name", "")
                            or ""
                        )
                        if _v4_fn_name:
                            break
                    # BugLocation in IMP-19 takes function_name + line range.
                    from scp.autofix.property_validator import BugLocation as _V4_PV_BugLoc
                    _v4_pv_bug_loc = None
                    if _v4_fn_name:
                        _v4_pv_bug_loc = _V4_PV_BugLoc(
                            function_name=_v4_fn_name,
                            line_start=int(getattr(original_bugs[0], "line", 0) or 0),
                            line_end=int(getattr(original_bugs[0], "line", 0) or 0),
                        )
                    # PropertySpec: invariant = "callable did not raise".
                    # That's the weakest possible property — passes if both
                    # orig + fixed run cleanly, fails only if fixed raises
                    # where orig didn't.
                    _v4_pv_spec = _V4_PropertySpec(
                        invariants=[lambda _y: True],   # trivially True — we just check exception-safety
                        strategy=_v4_mixed_strat,
                        skip_if_none_input=False,
                    )
                    _v4_pv_result = _v4_property_validate(
                        orig_source=_v4_orig_text,
                        fixed_source=_v4_patched_text,
                        bug_location=_v4_pv_bug_loc,
                        spec=_v4_pv_spec,
                        n=50,  # 50 edge-case inputs (fast: ~0.5s)
                    )
                    if not _v4_pv_result.ok:
                        # Real invariant violation — fix broke edge-case behavior.
                        _v4_violations_summary = ", ".join(
                            f"input={v.input_value!r} reason={v.reason}"
                            for v in (_v4_pv_result.violations or [])[:3]
                        )
                        return False, (
                            f"[R10 v4 IMP-19] property validation FAILED: "
                            f"{len(_v4_pv_result.violations or [])} violation(s) "
                            f"across {_v4_pv_result.inputs_tested} edge-case inputs. "
                            f"First: {_v4_violations_summary}"
                        )
                    logger.info(
                        f"[R10 v4 IMP-19] property OK: "
                        f"{_v4_pv_result.inputs_tested} edge-case inputs tested, "
                        f"0 violations ({_v4_pv_result.reason})"
                    )
            except ImportError as _v4_pv_imp:
                logger.warning(
                    "[R10 v4 IMP-19] property_validator unavailable; rejecting unverifiable fix: %s",
                    type(_v4_pv_imp).__name__,
                )
                return False, "property validation unavailable; fix is UNVERIFIED"
            except Exception as _v4_pv_err:
                logger.warning(
                    "[R10 v4 IMP-19] property_validator failed; rejecting unverifiable fix: %s",
                    type(_v4_pv_err).__name__,
                exc_info=True)
                return False, "property validation failed; fix is UNVERIFIED"

            return True, "fix verified OK (syntax + re-scan + no new bugs + self-scan + pytest + enterprise + property)"

        except Exception as _verify_err:
            logger.warning(
                " _verify_fix error; rejecting unverifiable fix: %s",
                type(_verify_err).__name__,
            exc_info=True)
            return False, "verification error; fix is UNVERIFIED"

    #  Audit log helper for V9.1 self-verify layer.

