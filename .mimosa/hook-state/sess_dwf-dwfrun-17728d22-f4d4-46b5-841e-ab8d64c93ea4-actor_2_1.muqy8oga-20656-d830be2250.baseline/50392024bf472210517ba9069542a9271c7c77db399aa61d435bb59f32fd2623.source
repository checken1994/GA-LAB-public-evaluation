import { NextResponse } from "next/server"
// [S6b security sweep] Base URL is resolved AND validated in
// scp-backend-url.ts (single PEP, no fetch sink there); this handler fetches
// only the validated base it returns.
import { resolveScpProxyBase } from "../../../../../lib/scp-backend-url"
// [AUDIT-R2 2026-10-01 · H-1] Route-level extractCallerAuth gate removed:
// the browser holds no auth credentials, so the gate 401'd EVERY call-session
// request (probe T1 evidence). middleware.ts remains the boundary
// (trusted-proxy secret 403 / dev-mode loopback+XFF fallback / 503
// fail-closed). Backend POST /v3/call/sessions requires verify_admin PLUS the
// PC-controller guard, so the proxy forwards caller credentials verbatim and
// injects X-SCP-PC-Token + Bearer only in the local (no proxy secret) posture.
import { injectServiceAuth } from "../../../../../lib/scp-service-auth"

export const dynamic = "force-dynamic"
export const revalidate = 0

export async function POST(request: Request) {
  try {
    const base = resolveScpProxyBase()
    const response = await fetch(`${base}/v3/call/sessions`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        ...injectServiceAuth(request),
      },
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    })
    const text = await response.text()
    let data: unknown = {}
    try { data = JSON.parse(text) } catch { data = { error: text.slice(0, 300) } }
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message.slice(0, 300) : "Không kết nối được SCP" }, { status: 502 })
  }
}
