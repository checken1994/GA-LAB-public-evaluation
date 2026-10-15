/**
 * API /api/scp/health — composite health check across all 3 SCP subsystems.
 *
 * Makes the dashboard a CONTROL PANEL (not just a static report).
 *
 * [Task 1-A · Fix 4-d-010] Previously this endpoint ONLY probed the FastAPI
 * Python backend on port 8000. So "SCP online" was a false-green whenever
 * the loop-scheduler (port 3030) or the llm-bridge (port 11434) was dead
 * — even though SCP's autofix engine depends on the LLM bridge. Now this
 * endpoint probes all 3 services in parallel with 1s timeouts and returns
 * a composite status. DNA #19 (observation gap closed) + #22 (PASS ≠ TRUE:
 * "online" no longer claimed from a single-subsystem probe) + #26 (reality
 * test).
 *
 * Backward compat: the legacy `scp: "online"|"degraded"|"offline"` field is
 * preserved for existing consumers (scp-control-panel.tsx). It is derived
 * from the new composite: "online" only if all 3 services ok.
 *
 * SCP started via:    SCP_PORT=8000 python -m scp
 * Scheduler started via: bun run mini-services/loop-scheduler
 * LLM bridge started via: bun run mini-services/llm-bridge
 */
import { NextRequest, NextResponse } from "next/server"
// [S6b security sweep] The env-derived probe targets are resolved AND
// allowlist-validated in dashboard/src/lib/scp-backend-url.ts (no fetch sink
// there); this route fetches only the bases that helper returns, and probe()
// still runs the same allowlist gate immediately before its fetch.
import { resolveHealthProbeTargets } from "../../../../lib/scp-backend-url"
// PEP at the sink (relative import so the T03 sweep test can load this
// module under plain node — no tsconfig paths there).
import { isAllowedProbeTarget } from "../../../../lib/probe-allowlist"


const START_HINTS = {
  fastapi: "Run: SCP_PORT=8000 python -m scp (in your scp folder)",
  loopScheduler: "Run: bun run mini-services/loop-scheduler (in project root)",
  llmBridge: "Run: bun run mini-services/llm-bridge (in project root)",
}

// [S5 security sweep] Extra probe hosts explicitly approved by the operator
// (comma-separated). Used as an extension of the internal-network allowlist
// in @/lib/probe-allowlist — e.g. "scp-api,scheduler.internal".
const EXTRA_PROBE_HOSTS = (process.env.SCP_HEALTH_ALLOWED_HOSTS ?? "")
  .split(",")
  .map((h) => h.trim().toLowerCase())
  .filter(Boolean)

interface ServiceHealth {
  ok: boolean
  latencyMs: number | null
  status?: number
  error?: string
  hint?: string
}

/**
 * Probe one HTTP endpoint with a hard timeout. Returns the latency in ms
 * if the response was ok, or `{ ok: false }` with the error otherwise.
 * DNA #7: fail-open — never throws.
 *
 * [S5 security sweep] SSRF gate (CWE-918): before any fetch the target is
 * validated against the probe allowlist (loopback/private/docker-internal +
 * operator extension from SCP_HEALTH_ALLOWED_HOSTS, resolved by
 * scp-backend-url.ts). A blocked target is reported as a service that is
 * down — no request leaves the process. This is the PEP placed immediately
 * before the fetch sink, so all probe call sites below are covered by the
 * same gate.
 */
async function probe(
  url: string,
  extraHosts: string[],
  timeoutMs = 1000,
): Promise<ServiceHealth> {
  const guard = isAllowedProbeTarget(url, extraHosts)
  if (!guard.allowed) {
    return {
      ok: false,
      latencyMs: 0,
      error: `probe blocked by allowlist: ${guard.reason}`.slice(0, 200),
    }
  }
  const t0 = Date.now()
  try {
    const res = await fetch(url, {
      signal: AbortSignal.timeout(timeoutMs),
      headers: { Accept: "application/json" },
      cache: "no-store",
    })
    const latencyMs = Date.now() - t0
    if (res.ok) {
      return { ok: true, latencyMs, status: res.status }
    }
    return { ok: false, latencyMs, status: res.status }
  } catch (e) {
    const latencyMs = Date.now() - t0
    const err = e instanceof Error ? e.message : String(e)
    return { ok: false, latencyMs, error: err.slice(0, 200) }
  }
}

export async function GET(request: NextRequest) {
  const _url = request.url
  const checkedAt = new Date().toISOString()

  // [S6b security sweep] Env-derived bases resolved + validated in
  // scp-backend-url.ts — no environment token remains in this file's
  // fetch dataflow.
  const targets = resolveHealthProbeTargets()

  // Probe all 3 services in parallel. DNA #19: cover observation gaps.
  // Promise.allSettled so one slow service can't block the others.
  const [fastapiResult, loopResult, llmResult] = await Promise.allSettled([
    probe(`${targets.fastapi}/health`, targets.extraHosts),
    // loop-scheduler exposes /healthz per mini-services/loop-scheduler/index.ts
    // (falls back to "/" if 404 — see below).
    probe(`${targets.loopScheduler}/healthz`, targets.extraHosts).then(async (h) => {
      if (h.ok || h.status !== 404) return h
      // Retry with "/" if /healthz is not implemented.
      return probe(`${targets.loopScheduler}/`, targets.extraHosts)
    }),
    // llm-bridge (Ollama-compatible API) exposes /api/tags — list of installed models.
    probe(`${targets.llmBridge}/api/tags`, targets.extraHosts),
  ])

  const fastapi: ServiceHealth =
    fastapiResult.status === "fulfilled"
      ? { ...fastapiResult.value, hint: START_HINTS.fastapi }
      : { ok: false, latencyMs: null, error: "probe rejected", hint: START_HINTS.fastapi }
  const loopScheduler: ServiceHealth =
    loopResult.status === "fulfilled"
      ? { ...loopResult.value, hint: START_HINTS.loopScheduler }
      : { ok: false, latencyMs: null, error: "probe rejected", hint: START_HINTS.loopScheduler }
  const llmBridge: ServiceHealth =
    llmResult.status === "fulfilled"
      ? { ...llmResult.value, hint: START_HINTS.llmBridge }
      : { ok: false, latencyMs: null, error: "probe rejected", hint: START_HINTS.llmBridge }

  const overall = fastapi.ok && loopScheduler.ok && llmBridge.ok

  // Backward-compat derivation: legacy `scp` field that the control panel
  // already consumes. "online" only if FastAPI responds 200.
  // "degraded" if FastAPI is up but a sibling service is down.
  // "offline" if FastAPI itself is unreachable.
  const scp: "online" | "degraded" | "offline" = fastapi.ok
    ? (overall ? "online" : "degraded")
    : "offline"

  const httpStatus = overall ? 200 : fastapi.ok ? 200 : 503

  return NextResponse.json(
    {
      // Legacy fields (backward compat for scp-control-panel.tsx).
      scp,
      hint: scp === "online" ? null : START_HINTS.fastapi,
      // Composite fields (new in Task 1-A — Fix 4-d-010).
      overall,
      fastapi,
      loopScheduler,
      llmBridge,
      checkedAt,
    },
    { status: httpStatus },
  )
}
