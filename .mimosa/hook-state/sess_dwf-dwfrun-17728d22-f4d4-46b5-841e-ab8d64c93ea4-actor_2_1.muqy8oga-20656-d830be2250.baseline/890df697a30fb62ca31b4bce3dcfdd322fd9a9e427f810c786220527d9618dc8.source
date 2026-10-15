/**
 * API /api/scp/loop — proxy to the SCP Loop Scheduler mini-service.
 *
 * The loop-scheduler mini-service (mini-services/loop-scheduler/index.ts)
 * runs on port 3030 and periodically calls SCP's
 * POST /v105/autofix/run-audit endpoint to close the self-healing loop.
 *
 * This route is the Next.js dashboard's read-only view into the scheduler:
 *   GET → fetch scheduler status, return { loop: "online", ...data }
 *                                       or { loop: "offline", hint, error } (503)
 *
 * DNA SCP #22 (PASS ≠ TRUE): we don't trust a static "ok" string — we
 * actually fetch http://127.0.0.1:3030/ and surface whatever it returns.
 * If the scheduler is offline, we return 503 with a clear "Run: ..."
 * hint so the dashboard fails open (no broken UI).
 */
import { NextResponse } from "next/server"
import { isAllowedProbeTarget } from "../../../../lib/probe-allowlist"

export const dynamic = "force-dynamic"
export const revalidate = 0

const SCHEDULER_URL =
  process.env.LOOP_SCHEDULER_URL ?? "http://127.0.0.1:3030"

const START_HINT =
  "Run: bun run dev (in mini-services/loop-scheduler)"

export async function GET() {
  try {
    const targetUrl = `${SCHEDULER_URL}/`
    const extraHosts = (process.env.SCP_HEALTH_ALLOWED_HOSTS ?? "").split(",").map((h) => h.trim().toLowerCase()).filter(Boolean)
    const guard = isAllowedProbeTarget(targetUrl, extraHosts)
    if (!guard.allowed) throw new Error(`SSRF blocked: ${guard.reason}`)
    const res = await fetch(targetUrl, {
      signal: AbortSignal.timeout(2000),
      headers: { Accept: "application/json" },
      cache: "no-store",
    })
    if (!res.ok) {
      return NextResponse.json(
        {
          loop: "degraded",
          httpStatus: res.status,
          hint: START_HINT,
        },
        { status: 502 },
      )
    }
    const data = (await res.json()) as Record<string, unknown>
    return NextResponse.json({ loop: "online", ...data })
  } catch (e) {
    const err = e instanceof Error ? e.message : String(e)
    return NextResponse.json(
      {
        loop: "offline",
        error: err.slice(0, 200),
        hint: START_HINT,
      },
      { status: 503 },
    )
  }
}
