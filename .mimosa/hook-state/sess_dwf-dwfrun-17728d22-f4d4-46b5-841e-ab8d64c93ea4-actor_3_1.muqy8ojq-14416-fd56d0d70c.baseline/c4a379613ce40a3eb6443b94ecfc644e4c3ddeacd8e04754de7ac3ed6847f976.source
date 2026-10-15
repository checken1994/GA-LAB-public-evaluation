/**
 * 6+ nguồn audit độc lập về lineage (separate file per task)
 *
 * DNA #5 + #14: Không tin đa số đồng ý nếu cùng lineage.
 * Round 7 dùng 7 nguồn (R6 dùng 6 — R7 thêm property-based testing).
 *
 * Lineage = engine phân tích + assumption set. Hai scanner cùng engine
 * (ví dụ cùng astroid) chia sẻ blind-spot → không độc lập thật.
 */

export interface AuditSource {
  id: string
  name: string
  version: string
  engine: string
  lineage: string
  blindSpot: string
  catchesWhat: string
  r7Findings: number
  r6Findings: number
  isNewInR7: boolean
  category: "syntax" | "semantic" | "type" | "dead-code" | "security" | "domain" | "reality" | "property"
}

export const AUDIT_SOURCES: AuditSource[] = [
  {
    id: "ruff",
    name: "ruff",
    version: "0.16.2",
    engine: "Rust + AST pattern",
    lineage: "Syntactic pattern matching (Rust impl of Python AST)",
    blindSpot: "Mù cross-module inference. Bị `# ruff: noqa: F821` che (file-level).",
    catchesWhat: "F821 undefined-name, F811 redefinition, B023 closure-over-loop, RUF006 task-not-stored, RUF021 combined-compare.",
    r7Findings: 11,
    r6Findings: 11,
    isNewInR7: false,
    category: "syntax",
  },
  {
    id: "pyflakes",
    name: "pyflakes",
    version: "3.4.0",
    engine: "Python AST (độc lập với ruff)",
    lineage: "Python AST, KHÔNG respect noqa → bắt được F821 bị ruff che",
    blindSpot: "Mù type, mù cross-module, không phân biệt dead-code.",
    catchesWhat: "F821 không bị noqa che (R5 Bug #1 _SCP_SAFE_FETCH_UA). Pre-existing slm_cache_set redefinition.",
    r7Findings: 119,
    r6Findings: 119,
    isNewInR7: false,
    category: "syntax",
  },
  {
    id: "pylint",
    name: "pylint",
    version: "4.0.6",
    engine: "astroid + cross-module inference",
    lineage: "Semantic graph (astroid), cross-module BUT same Python-AST base",
    blindSpot: "Mixin pattern → false positive E1101 no-member. Coroutine inference sai.",
    catchesWhat: "E0602 undefined-variable, E0606 possibly-undefined, E1101 no-member, E1102 not-callable.",
    r7Findings: 130,
    r6Findings: 130,
    isNewInR7: false,
    category: "semantic",
  },
  {
    id: "vulture",
    name: "vulture",
    version: "2.16",
    engine: "AST + confidence scoring",
    lineage: "Dead-code analysis, cross-file capable (R6 deeper than R5)",
    blindSpot: "Mù dynamic dispatch (getattr, plugin registry, signal handlers).",
    catchesWhat: "Category A (true dead), Category B (wired-but-never-called safety control), Category C (decorative enum methods).",
    r7Findings: 41,
    r6Findings: 33,
    isNewInR7: false,
    category: "dead-code",
  },
  {
    id: "mypy",
    name: "mypy",
    version: "2.3.0",
    engine: "Type inference + contract verification",
    lineage: "Type system (độc lập hoàn toàn với ruff/pylint/vulture)",
    blindSpot: "follow-imports=silent stub dataclass → báo 'dict has no attr value' thay vì None-comparison (R6-1 misleading).",
    catchesWhat: "return-type mismatch, Optional narrowing, union-attr (None>0 TypeError cluster), except-var-deleted, BaseException vs Exception.",
    r7Findings: 18,
    r6Findings: 8,
    isNewInR7: false,
    category: "type",
  },
  {
    id: "bandit",
    name: "bandit",
    version: "1.9.4",
    engine: "Security pattern matcher",
    lineage: "Security pattern (CWE-based)",
    blindSpot: "SCP patterns deliberately scanner-friendly → 0 HIGH.",
    catchesWhat: "Stylistic MEDIUM (assert, hardcoded-bind, subprocess shell=True). 0 real security bugs.",
    r7Findings: 13,
    r6Findings: 13,
    isNewInR7: false,
    category: "security",
  },
  {
    id: "scp-scanners",
    name: "SCP's OWN 18 scanners",
    version: "v104.75",
    engine: "AST + SCP domain-specific",
    lineage: "SCP-self (cùng codebase với code bị audit → có thể share blind-spot)",
    blindSpot: "Cùng base Python AST → không độc lập thật với pyflakes. Miss runtime contract bugs (R4).",
    catchesWhat: "APIWiring, DeadCode, DeadSLM, NullSafety, RaceCondition, ResourceLeak, RoutingGap, SchemaMismatch, SQLInjection, StaticMethodSelf, TaintFlow, TypeContract, XSS + 5 semantic scanners.",
    r7Findings: 188,
    r6Findings: 193,
    isNewInR7: false,
    category: "domain",
  },
  {
    id: "reality-log",
    name: "PowerShell.txt reality mining",
    version: "5169 lines",
    engine: "Log analysis (Reality — không phải model)",
    lineage: "DUY NHẤT không phải model — là bytestream từ runtime thực",
    blindSpot: "Chỉ thấy những gì được log. Silent failure = 0 traceback nhưng feature chết.",
    catchesWhat: "strategy=unknown 1108/1108, max_dev=1.0 72/72, 0 tracebacks → all silent (R4 evidence).",
    r7Findings: 1,
    r6Findings: 1,
    isNewInR7: false,
    category: "reality",
  },
  {
    id: "hypothesis",
    name: "hypothesis (property-based)",
    version: "6.108.0",
    engine: "Property-based testing + shrinking",
    lineage: "Runtime execution + random input generation (HOÀN TOÀN độc lập với static analysis)",
    blindSpot: "Cần test function viết sẵn. Không khám phá code path không có test.",
    catchesWhat: "TypeError khi input None/empty/edge-case (R7-1 mới: CryptoResult(value=None) → None>0 TypeError bị Hypothesis reproduce 1000 lần).",
    r7Findings: 3,
    r6Findings: 0,
    isNewInR7: true,
    category: "property",
  },
]

export const SOURCES_BY_CATEGORY = AUDIT_SOURCES.reduce(
  (acc, s) => {
    if (!acc[s.category]) acc[s.category] = []
    acc[s.category].push(s)
    return acc
  },
  {} as Record<string, AuditSource[]>,
)

export function getIndependentSources(): AuditSource[] {
  // DNA #14: chỉ tin cross-lineage agreement
  // 4 lineage groups: Rust-AST, Python-AST, astroid-semantic, type-system, reality-log, property-runtime
  return AUDIT_SOURCES.filter((s) =>
    ["ruff", "pyflakes", "pylint", "vulture", "mypy", "bandit", "reality-log", "hypothesis"].includes(s.id),
  )
}
