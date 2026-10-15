/**
 * Server-side service auth injection for dashboard → SCP backend proxies.
 *
 * [LOCAL-DEV 2026-10-01] The dashboard's Next.js proxy routes previously
 * forwarded only browser-sent auth headers to the SCP backend. The browser
 * holds no `Authorization` / `X-SCP-PC-Token` credentials, so every proxied
 * call reached the backend unauthenticated (401/403) and the V3.1/V3.5
 * control-plane cards rendered "offline". The dashboard is a trusted local
 * proxy: `src/middleware.ts` gates every /api/scp/* route fail-closed via the
 * trusted reverse-proxy shared secret (`x-scp-proxy-secret`, 403 on
 * missing/mismatch), with an explicit local-dev fallback
 * (`SCP_DEV_MODE=1` + secret unset: loopback-host + XFF-hop validation, and a
 * per-request `X-SCP-Dev-Mode-Warning` response header) and a hard 503 when
 * neither is configured — so injection below can only serve requests that
 * already passed that boundary.
 *
 * [AUDIT-R2 2026-10-01] Caller credentials are now FORWARDED VERBATIM.
 * Earlier the helpers returned only the injection delta, so a route building
 * its outgoing headers as `{Accept} ∪ injectServiceAuth(request)` silently
 * DROPPED an Authorization/X-SCP-PC-Token the caller had sent (the backend
 * then 401'd — caught by tests/T01_boot/test_live_cluster_e2e.py on the
 * trace proxy). The helpers now return the complete outgoing credential set:
 * caller-sent headers first, injected tokens only where still missing.
 *
 * Contract:
 * - Token values are read from the repo root `.env` (same `findScpRoot`
 *   pattern as the activity route) and cached for 30 seconds. Shell
 *   (process env) values override file values.
 * - Caller-sent credentials always take precedence and are forwarded
 *   verbatim; injection only fills headers the caller did NOT already send.
 * - [AUDIT-R2 2026-10-01] Injection is posture-gated: in the trusted
 *   reverse-proxy posture (`SCP_DASHBOARD_PROXY_SECRET` set) the proxy
 *   serves remote users who must present their OWN credentials —
 *   auto-injecting the operator's backend admin tokens for any caller that
 *   passed the gate would be an auth oracle / privilege escalation. The
 *   live cluster E2E pins this: an unauthenticated proxied call must reach
 *   the backend and surface its own 401. Injection therefore runs only when
 *   no proxy secret is configured (local posture; the middleware then
 *   restricts access to the explicit dev-mode loopback fallback or 503s).
 * - Secrets are never logged, never echoed into errors, and never returned —
 *   only mapped into outbound header names.
 * - [LOCAL-DEV 2026-10-01 · ask-flow] Backend endpoints requiring a SIGNED
 *   JWT (/ask via verify_jwt_token) are served by `injectBackendJwtAuth`:
 *   the proxy exchanges SCP_ADMIN_KEY at the backend's own /auth/token and
 *   caches the short-lived JWT (see below). No JWT is minted locally.
 */
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"

const ENV_CACHE_TTL_MS = 30_000

const PC_TOKEN_KEY = "SCP_PC_CONTROLLER_TOKEN"

// [AUDIT-R2 2026-10-01] The loop-scheduler mini-service (127.0.0.1:3030)
// authorizes POST /trigger|/pause|/resume against its own
// SCP_SCHEDULER_ADMIN_TOKEN (Bearer or x-scp-admin-token); with the token
// unset it answers 503 "scheduler admin auth not configured" (fail-closed).
const SCHEDULER_TOKEN_KEY = "SCP_SCHEDULER_ADMIN_TOKEN"

/**
 * [AUDIT-R2 2026-10-01] Posture gate for server-side credential injection.
 * When the dashboard runs behind the trusted reverse proxy
 * (`SCP_DASHBOARD_PROXY_SECRET` set on the Next.js process) the caller pool
 * is remote users: the proxy must forward THEIR credentials verbatim and
 * never attach the operator's own backend tokens — that would turn the
 * dashboard into an auth oracle (any gated caller gets admin backend access).
 * With the secret unset the middleware only lets through the explicit
 * local-dev loopback fallback (or 503s), which is the posture the
 * [LOCAL-DEV 2026-10-01] injection was built for.
 */
function isTrustedProxyPosture(): boolean {
  return (process.env.SCP_DASHBOARD_PROXY_SECRET?.trim() ?? "").length > 0
}

// [Evidence 2026-10-01] Backend auth acceptance, probed live against
// 127.0.0.1:8000 (tools probes, no secrets printed):
// - /v3/pc/*, /v3/hands/*, /v3/web/* (`_guard`) compare `X-SCP-PC-Token`
//   against SCP_PC_CONTROLLER_TOKEN → 200 with the token, 403 without.
// - /v3/trace/* (`verify_admin`, scp/security/auth.py) compares the Bearer
//   token against SCP_AUTH_TOKEN_SECRET / SCP_AUTH_PASSWORD only: a live
//   probe showed `Bearer <SCP_ADMIN_KEY>` → 401 while
//   `Bearer <SCP_AUTH_TOKEN_SECRET>` passed (404 = trace not found, i.e.
//   auth accepted). SCP_ADMIN_KEY remains as a fallback (it is accepted by
//   the api-key path `verify_api_key` in scp/security/jwt_guard.py) but
//   AUTH_TOKEN_SECRET wins for the Authorization header.
const BEARER_KEY_PRIORITY = ["SCP_AUTH_TOKEN_SECRET", "SCP_ADMIN_KEY"] as const

