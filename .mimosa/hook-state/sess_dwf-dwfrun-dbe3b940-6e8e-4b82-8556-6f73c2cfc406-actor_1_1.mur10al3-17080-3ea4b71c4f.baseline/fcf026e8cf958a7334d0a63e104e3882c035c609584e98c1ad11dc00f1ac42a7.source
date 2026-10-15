#!/usr/bin/env node
/**
 * Minimal Anthropic Messages API → OpenAI Chat Completions proxy.
 * Enables Claude Code to use any OpenAI-compatible API (Groq, OpenRouter,
 * local models, etc.) without an Anthropic API key.
 *
 * This is a JSON-to-JSON API proxy (Content-Type: application/json only).
 * It does NOT serve HTML. All responses use JSON.stringify with explicit
 * content-type headers.
 *
 * Security contract (audit C-01, 2026-10-01):
 * - Binds to 127.0.0.1 only (loopback); never exposed on a public interface.
 * - Client auth REQUIRED: set PROXY_CLIENT_TOKEN in the environment. The
 *   client must present the same value via the `x-api-key` header OR
 *   `Authorization: Bearer <token>`. Comparison is timing-safe.
 * - Fail-closed: if PROXY_CLIENT_TOKEN is unset/empty, EVERY request is
 *   rejected with 401 and nothing is forwarded upstream.
 * - Request body cap: PROXY_MAX_BODY_BYTES (default 1 MiB); larger bodies
 *   are rejected with 413.
 * - Upstream error details are logged server-side only; clients get a
 *   generic message (no upstream exception text echoed back).
 *
 * Usage:
 *   PROXY_CLIENT_TOKEN=<random-string> PROXY_API_KEY=<upstream-key> \
 *     PROXY_TARGET_URL=https://api.groq.com/openai/v1 node tools/anthropic_proxy.js
 *   # Claude Code env:
 *   #   ANTHROPIC_BASE_URL=http://127.0.0.1:8082
 *   #   ANTHROPIC_API_KEY=<same value as PROXY_CLIENT_TOKEN>
 */
const http = require("http");
const https = require("https");
const crypto = require("crypto");

const PORT = Number(process.env.PROXY_PORT ?? 8082);
const TARGET = process.env.PROXY_TARGET_URL ?? "https://api.groq.com/openai/v1";
const API_KEY = process.env.PROXY_API_KEY ?? "";
const DEFAULT_MODEL = process.env.PROXY_MODEL ?? "openai/gpt-oss-120b";
const CLIENT_TOKEN = process.env.PROXY_CLIENT_TOKEN ?? "";
const MAX_BODY_BYTES = Number(process.env.PROXY_MAX_BODY_BYTES ?? 1048576);

const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "X-Content-Type-Options": "nosniff",
  "Cache-Control": "no-store",
};

function sendJson(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, JSON_HEADERS);
  res.end(body);
}

/** Timing-safe string comparison, length-normalized via SHA-256 digests. */
function timingSafeEqualStr(a, b) {
  const da = crypto.createHash("sha256").update(a, "utf8").digest();
  const db = crypto.createHash("sha256").update(b, "utf8").digest();
  return crypto.timingSafeEqual(da, db);
}

function extractClientToken(req) {
  const xApiKey = req.headers["x-api-key"];
  if (typeof xApiKey === "string" && xApiKey.length > 0) return xApiKey;
  const auth = req.headers["authorization"];
  if (typeof auth === "string" && auth.toLowerCase().startsWith("bearer ")) {
    return auth.slice("bearer ".length).trim();
  }
  return "";
}

/** Fail-closed client auth: unset/empty configured token => reject all. */
function clientAuthorized(req) {
  if (CLIENT_TOKEN.length === 0) return false;
  const presented = extractClientToken(req);
  if (presented.length === 0) return false;
  return timingSafeEqualStr(presented, CLIENT_TOKEN);
}

function anthropicToOpenai(body) {
  const messages = [];
  if (body.system) {
    messages.push({ role: "system", content: body.system });
  }
  for (const msg of body.messages ?? []) {
    const content = typeof msg.content === "string"
      ? msg.content
      : (msg.content ?? []).filter(b => b.type === "text").map(b => b.text).join("\n");
    messages.push({ role: msg.role, content });
  }
  return {
    model: DEFAULT_MODEL,  // ALWAYS override — Claude Code sends Anthropic model names, we use our target
    messages,
    max_tokens: body.max_tokens ?? 4096,
    temperature: body.temperature ?? 0.7,
    stream: false,
  };
}

