/**
 * Autofix Engine v3 — 6 NEW improvements (IMP-13..IMP-18)
 *
 * "cập nhật autofix để autofix mạnh + chính xác + nhanh hơn, giống autofix của
 *  hệ thống tốt nhất khác của thế giới"
 *
 * R7-Full upgraded the engine to v2 (IMP-1..12). R8 upgrades to v3 with 6 more
 * improvements, each inspired by a world-class autofix system. All 6 are REAL
 * Python (not stubs), fail-open, backward-compatible, matching house style.
 *
 * Two axes of improvement:
 *   - ACCURACY: IMP-14 (confidence ranking) + IMP-15 (semantic equiv) — directly
 *     attacks the R5/R6 "22% false-positive fix rate" at the decision layer.
 *   - SPEED: IMP-13 (incremental cache) + IMP-18 (parallel fan-out) — targets
 *     the "45s → 3s" rescan claim by making it real at file + scanner level.
 *   - SAFETY: IMP-16 (blast radius) + IMP-17 (auto-rollback) — a fix that
 *     breaks callers now rolls back automatically (Sentry canary pattern).
 *
 * Source: scp/autofix/V3_MANIFEST.md + scp/autofix/V3_CHANGELOG.md
 */

export type V3Axis = "accuracy" | "speed" | "safety"

export interface AutofixV3Improvement {
  id: string
  name: string
  inspiration: string
  axis: V3Axis
  problem: string
  solution: string
  file: string
  loc: number
  failOpen: string
  astParseOk: boolean
  smokeTested: boolean
}