// [LOCAL-DEV 2026-10-01 · ask-flow] Backend /ask accepts ONLY a signed JWT
// (scp/security/jwt_guard.py verify_jwt_token — HS256 against the backend's
// JWT signing secret). Static Bearer tokens (SCP_AUTH_TOKEN_SECRET /
// SCP_ADMIN_KEY) are rejected there with 401 — they only satisfy verify_admin
// on /v3/* routes. The backend's documented exchange is POST /auth/token
// {admin_key} → {access_token} (scp/api_server.py /auth/token, keyed against
// SCP_ADMIN_KEY, rate-limited 5/minute). The proxy therefore exchanges the
// operator's own SCP_ADMIN_KEY for a short-lived JWT server-side and caches
// it until just before expiry. This is NOT self-minting: the backend issues
// and signs the token and enforces the admin key; the dashboard never holds
// the signing secret.
const ADMIN_EXCHANGE_KEY = "SCP_ADMIN_KEY"
const JWT_REFRESH_MARGIN_MS = 120_000
const JWT_DEFAULT_TTL_MS = 3_600_000
const JWT_MINT_TIMEOUT_MS = 10_000

interface CachedJwt {
  token: string
  expiresAtMs: number
}
let jwtCache: CachedJwt | null = null

/**
 * Client-side freshness read of the JWT `exp` claim. The signature is NOT
 * verified here (the backend verifies it on every request) — this only
 * prevents replaying a provably expired token. Unparsable → 0 → treated as
 * expired → re-mint (fail-closed).
 */
function jwtExpiryMs(token: string): number {
  try {
    const payloadPart = token.split(".")[1] ?? ""
    const payload = JSON.parse(Buffer.from(payloadPart, "base64url").toString("utf-8")) as Record<string, unknown>
    return typeof payload.exp === "number" && payload.exp > 0 ? payload.exp * 1000 : 0
  } catch {
    return 0
  }
}

/**
 * Exchanges SCP_ADMIN_KEY for a backend JWT via POST /auth/token.
 * Returns null on any failure (non-2xx, malformed body, network error) —
 * callers then send NO Authorization header so the backend's own 401/403
 * surfaces instead of a forged answer. Secrets are never logged.
 */
async function mintBackendJwt(backendBase: string, adminKey: string): Promise<string | null> {
  try {
    const response = await fetch(`${backendBase}/auth/token`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ admin_key: adminKey }),
      cache: "no-store",
      signal: AbortSignal.timeout(JWT_MINT_TIMEOUT_MS),
    })
    if (!response.ok) return null
    const data = (await response.json().catch(() => null)) as { access_token?: unknown } | null
    const token = typeof data?.access_token === "string" ? data.access_token.trim() : ""
    return token.length > 0 ? token : null
  } catch {
    return null
  }
}

/**
 * [LOCAL-DEV 2026-10-01 · ask-flow] Server-side JWT auth for proxy routes
 * whose backend endpoint requires a signed JWT (currently /ask). Mirrors the
 * injectServiceAuth contract:
 * - Caller-sent Authorization headers always take precedence (forwarded
 *   verbatim, no injection).
 * - [AUDIT-R2 2026-10-01] In the trusted-proxy posture (proxy secret set)
 *   nothing is minted or attached — the backend's own 401 surfaces.
 * - Otherwise a cached backend JWT is used; it is (re)minted via the
 *   backend's /auth/token exchange when missing, expired (with a 120s
 *   refresh margin), or when `forceRefresh` is set (used by callers to
 *   self-heal once after a backend 401).
 * - Fail-closed: without a configured SCP_ADMIN_KEY or on any mint failure
 *   the returned headers are empty, so the backend's own auth error reaches
 *   the dashboard instead of manufactured success.
 */
export async function injectBackendJwtAuth(
  request: Request,
  backendBase: string,
  options: { forceRefresh?: boolean } = {},
): Promise<Record<string, string>> {
  const callerAuth = request.headers.get("authorization")
  if (callerAuth && callerAuth.trim()) {
    return { Authorization: callerAuth.trim() }
  }

  // [AUDIT-R2 2026-10-01] Trusted-proxy posture: never mint/attach the
  // operator's credentials for a proxied caller — the backend's own 401
  // surfaces instead (fail-closed, same rationale as injectServiceAuth).
  if (isTrustedProxyPosture()) return {}

  const now = Date.now()
  if (
    !options.forceRefresh &&
    jwtCache &&
    jwtCache.expiresAtMs - JWT_REFRESH_MARGIN_MS > now
  ) {
    return { Authorization: `Bearer ${jwtCache.token}` }
  }

  const adminKey = loadServiceAuthValues()[ADMIN_EXCHANGE_KEY]
  if (!adminKey) return {}

  const token = await mintBackendJwt(backendBase, adminKey)
  if (!token) return {}

  const expMs = jwtExpiryMs(token)
  jwtCache = { token, expiresAtMs: expMs > now ? expMs : now + JWT_DEFAULT_TTL_MS }
  return { Authorization: `Bearer ${token}` }
}

