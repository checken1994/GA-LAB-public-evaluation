/**
 * Autofix Engine v4 — 6 NEW improvements (IMP-19..IMP-24)
 *
 * "cập nhật autofix để autofix mạnh + chính xác + nhanh hơn, giống autofix của
 *  hệ thống tốt nhất khác của thế giới" — User (Gà), R9.
 *
 * R7-Full upgraded v1→v2 (IMP-1..12, ~1,400 LOC). R8 upgraded v2→v3
 * (IMP-13..18, 2,586 LOC). R9 upgrades v3→v4 with 6 MORE improvements
 * (IMP-19..24, 4,894 LOC as of Phase 6-A audit — live count via
 * /api/scp/status which computes from scp/autofix/*.py at module load) —
 * 70% more substantial than v3, reflecting deeper
 * algorithms: property-based testing, cross-file type-flow, speculative
 * pre-fix generation, incremental call-graph, shadow-apply + canary, and a
 * constitutional policy gate with tamper-evident audit log.
 *
 * Three axes of improvement (matching v3's pattern):
 *   - ACCURACY: IMP-19 (property-based validation) + IMP-20 (type-flow verify)
 *   - SPEED:    IMP-21 (speculative prefixer) + IMP-22 (call-graph delta)
 *   - SAFETY:   IMP-23 (shadow canary) + IMP-24 (constitutional policy gate)
 *
 * Combined with v3's IMP-17 (auto-rollback post-apply), the engine now has
 * 4 layers of safety: pre-flight policy → pre-apply property → pre-apply
 * canary → post-apply rollback. No single layer is sufficient (DNA #22).
 *
 * Source: scp/autofix/V4_MANIFEST.md + scp/autofix/V4_CHANGELOG.md
 */

export type V4Axis = "accuracy" | "speed" | "safety"

export interface V4Improvement {
  id: string
  name: string
  inspiration: string
  axis: V4Axis
  problem: string
  solution: string
  file: string
  loc: number
  whatItDoes: string
  failOpen: string
  astParseOk: boolean
  smokeTested: boolean
  dnaPrinciples: string
}

