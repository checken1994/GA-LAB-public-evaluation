/**
 * API /api/scanners — returns all scanner info (SCP own + external)
 *
 * [Task 1-A · Fix 4-c-014] Previously `force-static` — the dashboard's
 * scanner count was FROZEN at build time. When the Python backend added
 * a new scanner, the dashboard continued to serve stale build-time data
 * until the next dashboard rebuild (DNA #5 + #26 — verify against
 * reality, not against a snapshot). Now `force-dynamic` with a live
 * fetch from SCP backend `/v105/scanners`; falls back to the static
 * audit-data array if SCP is offline or the endpoint 404s (DNA #7 —
 * fail-open). The `source` flag tells the operator which path was taken
 * (DNA #22 — make the staleness observable).
 */
import { NextResponse } from "next/server"
import { isAllowedProbeTarget } from "../../../lib/probe-allowlist"
import { SCP_SCANNERS, SCANNERS_BY_TYPE, IMPROVED_SCANNERS } from "@/lib/audit-data/scanners"

export const dynamic = "force-dynamic"
export const revalidate = 0

const SCP_BACKEND_URL =
  process.env.SCP_INTERNAL_URL ?? "http://127.0.0.1:8000"

// Build the static fallback once (cheaper than rebuilding per-request).
const STATIC_FALLBACK = {
  total: SCP_SCANNERS.length,
  scpOwn: SCP_SCANNERS.filter((s) => s.type === "scp-own").length,
  external: SCP_SCANNERS.filter((s) => s.type === "external").length,
  improvedInR7: IMPROVED_SCANNERS.length,
  scanners: SCP_SCANNERS,
  byType: SCANNERS_BY_TYPE,
  improved: IMPROVED_SCANNERS,
}

export async function GET() {
  const fetchedAt = new Date().toISOString()

  // Live fetch from SCP backend (server-side, direct is OK — no Caddy hop).
  // DNA #26: reality test against the live system, not the build-time snapshot.
  try {
    const targetUrl = `${SCP_BACKEND_URL}/v105/scanners`
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
      return NextResponse.json({
        ...data,
        source: "live",
        backendUrl: `${SCP_BACKEND_URL}/v105/scanners`,
        fetchedAt,
      })
    }
  } catch {
    /* fall through to static fallback (DNA #7 fail-open) */
  }

  return NextResponse.json({
    ...STATIC_FALLBACK,
    source: "fallback-static",
    backendUrl: `${SCP_BACKEND_URL}/v105/scanners`,
    fetchedAt,
    note: "SCP backend /v105/scanners unreachable — serving build-time static scanner registry. DNA #22: this data may be stale.",
  })
}
