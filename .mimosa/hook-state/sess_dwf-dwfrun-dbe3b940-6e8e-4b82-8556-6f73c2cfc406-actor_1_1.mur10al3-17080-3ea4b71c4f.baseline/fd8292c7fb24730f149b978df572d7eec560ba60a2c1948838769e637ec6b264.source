/**
 * Probe allowlist — SSRF gate for dashboard server-side health probes.
 *
 * [S5 security sweep · 2026-09-10] The static scan flagged 4 occurrences of
 * `probe()` in /api/scp/health/route.ts as SSRF sinks: URLs derived from
 * environment variables (SCP_INTERNAL_URL / LOOP_SCHEDULER_URL / LLM_BRIDGE_URL)
 * flow into fetch() without any validation. Env vars are operator-controlled,
 * but a misconfiguration (or a compromised process env) would let the
 * dashboard probe arbitrary hosts — including link-local cloud metadata
 * (169.254.169.254). This module is the PEP (policy enforcement point) placed
 * immediately before the fetch sink.
 *
 * Policy (deny-by-default, per scp-capability-security-review):
 *   - scheme must be http: or https:
 *   - userinfo (user:pass@host) is rejected
 *   - allowed hosts by default: loopback (localhost, 127.0.0.0/8, ::1)
 *     and *.docker.internal (compose.yml uses host.docker.internal).
 *     RFC1918 private ranges (10/8, 172.16/12, 192.168/16) are NOT allowed
 *     by default; they must be explicitly supplied in extraHosts / SCP_HEALTH_ALLOWED_HOSTS.
 *   - extra hosts: passed by the caller from SCP_HEALTH_ALLOWED_HOSTS
 *     (comma-separated, exact lowercase hostname match)
 *   - everything else is DENIED, including link-local 169.254.0.0/16
 *
 * Pure module (no imports, erasable TS only) so it is directly importable by
 * node-based tests without a build step.
 */

export interface GuardVerdict {
  allowed: boolean
  reason: string
}

const LOOPBACK_NAMES = new Set(["localhost", "ip6-localhost", "ip6-loopback"])

function parseIPv4(host: string): number[] | null {
  const m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(host)
  if (!m) return null
  const octets = [Number(m[1]), Number(m[2]), Number(m[3]), Number(m[4])]
  if (octets.some((n) => n > 255)) return null
  return octets
}

function isLoopbackHost(host: string): boolean {
  if (LOOPBACK_NAMES.has(host)) return true
  if (host === "::1") return true
  const v4 = parseIPv4(host)
  return v4 !== null && v4[0] === 127
}

function isPrivateIPv4(host: string): boolean {
  const v4 = parseIPv4(host)
  if (!v4) return false
  const [a, b] = v4
  if (a === 10) return true // 10.0.0.0/8
  if (a === 172 && b >= 16 && b <= 31) return true // 172.16.0.0/12
  if (a === 192 && b === 168) return true // 192.168.0.0/16
  return false
}

function isLinkLocalIPv4(host: string): boolean {
  const v4 = parseIPv4(host)
  return v4 !== null && v4[0] === 169 && v4[1] === 254 // 169.254.0.0/16 (cloud metadata)
}

/**
 * Decide whether a probe/fetch target URL is allowed. `extraHosts` is an
 * exact-match hostname allowlist supplied by the caller (typically parsed
 * from SCP_HEALTH_ALLOWED_HOSTS). Never fetches; never throws.
 */
export function isAllowedProbeTarget(
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
  const rawHost = u.hostname.toLowerCase()
  // WHATWG URL keeps brackets in .hostname for IPv6 literals ("[::1]").
  const host =
    rawHost.startsWith("[") && rawHost.endsWith("]") ? rawHost.slice(1, -1) : rawHost
  if (!host) {
    return { allowed: false, reason: "empty host" }
  }
  if (host.endsWith(".docker.internal") || host === "host.docker.internal") {
    return { allowed: true, reason: "docker internal host" }
  }
  if (isLoopbackHost(host)) {
    return { allowed: true, reason: "loopback" }
  }
  if (extraHosts.includes(host)) {
    return { allowed: true, reason: "explicitly allowlisted" }
  }
  if (isPrivateIPv4(host)) {
    return { allowed: false, reason: "private range (RFC1918) not allowed by default; must be in SCP_HEALTH_ALLOWED_HOSTS" }
  }
  if (isLinkLocalIPv4(host)) {
    return { allowed: false, reason: "link-local (cloud metadata) denied" }
  }
  return { allowed: false, reason: `host ${host} not in probe allowlist` }
}

/**
 * [S5b security sweep] Parse a comma-separated operator allowlist (e.g. the
 * raw value of SCP_API_ALLOWED_HOSTS / SCP_HEALTH_ALLOWED_HOSTS) into the
 * exact-match lowercase host list expected by isAllowedProbeTarget's
 * `extraHosts` parameter. Never throws; empty/undefined input yields [].
 */
export function parseHostList(
  raw: string | undefined | null,
): string[] {
  return (raw ?? "")
    .split(",")
    .map((h) => h.trim().toLowerCase())
    .filter(Boolean)
}
