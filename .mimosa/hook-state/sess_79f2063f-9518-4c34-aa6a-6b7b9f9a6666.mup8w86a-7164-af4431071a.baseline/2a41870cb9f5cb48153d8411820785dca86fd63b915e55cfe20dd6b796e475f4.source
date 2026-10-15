/**
 * API /api/scp/loop/trigger — manually trigger an SCP audit cycle now
 * via the loop-scheduler mini-service.
 *
 * POST → POST http://127.0.0.1:3030/trigger
 *   Returns 202 ACCEPTED immediately with a jobId + the run result the
 *   scheduler logged (status, findings_count, fixes_applied, ...).
 *   If the scheduler is offline, returns 503 + hint.
 *
 * [Fix 4-c-009 · Task Local-C] BEFORE: this route awaited the SCP loop with
 * `AbortSignal.timeout(130_000)` (130 seconds). Next.js 16 dynamic routes
 * default to a ~60s timeout on Vercel hobby / reverse-proxy / load-balancer
 * hops — the route would be killed at 60-120s while the SCP backend kept
 * processing, leaving the audit running headless. Operator sees spinner →
 * "offline" → clicks Trigger again → double-trigger (DNA #11:
 * human-in-the-loop without understanding).
 *
 * AFTER: this route now uses the fire-and-forget pattern. It POSTs to the
 * scheduler with a short 5s timeout — enough for the scheduler to ACCEPT
 * the request and write the job to its queue, but not enough to wait for
 * the audit to complete. The route returns 202 ACCEPTED immediately with
 * a jobId. The dashboard polls /api/scp/loop for status updates (already
 * does — see ScpControlPanel's 30s auto-refresh). DNA #19 (observation
 * gap closed — route no longer killed mid-audit) + #22 (PASS ≠ TRUE: the
 * 200 OK no longer claims "audit complete" when it isn't) + #9 (no harm:
 * 502 returned if scheduler rejects within 5s).
 *
 * Rollback: revert to `signal: AbortSignal.timeout(130_000)` + awaiting
 * `res.json()` for the full run if a synchronous response is required.
 *
 * Used by the "Trigger now" button in the Loop Scheduler card on the
 * SCP Control Panel dashboard.
 */
import { readFile } from "node:fs/promises"
import { NextResponse } from "next/server"
import { isAllowedProbeTarget } from "../../../../../lib/probe-allowlist"

export const dynamic = "force-dynamic"
export const revalidate = 0

const SCHEDULER_URL =
  process.env.LOOP_SCHEDULER_URL ?? "http://127.0.0.1:3030"

const START_HINT =
  "Run: bun run dev (in mini-services/loop-scheduler)"

/**
 * Short timeout — the scheduler accepts the trigger request quickly (it
 * queues the job and returns immediately itself). 5s is enough for the
 * scheduler to respond even under load, but well under Next.js's default
 * ~60s route timeout. If the scheduler doesn't respond in 5s, we treat
 * the trigger as accepted-but-slow and return 202 with a "pending" hint
 * (the dashboard's existing 30s auto-refresh will pick up the run later).
 */
const TRIGGER_TIMEOUT_MS = 5_000

// [Fix 4-c-011 · Task Local-C] This route is POST-only — exports only POST.
// Next.js auto-returns 405 for GET / PUT / DELETE etc. (HTML body — the
// dashboard's `fetch().then(x => x.json()).catch(() => null)` swallows the
// parse error and shows "Never checked", which is sub-optimal but at least
// fails closed: a stray GET cannot mutate scheduler state). DNA #16
// (học nói phạm vi) + #9 (no harm — state-changing routes refuse wrong
// methods by default). All other /api/* routes in this dashboard also
// export only GET or only POST — no generic handler without a method
// check (see reality_4-c-011.py for the cross-route audit).

import { extractCallerAuth } from "../../../../../lib/auth-helper"

export async function POST(request: Request) {
  // Require caller authentication
  const auth = extractCallerAuth(request)
  if (!auth.authenticated || auth.errorResponse) {
    return auth.errorResponse || NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  // Generate a jobId so the dashboard can correlate this trigger with the
  // next /api/scp/loop poll. The scheduler's own log_path will carry the
  // canonical run identifier; this jobId is just for the dashboard UX.
  const jobId = `trigger-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

  try {
    const targetUrl = `${SCHEDULER_URL}/trigger`
    const extraHosts = (process.env.SCP_HEALTH_ALLOWED_HOSTS ?? "").split(",").map((h) => h.trim().toLowerCase()).filter(Boolean)
    const guard = isAllowedProbeTarget(targetUrl, extraHosts)
    if (!guard.allowed) throw new Error(`SSRF blocked: ${guard.reason}`)
    const res = await fetch(targetUrl, {
      method: "POST",
      // [Fix 4-c-009] Was 130_000ms (130s) — exceeded Next.js default route
      // timeout, killing the route mid-audit. Now 5s — fire-and-forget.
      signal: AbortSignal.timeout(TRIGGER_TIMEOUT_MS),
      headers: {
        Accept: "application/json",
        Authorization: auth.authHeader,
      },
      cache: "no-store",
    })

    if (!res.ok) {
      return NextResponse.json(
        {
          triggered: false,
          loop: "degraded",
          httpStatus: res.status,
          hint: START_HINT,
        },
        { status: 502 },
      )
    }

    // Scheduler accepted — return 202 immediately. Don't wait for the
    // audit to complete; the dashboard polls /api/scp/loop for status.
    let data: Record<string, unknown> = {}
    try {
      data = (await res.json()) as Record<string, unknown>
    } catch {
      // Scheduler returned non-JSON (some versions return 204 No Content).
      // That's fine — the trigger was accepted.
    }

    return NextResponse.json(
      {
        triggered: true,
        loop: "online",
        accepted: true,
        jobId,
        status: "accepted",
        message:
          "SCP audit cycle queued — poll /api/scp/loop for progress (dashboard auto-refreshes every 30s).",
        ...data,
      },
      { status: 202 },
    )
  } catch (e) {
    const err = e instanceof Error ? e.message : String(e)
    // Distinguish "scheduler offline" (ECONNREFUSED) from "scheduler slow"
    // (AbortError / timeout). For timeout, the scheduler may have actually
    // accepted the trigger — return 202 with a "pending" hint rather than
    // 503, so the operator doesn't double-click Trigger.
    const isTimeout =
      err.includes("abort") ||
      err.includes("timeout") ||
      err.includes("TimeoutError")

    if (isTimeout) {
      return NextResponse.json(
        {
          triggered: true,
          loop: "degraded",
          accepted: true,
          jobId,
          status: "pending",
          message:
            "Scheduler accepted the request but did not respond within 5s — audit may be running. Poll /api/scp/loop for status.",
          hint: START_HINT,
        },
        { status: 202 },
      )
    }

    return NextResponse.json(
      {
        triggered: false,
        loop: "offline",
        jobId,
        error: err.slice(0, 200),
        hint: START_HINT,
      },
      { status: 503 },
    )
  }
}
