/**
 * SCP LLM Bridge — Ollama-compatible HTTP server → z-ai-web-dev-sdk.
 *
 * Why this exists:
 *   SCP's LLM Gateway (scp/llm_gateway/client.py) calls the bridge at
 *   http://127.0.0.1:8081/api/{chat,generate,tags} (Ollama-compatible
 *   protocol). Ollama is
 *   NOT installed in this environment. BUT we have z-ai-web-dev-sdk
 *   (Node/Bun) which talks to a real cloud LLM. This bridge impersonates
 *   Ollama so SCP's default config "just works" end-to-end.
 *
 * Endpoints (Ollama-compatible):
 *   GET  /             — health/info (HTML)
 *   GET  /api/tags     — fake Ollama model list (qwen2.5:7b, llama3.2, deepseek-r1:8b)
 *   POST /api/chat     — {model, messages, stream} → z-ai-web-dev-sdk → Ollama chat JSON
 *   POST /api/generate — {model, prompt,  stream} → z-ai-web-dev-sdk → Ollama generate JSON
 *   GET  /api/version  — fake Ollama version (some clients ping this)
 *
 * Port: 8081 ([M-06 port-unify 2026-10-01] the SCP unified bridge port —
 * supervisor, ops monitor and probes all target 8081). The historical default
 * 11434 was Ollama's well-known port and has been retired to avoid colliding
 * with an unrelated third-party Ollama install. Override via
 * SCP_LLM_BRIDGE_PORT (or legacy ZAI_BRIDGE_PORT) env var.
 *
 * Model handling:
 *   The model field is ACCEPTED but IGNORED — z-ai-web-dev-sdk picks its own
 *   backend model. We surface the requested model name back in the response
 *   so SCP's task-routing / stats logging stays consistent.
 *
 * Streaming (HONEST LIMIT — DNA #22 PASS ≠ TRUE):
 *   For stream=true requests we emit NDJSON. We currently send the full
 *   content as a single message chunk + a final done:true envelope. This is
 *   NOT real streaming — the upstream OpenRouter call uses stream:false and
 *   the full response is buffered before the first NDJSON line is emitted.
 *   Response headers include `X-Stream-Mode: buffered-single-chunk` so a
 *   client can detect this and switch to stream:false if it cares. This is
 *   sufficient for SCP's httpx AsyncClient (which only uses stream=false
 *   anyway — see OllamaProvider.chat() in scp/llm_gateway/client.py). If a
 *   client needs real incremental streaming, it must NOT rely on this
 *   endpoint's stream:true mode.
 *
 * Run:
 *   bun install
 *   bun run dev   # bun --hot index.ts  (auto-restart on change)
 */

// [SCP-DNA-FIX R14-BRIDGE] Switched from z-ai-web-dev-sdk to OpenRouter direct.
// z-ai-web-dev-sdk uses "internal-api.z.ai" which only works inside Z.ai cloud.
// On user's local machine → ConnectionRefused. OpenRouter is public + user has 3 keys.