export const V4_IMPROVEMENTS: V4Improvement[] = [
  {
    id: "IMP-19",
    name: "Property-Based Fix Validation",
    inspiration:
      "Hypothesis (Python, 2013-) + QuickCheck (Haskell, Claessen & Hughes 2000) + pytest-property + Sentry Autofix property test gate",
    axis: "accuracy",
    problem:
      "v3 IMP-15 (semantic_equiv) checks AST shape only — couldn't catch a fix that 'preserves AST shape but breaks invariant on edge input' (e.g. a fix that removes `if x is None: return None` guard → `f(None)` now raises TypeError, but the AST shape looks similar). Example-based smoke tests (R7-10) cover 12 hand-picked cases; property-based testing covers thousands of generated edge cases.",
    solution:
      "validate_fix(orig_source, fixed_source, bug_location, spec, n=100) generates N edge-case inputs (boundary values, empty, huge, unicode, negative, None, nested) via a built-in strategy generator, runs BOTH the original and fixed function on each input, and compares: (1) fixed violates invariant that original held → FAIL (regression); (2) fixed changes behavior on inputs OUTSIDE the bug location → over-broad FAIL; (3) fixed holds invariant that original violated → benign improvement.",
    file: "scp/autofix/property_validator.py (NEW)",
    loc: 728,
    whatItDoes:
      "8 built-in input strategies (int/float/str/list/dict/none/bool/mixed) + invariant comparison + coverage tracking + stable SHA-256 fingerprint for audit. Custom strategies registerable via register_strategy(name, fn).",
    failOpen:
      "Import error / strategy unavailable / compile error → ok=True, reason='skip — property validation unavailable (fail-open)'. No invariants in spec → ok=True (skip). Internal error → ok=True with reason. Pure function (no side effects on engine state).",
    astParseOk: true,
    smokeTested: true,
    dnaPrinciples: "#17 (Đã test chưa?) · #22 (PASS ≠ TRUE) · #9 (No harm) · #7 (Autofix safe) · #26 (Reality)",
  },
  {
    id: "IMP-20",
    name: "Cross-File Type-Flow Verification",
    inspiration:
      "pyright strict mode (Microsoft) + mypy --strict + mypyc + CodeQL type-flow taint tracking + TypeScript LSP 'find all references'",
    axis: "accuracy",
    problem:
      "v3 IMP-15 checks signature UNCHANGED. v3 IMP-16 counts callers but doesn't check type compatibility. No module detected 'fix narrows return type → 5 callers have dead None-branch' or 'fix widens return type → caller unwraps result.attr without None check → will AttributeError on None'.",
    solution:
      "verify_type_flow(target_file, target_function, orig_signature, new_signature, scp_root) walks all callers via a standalone shallow AST walker (_CallSiteCollector — doesn't depend on IMP-16). Detects: (a) return narrowing (Optional[X]→X, caller has `if result is None` → dead branch); (b) return widening (X→Optional[X], caller unwraps `result.attr` → AttributeError on None); (c) arg narrowing (Any→int, caller passes string literal → TypeError). Type parser handles Optional[X], List[X], Dict[K,V], Union[X,Y,...], PEP 604 X|Y, forward-ref quoted annotations.",
    file: "scp/autofix/type_flow_verifier.py (NEW)",
    loc: 723,
    whatItDoes:
      "TypeNode dataclass with is_optional()/unwrap_optional()/to_str(). parse_type(ann_str) fail-open on parse error. Signature + CallerSite + IncompatibleSite dataclasses. TypeFlowResult{compatible, breaking_callers, incompatible_sites, caller_count, reason, bounded}. summarize_type_flow(result) for human review.",
    failOpen:
      "Parse error / no callers found / scp_root missing → compatible=True, reason='skip — type-flow unverifiable (fail-open)'. Internal error → compatible=True with reason. Caller can force human review by setting confidence cap at 0.49 (DNA #4/#17).",
    astParseOk: true,
    smokeTested: true,
    dnaPrinciples: "#9 (No harm) · #22 (PASS ≠ TRUE) · #19 (Reality multi-source) · #7 (Autofix safe)",
  },
  {
    id: "IMP-21",
    name: "Speculative Pre-Fix Generation",
    inspiration:
      "GitHub Copilot speculative decoding (predict tokens while LLM computes) + CPU branch prediction (Pentium Pro, 1995) + V8 speculative optimization + nginx open file cache + ruff `--fix --cache`",
    axis: "speed",
    problem:
      "v3 IMP-18 (parallel scanner) parallelized scanners across files, but fix generation was still sequential AFTER scan. Each bug waited for LLM/rule-engine fix generation (200-2000ms). The scanner was fast, but the fix pipeline was the bottleneck.",
    solution:
      "SpeculativeCache stores pre-generated candidate fixes keyed by (file_sha256[:16], bug_pattern). While the scanner runs (slow), a speculative worker pre-generates candidate fixes for HIGH-CONFIDENCE bug patterns using fast template matchers. When scanner confirms a bug, if a cached candidate matches → apply INSTANTLY (0ms generation time) instead of waiting for LLM/solver. Cache invalidated on file change. LRU-evicted, thread-safe (threading.RLock), atomic JSON persistence via os.replace(tmp, cache_file).",
    file: "scp/autofix/speculative_prefixer.py (NEW)",
    loc: 798,
    whatItDoes:
      "4 high-confidence pattern templates: bare_except_pass, bare_except_broad, mutable_default_arg (list/dict/set), missing_encoding_open. Each pattern has a detector+generator function. Custom patterns registerable via PATTERN_REGISTRY. SpeculativeCache(cache_file, max_entries=1000, ttl_seconds=3600). Module-level shortcuts: prefetch_candidates(), lookup(), invalidate(), stats().",
    failOpen:
      "Cache miss → return None (caller falls back to normal path). Cache corrupt → rebuild from empty. Cache full → LRU eviction. Pattern generator crash → log + continue with remaining patterns. Cached fixes STILL go through IMP-14 confidence scoring + IMP-15 semantic equiv (NOT a free pass — DNA #22).",
    astParseOk: true,
    smokeTested: true,
    dnaPrinciples: "#9 (Tăng tốc) · #20 (Cache for speed) · #7 (Autofix safe) · #22 (PASS ≠ TRUE — cached fix still verified)",
  },
  {
    id: "IMP-22",
    name: "Incremental Call-Graph Delta",
    inspiration:
      "mypy daemon (dmypy) — incremental type checking since 2018 + TypeScript language server (tsserver) + Rust Analyzer (salsa-based incremental computation) + LLVM ThinLTO incremental index",
    axis: "speed",
    problem:
      "v3 IMP-16 (compute_blast_radius) re-walks the entire scp codebase each call. 371 files × ~10ms = 3.7s per call. 50 bugs per round = 185s just for blast-radius. Full-walk pattern doesn't scale as the codebase grows.",
    solution:
      "CallGraph maintains a persistent call-graph on disk (data/callgraph.json) keyed by file SHA. On file change, computes only the DELTA: which edges were added/removed, which callers are now affected. Avoids full re-scan of the whole codebase on every fix. Integrates with IMP-16 blast radius — caller can ask 'affected callers of func X since last build' and get a small list instead of re-walking 371 files.",
    file: "scp/autofix/callgraph_delta.py (NEW)",
    loc: 642,
    whatItDoes:
      "CallEdge(caller_file, target_name, line, col, is_method_call). FileNode(path, sha, mtime, functions_defined, calls, parse_error). DeltaResult{added_edges, removed_edges, affected_callers, affected_callees, files_rebuilt, files_skipped, bounded, reason}. CallGraph(cache_file) — thread-safe (RLock), atomic JSON persistence. Methods: build_full(scp_root), apply_delta(changed_files), get_callers(func_name), get_definitions(func_name), get_calls_in_file(file_path), invalidate_file(path), clear_all(), stats(), is_file_current(path).",
    failOpen:
      "Graph corrupt (JSON malformed / version mismatch) → rebuild from scratch (log warning). File unparseable → skip (don't crash build). Internal error → log + continue with empty graph. Has its own _FileAnalyzer AST visitor (doesn't import IMP-16's collector — stays standalone).",
    astParseOk: true,
    smokeTested: true,
    dnaPrinciples: "#9 (Tăng tốc) · #20 (Cache for speed) · #19 (Reality multi-source — file SHA + AST) · #7 (Autofix safe)",
  },
  {
    id: "IMP-23",
    name: "Shadow-Apply + Canary Compare",
    inspiration:
      "Sentry canary deploys (route 1% traffic, promote if healthy) + Istio traffic shadowing (mirror production to canary) + Netflix Chaos Monkey + Kubernetes canary + rollout + git stash + test before commit",
    axis: "safety",
    problem:
      "v3 IMP-17 (auto-rollback) applies fix to real file → reality_test runs → if regression detected in 60s window → rollback. Window of 'user sees broken behavior' exists between apply and rollback detection. A bad fix reaches production for ~60s before being undone.",
    solution:
      "shadow_apply_and_compare(target_file, fix, canary_suite) applies the fix to a SHADOW copy of the file (temp file in data/shadow/<basename>_shadow_<uuid8>.py), runs a canary test suite on BOTH original and shadow, compares outputs. Only promote to real apply if canary passes AND no regression. If canary fails → discard fix, log, fall back to human review. NO 'user sees broken behavior' window — bad fixes discarded before touching real file.",
    file: "scp/autofix/runner_phases/shadow_canary.py (NEW)",
    loc: 743,
    whatItDoes:
      "Default canary suite (default_canary_suite()) = 5 tests: ast_parse, import, smoke_call (calls each top-level function with edge inputs None/[]/{}/\"\"/0/1/-1, records per-input exception signature; detects 'shadow raises where original didn't' as REGRESSION), reality_test (IMP-2 on shadow, fail-open), property_test (IMP-19 on shadow, fail-open). Shadow temp files written to data/shadow/, cleaned up after canary run (best-effort, fail-open).",
    failOpen:
      "Empty canary suite → passed=True, flagged_for_review=True (don't block fixes if safety infra is down, but flag). Canary runner crash → passed=False (fail-closed for safety — a crashing safety net is worse than no net). Shadow apply fails (can't write temp file / can't import) → passed=False, reason='shadow apply failed (cannot verify — fail-closed)'. Internal error → passed=True, flagged_for_review=True with loud stderr warning. reality_test + property_validator imports are lazy (inside test functions) — fail-open if either is unavailable.",
    astParseOk: true,
    smokeTested: true,
    dnaPrinciples: "#9 (No harm) · #11 (Fail loudly) · #7 (Autofix safe) · #26 (Reality) · #17 (Operator oversight)",
  },
  {
    id: "IMP-24",
    name: "Constitutional Policy Gate",
    inspiration:
      "AWS Service Control Policies (SCPs) — org-level guardrails, can't be overridden by IAM + OPA/Rego policy-as-code + GitHub branch protection + Anthropic Constitutional AI (explicit principles independent of RLHF reward)",
    axis: "safety",
    problem:
      "v3 IMP-14 (_is_relaxation heuristic) checks 9 markers in patch text + caps confidence at 0.49. But a fix with confidence 0.95 (rule-based, reality-test OK, surgical) could STILL be dangerous if it matches `verify=False` or `os.chmod(path, 0o777)`. Confidence is not a constitutional check — DNA #22 (PASS ≠ TRUE) applies: confidence ≠ safety.",
    solution:
      "PolicyGate is a HARD policy gate that BLOCKS fixes matching forbidden patterns REGARDLESS of confidence score. Every block logged to IMMUTABLE append-only audit log (data/policy_blocks.jsonl) with timestamp, fix_id, matched pattern, scanner, file. Provides appeal_block(fix_id, human_token, justification) for operator override (logged separately to data/policy_appeals.jsonl). 13 forbidden patterns: lower_threshold, remove_check, disable_validation, allow_attack, skip_auth (BLOCK), bare_except_pass, noqa, type_ignore (REVIEW), world_writable_chmod, verify_false_tls (BLOCK), shell_true_subprocess, eval_call, exec_call (REVIEW).",
    file: "scp/autofix/policy_gate.py (NEW)",
    loc: 755,
    whatItDoes:
      "ForbiddenPattern(name, regex, severity, description, dna_ref). FORBIDDEN_PATTERNS list of 13 built-in patterns. PolicyFix dataclass. PolicyDecision{allowed, blocked_patterns, severity, reason, audit_id, fix_id, timestamp}. ImmutableAuditLog(log_file) — append-only JSONL with chained SHA-256 hashes (tamper-evident): append(entry) returns hash, read_since(ts), verify_chain() returns (ok, reason). PolicyGate(audit_log, extra_patterns) — evaluate_fix(fix), appeal_block(fix_id, human_token, justification), list_blocks(since_ts), stats().",
    failOpen:
      "Policy engine crash → DEFAULT-DENY (block + log) per DNA #4. Safer to block than allow a dangerous fix when safety net is broken. Audit log unwritable (disk full / permission denied) → DEFAULT-ALLOW with loud stderr warning per DNA #7 (don't brick engine if disk is full — but scream per DNA #11). In-memory BLOCK decision still in effect; only the audit trail is incomplete.",
    astParseOk: true,
    smokeTested: true,
    dnaPrinciples: "#4 (Constitution KILL) · #11 (Fail loudly) · #7 (Autofix safe) · #17 (Operator oversight) · #8 (KB accumulation — audit log) · #22 (PASS ≠ TRUE — confidence ≠ safety)",
  },
]

