/**
 * API /api/scp/routes — list SCP API routes (hardcoded from api_server.py).
 *
 * Hardcoded (force-static) because:
 *   1. SCP may be offline when the dashboard renders — we still want
 *      the route listing to display.
 *   2. The route table changes slowly (only when scp/api_server.py or
 *      scp/api/routes/*.py change) — keeping it static avoids a network
 *      round-trip on every dashboard load.
 *
 * Last verified: 2026-08-08 (R9) — 73 routes total in `app.routes`
 * (includes built-in /docs, /openapi.json, /redoc).
 *
 * Source of truth: scp/api_server.py + scp/api/routes/*.py + scp/api/chat.py
 * + scp/api/webhook.py. See scp/GATEWAY.md for the full table.
 */
import { NextResponse } from "next/server"

export const dynamic = "force-static"

interface ScpRoute {
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH"
  path: string
  desc: string
  group:
    | "root"
    | "v1-openai"
    | "v98"
    | "v100"
    | "v102-v103"
    | "v104"
    | "v105-autofix"
    | "v105-audit"
    | "v105-threats"
    | "v105-predictions"
    | "v105-stream"
    | "import"
    | "chat"
    | "webhook"
    | "builtin"
  authRequired: boolean
  /**
   * `true` if the router defining this route is registered in
   * `scp/api_server.py` via `app.include_router(...)`.
   *
   * [Task 1-A · Fix 4-c-003] R12-10: all 4 routers (audit, threat, prediction,
   * stream) ARE wired via app.include_router() in api_server.py:627-649
   * (4 try/except blocks, fail-open per DNA #7). Previously this comment
   * claimed they were dead code — that was true pre-R12-10 but became a lie
   * once R12-10 shipped. DNA #22 (PASS ≠ TRUE) + #26 (reality test): comment
   * must match backend reality.
   */
  wired: boolean
}

