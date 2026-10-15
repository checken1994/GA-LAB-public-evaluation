import { NextResponse } from "next/server"
// [S6b security sweep] Base URL is resolved AND validated in
// scp-backend-url.ts (single PEP, no fetch sink there); this handler fetches
// only the validated base it returns.
import { resolveScpApiBase } from "../../../../../../../lib/scp-backend-url"

// [LOCAL-DEV 2026-10-01] Inject backend service tokens (X-SCP-PC-Token) from
// the repo root .env for proxied calls; caller-sent headers are forwarded
// verbatim and take precedence. middleware.ts gates /api/scp/* fail-closed
// via the trusted reverse-proxy shared secret (x-scp-proxy-secret, 403 on
// missing/mismatch), with an explicit local-dev fallback (SCP_DEV_MODE=1 +
// loopback Host + XFF hops) and a hard 503 otherwise. Without a usable
// credential the backend answered 403 and the planner card rendered
// "offline".
import { injectServiceAuth } from "../../../../../../../lib/scp-service-auth"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

export async function GET(request: Request) {
  try {
    // [S6b security sweep] Resolve + allowlist-validate the backend base
    // BEFORE fetch (single PEP in scp-backend-url.ts). A blocked target
    // throws into the existing catch — offline shape unchanged.
    const base = resolveScpApiBase()
    const response = await fetch(`${base}/v3/hands/planner/status`, {
      cache: "no-store",
      headers: { Accept: "application/json", ...injectServiceAuth(request) },
      signal: AbortSignal.timeout(5000),
    })
    // [LOCAL-DEV 2026-10-01] Map backend 401/403 to the same offline shape as
    // the sibling v3 status routes (fail-closed fallback for the case where
    // no token is configured) instead of forwarding the raw 403.
    if (response.status === 403 || response.status === 401) {
      return NextResponse.json(
        { version: "3.7", planner: "offline", planCount: 0, activePlan: null, states: {}, reason: "Chưa cấu hình token hoặc chưa kích hoạt" },
        { status: 200 }
      )
    }
    const data = await response.json()
    return NextResponse.json(data, { status: response.ok ? 200 : response.status })
  } catch (error) {
    return NextResponse.json({ version: "3.7", planner: "offline", planCount: 0, activePlan: null, states: {}, error: error instanceof Error ? error.message : "Planner offline" }, { status: 200 })
  }
}
