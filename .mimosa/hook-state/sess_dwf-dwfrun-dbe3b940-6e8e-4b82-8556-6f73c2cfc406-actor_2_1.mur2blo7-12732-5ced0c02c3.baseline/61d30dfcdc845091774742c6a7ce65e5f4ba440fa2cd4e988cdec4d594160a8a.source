"""Runner phases package — extracted from `autofix/runner.py` in Task 10-B.

Sub-modules:
  - ast_scan: AST scanner classes + helpers (BareExceptPass, UndefinedName)
  - permission_check: V9.1 ImpactPrioritization layer
  - report: V5.9 + V8.0 full-scan + individual scanners + fix-and-report
  - pre_startup: STARTUP-GATE pre-startup audit + scheduled audit
  - post_fix_verify: [R7-Full IMP-1] post-fix verification (vulture + hypothesis
    + reality_test + completeness_check orchestration)
  - reality_test: [R7-Full IMP-2] import + exercise patched module
  - completeness_check: [R7-Full IMP-3] re-scan for same bug class after fix
  - lineage_cross_validation: [R7-Full IMP-7] require ≥2 distinct lineages
  - diff_rescan: [R7-Full IMP-12] only re-scan changed files (mtime + hash)

All public symbols are re-exported here so `from scp.autofix.runner_phases
import ast_scan_scp` works directly.
"""
from scp.autofix.runner_phases.ast_scan import (
    _MAX_BUGS_PER_SCAN,
    _MAX_SCAN_FILES,
    _SCP_ROOT,
    DEEP_AUDIT_RESULTS_FILE,
    _BareExceptPassFinder,
    _build_bug_report,
    _iter_python_files,
    _ModuleNameCollector,
    _scan_file,
    _UndefinedNameFinder,
    _write_deep_audit_result,
    ast_scan_scp,
)
from scp.autofix.runner_phases.completeness_check import (
    reopen_as_incomplete,
    run_completeness_check,
)
from scp.autofix.runner_phases.diff_rescan import (
    DiffRescanCache,
    compute_changed_files,
    get_diff_rescan_cache,
    update_cache_after_scan,
)
from scp.autofix.runner_phases.lineage_cross_validation import (
    collect_lineages,
    validate_bug_lineage,
)
from scp.autofix.runner_phases.permission_check import _prioritize_bugs
from scp.autofix.runner_phases.post_fix_verify import (
    rollback_fix as rollback_fix_post,
)

# [R7-Full] New phases — re-exported for convenience.
from scp.autofix.runner_phases.post_fix_verify import (
    run_full_post_fix_verify,
    run_post_fix_verify,
)
from scp.autofix.runner_phases.pre_startup import (
    pre_startup_audit,
    run_scheduled,
)
from scp.autofix.runner_phases.report import (
    run_full_scan,
    run_full_scan_and_fix,
    run_single_scanner,
)

__all__ = [
    # ast_scan
    "ast_scan_scp",
    "DEEP_AUDIT_RESULTS_FILE",
    "_MAX_SCAN_FILES",
    "_MAX_BUGS_PER_SCAN",
    "_SCP_ROOT",
    "_BareExceptPassFinder",
    "_ModuleNameCollector",
    "_UndefinedNameFinder",
    "_iter_python_files",
    "_scan_file",
    "_build_bug_report",
    "_write_deep_audit_result",
    # permission_check
    "_prioritize_bugs",
    # report
    "run_full_scan",
    "run_single_scanner",
    "run_full_scan_and_fix",
    # pre_startup
    "pre_startup_audit",
    "run_scheduled",
    # [R7-Full] new phases
    "run_post_fix_verify",
    "run_full_post_fix_verify",
    "rollback_fix_post",

    "run_completeness_check",
    "reopen_as_incomplete",
    "validate_bug_lineage",
    "collect_lineages",
    "DiffRescanCache",
    "compute_changed_files",
    "get_diff_rescan_cache",
    "update_cache_after_scan",
]
