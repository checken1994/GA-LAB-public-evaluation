import { NextResponse } from "next/server"
// [S6b security sweep] Base URL is resolved AND validated in
// scp-backend-url.ts (single PEP, no fetch sink there); this handler fetches
// only the validated base it returns.
import { resolveScpApiBase } from "../../../../../../lib/scp-backend-url"
// [LOCAL-DEV 2026-10-01] Inject backend service tokens (X-SCP-PC-Token /
// Authorization) from the repo root .env for proxied calls; browser-sent
// headers take precedence. middleware.ts already restricts /api/scp/* to
// loopback hostnames, so this injection only serves the trusted local proxy.
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
    const response = await fetch(`${base}/v3/pc/status`, { cache: "no-store", headers, signal: AbortSignal.timeout(5000) })
    if (response.status === 403 || response.status === 401) {
      return NextResponse.json({ controller: "offline", reason: "Chưa cấu hình token hoặc chưa kích hoạt" }, { status: 200 })
    }
    const data = await response.json().catch(() => ({ controller: "offline", error: "Invalid PC Controller response" }))
    return NextResponse.json(data, { status: response.ok ? 200 : response.status })
  } catch (error) {
    return NextResponse.json({ controller: "offline", error: error instanceof Error ? error.message : "PC Controller unavailable" }, { status: 503 })
  }
}
