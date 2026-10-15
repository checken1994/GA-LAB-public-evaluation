import { NextResponse } from "next/server"
// [S6b security sweep] The env-derived base URL is now resolved AND validated
// inside dashboard/src/lib/scp-backend-url.ts (single PEP, no fetch sink
// there); this handler fetches only the validated base it returns.
import { resolveScpProxyBase } from "../../../../lib/scp-backend-url"
// [AUDIT-FIX low-10] Cap conversation_history (per-item + total byte) trước
// khi forward lên backend — trước đây chỉ slice(-8) theo số item, không có
// size cap → payload upstream phình to tùy ý.
import { capConversationHistory } from "../../../../lib/scp-history"
import { injectBackendJwtAuth } from "../../../../lib/scp-service-auth"

export const dynamic = "force-dynamic"
export const revalidate = 0

export async function POST(request: Request) {
  try {
    const body = await request.json() as Record<string, unknown>
    const question = typeof body.question === "string" ? body.question.trim() : ""
    if (!question || question.length > 8000) {
      return NextResponse.json({ error: "Câu hỏi trống hoặc quá dài" }, { status: 400 })
    }
    const imageData = typeof body.image_data === "string" ? body.image_data : null
    if (imageData && imageData.length > 900_000) {
      return NextResponse.json({ error: "Ảnh quá lớn" }, { status: 413 })
    }
    // [AUDIT-FIX low-10] capConversationHistory thay cho slice(-8) thô:
    // max 8 item MỚI NHẤT, mỗi item ≤ 4KB serialized, tổng ≤ 32KB; flag
    // truncated được báo rõ trong payload gửi backend.
    const history = capConversationHistory(body.conversation_history)
    const payload = {
      question,
      domain: typeof body.domain === "string" ? body.domain.slice(0, 80) : "general",
      ai_answer: "",
      source: "desktop_chat",
      session_id: typeof body.session_id === "string" ? body.session_id.slice(0, 120) : undefined,
      conversation_history: history.items,
      conversation_history_truncated: history.truncated,
      image_data: imageData,
    }

    // [S6b security sweep] Resolve + allowlist-validate the backend base
    // BEFORE fetch (single PEP in scp-backend-url.ts). A blocked target throws
    // into the existing catch, so the response shape is unchanged and no
    // request leaves the process.
    //
    // [LOCAL-DEV 2026-10-01 · ask-flow] Route-level requireAuth gate removed
    // (same pattern as the v3 proxy routes, commit ab2aa8e3): the browser
    // holds no auth credentials, so the gate 401'd EVERY dashboard ask from
    // the "00 · Giao tiếp trực tiếp" panel. middleware.ts gates /api/scp/*
    // fail-closed via the trusted reverse-proxy shared secret
    // (x-scp-proxy-secret, 403 on missing/mismatch), with an explicit
    // local-dev fallback (SCP_DEV_MODE=1 + loopback Host + XFF hops) and a
    // hard 503 otherwise — that is the security boundary for local access.
    // Backend /ask accepts only a signed JWT (verify_jwt_token), so the proxy
    // exchanges SCP_ADMIN_KEY at the backend's own /auth/token server-side
    // (local posture only — [AUDIT-R2 2026-10-01] in the proxy posture the
    // caller's own Authorization is forwarded verbatim and nothing is minted);
    // browser-sent Authorization headers still take precedence.
    const base = resolveScpProxyBase()
    let authHeaders = await injectBackendJwtAuth(request, base)
    // requestInit is rebuilt per attempt: the 401 self-heal path swaps in the
    // refreshed Authorization header (reusing a shared object would replay the
    // stale token).
    const buildRequestInit = (headers: Record<string, string>): RequestInit => ({
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json", ...headers },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: AbortSignal.timeout(120_000),
    })
    let response = await fetch(`${base}/ask`, buildRequestInit(authHeaders))
    if (response.status === 401 && authHeaders.Authorization) {
      // Self-heal once: a cached JWT can be stale (backend JWT secret
      // rotation / early expiry). Force a fresh /auth/token exchange and
      // retry exactly once — no loops, the second result is final. When the
      // original attempt sent NO Authorization (exchange failed / no key
      // configured), a re-mint cannot succeed within this request, so the
      // backend 401 passes through without a second /auth/token hit.
      const refreshed = await injectBackendJwtAuth(request, base, { forceRefresh: true })
      if (refreshed.Authorization && refreshed.Authorization !== authHeaders.Authorization) {
        authHeaders = refreshed
        response = await fetch(`${base}/ask`, buildRequestInit(authHeaders))
      }
    }
    const text = await response.text()
    let data: unknown = {}
    try { data = JSON.parse(text) } catch { data = { error: text.slice(0, 500) } }
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Không kết nối được SCP"
    return NextResponse.json({ error: message.slice(0, 300) }, { status: 502 })
  }
}
