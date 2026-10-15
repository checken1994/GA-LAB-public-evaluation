/**
 * LLM egress guard — SSRF gate for llm-bridge outbound fetches.
 *
 * [S5 security sweep · 2026-09-10] The static scan flagged fetchWithTimeout()
 * in core.ts as an SSRF sink: OPENROUTER_BASE_URL (env) flows into fetch()
 * without host validation. The bridge is designed to talk to exactly two
 * cloud providers (OpenRouter, Groq); anything else is denied by default.
 *
 * Policy (deny-by-default):
 *   - scheme must be http: or https:
 *   - userinfo (user:pass@host) is rejected
 *   - allowed hosts (exact match): openrouter.ai, api.groq.com
 *   - extra hosts: LLM_EGRESS_ALLOWED_HOSTS env (comma-separated, passed in
 *     by the caller) — for operators who point OPENROUTER_BASE_URL / GROQ_BASE_URL
 *     at a self-hosted proxy
 *   - loopback/private/link-local/public hosts are DENIED unless explicitly
 *     allowlisted above (the bridge itself is a local service; it must not be
 *     turned into a relay against other local services or cloud metadata)
 *
 * Pure module (no imports, erasable TS only) so node-based tests can import
 * it directly without Bun or a build step.
 */

export interface GuardVerdict {
  allowed: boolean
  reason: string
}

/** Providers the llm-bridge is designed to talk to (exact hostname match). */
export const DEFAULT_LLM_EGRESS_HOSTS: string[] = ["openrouter.ai", "api.groq.com"]

/**
 * Decide whether an outbound LLM egress URL is allowed. `extraHosts` is an
 * exact-match hostname allowlist supplied by the caller (typically parsed
 * from LLM_EGRESS_ALLOWED_HOSTS). Never fetches; never throws.
 */
export function isAllowedLlmEgressUrl(
  rawUrl: string,
  extraHosts: string[] = [],
): GuardVerdict {
  let u: URL
  try {
    u = new URL(rawUrl)
  } catch {
    return { allowed: false, reason: "unparseable URL" }
  }
  if (u.protocol !== "http:" && u.protocol !== "https:") {
    return { allowed: false, reason: `scheme ${u.protocol} not allowed (http/https only)` }
  }
  if (u.username !== "" || u.password !== "") {
    return { allowed: false, reason: "userinfo in URL not allowed" }
  }
  const host = u.hostname.toLowerCase()
  if (!host) {
    return { allowed: false, reason: "empty host" }
  }
  if (DEFAULT_LLM_EGRESS_HOSTS.includes(host)) {
    return { allowed: true, reason: `default provider host ${host}` }
  }
  if (extraHosts.includes(host)) {
    return { allowed: true, reason: `explicitly allowlisted host ${host}` }
  }
  return { allowed: false, reason: `host ${host} not in LLM egress allowlist` }
}