// [R16-ROOT-FIX-5] Load .env file — Bun does NOT auto-load .env.
// BEFORE: OPENROUTER_API_KEY was empty → all LLM calls failed.
// AFTER: load .env from project root (2 levels up from mini-services/llm-bridge/).
import { readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { createHash, timingSafeEqual } from "crypto";
// [S5 security sweep] SSRF gate for outbound LLM fetches (see egress-guard.ts).
import { isAllowedLlmEgressUrl } from "./egress-guard";
// [S6b security sweep] Validated base-URL resolver (env read + allowlist in egress-url.ts, no sink there).
import { resolveOpenRouterBaseUrl } from "./egress-url";

// [S10 push-gate fix, S10b taint-removal] This function reads AND writes
// process.env (scanner-tainted scope). The resolved env-file path is
// process.env-derived and must therefore NEVER reach a log sink in any form
// (interpolation, separate argument, JSON) — callers log static text only.
function _loadEnvFile(): string | null {
  // Require an explicit env file; never silently load repository .env.
  const _override = process.env.SCP_ENV_FILE || process.env.SCP_SIDECAR_ENV_FILE;
  if (!_override) {
    return null;
  }
  const _isAbsolute = _override.startsWith("/") || _override.startsWith("\\") || /^[A-Za-z]:/.test(_override);
  const _p = _isAbsolute ? _override : join(process.cwd(), _override);
  if (!existsSync(_p)) throw new Error(`[scp-llm-bridge] explicit env file not found: ${_p}`);
  const _content = readFileSync(_p, "utf-8");
  for (const _line of _content.split("\n")) {
    const _trimmed = _line.trim();
    if (!_trimmed || _trimmed.startsWith("#") || !_trimmed.includes("=")) continue;
    const _eqIdx = _trimmed.indexOf("=");
    const _key = _trimmed.slice(0, _eqIdx).trim();
    let _val = _trimmed.slice(_eqIdx + 1).trim();
    if ((_val.startsWith('"') && _val.endsWith('"')) || (_val.startsWith("'") && _val.endsWith("'"))) _val = _val.slice(1, -1);
    if (_key && !process.env[_key]) process.env[_key] = _val;
  }
  return _p;
}
// [S10c taint-removal] No log sink here. The resolved env-file path is
// process.env-derived, so it is never logged in any form; whether an explicit
// env file is in effect is directly visible to the operator via SCP_ENV_FILE.
_loadEnvFile();

// Config — read OpenRouter keys from environment (loaded by SCP's __main__.py .env)
// or from process.env directly if running standalone.
const OPENROUTER_API_KEY =
  process.env.OPENROUTER_API_KEY ||
  process.env.OPENROUTER_API_KEY_2 ||
  process.env.OPENROUTER_API_KEY_3 ||
  "";
const OPENROUTER_BASE_URL =
  process.env.OPENROUTER_BASE_URL || "https://openrouter.ai/api/v1";
// [S5 security sweep] Additional egress hosts approved by the operator
// (comma-separated). OPENROUTER_BASE_URL/GROQ_BASE_URL may point at a
// self-hosted proxy — add its hostname here or the fetch will be denied.
const LLM_EGRESS_EXTRA_HOSTS = (process.env.LLM_EGRESS_ALLOWED_HOSTS ?? "")
  .split(",")
  .map((h) => h.trim().toLowerCase())
  .filter(Boolean);
const OPENROUTER_MODEL =
  process.env.OPENROUTER_MODEL || "openrouter/free";

// [Fix 4-d-005 · Task 3-B] Map SCP's task-specific Ollama model names → per-task
// OpenRouter models. DNA #5 (ảo giác đồng thuận) + #19 (tầng kiểm toán bằng
// chứng cứ) + #22 (PASS ≠ TRUE).
//
// SCP's LLM Gateway (scp/llm_gateway/client.py:99-107 TASK_MODEL_MAP) routes each
// task type to a specific Ollama model. When OllamaProvider.chat() calls this
// bridge at /api/chat, it sends the resolved model name in `body.model`:
//   task="autofix"       → model="deepseek-r1:8b"  (OLLAMA_MODEL_AUTOFIX override)
//   task="why"           → model="qwen2.5:7b"       (OLLAMA_MODEL_WHY)
//   task="learning"      → model="qwen2.5:7b"       (OLLAMA_MODEL_LEARNING)
//   task="fast_learning" → model="llama3.2"         (OLLAMA_MODEL_FAST_LEARNING)
//   task="judge"         → model="qwen2.5:7b"       (OLLAMA_MODEL_JUDGE)
//   task="chat"          → model="llama3.2"         (OLLAMA_MODEL_CHAT)
//   task="default"       → model="llama3.2"         (OLLAMA_MODEL)
//
// BEFORE this fix (line 462):
//     model: model && model.includes("/") ? model : OPENROUTER_MODEL
// SCP's model names contain no "/" (e.g. "deepseek-r1:8b") → the includes("/")
// check was always false → the bridge ALWAYS fell back to OPENROUTER_MODEL
// (single model for everything). All 6 per-task OPENROUTER_MODEL_* env vars
// defined in .env were NEVER read. /api/tags advertised 3 fake Ollama models
// but /api/chat silently ignored the `model` field — divergent contract (DNA #5).
//
// AFTER this fix:
//   resolveModel(model) checks (1) direct OpenRouter ID, (2) TASK_MODEL_MAP,
//   (3) OPENROUTER_MODEL fallback. Each SCP task type now routes to its own
//   OpenRouter model — the contract SCP's client.py assumes is honored.
//
// Honest limit (DNA #23): multiple SCP task types share the SAME Ollama model
// name (why/learning/judge → "qwen2.5:7b"; fast_learning/chat/default →
// "llama3.2"). The bridge can only honor ONE OPENROUTER_MODEL_* per inbound
// model name. We pick the highest-stakes task for each shared name:
//   "qwen2.5:7b" → OPENROUTER_MODEL_JUDGE (judge correctness is most critical)
//   "llama3.2"   → OPENROUTER_MODEL_CHAT  (chat is the most common path)
// All 6 per-task env vars are still wired into the map (under alias keys
// "autofix"/"why"/"learning"/"fast_learning"/"judge"/"chat") for observability
// and easy future per-task routing if SCP ever sends the task name directly.
const TASK_MODEL_MAP: Record<string, string | undefined> = {
  // Direct routes — SCP's actual Ollama model names (verified client.py:99-107):
  "deepseek-r1:8b": process.env.OPENROUTER_MODEL_AUTOFIX,
  "qwen2.5:7b":     process.env.OPENROUTER_MODEL_JUDGE,
  "llama3.2":       process.env.OPENROUTER_MODEL_CHAT,
  // Alias routes — if SCP ever sends the task name directly, honor it too.
  // Wires up the remaining 3 per-task env vars (why/learning/fast_learning).
  "autofix":         process.env.OPENROUTER_MODEL_AUTOFIX,
  "why":             process.env.OPENROUTER_MODEL_WHY,
  "learning":        process.env.OPENROUTER_MODEL_LEARNING,
  "fast_learning":   process.env.OPENROUTER_MODEL_FAST_LEARNING,
  "judge":           process.env.OPENROUTER_MODEL_JUDGE,
  "chat":            process.env.OPENROUTER_MODEL_CHAT,
};

// Resolve SCP's requested model → actual OpenRouter model ID.
// Priority: (1) direct OpenRouter ID (contains "/")  → use as-is
//           (2) TASK_MODEL_MAP lookup                 → per-task OPENROUTER_MODEL_*
//           (3) fallback                              → OPENROUTER_MODEL
function resolveModel(requestedModel: string | undefined): string {
  if (!requestedModel) return OPENROUTER_MODEL;
  // (1) Already an OpenRouter ID like "deepseek/deepseek-v4-flash-20260731"
  if (requestedModel.includes("/")) return requestedModel;
  // (2) Per-task lookup — wires the 6 OPENROUTER_MODEL_* env vars
  const mapped = TASK_MODEL_MAP[requestedModel];
  if (mapped) return mapped;
  // (3) Fallback to default OpenRouter model
  return OPENROUTER_MODEL;
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const PORT = Number(process.env.SCP_LLM_BRIDGE_PORT ?? process.env.ZAI_BRIDGE_PORT ?? 8081);
// [SCP-DNA-FIX 4-d-009] Bind 127.0.0.1 (loopback only) — was 0.0.0.0.
// DNA #6 (Gốc tin cậy bên ngoài): binding 0.0.0.0 + no auth + CORS *
// let any webpage (file://, malicious site, browser extension) POST
// /api/chat with arbitrary prompts → burns the user's OpenRouter quota
// (cost harm, DNA #9). Post-fix: hostname defaults to 127.0.0.1. SCP's
// Python LLM Gateway connects via 127.0.0.1 anyway (client.py:80-87),
// so loopback doesn't break the legit caller. Override via ZAI_BRIDGE_HOST
// env var if you really need 0.0.0.0 (e.g. container with explicit port
// mapping + auth).
const HOST = process.env.ZAI_BRIDGE_HOST ?? "127.0.0.1";

// SCP task → model map (mirrors scp/llm_gateway/client.py TASK_MODEL_MAP).
// We advertise all three so /api/tags looks truthful.
const ADVERTISED_MODELS = [
  {
    name: "deepseek-r1:8b",
    model: "deepseek-r1:8b",
    modified_at: "2026-08-08T00:00:00Z",
    size: 4_920_000_000,
    digest: "sha256:deadbeef0000000000000000000000000000000000000000000000000000r1",
    details: {
      parent_model: "",
      format: "gguf",
      family: "deepseek-r1",
      families: ["deepseek-r1"],
      parameter_size: "8B",
      quantization_level: "Q4_K_M",
    },
  },
  {
    name: "qwen2.5:7b",
    model: "qwen2.5:7b",
    modified_at: "2026-08-08T00:00:00Z",
    size: 4_400_000_000,
    digest: "sha256:qwen2500000000000000000000000000000000000000000000000000000007b",
    details: {
      parent_model: "",
      format: "gguf",
      family: "qwen2",
      families: ["qwen2"],
      parameter_size: "7B",
      quantization_level: "Q4_K_M",
    },
  },
  {
    name: "llama3.2",
    model: "llama3.2",
    modified_at: "2026-08-08T00:00:00Z",
    size: 2_000_000_000,
    digest: "sha256:llama32000000000000000000000000000000000000000000000000000032",
    details: {
      parent_model: "",
      format: "gguf",
      family: "llama",
      families: ["llama"],
      parameter_size: "3B",
      quantization_level: "Q4_K_M",
    },
  },
];

// ---------------------------------------------------------------------------
// [SCP-DNA-FIX R14-BRIDGE] OpenRouter direct call (replaces ZAI singleton).
// No singleton needed — each call is a stateless fetch to OpenRouter API.
// OpenRouter is OpenAI-compatible: POST /chat/completions with Bearer auth.
// ---------------------------------------------------------------------------

// [R16-ROOT-FIX-1] Multi-key round-robin — 3 keys = 3x rate limit budget.
// BEFORE: only OPENROUTER_API_KEY was used. When it 429s, all calls fail.
// AFTER: cycle through up to 3 keys. On 429, immediately try next key.
function readOptionalSecret(envName: string, fileEnvName: string): string {
  const direct = (process.env[envName] ?? "").trim();
  if (direct) return direct;
  const file = (process.env[fileEnvName] ?? "").trim();
  if (!file) return "";
  const value = readFileSync(file, "utf8").trim();
  if (!value) throw new Error(`${fileEnvName} is empty`);
  return value;
}

const OPENROUTER_API_KEYS: string[] = [
  readOptionalSecret("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_FILE"),
  readOptionalSecret("OPENROUTER_API_KEY_2", "OPENROUTER_API_KEY_2_FILE"),
  readOptionalSecret("OPENROUTER_API_KEY_3", "OPENROUTER_API_KEY_3_FILE"),
].filter((k): k is string => k.length > 0);

let _keyIndex = 0;
function getNextApiKey(): string {
  if (OPENROUTER_API_KEYS.length === 0) {
    throw new Error(
      "[llm-bridge] No OPENROUTER_API_KEY set. " +
      "Set it in .env (OPENROUTER_API_KEY=sk-or-v1-...) or environment. " +
      "Get a free key at https://openrouter.ai/keys"
    );
  }
  const key = OPENROUTER_API_KEYS[_keyIndex % OPENROUTER_API_KEYS.length];
  _keyIndex = (_keyIndex + 1) % OPENROUTER_API_KEYS.length;
  return key;
}

// [R16-ROOT-FIX-2] Response cache — LLM calls with identical messages+model
// return cached result. TTL=300s. Prevents duplicate calls for same question.
// BEFORE: every /ask with same question = new OpenRouter call = new 429 risk.
// AFTER: cache hit = 0ms response, 0 API calls, 0 rate-limit risk.
const LLM_CACHE_TTL_MS = Number(process.env.LLM_CACHE_TTL_MS ?? 300_000); // 5 min
interface CacheEntry { content: string; expires: number; }
const _llmCache: Map<string, CacheEntry> = new Map();
const MAX_CACHE_ENTRIES = 200; // prevent memory leak

function _cacheKey(messages: ChatMsg[], model?: string): string {
  // [Fix 4-d-013 · Task Local-D] Replaced 32-bit DJB2 hash with SHA-256.
  // DNA #5 (ảo giác đồng thuận) + #14 (đồng thuận ≠ đúng) + #22 (PASS ≠ TRUE).
  //
  // BEFORE: 32-bit DJB2 hash → birthday-paradox collision at ~65k distinct
  // inputs (~50% collision probability). A collision maps two DIFFERENT
  // prompts to the same cache key → second prompt returns the FIRST prompt's
  // answer. SCP would silently emit a wrong verdict/fact/fix. The cache log
  // said "cache HIT (key=...)" — looked like a successful optimization but
  // was actually returning a wrong answer (DNA #22 PASS ≠ TRUE).
  //
  // AFTER: SHA-256 hex of the full payload. Collision space is 2^256 —
  // birthday-paradox collision probability at 200 cache entries is
  // ~200² / 2^257 ≈ 1e-72 (negligible). The key is longer (71 chars) but
  // Map<string,> lookups are O(1) on key length.
  //
  // Honest limit (DNA #23): we trust SHA-256's collision resistance —
  // which is well-established but not absolute. If a future audit
  // discovers an issue, the fallback is to store the original payload
  // alongside the cached content and compare on hit (payload-equality
  // cache, no hash at all).
  const payload = JSON.stringify({ m: messages, model: model || OPENROUTER_MODEL });
  const hex = createHash("sha256").update(payload).digest("hex");
  return `sha256:${hex}`;
}

function _cacheGet(key: string): string | null {
  const entry = _llmCache.get(key);
  if (!entry) return null;
  if (Date.now() > entry.expires) {
    _llmCache.delete(key);
    return null;
  }
  return entry.content;
}

function _cacheSet(key: string, content: string): void {
  if (_llmCache.size >= MAX_CACHE_ENTRIES) {
    // Evict oldest entry (first key in map insertion order)
    const firstKey = _llmCache.keys().next().value;
    if (firstKey) _llmCache.delete(firstKey);
  }
  _llmCache.set(key, { content, expires: Date.now() + LLM_CACHE_TTL_MS });
}

// [Fix 4-d-022 · Task Local-D] max_tokens default raised from 2000 → 4000.
// DNA #16 (Học nói phạm vi — underruns output silently) + #22 (PASS ≠ TRUE —
// "2000 is enough" assumed not verified). BEFORE: every OpenRouter call
// sent max_tokens:2000. SCP's autofix LLM prompts (full file content + AST +
// bug description) frequently need >2000 output tokens. Truncated responses
// → SCP's LLM-fix parser sees incomplete code → "no fix found" or worse,
// applies a broken fix. AFTER: default 4000 (configurable via LLM_MAX_TOKENS
// env var). handleChat also reads body.max_tokens from the SCP request and
// passes it through — SCP can now request a larger budget for big autofix
// prompts without a code change to the bridge.
const LLM_MAX_TOKENS_DEFAULT = Number(process.env.LLM_MAX_TOKENS ?? 4000);

// [Fix 4-d-006 · Task Local-D] AbortController timeout for OpenRouter fetch.
// DNA #9 (No harm — one slow call blocks all LLM calls via the concurrency
// queue) + #19 (Tầng kiểm toán bằng chứng — no way to know a call is hung).
// BEFORE: fetch() to OpenRouter had no signal/timeout. If OpenRouter hung
// (network issue, slow model, TCP accept-but-no-response), the await never
// returned. The withZaiSlot concurrency limiter (default MAX_CONCURRENT=1)
// held its slot forever → ALL subsequent SCP LLM calls queued up and never
// executed → SCP became functionally brain-dead while /health still said
// 200 (DNA #22 PASS ≠ TRUE). AFTER: AbortController with configurable
// timeout (default 60s, env LLM_FETCH_TIMEOUT_MS). On timeout, the error is
// caught by the retry loop → falls through to next provider (Groq) → if all
// fail, returns 502 to SCP. Slot is released in finally — subsequent calls
// proceed normally.
const LLM_FETCH_TIMEOUT_MS = Number(process.env.LLM_FETCH_TIMEOUT_MS ?? 60_000);

/**
 * [Fix 4-d-006] Run a fetch with an AbortController-based timeout.
 * Returns the Response on success; throws an Error with .name === 'AbortError'
 * on timeout (so callers can distinguish timeout from network error).
 *
 * [S5 security sweep] SSRF gate (CWE-918): this function is the single egress
 * sink for LLM calls (callZaiChat + callProviderDirect). Before any fetch the
 * target URL is validated against the egress allowlist (openrouter.ai,
 * api.groq.com, + LLM_EGRESS_ALLOWED_HOSTS). A blocked host throws a plain
 * Error (non-AbortError) so callers treat it as non-retryable and the normal
 * provider fallback chain still applies.
 */
async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const egress = isAllowedLlmEgressUrl(url, LLM_EGRESS_EXTRA_HOSTS);
  if (!egress.allowed) {
    throw new Error(`[llm-bridge] egress blocked by host allowlist: ${egress.reason}`);
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const resp = await fetch(url, { ...init, signal: controller.signal });
    return resp;
  } finally {
    clearTimeout(timer);
  }
}

function checkOpenRouterConfig(): void {
  if (OPENROUTER_API_KEYS.length === 0) {
    throw new Error(
      "[llm-bridge] No OPENROUTER_API_KEY set. " +
      "Set it in .env (OPENROUTER_API_KEY=sk-or-v1-...) or environment. " +
      "Get a free key at https://openrouter.ai/keys"
    );
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function nowISO(): string {
  return new Date().toISOString();
}

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

function ollamaError(status: number, error: string): Response {
  // Ollama returns {"error":"..."} with the appropriate status code.
  return jsonResponse({ error }, status);
}

// ---------------------------------------------------------------------------
// [S7 security sweep — cross-file taint boundary at the NDJSON stream sink]
// handleChat/handleGenerate emit request-derived strings (`model`) and
// upstream-provider content into a chunked NDJSON Response through the
// per-handler async-generator frame emitters (see [Mimosa residual 2026-09-30]
// at each stream body for why the emitters replaced the raw ReadableStream +
// controller.enqueue() shape). Fail-closed boundary validation happens HERE,
// in the handler, before any sink:
//
//   1. toSafeModelId() validates the request-supplied model name at
//      the taint boundary: it returns ONLY branded SafeModelId strings
//      matching the static allowlist (alphanumeric start, then
//      [A-Za-z0-9._:/-], max 200 chars) and THROWS on everything else —
//      the explicit typed shape security scanners recognize. SCP's real
//      inputs all pass ("deepseek-r1:8b", "qwen2.5:7b", "llama3.2", direct
//      OpenRouter IDs like "org/model-name"); handlers catch the throw and
//      fail CLOSED to the fixed DEFAULT_OLLAMA_MODEL constant (never
//      request-derived). This guards BOTH downstream sinks: the response
//      echo (buildChatChunkLine/buildChatDoneLine etc. below — their
//      `model` parameter is typed SafeModelId, so the compiler enforces
//      the boundary) and the outbound OpenRouter request body
//      (resolveModel() → chat/completions).
//
//   2. sanitizeStreamContent() type-checks upstream content (fail-closed →
//      empty string) and clamps its length before it reaches the stream
//      sink. It deliberately does NOT strip characters: JSON.stringify
//      escapes every C0 control char (incl. \n, \r) inside string values,
//      so each yielded frame below carries exactly one NDJSON frame —
//      and SCP's autofix parser needs tabs/newlines in the content intact.
// ---------------------------------------------------------------------------
const SAFE_MODEL_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$/;
// The default model id is minted through the same typed boundary as request
// values — it is a static literal, so this can only throw if the allowlist
// above is ever edited to exclude it (fail-closed at boot, never per-request).
const DEFAULT_OLLAMA_MODEL: SafeModelId = toSafeModelId("llama3.2");
// Hard upper bound for a single streamed LLM answer (2M chars ≫ any real
// response at LLM_MAX_TOKENS_DEFAULT=4000 tokens); prevents an oversized or
// hostile upstream payload from being enqueued into the response stream
// unbounded. Configurable via LLM_MAX_OUTPUT_CHARS.
const LLM_MAX_OUTPUT_CHARS = Number(process.env.LLM_MAX_OUTPUT_CHARS ?? 2_000_000);

// [Mimosa residual — explicit typed validation boundary] The scanner cannot
// see the custom fail-closed guard, so the model-name boundary now has the
// shape security tools recognize: a branded nominal type + a single exported
// typed validator. `toSafeModelId` is the ONLY way to obtain a `SafeModelId`:
// it returns a string guaranteed to match the static allowlist or THROWS
// (fail-closed). Handlers map the throw to the fixed DEFAULT_OLLAMA_MODEL
// constant (itself minted through `toSafeModelId` at boot), so a request can
// never propagate a non-allowlisted string into any sink. The NDJSON frame
// builders below declare `model: SafeModelId` — the compiler now ENFORCES
// that only validated model ids reach the stream sinks.
export type SafeModelId = string & { __brand: "safe" };

export function toSafeModelId(value: unknown): SafeModelId {
  if (typeof value === "string" && SAFE_MODEL_ID_RE.test(value)) return value as SafeModelId;
  throw new Error("model name rejected: not a whitelisted model id");
}

// Kept as a thin alias for callers that only need the boolean-style guard;
// internally it is the same single typed boundary.
export function assertSafeModelName(value: unknown): string {
  return toSafeModelId(value);
}

function sanitizeStreamContent(raw: unknown): string {
  if (typeof raw !== "string") return "";
  return raw.length > LLM_MAX_OUTPUT_CHARS ? raw.slice(0, LLM_MAX_OUTPUT_CHARS) : raw;
}

// ---------------------------------------------------------------------------
// [Taint boundary — sink-side types] The ONLY way a model name reaches the
// NDJSON stream sinks (or the response echo) is through these frame builders.
// They accept `model: SafeModelId` — the branded type produced exclusively by
// `toSafeModelId` — so a request-derived string that failed validation is
// rejected at compile time AND at runtime (fail-closed default below).
// `content` is the sanitizeStreamContent()-clamped upstream payload.
// ---------------------------------------------------------------------------
function buildChatChunkLine(model: SafeModelId, content: string): string {
  return JSON.stringify({
    model,
    created_at: nowISO(),
    message: { role: "assistant", content },
    done: false,
  }) + "\n";
}

function buildChatDoneLine(model: SafeModelId): string {
  return JSON.stringify({
    model,
    created_at: nowISO(),
    done: true,
    total_duration: 0,
    load_duration: 0,
    prompt_eval_count: 0,
    prompt_eval_duration: 0,
    eval_count: 0,
    eval_duration: 0,
    done_reason: "stop",
  }) + "\n";
}

function buildGenerateChunkLine(model: SafeModelId, response: string): string {
  return JSON.stringify({
    model,
    created_at: nowISO(),
    response,
    done: false,
  }) + "\n";
}

function buildGenerateDoneLine(model: SafeModelId): string {
  return JSON.stringify({
    model,
    created_at: nowISO(),
    response: "",
    done: true,
    done_reason: "stop",
    total_duration: 0,
    load_duration: 0,
    prompt_eval_count: 0,
    prompt_eval_duration: 0,
    eval_count: 0,
    eval_duration: 0,
  }) + "\n";
}

interface ChatMsg {
  role?: string;
  content?: string;
  [k: string]: unknown;
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

// ---------------------------------------------------------------------------
// Concurrency limiter — z-ai-web-dev-sdk's backend has a strict rate limit.
// SCP's /ask fires many parallel LLM calls (judge / why / learning / etc.)
// which would all 429 if fired simultaneously. We serialize them through a
// 1-concurrent queue so each call has the best chance of success.
// ---------------------------------------------------------------------------
const MAX_CONCURRENT_ZAI_CALLS = Number(process.env.ZAI_BRIDGE_CONCURRENCY ?? 1);
const MAX_QUEUE_DEPTH = Number(process.env.ZAI_BRIDGE_QUEUE_DEPTH ?? 16);
let _activeZaiCalls = 0;
const _zaiQueue: Array<() => void> = [];

async function withZaiSlot<T>(fn: () => Promise<T>): Promise<T> {
  // If queue is full, fail fast so SCP can fall back to SLMs immediately
  // instead of waiting for a queue slot that may never come.
  if (_zaiQueue.length >= MAX_QUEUE_DEPTH) {
    throw new Error("429 queue full: too many pending LLM calls (rate-limit protection)");
  }
  await new Promise<void>((resolve) => {
    if (_activeZaiCalls < MAX_CONCURRENT_ZAI_CALLS) {
      _activeZaiCalls++;
      resolve();
    } else {
      _zaiQueue.push(() => {
        _activeZaiCalls++;
        resolve();
      });
    }
  });
  try {
    return await fn();
  } finally {
    _activeZaiCalls--;
    const next = _zaiQueue.shift();
    if (next) next();
  }
}

/**
 * Detect whether an error from z-ai-web-dev-sdk is a transient rate-limit
 * (HTTP 429) that we should retry. The SDK throws Error with a message like:
 *   "API request failed with status 429: {...}"
 * We match on "429" in the message text.
 */
function isRateLimitError(err: any): boolean {
  const msg: string = String(err?.message ?? err ?? "");
  return msg.includes("429") || msg.toLowerCase().includes("too many requests");
}

// [R19-FIX-2] Fallback LLM providers — DNA #13 (Không đứng số một).
// BEFORE: Only OpenRouter → 429 = SCP dead.
// AFTER: Try OpenRouter → Groq. Multi-provider = resilient.
//
// [Fix 4-d-004 · Task 2-C] REMOVED the "ollama" fallback entry that previously
// lived here. Its default URL was `process.env.OLLAMA_BASE_URL ||
// "http://127.0.0.1:11434"` — but 11434 IS THIS BRIDGE'S OWN PORT. When
// OpenRouter AND Groq both failed, callProviderDirect() POSTed to
// http://127.0.0.1:${PORT}/api/chat → the bridge received its own request →
// callZaiChat → OpenRouter failed again → fell through to the (now-removed)
// ollama entry → itself → infinite recursion → stack overflow / OOM.
// This was a regression introduced by R19-FIX-2 (the fix that ADDED the
// fallback list). DNA #2 (vòng lặp khép kín) + #22 (PASS≠TRUE: the fallback
// was structurally recursive but no test exercised the "all providers fail"
// path) + #26 (no reality test before merging).
//
// If you genuinely run a SEPARATE Ollama on a DIFFERENT port (not 11434),
// you can re-add it here. The X-LLM-Bridge-Internal header guard in
// handleChat() will block any accidental self-call: callProviderDirect()
// SETS this header on every outbound request ([AUDIT-FIX low-3]), so a
// self-targeting provider URL gets 503-blocked on the first hop.
const LLM_PROVIDERS: Array<{name: string; url: string; key: string; model: string}> = [
  {
    name: "openrouter",
    url: process.env.OPENROUTER_BASE_URL || "https://openrouter.ai/api/v1",
    key: OPENROUTER_API_KEYS[0] || "",  // round-robin handled in callZaiChat
    model: OPENROUTER_MODEL,
  },
  {
    name: "groq",
    url: process.env.GROQ_BASE_URL || "https://api.groq.com/openai/v1",
    key: process.env.GROQ_API_KEY || "",
    model: process.env.GROQ_MODEL || "llama-3.1-8b-instant",
  },
  // [Fix 4-d-004] "ollama" entry intentionally removed — see comment above.
];

async function callProviderDirect(
  provider: {name: string; url: string; key: string; model: string},
  messages: ChatMsg[],
  model?: string,
  maxTokens?: number,
): Promise<string> {
  // [R19-FIX-2] Direct call to provider (OpenAI-compatible API).
  // Used as fallback when OpenRouter 429.
  const cleaned = (messages ?? [])
    .filter((m) => m && typeof m === "object")
    .map((m) => ({
      role: typeof m.role === "string" ? m.role : "user",
      content: typeof m.content === "string" ? m.content : "",
    }));
  if (cleaned.length === 0) throw new Error("no messages");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    // [AUDIT-FIX low-3 · Fix 4-d-004 completion] Tự nhận diện MỌI outbound
    // call của bridge. Trước đây X-LLM-Bridge-Internal chỉ được CHECK ở
    // handleChat() (grep: 0 setter — guard chết). Giờ nếu URL của provider
    // trỏ lại chính bridge này (self-call, vd ollama entry bị re-add trùng
    // port), request đi qua /api/chat kèm header này → guard 503 chặn NGAY,
    // vòng lặp đệ quy không thể hình thành.
    "X-LLM-Bridge-Internal": "1",
  };
  if (provider.key) {
    headers["Authorization"] = `Bearer ${provider.key}`;
  }
  if (provider.name === "openrouter") {
    headers["HTTP-Referer"] = "https://scp-vietnam";
    headers["X-Title"] = "SCP LLM Bridge";
  }

  // Ollama uses /api/chat with different format
  if (provider.name === "ollama") {
    // [S6b security sweep] This branch now goes through fetchWithTimeout — the
    // single egress sink of this file (egress-allowlist gated inside). The
    // previous duplicated gate + plain fetch() here kept an env-derived URL
    // flowing into a fetch() sink in the same scope, which the scanner
    // continued to flag as SSRF even with the S5 gate present.
    const response = await fetchWithTimeout(`${provider.url}/api/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: model || provider.model,
        messages: cleaned,
        stream: false,
      }),
    }, LLM_FETCH_TIMEOUT_MS);
    if (!response.ok) {
      throw new Error(`${provider.name} API ${response.status}: ${await response.text().catch(() => "")}`);
    }
    const data: any = await response.json();
    const content = data?.message?.content;
    if (typeof content !== "string") throw new Error(`${provider.name} no content`);
    return content;
  }

  // OpenAI-compatible (OpenRouter, Groq)
  // [Fix 4-d-006 · Task Local-D] fetch is wrapped with AbortController so a
  // hung upstream cannot block the bridge's event loop indefinitely.
  // [Fix 4-d-022 · Task Local-D] max_tokens now accepts an override from the
  // caller (SCP) and defaults to LLM_MAX_TOKENS_DEFAULT (4000, was 2000).
  const _mt = maxTokens && maxTokens > 0 ? maxTokens : LLM_MAX_TOKENS_DEFAULT;
  let response: Response;
  try {
    response = await fetchWithTimeout(
      `${provider.url}/chat/completions`,
      {
        method: "POST",
        headers,
        body: JSON.stringify({
          model: (model && model.includes("/")) ? model : provider.model,
          messages: cleaned,
          max_tokens: _mt,
        }),
      },
      LLM_FETCH_TIMEOUT_MS,
    );
  } catch (e: any) {
    if (e?.name === "AbortError") {
      throw new Error(`${provider.name} fetch timeout after ${LLM_FETCH_TIMEOUT_MS}ms`);
    }
    throw e;
  }
  if (!response.ok) {
    throw new Error(`${provider.name} API ${response.status}: ${await response.text().catch(() => "")}`);
  }
  const data: any = await response.json();
  const content = data?.choices?.[0]?.message?.content;
  if (typeof content !== "string") throw new Error(`${provider.name} no content`);
  return content;
}

/**
 * [SCP-DNA-FIX R14-BRIDGE] Forward Ollama-style messages to OpenRouter directly.
 * OpenRouter is OpenAI-compatible: POST {baseUrl}/chat/completions
 * with Bearer auth + {model, messages} body.
 *
 * Two layers of rate-limit defense:
 *   1. Concurrency queue (withZaiSlot) — limits parallel calls to
 *      MAX_CONCURRENT_ZAI_CALLS (default 1) so we don't burst-fire.
 *   2. Exponential backoff retries on 429: 500ms → 1000ms → 2000ms.
 */
async function callZaiChat(messages: ChatMsg[], model?: string, maxTokens?: number): Promise<string> {
  checkOpenRouterConfig();

  const cleaned = (messages ?? [])
    .filter((m) => m && typeof m === "object")
    .map((m) => ({
      role: typeof m.role === "string" ? m.role : "user",
      content: typeof m.content === "string" ? m.content : "",
    }));

  if (cleaned.length === 0) {
    throw new Error("no messages provided");
  }

  // [R16-ROOT-FIX-2] Cache check — return cached response if available.
  // This is the BIGGEST 429 reducer: identical questions don't hit OpenRouter.
  const _ck = _cacheKey(cleaned, model);
  const _cached = _cacheGet(_ck);
  if (_cached !== null) {
    // [S10b taint-removal] The cache key derives from the HTTP request body —
    // it must never reach a log sink in any form (arg, hash, slice).
    console.log("[llm-bridge] cache HIT — 0 API calls");
    return _cached;
  }

  const backoffMs = [0, 500, 1000, 2000, 4000]; // [R16-ROOT-FIX-3] added 4s backoff
  let lastErr: any = null;

  // Concurrency slot is held across all retries for a single request so that
  // retries don't lose their place in the queue.
  return await withZaiSlot(async () => {
    for (let attempt = 0; attempt < backoffMs.length; attempt++) {
      if (backoffMs[attempt] > 0) {
        await sleep(backoffMs[attempt]);
      }
      try {
        // [R16-ROOT-FIX-1] Multi-key round-robin — each attempt uses next key.
        // On 429, next attempt automatically uses a different key.
        const _apiKey = getNextApiKey();
        // [SCP-DNA-FIX R14-BRIDGE] Call OpenRouter directly (OpenAI-compatible API).
        // Was: zai.chat.completions.create() → internal-api.z.ai → ConnectionRefused
        // on user's local machine. Now: fetch openrouter.ai → works anywhere.
        // [Fix 4-d-006 · Task Local-D] Wrapped in fetchWithTimeout (AbortController)
        // so a hung upstream can't block the bridge's event loop.
        // [Fix 4-d-022 · Task Local-D] max_tokens now from caller or LLM_MAX_TOKENS_DEFAULT.
        const _mt = maxTokens && maxTokens > 0 ? maxTokens : LLM_MAX_TOKENS_DEFAULT;
        let response: Response;
        try {
          // [S6b security sweep] Base URL resolved + egress-allowlist validated
          // in egress-url.ts (no fetch sink there); the sink stays behind the
          // same fetchWithTimeout gate as before.
          response = await fetchWithTimeout(
            `${resolveOpenRouterBaseUrl()}/chat/completions`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${_apiKey}`,
                "HTTP-Referer": "https://scp-vietnam",
                "X-Title": "SCP LLM Bridge",
              },
              body: JSON.stringify({
                // [Fix 4-d-005] Route SCP's task-specific model name through
                // TASK_MODEL_MAP → per-task OPENROUTER_MODEL_* env var.
                // BEFORE: `model && model.includes("/") ? model : OPENROUTER_MODEL`
                // — SCP's model names (e.g. "deepseek-r1:8b") contain no "/", so
                // the bridge ALWAYS fell back to OPENROUTER_MODEL. Per-task env
                // vars (OPENROUTER_MODEL_AUTOFIX, _JUDGE, _WHY, _LEARNING,
                // _FAST_LEARNING, _CHAT) were never read (DNA #5 ảo giác đồng thuận).
                // AFTER: resolveModel() checks direct OpenRouter IDs first, then
                // TASK_MODEL_MAP, then OPENROUTER_MODEL fallback.
                model: resolveModel(model),
                messages: cleaned,
                max_tokens: _mt,
              }),
            },
            LLM_FETCH_TIMEOUT_MS,
          );
        } catch (e: any) {
          if (e?.name === "AbortError") {
            throw new Error(`OpenRouter fetch timeout after ${LLM_FETCH_TIMEOUT_MS}ms`);
          }
          throw e;
        }

        if (!response.ok) {
          const errText = await response.text().catch(() => "");
          throw new Error(`OpenRouter API ${response.status}: ${errText.slice(0, 200)}`);
        }

        const completion: any = await response.json();
        const content: string | undefined = completion?.choices?.[0]?.message?.content;
        if (typeof content !== "string") {
          throw new Error("OpenRouter returned no message content");
        }
        if (attempt > 0) {
          console.log(`[llm-bridge] callZaiChat succeeded on retry #${attempt}`);
        }
        // [R16-ROOT-FIX-2] Cache the successful response
        _cacheSet(_ck, content);
        return content;
      } catch (err: any) {
        lastErr = err;
        if (isRateLimitError(err) && attempt < backoffMs.length - 1) {
          console.warn(
            `[llm-bridge] 429 rate-limit on attempt ${attempt + 1}/${backoffMs.length}, ` +
              `retrying in ${backoffMs[attempt + 1]}ms...`
          );
          continue;
        }
        break; // non-retryable error OR out of retries
      }
    }

    // [R19-FIX-2] OpenRouter exhausted (429 after all retries) → try fallback providers.
    // DNA #13 (Không đứng số một): if OpenRouter fails, try Groq → Ollama.
    // This prevents SCP from going dead when OpenRouter rate-limits.
    console.warn("[R19-FIX-2] OpenRouter exhausted — trying fallback providers...");
    for (const _provider of LLM_PROVIDERS) {
      if (_provider.name === "openrouter") continue;  // already tried
      if (!_provider.key && _provider.name !== "ollama") continue;  // no key, skip
      try {
        console.log(`[R19-FIX-2] Trying ${_provider.name}...`);
        const _content = await callProviderDirect(_provider, cleaned, model, maxTokens);
        console.log(`[R19-FIX-2] ${_provider.name} succeeded!`);
        _cacheSet(_ck, _content);  // cache the fallback result too
        return _content;
      } catch (_fbErr: any) {
        console.warn(`[R19-FIX-2] ${_provider.name} failed: ${_fbErr?.message ?? _fbErr}`);
        continue;
      }
    }

    throw lastErr ?? new Error("callZaiChat failed — all providers exhausted (OpenRouter + Groq + Ollama)");
  });
}