interface ServiceAuthValues {
  values: Partial<Record<string, string>>
  loadedAt: number
}
let envCache: ServiceAuthValues | null = null

function findScpRoot(): string {
  if (process.env.SCP_ROOT && existsSync(process.env.SCP_ROOT)) return process.env.SCP_ROOT
  let cur = process.cwd()
  for (let i = 0; i < 4; i++) {
    if (existsSync(path.join(cur, "data")) && (existsSync(path.join(cur, "spec")) || existsSync(path.join(cur, "scp")))) {
      return cur
    }
    cur = path.resolve(cur, "..")
  }
  return "D:\\scp"
}

function parseEnvFile(content: string): Record<string, string> {
  const values: Record<string, string> = {}
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line || line.startsWith("#")) continue
    const eq = line.indexOf("=")
    if (eq <= 0) continue
    const key = line.slice(0, eq).trim()
    let value = line.slice(eq + 1).trim()
    if (
      value.length >= 2 &&
      ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'")))
    ) {
      value = value.slice(1, -1)
    }
    if (key) values[key] = value
  }
  return values
}

function loadServiceAuthValues(): Partial<Record<string, string>> {
  const now = Date.now()
  if (envCache && now - envCache.loadedAt < ENV_CACHE_TTL_MS) return envCache.values

  const values: Partial<Record<string, string>> = {}
  const wanted: readonly string[] = [...BEARER_KEY_PRIORITY, PC_TOKEN_KEY, SCHEDULER_TOKEN_KEY]
  try {
    const envPath = path.join(findScpRoot(), ".env")
    if (existsSync(envPath)) {
      const parsed = parseEnvFile(readFileSync(envPath, "utf8"))
      for (const key of wanted) {
        const value = parsed[key]?.trim()
        if (value) values[key] = value
      }
    }
  } catch {
    // Fail closed to "no injection" rather than a wrong injection: the
    // proxied call then surfaces the backend's own 401/403 offline shape.
  }

  // Shell env overrides file values.
  for (const key of wanted) {
    const value = process.env[key]?.trim()
    if (value) values[key] = value
  }

  envCache = { values, loadedAt: now }
  return values
}

/**
 * Complete outgoing credential header set for the backend proxy fetch.
 *
 * [AUDIT-R2 2026-10-01] Behavior (supersedes the "injection delta only"
 * contract, which made routes like the trace proxy drop caller-sent
 * credentials — PRODUCT_FAIL in tests/T01_boot/test_live_cluster_e2e.py):
 * 1. Caller-sent `Authorization` / `X-SCP-PC-Token` are forwarded verbatim
 *    (precedence — the caller's credential, if any, is authoritative).
 * 2. Outside the trusted-proxy posture, missing credentials are filled from
 *    the operator's own configured tokens (local-dev injection).
 * 3. In the trusted-proxy posture NOTHING is injected: an unauthenticated
 *    caller reaches the backend unauthenticated and its own 401/403 surfaces
 *    (fail-closed; pinned by the live cluster E2E).
 */
export function injectServiceAuth(request: Request): Record<string, string> {
  const headers: Record<string, string> = {}

  const callerAuth = request.headers.get("authorization")?.trim()
  if (callerAuth) headers["Authorization"] = callerAuth
  const callerPcToken = request.headers.get("x-scp-pc-token")?.trim()
  if (callerPcToken) headers["X-SCP-PC-Token"] = callerPcToken

  if (isTrustedProxyPosture()) return headers

  const values = loadServiceAuthValues()
  if (!callerPcToken) {
    const pcToken = values[PC_TOKEN_KEY]
    if (pcToken) headers["X-SCP-PC-Token"] = pcToken
  }
  if (!callerAuth) {
    for (const key of BEARER_KEY_PRIORITY) {
      const value = values[key]
      if (value) {
        headers["Authorization"] = `Bearer ${value}`
        break
      }
    }
  }

  return headers
}

/**
 * [AUDIT-R2 2026-10-01] Outgoing Authorization for the loop-scheduler
 * mini-service (POST /trigger). Same contract as `injectServiceAuth`:
 * caller-sent Authorization is forwarded verbatim; otherwise the operator's
 * own SCP_SCHEDULER_ADMIN_TOKEN is injected — local posture only. With no
 * token available anywhere, no Authorization is sent and the scheduler's own
 * 401/503 surfaces (fail-closed, never a forged success).
 */
export function injectSchedulerAuth(request: Request): Record<string, string> {
  const callerAuth = request.headers.get("authorization")?.trim()
  if (callerAuth) return { Authorization: callerAuth }
  if (isTrustedProxyPosture()) return {}

  const token = loadServiceAuthValues()[SCHEDULER_TOKEN_KEY]
  return token ? { Authorization: `Bearer ${token}` } : {}
}
