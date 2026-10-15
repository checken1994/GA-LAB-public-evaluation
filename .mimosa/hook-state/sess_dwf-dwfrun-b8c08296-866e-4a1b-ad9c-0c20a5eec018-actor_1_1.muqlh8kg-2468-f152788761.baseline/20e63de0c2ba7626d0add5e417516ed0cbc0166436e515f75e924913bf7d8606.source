import { NextResponse } from "next/server"
import { resolveScpApiBase } from "../../../../../../lib/scp-backend-url"

// [LOCAL-DEV 2026-10-01] Route-level requireAuth gate removed: the browser
// holds no auth credentials, so the gate broke trace lookups from the
// dashboard. middleware.ts gates /api/scp/* fail-closed via the trusted
// reverse-proxy shared secret (x-scp-proxy-secret, 403 on missing/mismatch),
// with an explicit local-dev fallback (SCP_DEV_MODE=1 + loopback Host + XFF
// hops) and a hard 503 otherwise — that is the security boundary for local
// access. Backend credentials are injected server-side (local posture only;
// in the proxy posture caller-sent credentials are forwarded verbatim and
// unauthenticated calls surface the backend's own 401 — the contract pinned
// by tests/T01_boot/test_live_cluster_e2e.py). Note: the backend
// /v3/trace/* guard (verify_admin) accepts Bearer SCP_AUTH_TOKEN_SECRET —
// see scp-service-auth.ts evidence.
// [AUDIT-R2 2026-10-01] injectServiceAuth now RETURNS the caller's
// Authorization/X-SCP-PC-Token verbatim (the old injection-delta contract
// silently dropped caller credentials here → backend 401, PRODUCT_FAIL).
import { injectServiceAuth } from "../../../../../../lib/scp-service-auth"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

export async function GET(
  request: Request,
  { params }: { params: Promise<{ trace_id: string }> }
) {
  try {
    const { trace_id } = await params
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...injectServiceAuth(request),
    }

    const base = resolveScpApiBase()
    const response = await fetch(`${base}/v3/trace/${encodeURIComponent(trace_id)}`, {
      cache: "no-store",
      headers,
      signal: AbortSignal.timeout(10000),
    })
    const data = await response.json().catch(() => ({ error: "Invalid trace response" }))
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Trace retrieval failed" },
      { status: 502 }
    )
  }
}
