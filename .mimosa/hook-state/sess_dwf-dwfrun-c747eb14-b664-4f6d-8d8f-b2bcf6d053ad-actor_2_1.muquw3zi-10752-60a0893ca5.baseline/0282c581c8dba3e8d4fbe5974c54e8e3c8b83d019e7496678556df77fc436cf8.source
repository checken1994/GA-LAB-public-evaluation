/**
 * API /api/scp/status — overall SCP system status.
 *
 * Combines:
 *   1. SCP liveness (live fetch of /health, fail-open if down)
 *   2. Autofix engine metadata (engine version v4, modules wired status)
 *   3. R9 audit metadata
 *
 * [Task 1-A · Fix 4-c-012 + 4-d-021] All 6 v4 modules ARE wired into
 * engine.py + runner.py + llm_fix.py (per R19-FIX-6 reconciliation against
 * scp/autofix/engine.py imports). Prior comment block said "0/6 wired" and
 * UI text said "standalone / deferred" — both contradicted the data array
 * which marks all 6 wired:true. DNA #22 (PASS ≠ TRUE) + #5 (single source
 * fabricates consensus): comment must match code must match reality.
 *
 * [Task 6-A · Fix 4-c-006] v4 module LOC is now COMPUTED from actual files at
 * module load (computeAutofixLoc reads scp/autofix/*.py via fs.readFileSync +
 * counts '\n'). Previously hardcoded 728/723/798/642/743/755 = 4,389 total —
 * drifted +505 from reality (actual 4,894 per `wc -l` as of audit). If the
 * Python tree is unreachable at module load (e.g. dashboard deployed without
 * backend), computeAutofixLoc falls back to LAST_VERIFIED_FALLBACK_LOC with
 * a documented `lastVerified` date — never silently uses a stale constant.
 * DNA #22 (PASS ≠ TRUE) + #14 (numbers must match reality) + #26 (reality
 * has final authority).
 *
 * This endpoint is dynamic (force-dynamic, revalidate=0) because SCP
 * liveness changes at runtime.
 */
import { readdirSync, readFileSync, statSync } from "fs"
import path from "path"
import { isAllowedProbeTarget } from "../../../../lib/probe-allowlist"
import { NextResponse } from "next/server"
import {
  CURRENT_ROUND,
  SCP_CANONICAL_MODEL_ID,
  DOMAIN_EXPERT_ENSEMBLE_TERM,
  SCP_LEGACY_PROTOCOLS,
  SCP_RELEASE_LABEL,
  SCP_RELEASE_VERSION,
} from "@/lib/audit-data/version"

export const dynamic = "force-dynamic"
export const revalidate = 0

const SCP_BASE_URL =
  process.env.SCP_INTERNAL_URL ?? "http://127.0.0.1:8000"

const START_HINT = "Run: SCP_PORT=8000 python -m scp (in your scp folder)"

// SCP root: parent of dashboard/. Override via env when dashboard and backend
// are deployed separately. Resolving from cwd avoids a machine-specific path.
const SCP_ROOT = process.env.SCP_ROOT ?? path.resolve(process.cwd(), "..")

