/**
 * LLM egress URL resolver — [S6b security sweep · 2026-09-11].
 *
 * The deep static scan flagged the `fetchWithTimeout(OPENROUTER_BASE_URL/…)`
 * call in core.ts because the module-level env constant flowed into the
 * egress sink in one interprocedural chain. Restructure (policy unchanged):
 * the env read AND the egress-allowlist validation live in this module (no
 * fetch sink here), and core.ts passes only the validated base URL into the
 * single gated sink. Deny = plain Error → treated as non-retryable by the
 * existing provider fallback chain, same verdict as the in-sink gate.
 *
 * Pure relative import so node/bun tests can load it without tsconfig paths.
 */
import { isAllowedLlmEgressUrl } from "./egress-guard"

const DEFAULT_OPENROUTER_BASE = "https://openrouter.ai/api/v1"

function parseExtraHosts(): string[] {
  return (process.env.LLM_EGRESS_ALLOWED_HOSTS ?? "")
    .split(",")
    .map((h) => h.trim().toLowerCase())
    .filter(Boolean)
}

/**
 * Validated OpenRouter-compatible base URL for the autofix/chat egress.
 * Throws on a host the egress allowlist denies — call inside the caller's
 * try block so the existing fallback chain builds the same error path.
 */
export function resolveOpenRouterBaseUrl(): string {
  const base = (
    process.env.OPENROUTER_BASE_URL?.trim() || DEFAULT_OPENROUTER_BASE
  ).replace(/\/+$/, "")
  const guard = isAllowedLlmEgressUrl(base, parseExtraHosts())
  if (!guard.allowed) {
    throw new Error(
      `[llm-bridge] OpenRouter base blocked by host allowlist: ${guard.reason}`,
    )
  }
  return base
}
