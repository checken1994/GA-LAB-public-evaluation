import { NextResponse } from "next/server"
import { resolveScpProxyBase } from "../../../../lib/scp-backend-url"
import { extractCallerAuth } from "../../../../lib/auth-helper"

export const dynamic = "force-dynamic"
export const revalidate = 0

export async function POST(request: Request) {
  try {
    const auth = extractCallerAuth(request)
    if (!auth.authenticated || auth.errorResponse) {
      return auth.errorResponse || NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = await request.json() as Record<string, unknown>
    const audioBase64 = typeof body.audio_base64 === "string" ? body.audio_base64 : ""
    if (!audioBase64) return NextResponse.json({ error: "Chưa nhận được audio" }, { status: 400 })
    if (audioBase64.length > 8_000_000) return NextResponse.json({ error: "Audio quá lớn" }, { status: 413 })

    // [S6b security sweep] Resolve + allowlist-validate the backend base
    const base = resolveScpProxyBase()
    const response = await fetch(`${base}/v104/voice/check`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: auth.authHeader,
      },
      body: JSON.stringify({ audio_base64: audioBase64 }),
      cache: "no-store",
      signal: AbortSignal.timeout(120_000),
    })
    const text = await response.text()
    let data: unknown = {}
    try { data = JSON.parse(text) } catch { data = { error: text.slice(0, 500) } }
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Không kết nối được SCP voice detector"
    return NextResponse.json({ error: message.slice(0, 300) }, { status: 502 })
  }
}