function openaiToAnthropic(data, model) {
  const choice = data.choices?.[0];
  const text = choice?.message?.content ?? "";
  return {
    id: data.id ?? `msg_${Date.now()}`,
    type: "message",
    role: "assistant",
    model: model ?? data.model ?? DEFAULT_MODEL,
    content: [{ type: "text", text }],
    stop_reason: choice?.finish_reason === "length" ? "max_tokens" : "end_turn",
    usage: {
      input_tokens: data.usage?.prompt_tokens ?? 0,
      output_tokens: data.usage?.completion_tokens ?? 0,
    },
  };
}

const server = http.createServer((req, res) => {
  if (!clientAuthorized(req)) {
    return sendJson(res, 401, { error: { type: "authentication_error", message: "unauthorized" } });
  }

  if (req.method !== "POST" || !req.url.includes("/messages")) {
    if (req.url === "/health" || req.url === "/") {
      return sendJson(res, 200, { status: "ok", target: TARGET, model: DEFAULT_MODEL });
    }
    return sendJson(res, 404, { error: "not found" });
  }

  const chunks = [];
  let bodyBytes = 0;
  let aborted = false;
  req.on("data", (chunk) => {
    if (aborted) return;
    bodyBytes += chunk.length;
    if (bodyBytes > MAX_BODY_BYTES) {
      aborted = true;
      return sendJson(res, 413, { error: { type: "invalid_request_error", message: "request body too large" } });
    }
    chunks.push(chunk);
  });
  req.on("end", () => {
    if (aborted) return;
    const body = Buffer.concat(chunks).toString("utf8");
    let anthropicReq;
    try {
      anthropicReq = JSON.parse(body);
    } catch (e) {
      return sendJson(res, 400, { error: { type: "invalid_request_error", message: "invalid JSON body" } });
    }

    const openaiBody = anthropicToOpenai(anthropicReq);
    const payload = JSON.stringify(openaiBody);
    const url = new URL(`${TARGET}/chat/completions`);
    const mod = url.protocol === "https:" ? https : http;

    const outReq = mod.request({
      hostname: url.hostname,
      port: url.port || (url.protocol === "https:" ? 443 : 80),
      path: url.pathname + url.search,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${API_KEY}`,
        "Content-Length": Buffer.byteLength(payload),
      },
    }, (outRes) => {
      let out = "";
      outRes.on("data", (c) => (out += c));
      outRes.on("end", () => {
        try {
          const parsed = JSON.parse(out);
          if (parsed && typeof parsed === "object" && parsed.error) {
            console.error(`[anthropic-proxy] upstream rejected request (status ${outRes.statusCode})`);
            return sendJson(res, 502, { error: { type: "api_error", message: `upstream rejected request (status ${outRes.statusCode})` } });
          }
          const result = openaiToAnthropic(parsed, openaiBody.model);
          sendJson(res, 200, result);
        } catch (e) {
          console.error(`[anthropic-proxy] upstream parse error: ${e.message}`);
          sendJson(res, 502, { error: { type: "api_error", message: "upstream returned an invalid response" } });
        }
      });
    });
    outReq.on("error", (e) => {
      console.error(`[anthropic-proxy] upstream connection error: ${e.message}`);
      sendJson(res, 502, { error: { type: "api_error", message: "upstream connection failed" } });
    });
    outReq.write(payload);
    outReq.end();
  });
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[anthropic-proxy] JSON-to-JSON API proxy listening on 127.0.0.1:${PORT} (loopback only)`);
  console.log(`[anthropic-proxy] target: ${TARGET} (model: ${DEFAULT_MODEL})`);
  if (CLIENT_TOKEN.length === 0) {
    console.error("[anthropic-proxy] FAIL-CLOSED: PROXY_CLIENT_TOKEN is unset — ALL requests will be rejected with 401.");
  }
  console.log(`[anthropic-proxy] Claude Code env:`);
  console.log(`  ANTHROPIC_BASE_URL=http://127.0.0.1:${PORT}`);
  console.log(`  ANTHROPIC_API_KEY=<value of PROXY_CLIENT_TOKEN>`);
});