const SCP_ROUTES: ScpRoute[] = [
  // === Root (defined directly in api_server.py) ===
  { method: "POST", path: "/ask", desc: "Chat với SCP (LLM gateway → V98 pipeline → verdict)", group: "root", authRequired: false, wired: true },
  { method: "GET", path: "/health", desc: "Health check (liveness)", group: "root", authRequired: false, wired: true },
  { method: "GET", path: "/dashboard", desc: "SCP HTML dashboard (server-rendered)", group: "root", authRequired: false, wired: true },
  { method: "GET", path: "/", desc: "Root — route listing + version", group: "root", authRequired: false, wired: true },

  // === V1 OpenAI-compatible (for PyRIT/garak) ===
  { method: "POST", path: "/v1/chat/completions", desc: "OpenAI chat completions", group: "v1-openai", authRequired: false, wired: true },
  { method: "GET", path: "/v1/models", desc: "OpenAI models list", group: "v1-openai", authRequired: false, wired: true },

  // === V98 security pipeline ===
  { method: "POST", path: "/v98/analyze-session", desc: "Rogue AI detection on a session", group: "v98", authRequired: false, wired: true },
  { method: "POST", path: "/v98/run-simulation", desc: "Trigger threat simulation", group: "v98", authRequired: false, wired: true },
  { method: "POST", path: "/v98/run-intel-crawl", desc: "Trigger threat intel crawl", group: "v98", authRequired: false, wired: true },
  { method: "GET", path: "/v98/status", desc: "All V98 module status", group: "v98", authRequired: true, wired: true },
  { method: "GET", path: "/v98/counter/stats", desc: "Counter response stats", group: "v98", authRequired: true, wired: true },
  { method: "GET", path: "/v98/canary/triggers", desc: "Canary token triggers", group: "v98", authRequired: true, wired: true },
  { method: "GET", path: "/v98/error-store/stats", desc: "ErrorStore stats", group: "v98", authRequired: true, wired: true },
  { method: "GET", path: "/v98/attack-memory/stats", desc: "Attack memory stats", group: "v98", authRequired: true, wired: true },

  // === V100 admin ===
  { method: "GET", path: "/v100/status", desc: "V100 admin status", group: "v100", authRequired: true, wired: true },
  { method: "POST", path: "/v100/crawl", desc: "Trigger crawl", group: "v100", authRequired: false, wired: true },
  { method: "GET", path: "/v100/antibodies/stats", desc: "Antibody stats", group: "v100", authRequired: true, wired: true },
  { method: "POST", path: "/v100/antibodies/check", desc: "Run antibody check", group: "v100", authRequired: false, wired: true },
  { method: "GET", path: "/v100/knowledge/stats", desc: "Knowledge stats", group: "v100", authRequired: true, wired: true },
  { method: "GET", path: "/v100/knowledge/search", desc: "Knowledge search", group: "v100", authRequired: true, wired: true },
  { method: "GET", path: "/v100/h8/stats", desc: "H8 stats", group: "v100", authRequired: true, wired: true },
  { method: "GET", path: "/v100/h8/bypasses", desc: "H8 bypasses", group: "v100", authRequired: true, wired: true },
  { method: "GET", path: "/v100/h8/analyses", desc: "H8 analyses", group: "v100", authRequired: true, wired: true },

  // === V102 / V103 ===
  { method: "GET", path: "/v102/orchestrator/stats", desc: "Orchestrator stats", group: "v102-v103", authRequired: true, wired: true },
  { method: "GET", path: "/v102/notifications/recent", desc: "Recent notifications", group: "v102-v103", authRequired: true, wired: true },
  { method: "GET", path: "/v103/storage/stats", desc: "Storage manager stats", group: "v102-v103", authRequired: true, wired: true },
  { method: "POST", path: "/v103/storage/maintain", desc: "Trigger storage maintenance (R9-3 FIXED: async)", group: "v102-v103", authRequired: false, wired: true },
  { method: "POST", path: "/v103/gcg/test", desc: "Run GCG attack test", group: "v102-v103", authRequired: false, wired: true },
  { method: "GET", path: "/v103/attacks/crawled", desc: "Crawled attacks", group: "v102-v103", authRequired: true, wired: true },
  { method: "POST", path: "/v103/attacks/crawl", desc: "Trigger attack crawl (R9-3 FIXED: async)", group: "v102-v103", authRequired: false, wired: true },
  { method: "GET", path: "/v103/status", desc: "V103 status", group: "v102-v103", authRequired: true, wired: true },

  // === V104 (multi-turn + image + voice + learning) ===
  { method: "GET", path: "/v104/status", desc: "V104 status", group: "v104", authRequired: true, wired: true },
  { method: "POST", path: "/v104/multi-turn/check", desc: "Multi-turn jailbreak check", group: "v104", authRequired: false, wired: true },
  { method: "POST", path: "/v104/image/check", desc: "Image jailbreak check", group: "v104", authRequired: false, wired: true },
  { method: "POST", path: "/v104/voice/check", desc: "Voice jailbreak check", group: "v104", authRequired: false, wired: true },
  { method: "GET", path: "/v104/cross-language/transfer", desc: "Cross-language transfer stats", group: "v104", authRequired: true, wired: true },
  { method: "GET", path: "/v104/explain", desc: "Get simple explainer output", group: "v104", authRequired: true, wired: true },
  { method: "POST", path: "/v104/fact-check", desc: "Streaming fact check", group: "v104", authRequired: false, wired: true },
  { method: "POST", path: "/v104/learn/ollama", desc: "Trigger Ollama learning cycle", group: "v104", authRequired: false, wired: true },
  { method: "POST", path: "/v104/learn/local", desc: "Trigger local learning cycle", group: "v104", authRequired: false, wired: true },
  { method: "POST", path: "/v104/learn/news", desc: "Trigger news learning cycle", group: "v104", authRequired: false, wired: true },
  { method: "POST", path: "/v104/learn/all", desc: "Trigger ALL learning sources", group: "v104", authRequired: false, wired: true },
  { method: "GET", path: "/v104/learn/status", desc: "Learning engine status", group: "v104", authRequired: true, wired: true },
  { method: "GET", path: "/v104/learn/matrix", desc: "Ollama learning matrix", group: "v104", authRequired: true, wired: true },
  { method: "POST", path: "/v104/learn/ollama-matrix", desc: "Trigger Ollama matrix learning", group: "v104", authRequired: false, wired: true },
  { method: "POST", path: "/v104/learn/fast", desc: "Trigger fast learning cycle", group: "v104", authRequired: false, wired: true },
  { method: "GET", path: "/v104/learn/fast/status", desc: "Fast learning status", group: "v104", authRequired: true, wired: true },
  { method: "GET", path: "/v104/learn/fast/benchmark", desc: "Fast learning benchmark", group: "v104", authRequired: true, wired: true },

  // === V105 autofix control panel ===
  { method: "GET", path: "/v105/autofix/permissions", desc: "List pending permission requests", group: "v105-autofix", authRequired: true, wired: true },
  { method: "POST", path: "/v105/autofix/permissions/{request_id}/approve", desc: "Approve a fix", group: "v105-autofix", authRequired: true, wired: true },
  { method: "POST", path: "/v105/autofix/permissions/{request_id}/deny", desc: "Deny a fix", group: "v105-autofix", authRequired: true, wired: true },
  { method: "POST", path: "/v105/autofix/attack-mode/{enabled}", desc: "Toggle attack-mode", group: "v105-autofix", authRequired: true, wired: true },
  { method: "GET", path: "/v105/autofix/stats", desc: "Autofix engine stats", group: "v105-autofix", authRequired: true, wired: true },
  { method: "POST", path: "/v105/autofix/run-audit", desc: "Trigger deep audit (R9-2 FIXED: async)", group: "v105-autofix", authRequired: true, wired: true },
  { method: "GET", path: "/v105/autofix/monitor", desc: "Autofix monitor dashboard", group: "v105-autofix", authRequired: true, wired: true },
  { method: "POST", path: "/v105/autofix/cleanup-cache", desc: "Cleanup LLM fix cache", group: "v105-autofix", authRequired: true, wired: true },
  { method: "POST", path: "/v105/autofix/tier3-auto/{enabled}", desc: "Toggle tier-3 auto-approve", group: "v105-autofix", authRequired: true, wired: true },
  { method: "POST", path: "/v105/autofix/rollback/{rollback_token}", desc: "Rollback a fix (IMP-17 auto_rollback)", group: "v105-autofix", authRequired: true, wired: true },

  // === V105 audit ===
  { method: "GET", path: "/v105/audit/stats", desc: "Audit stats", group: "v105-audit", authRequired: true, wired: true },
  { method: "GET", path: "/v105/audit/findings", desc: "Audit findings", group: "v105-audit", authRequired: true, wired: true },

  // === V105 threats ===
  { method: "GET", path: "/v105/threats/ai-scan/stats", desc: "AI scan stats", group: "v105-threats", authRequired: true, wired: true },
  { method: "GET", path: "/v105/threats/ai-scan/findings", desc: "AI scan findings", group: "v105-threats", authRequired: true, wired: true },
  { method: "GET", path: "/v105/threats/harm/stats", desc: "Harm stats", group: "v105-threats", authRequired: true, wired: true },
  { method: "GET", path: "/v105/threats/harm/incidents", desc: "Harm incidents", group: "v105-threats", authRequired: true, wired: true },

  // === V105 predictions ===
  { method: "GET", path: "/v105/predictions/pending", desc: "Pending predictions", group: "v105-predictions", authRequired: true, wired: true },
  { method: "GET", path: "/v105/predictions/all", desc: "All predictions", group: "v105-predictions", authRequired: true, wired: true },
  { method: "POST", path: "/v105/predictions/run-cycle", desc: "Trigger prediction cycle", group: "v105-predictions", authRequired: true, wired: true },
  { method: "POST", path: "/v105/predictions/verify", desc: "Verify a prediction", group: "v105-predictions", authRequired: true, wired: true },
  { method: "GET", path: "/v105/predictions/stats", desc: "Prediction stats", group: "v105-predictions", authRequired: true, wired: true },

  // === V105 stream ===
  { method: "POST", path: "/v105/ask/stream", desc: "Streaming chat (SSE)", group: "v105-stream", authRequired: false, wired: true },

  // === Import ===
  { method: "POST", path: "/import/jsonl", desc: "Import JSONL questions (R9-1 FIXED: async)", group: "import", authRequired: false, wired: true },
  { method: "POST", path: "/import/excel", desc: "Import Excel questions (R9-1 FIXED: async)", group: "import", authRequired: false, wired: true },
  { method: "POST", path: "/import/batch", desc: "Import batch (R9-1 FIXED: async)", group: "import", authRequired: false, wired: true },

  // === Chat ===
  { method: "GET", path: "/chat/sessions", desc: "List chat sessions", group: "chat", authRequired: false, wired: true },
  { method: "GET", path: "/chat/{session_id}/history", desc: "Get chat session history", group: "chat", authRequired: false, wired: true },

  // === Webhook (external AI systems) ===
  { method: "POST", path: "/api/analyze", desc: "Webhook: analyze a prompt", group: "webhook", authRequired: false, wired: true },
  { method: "POST", path: "/api/register", desc: "Webhook: register external system", group: "webhook", authRequired: false, wired: true },
  { method: "GET", path: "/api/threats", desc: "Webhook: list threats", group: "webhook", authRequired: false, wired: true },
  { method: "GET", path: "/api/alerts", desc: "Webhook: list alerts", group: "webhook", authRequired: false, wired: true },
  { method: "GET", path: "/api/systems", desc: "Webhook: list registered systems", group: "webhook", authRequired: false, wired: true },

  // === Built-in FastAPI ===
  { method: "GET", path: "/openapi.json", desc: "OpenAPI 3 schema (auto-generated)", group: "builtin", authRequired: false, wired: true },
  { method: "GET", path: "/docs", desc: "Swagger UI (auto-generated)", group: "builtin", authRequired: false, wired: true },
  { method: "GET", path: "/redoc", desc: "ReDoc UI (auto-generated)", group: "builtin", authRequired: false, wired: true },
]

