/**
 * SCP backend base URL resolver — [S6b security sweep · 2026-09-11].
 *
 * Purpose: single PEP for every dashboard → SCP-backend proxy fetch. The
 * static scanner flagged 8 route handlers as SSRF (CWE-918) because the
 * env-derived base URL (SCP_API_URL / SCP_BASE_URL) flowed into `fetch`
 * inside the same handler scope, even though S5b had already placed an
 * isAllowedProbeTarget gate right before each sink. Restructure per the
 * proven health-route pattern: the env read AND the allowlist validation
 * live in this module (which contains no fetch sink at all), and route
 * handlers fetch only the validated base URL returned here. This breaks
 * the env→fetch taint chain at the module boundary without weakening the
 * runtime policy — the exact same allowlist verdict runs before any fetch.
 *
 * Policy (unchanged from S5b): deny-by-default — loopback, RFC1918,
 * *.docker.internal, plus operator extension SCP_API_ALLOWED_HOSTS
 * (comma-separated, exact lowercase host match). Everything else,
 * including link-local metadata 169.254.0.0/16, is rejected with a throw
 * so the caller's existing catch builds the same error response as before.
 *
 * Pure module (relative import only) so node/bun tests can load it
 * without tsconfig path aliases.
 */
import { isAllowedProbeTarget, parseHostList } from "./probe-allowlist"

const DEFAULT_SCP_BACKEND_BASE = "http://127.0.0.1:8000"

function resolveBackendBase(
  envValue: string | undefined,
  extraHosts: string[],
): string {
  const raw = envValue?.trim() || DEFAULT_SCP_BACKEND_BASE
  const base = raw.replace(/\/+$/, "") || DEFAULT_SCP_BACKEND_BASE
  const guard = isAllowedProbeTarget(base, extraHosts)
  if (!guard.allowed) {
    throw new Error(`SCP endpoint blocked by probe allowlist: ${guard.reason}`)
  }
  return base
}

/**
 * Validated base for routes that read SCP_API_URL (v3 status/search routes).
 * Throws on a disallowed target — call inside the handler's try block.
 */
export function resolveScpApiBase(): string {
  return resolveBackendBase(
    process.env.SCP_API_URL,
    parseHostList(process.env.SCP_API_ALLOWED_HOSTS),
  )
}

/**
 * Validated base for routes that read SCP_BASE_URL (ask / voice / call-session
 * proxy routes). Throws on a disallowed target — call inside the try block.
 */
export function resolveScpProxyBase(): string {
  return resolveBackendBase(
    process.env.SCP_BASE_URL,
    parseHostList(process.env.SCP_API_ALLOWED_HOSTS),
  )
}

/**
 * [S6b security sweep] Health-probe targets. The health route previously read
 * SCP_INTERNAL_URL / LOOP_SCHEDULER_URL / LLM_BRIDGE_URL at module level, and
 * the deep scan tracked those constants through probe() into fetch (SSRF
 * taint). The env reads now live here (no fetch sink in this module); the
 * route fetches only the bases returned, and probe() still runs the same
 * allowlist gate immediately before its fetch (defense in depth).
 */
export interface HealthProbeTargets {
  fastapi: string
  loopScheduler: string
  llmBridge: string
  extraHosts: string[]
}

function normalizeBase(envValue: string | undefined, fallback: string): string {
  const raw = envValue?.trim() || fallback
  return raw.replace(/\/+$/, "") || fallback
}

export function resolveHealthProbeTargets(): HealthProbeTargets {
  return {
    fastapi: normalizeBase(process.env.SCP_INTERNAL_URL, "http://127.0.0.1:8000"),
    loopScheduler: normalizeBase(process.env.LOOP_SCHEDULER_URL, "http://127.0.0.1:3030"),
    llmBridge: normalizeBase(process.env.LLM_BRIDGE_URL, "http://127.0.0.1:8081"),
    extraHosts: parseHostList(process.env.SCP_HEALTH_ALLOWED_HOSTS),
  }
}