export const AUTOFIX_V3_IMPROVEMENTS: AutofixV3Improvement[] = [
  {
    id: "IMP-13",
    name: "Incremental AST-Diff Cache",
    inspiration: "ruff --diff cache + pytest --testmon",
    axis: "speed",
    problem:
      "R7-Full's IMP-12 (diff-aware rescan) claimed '45s → 3s' but was never benchmarked. Without a file-level content-hash + AST-hash cache, every re-scan re-parses every file — even unchanged ones. The 45s baseline is real; the 3s target was a hope.",
    solution:
      "ASTDiffCache stores {file: {content_sha, ast_sha, last_scan_ts, findings_count}} in data/ast_diff_cache.json. On re-scan, skip files whose content-hash + AST-hash unchanged since last scan. Thread-safe (RLock), atomic writes (.tmp + os.replace), fail-open (corrupt cache → rebuild). Singleton via get_ast_diff_cache().",
    file: "scp/autofix/ast_diff_cache.py (NEW)",
    loc: 412,
    failOpen:
      "Corrupt cache JSON → log + rebuild from scratch. Missing data/ dir → create. Cache miss → full scan (degrades to v2 behavior).",
    astParseOk: true,
    smokeTested: true,
  },
  {
    id: "IMP-14",
    name: "Confidence-Scored Fix Ranking",
    inspiration: "GitHub Copilot Autofix confidence scores + Sentry Autofix validation",
    axis: "accuracy",
    problem:
      "R5/R6 had ~22% false-positive fix rate — fixes that 'claimed done' but the bug persisted. The engine applied ALL fixes equally: deterministic rule fixes (high trust) alongside LLM-generated fixes (lower trust) alongside relaxation patches (should NEVER auto-apply). No decision layer separated 'definitely safe' from 'needs human'.",
    solution:
      "ProposedFix dataclass + score_fix() weighted sum: 0.30 ast_parse + 0.25 reality_test + 0.15 blast_radius + 0.15 bug_fp_inverse + 0.15 source. Hard caps: ast.parse FAIL → 0.20 (discard); relaxation patch → 0.49 (DNA #4 — force human review). rank_fixes() sorts desc, drops <0.50, returns auto_apply (≥0.85) / human_review (0.50-0.84) / discard (<0.50) buckets.",
    file: "scp/autofix/confidence_ranker.py (NEW)",
    loc: 402,
    failOpen:
      "Scoring error → default 0.50 (human review). Missing input field → neutral 0.5 weight. Pure function — no side effects.",
    astParseOk: true,
    smokeTested: true,
  },
  {
    id: "IMP-15",
    name: "Semantic Equivalence Verification",
    inspiration: "DeepCode/CodeQL semantic analysis + ast.dump comparison",
    axis: "accuracy",
    problem:
      "A 'fix' that changes behavior outside the bug location is a regression. R7-Full's IMP-2 (reality_test) exercises the function with smoke inputs, but doesn't verify the fix ONLY changed what it should. An over-broad fix (e.g., rewriting a whole function to fix one line) passes reality_test but may introduce subtle behavior changes.",
    solution:
      "verify_semantic_equiv(original_ast, fixed_ast, bug_location) uses ast.dump to compare function bodies before/after. Detects: CRITICAL (function deleted), over_broad (AST changed outside bug_location span), in_scope (change confined to bug lines). Returns SemanticEquivResult with diff summary. Combines with IMP-2 reality_test for full post-fix verification.",
    file: "scp/autofix/runner_phases/semantic_equiv.py (NEW)",
    loc: 397,
    failOpen:
      "Can't parse original or fixed → skip check + log warning (don't block the fix). ast.dump too large → truncate comparison. Backward-compat: standalone module.",
    astParseOk: true,
    smokeTested: true,
  },
  {
    id: "IMP-16",
    name: "Fix Blast-Radius Analysis",
    inspiration: "CodeQL data-flow + GitHub code review 'files changed' view",
    axis: "safety",
    problem:
      "A fix to a leaf function (0 callers) is low-risk. A fix to judge.py::ingestion_decision (many callers) is high-risk and should escalate tier. R7-Full had no blast-radius concept — every fix was applied at the tier the classifier assigned, regardless of how many callers depended on the patched function.",
    solution:
      "compute_blast_radius(target_file, target_function, scp_root) walks the scp_root AST, finds all callers via _CallSiteCollector (Name + Attribute calls). Returns BlastRadiusResult with caller_count, caller_files, test_coverage_count, risk_level (LOW/MEDIUM/HIGH/CRITICAL). Bounded walk (5000 nodes/file, 400 files, 200 callers) for performance. Engine can escalate tier based on risk_level.",
    file: "scp/autofix/runner_phases/blast_radius.py (NEW)",
    loc: 372,
    failOpen:
      "Can't build call graph → risk_level=MEDIUM (conservative) + log. Walk exceeds bound → cap + log. Backward-compat: standalone.",
    astParseOk: true,
    smokeTested: true,
  },
  {
    id: "IMP-17",
    name: "Auto-Rollback on Regression",
    inspiration: "Sentry canary deploys + git bisect + K8s liveness probes",
    axis: "safety",
    problem:
      "R7-Full's IMP-6 (RollbackTokenRegistry) provided rollback CAPABILITY but not rollback TRIGGERING. A fix that passes post-fix verify (IMP-1/2/3) but then causes a hypothesis property test (IMP-5) to fail 30s later had no automatic rollback — it sat broken until an operator noticed.",
    solution:
      "RegressionWatcher class with daemon thread (default 15s interval) that re-runs reality_test on patched files within TTL (60s). On FAIL → auto-rollback via IMP-6 RollbackTokenRegistry. Pluggable reality_test_fn + rollback_fn. Env var SCP_REGRESSION_WATCHER_DISABLED=1 → _NoOpWatcher (fail-open). Writes JSONL audit log to data/regression_watch.jsonl (DNA #8).",
    file: "scp/autofix/runner_phases/auto_rollback.py (NEW)",
    loc: 575,
    failOpen:
      "Watcher thread crash → recover next loop + log. Rollback itself fails → log loudly (DNA #11) + leave fix in place (don't make it worse). Daemon thread → won't block shutdown.",
    astParseOk: true,
    smokeTested: true,
  },
  {
    id: "IMP-18",
    name: "Parallel Scanner Fan-Out with Result Dedup",
    inspiration: "semgrep --parallel + ruff --parallel + mypy daemon",
    axis: "speed",
    problem:
      "R7-Full's IMP-11 (concurrent fix worker pool) parallelized FIXES, not SCANS. Scanners still ran sequentially: 21 scanners × N files = 21×N serial AST walks. On a 365-file codebase, a full scan took ~45s. The 'parallel' in the v2 name only applied to the fix-application phase.",
    solution:
      "run_scanners_parallel(scanners, files, max_workers) fans out scanners across files using ProcessPoolExecutor (processes — scanners are CPU-bound AST work). Falls back to ThreadPoolExecutor → sequential if unavailable. dedup_findings() merges overlapping findings (same file:line:bug_class) by keeping highest-severity + merging evidence + tracking other_scanners list. Default max_workers = min(cpu_count, 8). Integrates with IMP-13 (skip unchanged files).",
    file: "scp/autofix/parallel_scanner.py (NEW)",
    loc: 428,
    failOpen:
      "One scanner crash → log + continue (don't fail whole batch). ProcessPoolExecutor unavailable → ThreadPoolExecutor. ThreadPool unavailable → sequential. Deterministic dedup (sort before merge for reproducibility).",
    astParseOk: true,
    smokeTested: true,
  },
]

