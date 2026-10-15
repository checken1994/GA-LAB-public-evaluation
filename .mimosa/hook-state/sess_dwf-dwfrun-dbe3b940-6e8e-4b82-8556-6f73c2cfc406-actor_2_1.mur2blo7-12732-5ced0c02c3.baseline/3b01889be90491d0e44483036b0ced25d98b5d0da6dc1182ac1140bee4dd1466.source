"""
[V5.9-SCANNER + V8.0-SCANNER] Full system-wide scan report generation.

TẠI SAO: Gà yêu cầu "quét toàn hệ thống chứ không phải bị giới hạn như này."
AST scanner cũ (BareExceptPass + UndefinedName) chỉ bắt syntax bugs.
V5.9: 5 scanners mới bắt LOGIC/WIRING/ROUTING/SCHEMA bugs.
V8.0: 8 scanners mới bắt TYPE/NULL/RACE/SQL/RESOURCE/PERF/SECURITY/DEAD-CODE bugs.
  - DeadSLMScanner        — SLMs init nhưng không bao giờ được route
  - RoutingGapScanner     — SLM có route nhưng keywords quá hẹp
  - APIWiringScanner      — .env API keys nhưng data_source không wire
  - LogicFlowScanner      — `if confidence == 0.7` exact float (fragile)
  - SchemaMismatchScanner — CREATE TABLE khác shape giữa các file
  - TypeContractScanner   — dict > int, None.attr, str+int, list[str]
  - NullSafetyScanner     — Optional[X] return without None-check
  - RaceConditionScanner  — mutation on shared state without lock
  - SQLInjectionScanner   — f-string/concat/%-format SQL execution
  - ResourceLeakScanner   — open/socket/connect without `with`/`.close()`
  - PerformanceScanner    — O(n²) nested loops, list.index in loop, etc.
  - SecurityScanner       — CWE Top 25 (cmd injection, deserialization, etc.)
  - DeadCodeScanner       — functions/classes never referenced
  [OPT-18] XSS scanner:
  - XSSScanner            — CWE-79 reflected/stored XSS (Markup, HTMLResponse,
                            f-string HTML + request.args, etc.)
Tất cả OPT-IN qua `--full-scan` hoặc individual `--scan-*` flags.
Không phá flow cũ (BareExceptPass/UndefinedName vẫn default).

Extracted from `autofix/runner.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import logging

from scp.autofix.classifier import BugReport
from scp.autofix.engine import get_autofix_engine
from scp.autofix.runner_phases.ast_scan import ast_scan_scp

logger = logging.getLogger("scp.autofix.runner")


def run_full_scan(include_ast: bool = True, max_bugs: int = 0) -> dict:
    """[V5.9+V8.0+OPT-18-SCANNER+R5-3] Run ALL 18 scanners + (optionally) AST scan.

    Returns a summary dict with:
      - per-scanner bug counts
      - total bugs found
      - list of all BugReports (in `bugs` key)
      - if include_ast=True, also runs ast_scan_scp() and merges results

    [SCP-DNA-FIX R5-3] Previously claimed "14 scanners" but actually ran 14 of
    18 — 4 scanner modules existed but were never registered. Now all 18 run.
    """
    from scp.autofix.scanners import (
        APIWiringScanner,
        CrossFuncTaintScanner,
        DeadCodeScanner,
        DeadSLMScanner,
        HypothesisScanner,  #  wire IMP-5
        LogicFlowScanner,
        NullSafetyScanner,
        PerformanceScanner,
        RaceConditionScanner,
        ResourceLeakScanner,
        RoutingGapScanner,
        ScannerSelfAudit,  #  wire IMP-10
        SchemaMismatchScanner,
        SecurityScanner,
        SemanticIntentScanner,
        SQLInjectionScanner,
        StaticMethodSelfScanner,
        TaintFlowScanner,
        TypeContractScanner,
        XSSScanner,
    )

    all_bugs: list[BugReport] = []
    per_scanner: dict[str, int] = {}

    scanners = [
        # V5.9 scanners
        ("DeadSLMScanner", DeadSLMScanner()),
        ("RoutingGapScanner", RoutingGapScanner()),
        ("APIWiringScanner", APIWiringScanner()),
        ("LogicFlowScanner", LogicFlowScanner()),
        ("SchemaMismatchScanner", SchemaMismatchScanner()),
        # V8.0 scanners
        ("TypeContractScanner", TypeContractScanner()),
        ("NullSafetyScanner", NullSafetyScanner()),
        ("RaceConditionScanner", RaceConditionScanner()),
        ("SQLInjectionScanner", SQLInjectionScanner()),
        ("ResourceLeakScanner", ResourceLeakScanner()),
        ("PerformanceScanner", PerformanceScanner()),
        ("SecurityScanner", SecurityScanner()),
        ("DeadCodeScanner", DeadCodeScanner()),
        # OPT-18 scanner
        ("XSSScanner", XSSScanner()),
        # [SCP-DNA-FIX R5-3] 4 previously-unregistered scanners
        ("CrossFuncTaintScanner", CrossFuncTaintScanner()),
        ("TaintFlowScanner", TaintFlowScanner()),
        ("SemanticIntentScanner", SemanticIntentScanner()),
        ("StaticMethodSelfScanner", StaticMethodSelfScanner()),
        # [SCP-DNA-FIX R12-7] Wire 2 dead scanners (IMP-5 + IMP-10)
        # Tại sao: wiring-scan report found HypothesisScanner + ScannerSelfAudit
        # imported + __all__'d but NEVER instantiated in run_full_scan(). R11 claim
        # "12/12 wired" but these 2 were dead re-exports. DNA #22 (PASS ≠ TRUE).
        ("HypothesisScanner", HypothesisScanner()),
        ("ScannerSelfAudit", ScannerSelfAudit()),
    ]
    for name, scanner in scanners:
        try:
            found = scanner.scan()
            per_scanner[name] = len(found)
            all_bugs.extend(found)
        except Exception as e:
            logger.error(f"[V8.0-SCANNER] {name} failed: {e}", exc_info=True)
            per_scanner[name] = -1  # signal error

    if include_ast:
        ast_bugs = ast_scan_scp()
        per_scanner["ASTScanner"] = len(ast_bugs)
        all_bugs.extend(ast_bugs)

    # [SCP-DNA-FIX R15] Validate findings BEFORE returning — filter false positives.
    # TẠI SAO: R13 audit showed ~92% false-positive rate in SCP's own scanners.
    # Scanners are PATTERN MATCHERS, not EVIDENCE VALIDATORS. This validation
    # layer (DNA #4 Evidence-First) filters:
    #   - Comment markers (nosec / noqa / SCP-DNA-FIX / intentional markers)
    #   - Test files (non-test bugs in test files)
    #   - String literal context (patterns inside strings)
    #   - Historical feedback (previously dismissed findings)
    # And calibrates confidence based on bug-type FP rates.
    try:
        from scp.autofix.bug_report_validator import validate_findings
        pre_count = len(all_bugs)
        all_bugs = validate_findings(all_bugs)
        post_count = len(all_bugs)
        per_scanner["_R15_Validator"] = f"{pre_count}→{post_count} (filtered {pre_count - post_count} FP)"
        logger.info(
            f"[R15-Validator] {pre_count} findings → {post_count} valid "
            f"({pre_count - post_count} false positives filtered)"
        )
    except Exception as e:
        logger.warning(f"[R15-Validator] validation failed (fail-open, raw findings used): {e}", exc_info=True)

    if max_bugs > 0 and len(all_bugs) > max_bugs:
        logger.info(
            f"[V8.0-SCANNER] capping at {max_bugs} bugs (had {len(all_bugs)})"
        )
        all_bugs = all_bugs[:max_bugs]

    summary = {
        "source": "full_scan",
        "scanners": per_scanner,
        "total_bugs": len(all_bugs),
        "bugs": all_bugs,
    }
    logger.info(
        f"[V8.0-SCANNER] full scan complete: {summary['total_bugs']} bug(s) — "
        f"{per_scanner}"
    )
    return summary


def run_single_scanner(scanner_name: str) -> list[BugReport]:
    """[V5.9+V8.0-SCANNER] Run a single named scanner. Returns its BugReports.

    Used by individual --scan-* CLI flags.
    """
    name = scanner_name.lower()
    # V5.9 scanners
    if name in ("dead_slm", "dead-slm", "deadslm"):
        from scp.autofix.scanners import DeadSLMScanner
        return DeadSLMScanner().scan()
    if name in ("routing", "routing_gap", "routing-gap"):
        from scp.autofix.scanners import RoutingGapScanner
        return RoutingGapScanner().scan()
    if name in ("api_wiring", "api-wiring", "apiwiring"):
        from scp.autofix.scanners import APIWiringScanner
        return APIWiringScanner().scan()
    if name in ("logic", "logic_flow", "logic-flow"):
        from scp.autofix.scanners import LogicFlowScanner
        return LogicFlowScanner().scan()
    if name in ("schema", "schema_mismatch"):
        from scp.autofix.scanners import SchemaMismatchScanner
        return SchemaMismatchScanner().scan()
    # V8.0 scanners
    if name in ("type", "type_contract", "type-contract", "typecontract"):
        from scp.autofix.scanners import TypeContractScanner
        return TypeContractScanner().scan()
    if name in ("null", "null_safety", "null-safety", "nullsafety"):
        from scp.autofix.scanners import NullSafetyScanner
        return NullSafetyScanner().scan()
    if name in ("race", "race_condition", "race-condition", "racecondition"):
        from scp.autofix.scanners import RaceConditionScanner
        return RaceConditionScanner().scan()
    if name in ("sql", "sql_injection", "sql-injection", "sqlinjection"):
        from scp.autofix.scanners import SQLInjectionScanner
        return SQLInjectionScanner().scan()
    if name in ("resource", "resource_leak", "resource-leak", "resourceleak"):
        from scp.autofix.scanners import ResourceLeakScanner
        return ResourceLeakScanner().scan()
    if name in ("perf", "performance"):
        from scp.autofix.scanners import PerformanceScanner
        return PerformanceScanner().scan()
    if name in ("security",):
        from scp.autofix.scanners import SecurityScanner
        return SecurityScanner().scan()
    if name in ("dead_code", "dead-code", "deadcode"):
        from scp.autofix.scanners import DeadCodeScanner
        return DeadCodeScanner().scan()
    # OPT-18 scanner
    if name in ("xss", "xss_vulnerability", "xss-vulnerability", "xssvulnerability"):
        from scp.autofix.scanners import XSSScanner
        return XSSScanner().scan()
    #  2 previously-dead scanners — now wireable individually
    if name in ("hypothesis", "hypothesis_scanner", "hypothesis-scanner"):
        from scp.autofix.scanners import HypothesisScanner
        return HypothesisScanner().scan()
    if name in ("self_audit", "self-audit", "selfaudit", "scanner_self_audit"):
        from scp.autofix.scanners import ScannerSelfAudit
        return ScannerSelfAudit().scan()
    raise ValueError(f"unknown scanner: {scanner_name}")


def run_full_scan_and_fix(max_bugs: int = 0) -> dict:
    """[V5.9-SCANNER] Run full scan AND feed bugs into AutoFixEngine.

    Like run_once(ast_scan=True) but uses the full-scan bug list.
    Respects all safety guards (Tier 1-4, classifier, rate limit, cooldown).
    """
    scan_summary = run_full_scan(include_ast=True, max_bugs=max_bugs)
    bugs: list[BugReport] = scan_summary["bugs"]
    engine = get_autofix_engine()

    summary = {
        "processed": 0, "fixed": 0, "permission_requested": 0,
        "skipped": 0, "denied": 0, "details": [], "engine_stats": {},
        "source": "full_scan_and_fix",
        "scanners": scan_summary["scanners"],
        "total_bugs_found": scan_summary["total_bugs"],
    }

    from scp.autofix.llm_fix import process_bug_with_llm
    for bug in bugs:
        try:
            result = process_bug_with_llm(bug, engine)
        except Exception as e:
            logger.error(
                f"[runner] process_bug_with_llm failed for "
                f"{bug.file}:{bug.line}: {e}", exc_info=True
            )
            result = {"action": "skipped", "tier": 0,
                      "reason": f"runner error: {e}"}

        summary["processed"] += 1
        action = result.get("action", "skipped")
        if action == "fixed":
            summary["fixed"] += 1
        elif action == "permission_requested":
            summary["permission_requested"] += 1
        elif action == "denied":
            summary["denied"] += 1
        else:
            summary["skipped"] += 1

        summary["details"].append({
            "file": bug.file, "line": bug.line,
            "bug_type": bug.bug_type, "result": result,
        })

    summary["engine_stats"] = engine.stats()
    return summary