// [4-c-006] Last-verified fallback LOC values (per `wc -l` of actual files).
// Used ONLY when computeAutofixLoc cannot read the actual file at module load
// (e.g. dashboard deployed separately from backend). Last verified date
// documents when the fallback was last cross-checked against reality.
// Drift will recur if SCP changes; recompute via `wc -l scp/autofix/*.py`
// after backend updates and bump the date.
// S17 drift refresh (2026-09-13): the B1 logging campaign legitimately added
// LOC to the autofix modules; fallback re-measured via `wc -l` on the actual
// 6 v4 files (total 5,007 = 924+806+847+751+784+895) and the date bumped.
// Drift refresh (2026-09-24): commit e40af00 (M1/M2/M3 fixes) added +3 net
// LOC to type_flow_verifier.py (806 → 809, confirmed via `git show e40af00
// --shortstat` = +7/-4); fallback re-measured via `wc -l` on the actual
// 6 v4 files (total 5,010 = 924+809+847+751+784+895) and the date bumped.
// Drift refresh (2026-09-26): the silent-except visibility sweep + gap
// closure legitimately added LOC (policy_gate +136, property_validator +1,
// speculative_prefixer +1, type_flow_verifier -1, shadow_canary -2);
// fallback re-measured via `wc -l` on the actual
// 6 v4 files (total 5,145 = 925+808+848+751+782+1031) and the date bumped.
// Drift refresh (2026-09-30, Mimosa S311-fix): property_validator +78 net LOC
// (isolated SystemRandom strategy source + hashlib deterministic sampler for
// seeded runs + seeding-contract comments; 925 → 1003, measured via `wc -l`
// after the edit); fallback re-measured on the actual 6 v4 files
// (total 5,235 = 1003+808+848+751+782+1043) and the date bumped.
// Drift refresh (2026-10-01, audit-r2): commit a068dbe2 added +34/-15 net
// +19 LOC across type_flow_verifier.py (808 → 817) and callgraph_delta.py
// (751 → 761), confirmed via `git show a068dbe2 --shortstat`; fallback
// re-measured via `wc -l` on the actual 6 v4 files
// (total 5,254 = 1003+817+848+761+782+1043) and the date bumped.
const LAST_VERIFIED_DATE = "2026-10-01 (post audit-r2 drift refresh)"
const LAST_VERIFIED_FALLBACK_LOC: Record<string, number> = {
  "scp/autofix/property_validator.py": 1003,
  "scp/autofix/type_flow_verifier.py": 817,
  "scp/autofix/speculative_prefixer.py": 848,
  "scp/autofix/callgraph_delta.py": 761,
  "scp/autofix/runner_phases/shadow_canary.py": 782,
  "scp/autofix/policy_gate.py": 1043,
}

/**
 * [4-c-006] Compute LOC of an actual scp/autofix/*.py file at module load.
 * Reads the file via fs.readFileSync and counts '\n' (matches `wc -l`).
 * Falls back to a documented last-verified constant if the file is
 * unreachable (dashboard deployed without backend tree).
 *
 * Returns { loc, live } where `live` indicates whether the value was
 * computed from the actual file (true) or fell back to the documented
 * constant (false). Caller can surface this to operators so they know
 * whether the number is fresh or stale.
 */
function computeAutofixLoc(relPath: string): { loc: number; live: boolean } {
  // [S5b security sweep] Path containment (CWE-22, finding
  // finding:1827bf0d8e92358bde84bc24): resolve relPath against SCP_ROOT and
  // require the result to stay INSIDE the root before any fs access.
  // relPath is a compile-time constant from the V4_MODULES table today (no
  // request/user input reaches this function), so containment cannot fail in
  // practice — but the explicit boundary keeps the read safe if the path
  // source ever becomes dynamic ("../../x" resolves outside and is rejected
  // into the documented fallback path below, loc=0/live=false if unknown).
  // path.resolve also neutralizes absolute-path traversal (an absolute
  // relPath replaces the base and then fails the startsWith check).
  const rootAbs = path.resolve(SCP_ROOT)
  const abs = path.resolve(rootAbs, relPath)
  const contained = abs === rootAbs || abs.startsWith(rootAbs + path.sep)
  try {
    if (!contained) {
      throw new Error(`path escapes SCP_ROOT: ${relPath}`)
    }
    const stats = statSync(/* turbopackIgnore: true */ abs)
    if (!stats.isFile()) {
      throw new Error(`not a file: ${abs}`)
    }
    const content = readFileSync(/* turbopackIgnore: true */ abs, "utf-8")
    // `wc -l` counts newline characters. A file with no trailing newline still
    // has its last line; split('\n').length - 1 matches wc -l, but to align
    // exactly with wc -l semantics (which counts \n bytes), we count newlines.
    const newlineCount = (content.match(/\n/g) ?? []).length
    // Edge case: file with content but no trailing newline → wc -l reports
    // lines-1, but split('\n').length includes the last partial line. Use
    // the larger of (newlineCount, split('\n').length - 1) for safety.
    const splitCount = content.split("\n").length - 1
    const loc = Math.max(newlineCount, splitCount)
    if (loc <= 0) {
      throw new Error(`empty or unreadable: ${abs}`)
    }
    return { loc, live: true }
  } catch {
    const fallback = LAST_VERIFIED_FALLBACK_LOC[relPath]
    if (typeof fallback === "number") {
      return { loc: fallback, live: false }
    }
    // Unknown file path — return 0 rather than fabricating a number.
    return { loc: 0, live: false }
  }
}

