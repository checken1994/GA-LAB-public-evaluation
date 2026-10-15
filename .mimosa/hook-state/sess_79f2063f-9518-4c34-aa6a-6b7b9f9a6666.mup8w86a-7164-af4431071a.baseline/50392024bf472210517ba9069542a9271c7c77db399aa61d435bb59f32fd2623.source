import { NextResponse } from "next/server"
import { resolveScpProxyBase } from "../../../../../lib/scp-backend-url"
import { extractCallerAuth } from "../../../../../lib/auth-helper"

export const dynamic = "force-dynamic"
export const revalidate = 0

export async function POST(request: Request) {
  try {
    const auth = extractCallerAuth(request)
    if (!auth.authenticated || auth.errorResponse) {
      return auth.errorResponse || NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const base = resolveScpProxyBase()
    const response = await fetch(`${base}/v3/call/sessions`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: auth.authHeader,
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
