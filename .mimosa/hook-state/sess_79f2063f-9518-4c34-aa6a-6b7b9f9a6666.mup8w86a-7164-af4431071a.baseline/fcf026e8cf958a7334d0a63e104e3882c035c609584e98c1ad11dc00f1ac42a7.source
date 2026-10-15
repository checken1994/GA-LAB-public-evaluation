#!/usr/bin/env node
/**
 * Minimal Anthropic Messages API → OpenAI Chat Completions proxy.
 * Enables Claude Code to use any OpenAI-compatible API (Groq, OpenRouter,
 * local models, etc.) without an Anthropic API key.
 *
 * This is a JSON-to-JSON API proxy (Content-Type: application/json only).
 * It does NOT serve HTML. All responses use JSON.stringify with explicit
 * content-type headers.
 */
const http = require("http");
const https = require("https");

const PORT = Number(process.env.PROXY_PORT ?? 8082);
const TARGET = process.env.PROXY_TARGET_URL ?? "https://api.groq.com/openai/v1";
const API_KEY = process.env.PROXY_API_KEY ?? "";
const DEFAULT_MODEL = process.env.PROXY_MODEL ?? "openai/gpt-oss-120b";

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
  if (req.method !== "POST" || !req.url.includes("/messages")) {
    if (req.url === "/health" || req.url === "/") {
      return sendJson(res, 200, { status: "ok", target: TARGET, model: DEFAULT_MODEL });
    }
    return sendJson(res, 404, { error: "not found" });
  }

  let body = "";
  req.on("data", (chunk) => (body += chunk));
  req.on("end", () => {
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
          const result = openaiToAnthropic(parsed, openaiBody.model);
          sendJson(res, 200, result);
        } catch (e) {
          sendJson(res, 502, { error: { type: "api_error", message: `upstream parse error: ${e.message}` } });
        }
      });
    });
    outReq.on("error", (e) => {
      sendJson(res, 502, { error: { type: "api_error", message: `upstream connection: ${e.message}` } });
    });
    outReq.write(payload);
    outReq.end();
  });
});

server.listen(PORT, () => {
  console.log(`[anthropic-proxy] JSON-to-JSON API proxy listening on :${PORT}`);
  console.log(`[anthropic-proxy] target: ${TARGET} (model: ${DEFAULT_MODEL})`);
  console.log(`[anthropic-proxy] Claude Code env:`);
  console.log(`  ANTHROPIC_BASE_URL=http://127.0.0.1:${PORT}`);
  console.log(`  ANTHROPIC_API_KEY=proxy-local`);
});