// v4 modules (6 IMP-19..24) — created by Subagent C in R9.
// [R19-FIX-6] UPDATED: all 6 v4 modules ARE NOW WIRED into engine.py +
// runner.py + llm_fix.py (engine.py imports/calls each module — verified
// at L599, L604, L634, L844, L922, L925, L1502, L1609; runner.py L394;
// llm_fix.py L744). DNA #22 (PASS ≠ TRUE): dashboard previously said
// "not wired / standalone / deferred" but code reality = wired. Comment +
// text reconciled in Task 1-A.
//
// [4-c-006] LOC for each module is now computed live from the actual file
// at module load via computeAutofixLoc. See LAST_VERIFIED_FALLBACK_LOC for
// the documented fallback used when the backend tree is unreachable.
const V4_MODULES = [
  {
    imp: "IMP-19",
    file: "scp/autofix/property_validator.py",
    axis: "ACCURACY",
    name: "Property-Based Validation",
    wired: true,
    loc: computeAutofixLoc("scp/autofix/property_validator.py").loc,
    locLive: computeAutofixLoc("scp/autofix/property_validator.py").live,
  },
  {
    imp: "IMP-20",
    file: "scp/autofix/type_flow_verifier.py",
    axis: "ACCURACY",
    name: "Cross-File Type-Flow",
    wired: true,
    loc: computeAutofixLoc("scp/autofix/type_flow_verifier.py").loc,
    locLive: computeAutofixLoc("scp/autofix/type_flow_verifier.py").live,
  },
  {
    imp: "IMP-21",
    file: "scp/autofix/speculative_prefixer.py",
    axis: "SPEED",
    name: "Speculative Pre-Fix",
    wired: true,
    loc: computeAutofixLoc("scp/autofix/speculative_prefixer.py").loc,
    locLive: computeAutofixLoc("scp/autofix/speculative_prefixer.py").live,
  },
  {
    imp: "IMP-22",
    file: "scp/autofix/callgraph_delta.py",
    axis: "SPEED",
    name: "Incremental Call-Graph",
    wired: true,
    loc: computeAutofixLoc("scp/autofix/callgraph_delta.py").loc,
    locLive: computeAutofixLoc("scp/autofix/callgraph_delta.py").live,
  },
  {
    imp: "IMP-23",
    file: "scp/autofix/runner_phases/shadow_canary.py",
    axis: "SAFETY",
    name: "Shadow-Apply + Canary",
    wired: true,
    loc: computeAutofixLoc("scp/autofix/runner_phases/shadow_canary.py").loc,
    locLive: computeAutofixLoc(
      "scp/autofix/runner_phases/shadow_canary.py"
    ).live,
  },
  {
    imp: "IMP-24",
    file: "scp/autofix/policy_gate.py",
    axis: "SAFETY",
    name: "Constitutional Policy Gate",
    wired: true,
    loc: computeAutofixLoc("scp/autofix/policy_gate.py").loc,
    locLive: computeAutofixLoc("scp/autofix/policy_gate.py").live,
  },
]

const V3_MODULES = [
  { imp: "IMP-13", file: "scp/autofix/ast_diff_cache.py", wired: true },
  { imp: "IMP-14", file: "scp/autofix/confidence_ranker.py", wired: true },
  { imp: "IMP-15", file: "scp/autofix/runner_phases/semantic_equiv.py", wired: true },
  { imp: "IMP-16", file: "scp/autofix/runner_phases/blast_radius.py", wired: true },
  { imp: "IMP-17", file: "scp/autofix/runner_phases/auto_rollback.py", wired: true },
  { imp: "IMP-18", file: "scp/autofix/parallel_scanner.py", wired: true },
]