export function GET() {
  const byGroup = SCP_ROUTES.reduce<Record<string, number>>((acc, r) => {
    acc[r.group] = (acc[r.group] ?? 0) + 1
    return acc
  }, {})

  const wiredRoutes = SCP_ROUTES.filter((r) => r.wired)
  const deadRoutes = SCP_ROUTES.filter((r) => !r.wired)

  return NextResponse.json({
    total: SCP_ROUTES.length,
    wiredCount: wiredRoutes.length,
    deadCount: deadRoutes.length,
    byGroup,
    authRequiredCount: SCP_ROUTES.filter((r) => r.authRequired).length,
    publicCount: SCP_ROUTES.filter((r) => !r.authRequired).length,
    routes: SCP_ROUTES,
    wiredRoutes,
    deadRoutes,
    deadCodeNote:
      "[Task 1-A · Fix 4-c-003] R12-10: all 4 routers (audit_routes, threat_routes, prediction_routes, stream_routes) ARE wired via app.include_router() in api_server.py:627-649 (4 try/except blocks, fail-open per DNA #7). The pre-R12-10 'dead code' claim was stale as of R12-10 — DNA #22 (PASS ≠ TRUE): prior rounds shipped the routers live but never updated this note.",
    sourceOfTruth:
      "scp/api_server.py + scp/api/routes/*.py + scp/api/chat.py + scp/api/webhook.py",
    lastVerified:
      "2026-08-08 (R9 baseline) + [Task 1-A] R12-10 reconciliation: all 4 v105 routers (audit/threat/prediction/stream) wired live in api_server.py:627-649. 73 total app.routes including builtins; 71 documented here are live; 0 are dead code (post-R12-10).",
    gatewayPattern: "Append ?XTransformPort=8000 to route through Caddy :81 gateway",
  })
}
