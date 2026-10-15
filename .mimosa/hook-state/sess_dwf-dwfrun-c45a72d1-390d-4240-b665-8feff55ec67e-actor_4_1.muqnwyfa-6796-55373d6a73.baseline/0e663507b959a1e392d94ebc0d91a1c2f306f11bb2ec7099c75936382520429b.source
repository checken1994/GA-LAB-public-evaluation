import { NextResponse } from "next/server"
// [S6b security sweep] Base URL is resolved AND validated in
// scp-backend-url.ts (single PEP, no fetch sink there); this handler fetches
// only the validated base it returns.
import { resolveScpProxyBase } from "../../../../lib/scp-backend-url"
// [AUDIT-R2 2026-10-01 · H-1] Route-level extractCallerAuth gate removed:
// the browser holds no auth credentials, so the gate 401'd EVERY dashboard
// voice probe (probe T1 evidence). middleware.ts remains the boundary
// (trusted-proxy secret 403 / dev-mode loopback+XFF fallback / 503
// fail-closed). Backend /v104/voice/check requires verify_admin; the proxy
// forwards caller-sent credentials verbatim and injects the operator's own
// Bearer token only in the local (no proxy secret) posture.
import { injectServiceAuth } from "../../../../lib/scp-service-auth"

export const dynamic = "force-dynamic"
export const revalidate = 0

export async function POST(request: Request) {
  try {
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
        ...injectServiceAuth(request),
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
