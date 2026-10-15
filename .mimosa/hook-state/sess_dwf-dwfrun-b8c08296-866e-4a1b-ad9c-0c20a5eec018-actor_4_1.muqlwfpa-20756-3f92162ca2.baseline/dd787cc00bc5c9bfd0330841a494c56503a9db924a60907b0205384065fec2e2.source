import { NextResponse } from "next/server"
// [S6b security sweep] Base URL is resolved AND validated in
// scp-backend-url.ts (single PEP, no fetch sink there); this handler fetches
// only the validated base it returns.
import { resolveScpApiBase } from "../../../../../../lib/scp-backend-url"
// [LOCAL-DEV 2026-10-01] Inject backend service tokens (X-SCP-PC-Token /
// Authorization) from the repo root .env for proxied calls; caller-sent
// headers are forwarded verbatim and take precedence. middleware.ts gates
// /api/scp/* fail-closed via the trusted reverse-proxy shared secret
// (x-scp-proxy-secret, 403 on missing/mismatch), with an explicit local-dev
// fallback (SCP_DEV_MODE=1 + loopback Host + XFF hops) and a hard 503
// otherwise — injection only serves the local posture.
import { injectServiceAuth } from "../../../../../../lib/scp-service-auth"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

export async function GET(request: Request) {
  try {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...injectServiceAuth(request),
    }
    // [S6b security sweep] Resolve + allowlist-validate the backend base
    // BEFORE fetch (single PEP in scp-backend-url.ts). A blocked target
    // throws into the existing catch — offline shape unchanged.
    const base = resolveScpApiBase()
    const response = await fetch(`${base}/v3/web/status`, { cache: "no-store", headers, signal: AbortSignal.timeout(5000) })
    if (response.status === 403 || response.status === 401) {
      return NextResponse.json({ navigator: { available: false }, orchestrator: { available: false }, reason: "Chưa cấu hình token hoặc chưa kích hoạt" }, { status: 200 })
    }
    const data = await response.json().catch(() => ({ error: "Invalid web control response" }))
    return NextResponse.json(data, { status: response.ok ? 200 : response.status })
  } catch (error) {
    return NextResponse.json({ navigator: { available: false }, orchestrator: { available: false }, error: error instanceof Error ? error.message : "Web control unavailable" }, { status: 200 })
  }
}