export const V4_STATS = {
  total: V4_IMPROVEMENTS.length,
  totalLoc: V4_IMPROVEMENTS.reduce((s, i) => s + i.loc, 0),
  byAxis: {
    accuracy: V4_IMPROVEMENTS.filter((i) => i.axis === "accuracy").length,
    speed: V4_IMPROVEMENTS.filter((i) => i.axis === "speed").length,
    safety: V4_IMPROVEMENTS.filter((i) => i.axis === "safety").length,
  },
  allAstParseOk: V4_IMPROVEMENTS.every((i) => i.astParseOk),
  allSmokeTested: V4_IMPROVEMENTS.every((i) => i.smokeTested),
  v2V3FilesUnchanged: true, // 0 v2/v3 files modified — light-touch integration
  totalAutofixPyFiles: 63, // 51 v2 + 6 v3 + 6 v4
  totalScpPyFiles: 377, // 371 R8 baseline + 6 v4 NEW
}

/**
 * World-class autofix systems v4 learns from — the 8 NEW systems beyond v3's 7.
 *
 * v3 had 7 systems (Sentry Autofix, GitHub Copilot, Semgrep, CodeQL/DeepCode,
 * Hypothesis+QuickCheck, pytest-xdist+ruff, terraform+git). v4 adds 8 more
 * (Hypothesis proper, pyright, mypy daemon, Copilot speculative decoding,
 * Istio traffic shadowing, OPA/Rego, AWS SCP, Anthropic Constitutional AI).
 * Total 15 systems — SCP synthesizes patterns from all.
 */
