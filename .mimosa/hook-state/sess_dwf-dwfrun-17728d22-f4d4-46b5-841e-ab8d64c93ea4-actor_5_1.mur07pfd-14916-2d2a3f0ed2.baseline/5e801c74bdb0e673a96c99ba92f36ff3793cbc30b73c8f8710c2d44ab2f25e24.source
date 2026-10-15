/**
 * [AUDIT-R2 2026-10-01 · M-4] Log redaction for browser-exposed log streams.
 *
 * The activity route (src/app/api/scp/activity) previously read
 * `data/service-logs/*.log` + `data/loop_runs.jsonl` and forwarded the raw
 * lines to the browser. Service logs routinely embed credential material
 * (Authorization headers from failed requests, `KEY=value` echoes from boot
 * dumps, provider tokens in error messages), so anything shipped unredacted
 * turns the dashboard into a secret oracle for whoever can open the page.
 *
 * Contract (fail-closed by construction):
 * - `redactLogLine` first TRUNCATES the line, then replaces every recognized
 *   secret shape with `[REDACTED]`, and finally DROPS the line entirely when
 *   it still looks like it carries a credential (defense in depth — unknown
 *   secret formats are not shipped on the off chance a regex missed them).
 * - Line values are capped so a single huge log line cannot blow up the
 *   response, and `capEventsPayload` bounds the total JSON payload size.
 * - Redaction is content-based, never echo-based: `[REDACTED]` placeholders
 *   are stable, so the ERROR/WARN level classification of the activity route
 *   keeps working on redacted text.
 */

/** Max characters kept per log line / per embedded error message. */
const MAX_LINE_CHARS = 300

/**
 * Secret shapes replaced with `[REDACTED]` in place. Each entry pairs a
 * pattern with a String.replace template ($1 = kept prefix). Order matters:
 * the keyed `secret=value` patterns run first so the value is gone before
 * any generic token matcher could leave a fragment behind.
 */
const REDACTION_PATTERNS: ReadonlyArray<{ pattern: RegExp; replace: string }> = [
  // Keyed assignments / headers: password=, token:, authorization: Bearer x,
  // scp_admin_key=..., x-api-key: ..., set-cookie: ... The value is eaten to
  // END OF LINE (fail-closed: `Authorization: Bearer abc def` must not leave
  // "def" behind just because the value contains a space).
  {
    pattern: /((?:password|passwd|pwd|secret|token|api[-_]?key|admin[-_]?key|auth[-_]?key|access[-_]?key|private[-_]?key|client[-_]?secret|session[-_]?id|authorization|cookie)\s*[=:]\s*)(?:"[^"]{4,}"|'[^']{4,}'|.{4,})/gi,
    replace: "$1[REDACTED]",
  },
  // "Bearer <credential>"
  { pattern: /(bearer\s+)[A-Za-z0-9\-._~+/=]{8,}/gi, replace: "$1[REDACTED]" },
  // JSON style: "password": "value", "api_key":"value" (quotes kept)
  {
    pattern: /("(?:password|passwd|pwd|secret|token|api[-_]?key|admin[-_]?key|auth[-_]?key|access[-_]?key|private[-_]?key|client[-_]?secret|session[-_]?id)"\s*:\s*)("[^"]{4,}")/gi,
    replace: '$1"[REDACTED]"',
  },
  // Well-known provider token prefixes
  {
    pattern: /\b(?:sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{8,}|gho_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,}|xox[baprs]-[A-Za-z0-9-]{8,}|ya29\.[A-Za-z0-9_-]{8,}|AKIA[0-9A-Z]{8,}|AIza[0-9A-Za-z_-]{8,}|glpat-[A-Za-z0-9_-]{8,})\b/g,
    replace: "[REDACTED]",
  },
  // JWT-shaped credentials (header.payload.signature)
  {
    pattern: /\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\b/g,
    replace: "[REDACTED]",
  },
  // Basic auth userinfo in URLs
  { pattern: /(https?:\/\/)[^\s/@:]+:[^\s/@]+@/g, replace: "$1[REDACTED]@" },
]

/**
 * Residual secret shapes that cause the WHOLE line to be dropped after
 * in-place redaction: PEM private key blocks (multi-line, cannot be
 * neutralized line-by-line) and a secret-keyed long opaque blob that
 * survived every replacement above (unknown credential format — fail-closed:
 * the line is not shipped rather than gambling that it is benign).
 */
const DROP_PATTERNS: ReadonlyArray<RegExp> = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /\b(?:password|passwd|pwd|secret|token|api[-_]?key|admin[-_]?key|access[-_]?key|authorization|credential)\s*[=:]\s*[A-Za-z0-9+/_-]{24,}/i,
]

export function redactLogLine(line: string, maxChars: number = MAX_LINE_CHARS): string | null {
  let working = line.length > maxChars ? `${line.slice(0, maxChars)}…[truncated]` : line
  for (const { pattern, replace } of REDACTION_PATTERNS) {
    working = working.replace(pattern, replace)
  }
  for (const pattern of DROP_PATTERNS) {
    if (pattern.test(working)) return null
  }
  return working
}

/** Redact a short unstructured error/message field (JSONL entries, run metadata). */
export function redactLogText(text: string, maxChars: number = MAX_LINE_CHARS): string {
  return redactLogLine(text, maxChars) ?? "[REDACTED]"
}

/**
 * Bound the total serialized payload shipped to the browser. Events are
 * assumed newest-first; once the cap is hit the remaining (older) events are
 * dropped and the overflow is reported so the UI can say "older events
 * hidden" instead of silently truncating.
 */
export function capEventsPayload<T>(
  events: T[],
  serialize: (event: T) => unknown,
  maxBytes: number = 48_000,
): { events: T[]; dropped: number } {
  let size = 0
  let dropped = 0
  const kept: T[] = []
  for (const event of events) {
    const serialized = JSON.stringify(serialize(event)) ?? ""
    if (size + serialized.length > maxBytes) {
      dropped += 1
      continue
    }
    size += serialized.length
    kept.push(event)
  }
  return { events: kept, dropped }
}