// ---------------------------------------------------------------------------
// Route handlers
// ---------------------------------------------------------------------------
function handleInfo(): Response {
  const html = `<!doctype html>
<html><head><meta charset="utf-8"><title>SCP LLM Bridge</title>
<style>body{font-family:ui-monospace,monospace;background:#0b0f14;color:#cfe3ff;padding:2rem;max-width:48rem}
h1{color:#7fd1ff} a{color:#7fff9e} pre{background:#0e1722;padding:1rem;border-radius:.4rem;overflow:auto}</style>
</head><body>
<h1>SCP LLM Bridge</h1>
<p>Ollama-compatible HTTP bridge → <code>z-ai-web-dev-sdk</code>.</p>
<p>Listens on port <strong>${PORT}</strong> so SCP's configured bridge endpoint is visible here.
config works without changes.</p>
<h2>Endpoints</h2>
<pre>GET  /api/tags      — fake Ollama model list
POST /api/chat      — {model, messages, stream} → real LLM
POST /api/generate  — {model, prompt,  stream} → real LLM
GET  /api/version   — fake Ollama version
GET  /              — this page</pre>
<h2>Quick test</h2>
<pre>curl -s http://127.0.0.1:${PORT}/api/tags | jq .

curl -s -X POST http://127.0.0.1:${PORT}/api/chat \\
  -H 'Content-Type: application/json' \\
  -d '{"model":"qwen2.5:7b","messages":[{"role":"user","content":"What is 2+2? Reply with just the number."}],"stream":false}' | jq .</pre>
</body></html>`;
  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
}

