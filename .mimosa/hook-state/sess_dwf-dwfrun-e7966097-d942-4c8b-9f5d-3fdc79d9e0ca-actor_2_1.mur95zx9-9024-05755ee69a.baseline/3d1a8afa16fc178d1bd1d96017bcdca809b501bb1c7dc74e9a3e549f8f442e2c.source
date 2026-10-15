/**
 * API /api/audit — returns Round 7 audit findings + stats
 *
 * DNA #22: PASS ≠ TRUE. This endpoint serves FRESH Round 7 data,
 * explicitly NOT trusting R3-R6 reports.
 *
 * [Task 1-A · Fix 4-c-013] Previously `force-static` — Next.js computed
 * the JSON ONCE at build time and cached it. But `generatedAt` calls
 * `new Date().toISOString()`, which became frozen at build time. An
 * operator inspecting `/api/audit` saw a timestamp that NEVER changed
 * even weeks after deploy. Now `force-dynamic` so `generatedAt` is the
 * actual request time. DNA #26 (reality test): the timestamp must
 * reflect reality.
 */
import { NextResponse } from "next/server"
import { ROUND7_FINDINGS, R7_STATS, FINDINGS_BY_SEVERITY } from "@/lib/audit-data/round7"
import { AUDIT_SOURCES } from "@/lib/audit-data/sources"
import { SCP_DNA } from "@/lib/audit-data/dna"

export const dynamic = "force-dynamic"
export const revalidate = 0

export function GET() {
  return NextResponse.json(
    {
      round: 7,
      motto: "PASS ≠ TRUE (DNA #22)",
      methodology: {
        sources: AUDIT_SOURCES.length,
        independent_lineages: 8,
        newInR7: ["hypothesis (property-based testing)"],
        r_fix_completeness_check: true,
        cross_file_vulture: true,
      },
      stats: R7_STATS,
      findings: ROUND7_FINDINGS,
      bySeverity: FINDINGS_BY_SEVERITY,
      sources: AUDIT_SOURCES,
      dnaPrinciples: SCP_DNA.length,
      generatedAt: new Date().toISOString(),
    },
    {
      headers: {
        // Make staleness explicit: audit data changes only when a new
        // Round ships, so a 1-hour browser/CDN cache is safe.
        "Cache-Control": "public, max-age=3600",
      },
    },
  )
}
