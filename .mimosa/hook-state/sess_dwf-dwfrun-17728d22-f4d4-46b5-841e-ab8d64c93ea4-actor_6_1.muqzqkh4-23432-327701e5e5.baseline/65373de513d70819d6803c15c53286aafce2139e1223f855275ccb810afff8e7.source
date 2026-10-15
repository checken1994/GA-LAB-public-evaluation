/**
 * API /api/autofix — returns autofix engine spec + improvements
 *
 * The "UPDATE" the user requested: stronger + more accurate + faster autofix,
 * inspired by best world systems (Sentry, Copilot, Semgrep, Cursor).
 *
 * [Task 1-A · Fix 4-c-014] Previously `force-static` — the dashboard's
 * autofix metadata was FROZEN at build time. When the Python backend
 * shipped a new autofix improvement, the dashboard continued to serve
 * stale build-time data until the next dashboard rebuild (DNA #5 + #26).
 * Now `force-dynamic` with a live fetch from SCP backend
 * `/v105/autofix/stats`; falls back to the static audit-data array if
 * SCP is offline or the endpoint 404s (DNA #7 fail-open). The `source`
 * flag tells the operator which path was taken (DNA #22).
 */
import { NextResponse } from "next/server"
import { isAllowedProbeTarget } from "../../../lib/probe-allowlist"
import {
  AUTOFIX_TIERS,
  AUTOFIX_PIPELINE,
  AUTOFIX_CONFIG,
} from "@/lib/audit-data/autofix-engine"
import {
  AUTOFIX_IMPROVEMENTS,
  IMPROVEMENT_STATS,
} from "@/lib/audit-data/autofix-improvements"

export const dynamic = "force-dynamic"
export const revalidate = 0

const SCP_BACKEND_URL =
  process.env.SCP_INTERNAL_URL ?? "http://127.0.0.1:8000"

// Build the static fallback once (cheaper than rebuilding per-request).
const STATIC_FALLBACK = {
  engine: {
    version: "v104.75-R7",
    tiers: AUTOFIX_TIERS,
    pipeline: AUTOFIX_PIPELINE,
    config: AUTOFIX_CONFIG,
  },
  improvements: {
    stats: IMPROVEMENT_STATS,
    list: AUTOFIX_IMPROVEMENTS,
  },
  inspirations: [
    "Sentry Autofix — test suite verification post-patch",
    "GitHub Copilot Autofix — pattern-hash caching",
    "Semgrep — cross-file dataflow + multi-rule agreement",
    "Cursor Bugbot — dry-run diff preview",
    "Hypothesis — property-based testing",
    "pytest-xdist — parallel worker pool",
  ],
}

export async function GET() {
  const fetchedAt = new Date().toISOString()

  // Live fetch from SCP backend (server-side). `/v105/autofix/stats`
  // is registered in api_server.py (see SCP_ROUTES listing).
  // DNA #26: reality test against the live system.
  try {
    const targetUrl = `${SCP_BACKEND_URL}/v105/autofix/stats`
    const extraHosts = (process.env.SCP_HEALTH_ALLOWED_HOSTS ?? "").split(",").map((h) => h.trim().toLowerCase()).filter(Boolean)
    const guard = isAllowedProbeTarget(targetUrl, extraHosts)
    if (!guard.allowed) throw new Error(`SSRF blocked: ${guard.reason}`)
    const resp = await fetch(targetUrl, {
      signal: AbortSignal.timeout(2000),
      headers: { Accept: "application/json" },
      cache: "no-store",
    })
    if (resp.ok) {
      const data = (await resp.json()) as Record<string, unknown>
      // Merge: backend `/v105/autofix/stats` returns runtime stats
      // (cache hits, runs, fix counts). The static fallback carries the
      // engine spec + improvements list. Combine both so the dashboard
      // can show live stats + design docs together.
      return NextResponse.json({
        ...STATIC_FALLBACK,
        liveStats: data,
        source: "live",
        backendUrl: `${SCP_BACKEND_URL}/v105/autofix/stats`,
        fetchedAt,
      })
    }
  } catch {
    /* fall through to static fallback (DNA #7 fail-open) */
  }

  return NextResponse.json({
    ...STATIC_FALLBACK,
    source: "fallback-static",
    backendUrl: `${SCP_BACKEND_URL}/v105/autofix/stats`,
    fetchedAt,
    note: "SCP backend /v105/autofix/stats unreachable — serving build-time static autofix spec. DNA #22: stats may be stale.",
  })
}