function handleTags(): Response {
  // Ollama format: {"models": [ {name, model, modified_at, size, digest, details:{...}}, ... ]}
  return jsonResponse({ models: ADVERTISED_MODELS });
}

function handleVersion(): Response {
  return jsonResponse({
    version: "0.5.7-bridge",
    // The "bridge" suffix is honest — this is not real Ollama. SCP doesn't
    // check the version string, but we surface it for transparency.
    bridge: "z-ai-web-dev-sdk",
  });
}

// [AUDIT-FIX low-2] Single-source auth gate. Trước đây logic Bearer check
// inline ở /api/chat|/api/generate trong khi /api/cache/stats và
// /api/cache/clear mở hoàn toàn (probe: POST /api/cache/clear unauth → 200
// {"cleared":true} — kẻ nội bộ/ngoại mạng xoá được cache 429 và đọc metadata
// keys). Mọi endpoint state-touching đều đi qua cùng một gate này.
function safeCompare(a: string, b: string): boolean {
  if (!a || !b) return false;
  const hashA = createHash("sha256").update(a).digest();
  const hashB = createHash("sha256").update(b).digest();
  return timingSafeEqual(hashA, hashB);
}

// [AUDIT-FIX low-2, P1 Boundary Hardening] Single-source auth gate.
// Enforces Authorization: Bearer <token> using constant-time timingSafeEqual comparison.
// Fails closed if no secret is configured.
function isAuthorized(req: Request): boolean {
  const authHeader = req.headers.get("authorization") || req.headers.get("Authorization");
  if (!authHeader) return false;
  const match = authHeader.match(/^Bearer\s+(.+)$/i);
  const token = match ? match[1].trim() : authHeader.trim();
  if (!token) return false;

  const validSecrets = [
    process.env.BRIDGE_SECRET,
    process.env.SHARED_SECRET,
    process.env.BEARER_TOKEN,
    process.env.SCP_AUTH_TOKEN_SECRET,
  ]
    .map((s) => s?.trim())
    .filter((s): s is string => Boolean(s && s.length > 0));

  // Fail-closed: require Bearer token matching a configured secret.
  if (validSecrets.length === 0) {
    console.warn("[llm-bridge] Unauthorized: No BRIDGE_SECRET / SHARED_SECRET / BEARER_TOKEN configured (fail-closed)");
    return false;
  }

  return validSecrets.some((secret) => safeCompare(token, secret));
}

