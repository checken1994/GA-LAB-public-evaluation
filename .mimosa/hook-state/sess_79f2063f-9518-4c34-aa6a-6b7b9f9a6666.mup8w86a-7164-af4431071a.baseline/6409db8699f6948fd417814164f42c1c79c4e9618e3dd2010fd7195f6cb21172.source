import { NextResponse } from "next/server"
// [S6b security sweep] Base URL is resolved AND validated in
// scp-backend-url.ts (single PEP, no fetch sink there); this handler fetches
// only the validated base it returns.
import { resolveScpApiBase } from "../../../../../../lib/scp-backend-url"

// [LOCAL-DEV 2026-10-01] Route-level requireAuth gate removed: the browser
// holds no auth credentials, so the gate broke the dashboard's web search.
// middleware.ts already restricts /api/scp/* fail-closed to loopback
// hostnames — that is the security boundary for local access. Backend
// credentials are injected server-side instead (browser-sent headers still
// take precedence).
import { injectServiceAuth } from "../../../../../../lib/scp-service-auth"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}))
    const base = resolveScpApiBase()
    const headers: Record<string, string> = {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...injectServiceAuth(request),
    }
    const response = await fetch(`${base}/v3/web/search`, {
      method: "POST",
      cache: "no-store",
      headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(30000),
    })
    const data = await response.json().catch(() => ({ error: "Invalid search response" }))
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    return NextResponse.json({ success: false, error: error instanceof Error ? error.message : "Internet search unavailable", results: [] }, { status: 503 })
  }
}
