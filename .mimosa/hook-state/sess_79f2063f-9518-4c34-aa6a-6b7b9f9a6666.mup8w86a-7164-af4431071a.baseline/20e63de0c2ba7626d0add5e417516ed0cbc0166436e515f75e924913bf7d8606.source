import { NextResponse } from "next/server"
import { resolveScpApiBase } from "../../../../../../lib/scp-backend-url"

// [LOCAL-DEV 2026-10-01] Route-level requireAuth gate removed: the browser
// holds no auth credentials, so the gate broke trace lookups from the
// dashboard. middleware.ts already restricts /api/scp/* fail-closed to
// loopback hostnames — that is the security boundary for local access.
// Backend credentials are injected server-side instead (browser-sent headers
// still take precedence). Note: the backend /v3/trace/* guard (verify_admin)
// accepts Bearer SCP_AUTH_TOKEN_SECRET — see scp-service-auth.ts evidence.
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