export async function GET() {
  const checkedAt = new Date().toISOString()

  // --- 1. SCP liveness ---
  let scpStatus: "online" | "degraded" | "offline" = "offline"
  let scpHealth: Record<string, unknown> | null = null
  let scpError: string | null = null
  let scpHttpStatus: number | null = null

  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 3000)
    const targetUrl = `${SCP_BASE_URL}/health`
    const extraHosts = (process.env.SCP_HEALTH_ALLOWED_HOSTS ?? "").split(",").map((h) => h.trim().toLowerCase()).filter(Boolean)
    const guard = isAllowedProbeTarget(targetUrl, extraHosts)
    if (!guard.allowed) {
      throw new Error(`SSRF blocked: ${guard.reason}`)
    }
    const res = await fetch(targetUrl, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
      cache: "no-store",
    })
    clearTimeout(timeout)
    scpHttpStatus = res.status
    if (res.ok) {
      scpStatus = "online"
      scpHealth = (await res.json()) as Record<string, unknown>
    } else {
      scpStatus = "degraded"
    }
  } catch (e) {
    scpError = e instanceof Error ? e.message : String(e)
  }

  // --- 2. Autofix engine metadata ---
  // [4-c-006] v4Loc is now the sum of live-computed module LOCs.
  // If any module fell back to the documented constant, v4LocLive=false so
  // operators can see the number may be stale.
  const v4LocTotal = V4_MODULES.reduce((sum, m) => sum + m.loc, 0)
  const v4LocAllLive = V4_MODULES.every((m) => m.locLive)
  const engine = {
    version: SCP_RELEASE_VERSION,
    modelId: SCP_CANONICAL_MODEL_ID,
    release: SCP_RELEASE_LABEL,
    auditRound: CURRENT_ROUND,
    expertTerm: DOMAIN_EXPERT_ENSEMBLE_TERM,
    legacyProtocols: SCP_LEGACY_PROTOCOLS,
    versionHistory: [
      `${SCP_RELEASE_LABEL} (current)`,
      "Autofix generation 2 (audit R7)",
      "Autofix generation 3 (audit R8)",
      "Autofix generation 4 (audit R9)",
    ],
    totalAutofixPyFiles: 63, // 51 v2 + 6 v3 + 6 v4
    modulesByGeneration: {
      v2_count: 51,
      v3_count: 6,
      v4_count: 6,
    },
    modulesWired: {
      v3: V3_MODULES.filter((m) => m.wired).length, // 6/6 wired (R8)
      v4: V4_MODULES.filter((m) => m.wired).length, // 6/6 wired (R19-FIX-6 — Task 1-A reconciled)
    },
    modulesStandalone: {
      v3: V3_MODULES.filter((m) => !m.wired).length, // 0/6 standalone
      v4: V4_MODULES.filter((m) => !m.wired).length, // 0/6 standalone (all wired R19-FIX-6)
    },
    // [4-c-006] Live-computed v4 LOC (was hardcoded 4,389 — drifted +505
    // from actual 4,894). Now reflects actual file sizes at module load.
    v4Loc: v4LocTotal,
    v4LocLive: v4LocAllLive,
    v4LocLastVerifiedDate: LAST_VERIFIED_DATE,
    v4LocMethod: v4LocAllLive
      ? "live (computed from scp/autofix/*.py at module load)"
      : `fallback (last verified ${LAST_VERIFIED_DATE}; at least one module's file was unreachable at ${SCP_ROOT})`,
  }

  // --- 3. Audit metadata ---
  // Audit Round 20 is the current operator-visible round; the fields below
  // are historical R9/R8 evidence retained for compatibility and provenance.
  const audit = {
    auditRound: CURRENT_ROUND,
    historicalEvidenceRound: 9,
    evidenceLabel: "Historical R9 audit evidence",
    pythonFilesAstParseOk: "377/377",
    r9BugsFound: 7,
    r9BugsPatched: 7,
    saR9Findings: 6,
    r8ClaimsVerifiedTrue: 19,
    r8ClaimsVerifiedFalse: 6,
    crossValidation: "SA-R9-2 (Subagent A) = R9-7 (Subagent B) — same R8-1 regression, 2 independent lineages (DNA #5)",
  }

  return NextResponse.json({
    scp: scpStatus,
    scpHealth,
    scpError: scpError?.slice(0, 200) ?? null,
    scpHttpStatus,
    checkedAt,
    hint: scpStatus === "online" ? null : START_HINT,
    engine,
    audit,
    modules: {
      v3: V3_MODULES,
      v4: V4_MODULES,
    },
  })
}