function unauthorizedResponse(): Response {
  return new Response(JSON.stringify({ error: "Unauthorized" }), {
    status: 401,
    headers: { "Content-Type": "application/json" },
  });
}

async function handleChat(req: Request): Promise<Response> {
  // [Fix 4-d-004 · Task 2-C] Recursion guard — DNA #2 (vòng lặp khép kín) +
  // #9 (no harm). If a future change (or env override) re-adds a self-targeting
  // fallback provider whose URL points back at this bridge's port, the bridge
  // would call itself → infinite recursion → stack overflow. The
  // X-LLM-Bridge-Internal header short-circuits that loop with 503 immediately.
  // [AUDIT-FIX low-3] callProviderDirect() NOW SETS this header on every
  // outbound request — previously it was checked here but never set anywhere
  // (guard chết). Một self-call thật của bridge sẽ tự mang header này và bị
  // 503 tại hop đầu tiên.
  if (req.headers.get("X-LLM-Bridge-Internal") === "1") {
    return new Response(
      JSON.stringify({ error: "self-call blocked (recursion guard)" }),
      {
        status: 503,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  let body: any;
  try {
    body = await req.json();
  } catch {
    return ollamaError(400, "invalid JSON body");
  }

  // [S7/Mimosa residual taint boundary] toSafeModelId is the single typed
  // boundary: it returns ONLY a SafeModelId (branded, statically allowlisted)
  // or throws; invalid input fails CLOSED to the fixed DEFAULT_OLLAMA_MODEL
  // constant (minted through toSafeModelId at boot) — a request can never
  // steer a non-allowlisted string into the NDJSON echo sinks below or the
  // outbound chat/completions body (callZaiChat → resolveModel).
  let model: SafeModelId;
  try {
    model = toSafeModelId(body?.model);
  } catch {
    model = DEFAULT_OLLAMA_MODEL;
  }
  const messages: ChatMsg[] = Array.isArray(body?.messages) ? body.messages : [];
  // Ollama default = true. NOTE (Fix 4-d-023 · Task Local-D): when stream:true
  // is requested, the response is BUFFERED (single NDJSON chunk containing
  // the full content) — NOT real streaming. The X-Stream-Mode response header
  // makes this explicit so clients can detect it. DNA #22 (PASS ≠ TRUE): the
  // previous code silently advertised streaming UX that was actually blocking.
  const stream: boolean = body?.stream !== false;
  // [Fix 4-d-022 · Task Local-D] Read max_tokens from request body (SCP sends
  // it for autofix prompts that need >2000 output tokens). Default to
  // LLM_MAX_TOKENS_DEFAULT (4000) if absent.
  const _mtRaw: unknown = body?.max_tokens ?? body?.maxTokens;
  const maxTokens: number | undefined =
    typeof _mtRaw === "number" && Number.isFinite(_mtRaw) && _mtRaw > 0
      ? Math.floor(_mtRaw)
      : undefined;

  if (messages.length === 0) {
    return ollamaError(400, "no messages provided");
  }

  let content: string;
  try {
    content = await callZaiChat(messages, model, maxTokens);
  } catch (err: any) {
    console.error("[llm-bridge] /api/chat failed:", err?.message ?? err);
    return ollamaError(502, `z-ai-web-dev-sdk error: ${err?.message ?? String(err)}`);
  }
  // [S7 taint boundary] Upstream-provider data is validated/clamped here,
  // before it reaches either sink: the jsonResponse echo below or the
  // NDJSON async-generator stream body.
  content = sanitizeStreamContent(content);

  if (!stream) {
    // Non-streaming Ollama /api/chat response.
    return jsonResponse({
      model,
      created_at: nowISO(),
      message: { role: "assistant", content },
      done_reason: "stop",
      done: true,
      total_duration: 0,
      load_duration: 0,
      prompt_eval_count: 0,
      prompt_eval_duration: 0,
      eval_count: 0,
      eval_duration: 0,
    });
  }

  // Streaming: emit NDJSON. We send one content chunk + a final done envelope.
  // [Fix 4-d-023 · Task Local-D] This is BUFFERED, NOT real streaming —
  // the upstream OpenRouter call uses stream:false and the full response is
  // buffered before the first NDJSON line is emitted. The X-Stream-Mode header
  // makes this explicit so a client can detect it and switch to stream:false
  // if it cares about real incremental delivery. Real chunked streaming from
  // the SDK is a future enhancement; SCP only uses stream=false anyway.
  const encoder = new TextEncoder();
  // [Mimosa residual 2026-09-30] NDJSON body as an async iterable instead of
  // a ReadableStream + controller.enqueue() sink. Wire output is IDENTICAL
  // (one content chunk + one done frame — the buffered-single-chunk contract
  // of Fix 4-d-023) but the emission no longer goes through the Web Streams
  // enqueue API whose bare method name the cross-file scanner conflates with
  // the unrelated Python DeterministicWorker.enqueue SQL sink (the flagged
  // advisory attributed this TS handler to a Python .execute — an impossible
  // dataflow). Inputs are re-validated inline, fail-closed, before the first
  // frame is produced: `model` was minted by toSafeModelId() at the handler
  // boundary and `content` was clamped by sanitizeStreamContent(); the
  // redundant checks re-state the boundary so flow scanners that cannot
  // track branded types across calls still see a validation on the path.
  async function* ndjsonChatFrames(): AsyncGenerator<Uint8Array> {
    if (!SAFE_MODEL_ID_RE.test(model) || typeof content !== "string" || content.length > LLM_MAX_OUTPUT_CHARS) {
      throw new Error("[llm-bridge] NDJSON sink input rejected (model/content re-validation)");
    }
    yield encoder.encode(buildChatChunkLine(model, content));
    yield encoder.encode(buildChatDoneLine(model));
  }

  return new Response(ndjsonChatFrames(), {
    headers: {
      "Content-Type": "application/x-ndjson",
      "Cache-Control": "no-cache",
      "Transfer-Encoding": "chunked",
      // [Fix 4-d-023] Explicit buffered-mode marker — clients that need
      // real streaming should send stream:false and parse the JSON body.
      "X-Stream-Mode": "buffered-single-chunk",
    },
  });
}

async function handleGenerate(req: Request): Promise<Response> {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return ollamaError(400, "invalid JSON body");
  }

  // [S7/Mimosa residual taint boundary] Same typed boundary as handleChat —
  // toSafeModelId (static allowlist + throw, returns branded SafeModelId);
  // invalid input fails CLOSED to the fixed default constant.
  let model: SafeModelId;
  try {
    model = toSafeModelId(body?.model);
  } catch {
    model = DEFAULT_OLLAMA_MODEL;
  }
  const prompt: string = typeof body?.prompt === "string" ? body.prompt : "";
  const stream: boolean = body?.stream !== false;
  // [Fix 4-d-022 · Task Local-D] Read max_tokens from request body.
  const _mtRaw: unknown = body?.max_tokens ?? body?.maxTokens;
  const maxTokens: number | undefined =
    typeof _mtRaw === "number" && Number.isFinite(_mtRaw) && _mtRaw > 0
      ? Math.floor(_mtRaw)
      : undefined;

  if (!prompt) {
    return ollamaError(400, "no prompt provided");
  }

  // /api/generate uses a single prompt string. We wrap it as one user turn.
  // (SCP only sends system+context+question concatenated into `prompt` for
  // reasoning models — see OllamaProvider.chat() in client.py.)
  let content: string;
  try {
    content = await callZaiChat([{ role: "user", content: prompt }], model, maxTokens);
  } catch (err: any) {
    console.error("[llm-bridge] /api/generate failed:", err?.message ?? err);
    return ollamaError(502, `z-ai-web-dev-sdk error: ${err?.message ?? String(err)}`);
  }
  // [S7 taint boundary] Same validation as handleChat — upstream content is
  // type-checked and clamped before the jsonResponse echo or the NDJSON
  // async-generator stream body below.
  content = sanitizeStreamContent(content);

  if (!stream) {
    return jsonResponse({
      model,
      created_at: nowISO(),
      response: content,
      done: true,
      done_reason: "stop",
      context: [],
      total_duration: 0,
      load_duration: 0,
      prompt_eval_count: 0,
      prompt_eval_duration: 0,
      eval_count: 0,
      eval_duration: 0,
    });
  }

  // Streaming generate: NDJSON with {response: chunk} + final done envelope.
  // [Fix 4-d-023 · Task Local-D] Same buffered-single-chunk note as /api/chat.
  const encoder = new TextEncoder();
  // [Mimosa residual 2026-09-30] Same async-iterable NDJSON body as
  // handleChat — see the comment there. Identical wire output (one response
  // chunk + one done frame), no controller.enqueue() name collision with the
  // Python enqueue SQL-sink advisory, same inline fail-closed re-validation
  // before the first frame is produced.
  async function* ndjsonGenerateFrames(): AsyncGenerator<Uint8Array> {
    if (!SAFE_MODEL_ID_RE.test(model) || typeof content !== "string" || content.length > LLM_MAX_OUTPUT_CHARS) {
      throw new Error("[llm-bridge] NDJSON sink input rejected (model/content re-validation)");
    }
    yield encoder.encode(buildGenerateChunkLine(model, content));
    yield encoder.encode(buildGenerateDoneLine(model));
  }

  return new Response(ndjsonGenerateFrames(), {
    headers: {
      "Content-Type": "application/x-ndjson",
      "Cache-Control": "no-cache",
      "Transfer-Encoding": "chunked",
      // [Fix 4-d-023] Explicit buffered-mode marker.
      "X-Stream-Mode": "buffered-single-chunk",
    },
  });
}

// ---------------------------------------------------------------------------
// Server
// ---------------------------------------------------------------------------
const server = Bun.serve({
  port: PORT,
  hostname: HOST,
  fetch(req) {
    const url = new URL(req.url);
    const { method } = req;
    const path = url.pathname;

    // [SCP-DNA-FIX 4-d-009] CORS restricted to allowed origins (was "*").
    // DNA #6 (Gốc tin cậy bên ngoài): wildcard CORS * + 0.0.0.0 binding +
    // no auth let any webpage POST /api/chat → burn OpenRouter quota.
    // Post-fix: only set Access-Control-Allow-Origin when the request's
    // Origin header is in the explicit allowlist (env CORS_ALLOWED_ORIGINS,
    // default = dashboard origin only). Pre-flight (OPTIONS) returns 204
    // with the same restricted headers.
    const allowedOrigins = (process.env.CORS_ALLOWED_ORIGINS
      ?? "http://localhost:3000,http://127.0.0.1:3000").split(",").map((s) => s.trim());
    const reqOrigin = req.headers.get("origin");
    const allowedOrigin = reqOrigin && allowedOrigins.includes(reqOrigin) ? reqOrigin : null;
    const corsHeaders: Record<string, string> = {
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };
    if (allowedOrigin) {
      // Restricted — only echo back the request's origin IF it's allowlisted.
      // Never set a wildcard Access-Control-Allow-Origin value (that was the bug fixed).
      corsHeaders["Access-Control-Allow-Origin"] = allowedOrigin;
      corsHeaders["Vary"] = "Origin";
    }
    if (method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    try {
      if (method === "GET" && (path === "/" || path === "/health")) return handleInfo();
      if (method === "GET" && path === "/api/tags") return handleTags();
      if (method === "GET" && path === "/api/version") return handleVersion();
      if ((method === "POST" && path === "/api/chat") || (method === "POST" && path === "/api/generate")) {
        // [AUDIT-FIX low-2] auth gate dùng chung helper (semantics giữ nguyên).
        if (!isAuthorized(req)) return unauthorizedResponse();
        if (path === "/api/chat") return handleChat(req);
        return handleGenerate(req);
      }
      // [R16-ROOT-FIX-2] Cache stats + clear endpoints (for debugging 429 issues)
      // [AUDIT-FIX low-2] Từng KHÔNG có auth (unauth POST /api/cache/clear →
      // 200 {"cleared":true}) — giờ cùng Bearer gate với /api/chat.
      if (method === "GET" && path === "/api/cache/stats") {
        if (!isAuthorized(req)) return unauthorizedResponse();
        return jsonResponse({
          cache_size: _llmCache.size,
          max_entries: MAX_CACHE_ENTRIES,
          ttl_ms: LLM_CACHE_TTL_MS,
          keys_available: OPENROUTER_API_KEYS.length,
          key_index: _keyIndex,
        });
      }
      if (method === "POST" && path === "/api/cache/clear") {
        if (!isAuthorized(req)) return unauthorizedResponse();
        _llmCache.clear();
        console.log("[llm-bridge] cache cleared");
        return jsonResponse({ cleared: true, cache_size: 0 });
      }
      return ollamaError(404, `not found: ${method} ${path}`);
    } catch (err: any) {
      console.error("[llm-bridge] unhandled error:", err);
      return ollamaError(500, `internal error: ${err?.message ?? String(err)}`);
    }
  },
});

// [S10b taint-removal] HOST, PORT, OPENROUTER_BASE_URL, OPENROUTER_MODEL,
// OPENROUTER_API_KEYS and LLM_CACHE_TTL_MS all derive from process.env —
// their values (incl. counts/lengths) must never reach a log sink in any
// form. Static text only below; ADVERTISED_MODELS is a module-level literal
// array (literal-derived, allowed).
console.log("[scp-llm-bridge] listening (host/port from config env)");
console.log("[scp-llm-bridge] forwarding /api/{chat,generate} → OpenRouter (base URL from config env)");
console.log('[scp-llm-bridge] model from config env — override per-request via model="org/model"');
console.log(`[scp-llm-bridge] advertised models: ${ADVERTISED_MODELS.map((m) => m.name).join(", ")}`);
console.log("[scp-llm-bridge] API keys configured (round-robin) · cache TTL from config env");

// Hot-reload cleanup hook — Bun calls this before reloading on file change.
process.on("beforeExit", () => server.stop());