export const V3_STATS = {
  total: AUTOFIX_V3_IMPROVEMENTS.length,
  totalLoc: AUTOFIX_V3_IMPROVEMENTS.reduce((s, i) => s + i.loc, 0),
  byAxis: {
    accuracy: AUTOFIX_V3_IMPROVEMENTS.filter((i) => i.axis === "accuracy").length,
    speed: AUTOFIX_V3_IMPROVEMENTS.filter((i) => i.axis === "speed").length,
    safety: AUTOFIX_V3_IMPROVEMENTS.filter((i) => i.axis === "safety").length,
  },
  allAstParseOk: AUTOFIX_V3_IMPROVEMENTS.every((i) => i.astParseOk),
  allSmokeTested: AUTOFIX_V3_IMPROVEMENTS.every((i) => i.smokeTested),
  v2FilesUnchanged: true, // 0 v2 files modified — light-touch integration
  totalAutofixPyFiles: 57, // 51 v2 + 6 v3
}

/**
 * World's-best autofix systems — what SCP's v3 engine learns from.
 * Each entry: the system, what it does best, and which SCP improvement adopts the pattern.
 */
export interface WorldTool {
  name: string
  vendor: string
  specialty: string
  scpAdoption: string
  relatedImp: string[]
}

export const WORLD_TOOLS: WorldTool[] = [
  {
    name: "Sentry Autofix",
    vendor: "Sentry",
    specialty:
      "Production-error-driven fixes. When an error spikes in prod, Autofix generates a patch, runs the test suite, and reverts if metrics regress. The gold standard for 'fix → verify → revert-if-broken'.",
    scpAdoption:
      "IMP-1 (post-fix verify), IMP-3 (completeness check), IMP-17 (auto-rollback on regression — the canary pattern), IMP-14 (confidence scoring).",
    relatedImp: ["IMP-1", "IMP-3", "IMP-14", "IMP-17"],
  },
  {
    name: "GitHub Copilot Autofix",
    vendor: "GitHub",
    specialty:
      "Confidence-scored security fixes for CodeQL alerts. Each fix has a confidence score; low-confidence fixes require human review. The decision-layer pattern that separates 'auto-apply' from 'needs human'.",
    scpAdoption:
      "IMP-14 (confidence-scored fix ranking with auto_apply / human_review / discard buckets), IMP-8 (LLM fix caching).",
    relatedImp: ["IMP-14", "IMP-8"],
  },
  {
    name: "Semgrep",
    vendor: "Semgrep Inc.",
    specialty:
      "Multi-language static analysis with --parallel fan-out and multi-rule cross-validation. The performance + cross-lineage-agreement pattern.",
    scpAdoption:
      "IMP-18 (parallel scanner fan-out with dedup), IMP-7 (lineage-aware cross-validation), IMP-4 (cross-file vulture default).",
    relatedImp: ["IMP-18", "IMP-7", "IMP-4"],
  },
  {
    name: "CodeQL / DeepCode",
    vendor: "GitHub (CodeQL) / Snyk (DeepCode)",
    specialty:
      "Semantic data-flow analysis. Tracks how user input flows to dangerous sinks across function boundaries. The blast-radius + semantic-equivalence pattern.",
    scpAdoption:
      "IMP-16 (fix blast-radius analysis via reverse call-graph), IMP-15 (semantic equivalence via ast.dump).",
    relatedImp: ["IMP-16", "IMP-15"],
  },
  {
    name: "Hypothesis + QuickCheck",
    vendor: "Hypothesis Project (Python) / Haskell QuickCheck",
    specialty:
      "Property-based testing — generate thousands of random inputs to test invariants, not just example cases. Catches edge cases example tests miss.",
    scpAdoption:
      "IMP-5 (hypothesis property-based scanner), R7-10 (12 hypothesis tests for None-safety), R8-6/R8-7 (concurrency bugs found by manual property reasoning).",
    relatedImp: ["IMP-5"],
  },
  {
    name: "pytest-xdist + ruff --parallel",
    vendor: "pytest-dev / Astral",
    specialty:
      "Parallel test execution + parallel linting. CPU-bound work fanned out across cores. The speed pattern for CPU-bound AST work.",
    scpAdoption:
      "IMP-11 (concurrent fix worker pool — v2), IMP-18 (parallel scanner fan-out — v3), IMP-13 (incremental cache — skip unchanged).",
    relatedImp: ["IMP-11", "IMP-18", "IMP-13"],
  },
  {
    name: "terraform plan + git diff",
    vendor: "HashiCorp / Git",
    specialty:
      "Dry-run before apply. Show what WOULD change without changing it. The safety pattern for destructive operations.",
    scpAdoption:
      "IMP-9 (dry-run mode — show patch without applying), IMP-12 (diff-aware rescan — only re-scan changed files).",
    relatedImp: ["IMP-9", "IMP-12"],
  },
]