export interface V4WorldTool {
  name: string
  vendor: string
  specialty: string
  scpAdoption: string
  relatedImp: string[]
  versionAdded: "v4"
}

export const V4_WORLD_TOOLS: V4WorldTool[] = [
  {
    name: "Hypothesis (property-based testing, proper)",
    vendor: "Hypothesis Project (Python)",
    specialty:
      "Generate thousands of random edge-case inputs to test invariants, not just example cases. Shrinks failing inputs to minimal repro. The gold standard for 'does this fix break on weird input I didn't think of'.",
    scpAdoption:
      "IMP-19 (Property-Based Fix Validation) — 8 built-in input strategies (int/float/str/list/dict/none/bool/mixed) + invariant comparison + coverage tracking + stable SHA-256 fingerprint for audit.",
    relatedImp: ["IMP-19"],
    versionAdded: "v4",
  },
  {
    name: "pyright strict mode",
    vendor: "Microsoft",
    specialty:
      "Static type-checking with type-flow analysis. Tracks how types narrow/widen across function boundaries. Catches 'fix narrows return type → caller has dead None-branch' that example tests miss.",
    scpAdoption:
      "IMP-20 (Cross-File Type-Flow Verification) — type parser (Optional[X], PEP 604 X|Y, Union, forward-ref) + AST walker + per-caller None-check + attribute-unwrap detection.",
    relatedImp: ["IMP-20"],
    versionAdded: "v4",
  },
  {
    name: "mypy daemon (dmypy)",
    vendor: "Python Software Foundation",
    specialty:
      "Incremental type-checking server — caches analysis across runs, only re-checks changed files. The 'don't re-walk the whole codebase every time' pattern.",
    scpAdoption:
      "IMP-22 (Incremental Call-Graph Delta) — persistent call-graph JSON keyed by file SHA, apply_delta(changed_files) returns only the affected edges/callers.",
    relatedImp: ["IMP-22"],
    versionAdded: "v4",
  },
  {
    name: "GitHub Copilot speculative decoding",
    vendor: "GitHub / OpenAI",
    specialty:
      "While the LLM generates tokens, the client speculatively predicts likely continuations and verifies them in parallel. Hides LLM latency behind CPU work. The 'do work in parallel with the slow path' pattern.",
    scpAdoption:
      "IMP-21 (Speculative Pre-Fix Generation) — while scanner runs (slow), speculative worker pre-generates candidate fixes for HIGH-CONFIDENCE bug patterns. Cache hit → 0ms generation time.",
    relatedImp: ["IMP-21"],
    versionAdded: "v4",
  },
  {
    name: "Istio traffic shadowing",
    vendor: "Istio / CNCF",
    specialty:
      "Mirror production traffic to a canary deployment — compare outputs without affecting users. The 'test in shadow before promoting' pattern for safe rollout.",
    scpAdoption:
      "IMP-23 (Shadow-Apply + Canary Compare) — apply fix to a shadow temp file, run canary suite on BOTH original and shadow, only promote if no regression. Bad fixes never touch the real file.",
    relatedImp: ["IMP-23"],
    versionAdded: "v4",
  },
  {
    name: "OPA / Rego (policy-as-code)",
    vendor: "Styra / CNCF",
    specialty:
      "Declarative policy engine — write policies as code, evaluate at decision points, log every decision. Decouples 'is this allowed?' from 'is this correct?'.",
    scpAdoption:
      "IMP-24 (Constitutional Policy Gate) — 13 forbidden patterns (BLOCK/REVIEW) as declarative regexes, evaluate_fix(fix) returns PolicyDecision, every decision logged to tamper-evident audit log.",
    relatedImp: ["IMP-24"],
    versionAdded: "v4",
  },
  {
    name: "AWS Service Control Policies (SCPs)",
    vendor: "Amazon Web Services",
    specialty:
      "Org-level guardrails that CANNOT be overridden by IAM — even root account can't bypass them. The 'hard guard, regardless of caller privilege' pattern.",
    scpAdoption:
      "IMP-24 (Constitutional Policy Gate) — BLOCK-severity patterns reject fix regardless of IMP-14 confidence score (even 0.95 confidence doesn't bypass verify=False / chmod 0o777 blocks).",
    relatedImp: ["IMP-24"],
    versionAdded: "v4",
  },
  {
    name: "Anthropic Constitutional AI",
    vendor: "Anthropic",
    specialty:
      "Explicit principles (a 'constitution') that the model must obey, independent of RLHF reward. The model self-critiques against the constitution before responding. Principles > reward.",
    scpAdoption:
      "IMP-24 (Constitutional Policy Gate) — explicit Constitution (DNA #4 KILL list) independent of confidence scoring. appeal_block() provides principled override path with human-token + justification.",
    relatedImp: ["IMP-24"],
    versionAdded: "v4",
  },
]
