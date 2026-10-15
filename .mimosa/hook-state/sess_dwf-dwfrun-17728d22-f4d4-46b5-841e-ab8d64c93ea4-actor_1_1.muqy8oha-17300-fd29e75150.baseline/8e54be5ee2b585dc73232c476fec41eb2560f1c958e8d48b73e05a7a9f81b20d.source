/**
 * SCP Loop Scheduler — closed-loop mini-service.
 *
 * Goal (R10 Task 14.A):
 *   SCP has all the components of a self-healing closed loop (scan → detect →
 *   fix → verify) but NO scheduler to trigger it periodically. The story
 *   (Gà Lab) says "vòng lặp thay đổi hệ thống có thể khép kín" but it
 *   required manual trigger. This file IS the scheduler that closes the loop.
 *
 * What it does:
 *   1. Every LOOP_INTERVAL_SEC seconds (default 300 = 5 min), calls SCP's
 *      POST /v105/autofix/run-audit endpoint to trigger a deep audit cycle.
 *      SCP AST-scans scp/ for bugs, auto-fixes Tier 1/2, requests permission
 *      for Tier 3, writes per-bug result to data/deep_audit_results.jsonl.
 *   2. Logs every run to scp/data/loop_runs.jsonl:
 *        { ts, scp_online, status, findings_count, fixes_applied, error? }
 *   3. Exposes a small HTTP dashboard on port 3030:
 *        GET  /         — loop status JSON
 *        POST /trigger  — manually trigger a run now (returns run result)
 *        POST /pause    — pause the loop
 *        POST /resume   — resume the loop
 *        GET  /healthz  — liveness
 *   4. Reads loop_runs.jsonl on startup to restore total_runs count.
 *
 * Fail-open policy (DNA SCP #7 safe):
 *   - SCP offline             → log "scp_online: false", continue loop.
 *   - Log file unwritable     → log to stderr, continue loop.
 *   - Any other error         → log to stderr, continue loop.
 *   The loop NEVER crashes the scheduler. If SCP is offline for hours, the
 *   scheduler keeps probing every LOOP_INTERVAL_SEC and resumes the moment
 *   SCP comes back.
 *
 * Auth:
 *   The /v105/autofix/run-audit route requires admin auth (Depends(verify_admin)
 *   in scp/api/_shared.py). The scheduler reads SCP_AUTH_TOKEN_SECRET or
 *   SCP_AUTH_PASSWORD from env and sends it as a Bearer token. If neither is
 *   set, SCP will return 503 "Auth not configured" — we log that and continue.
 *
 * Run:
 *   cd "$SCP_ROOT/mini-services/loop-scheduler"
 *   bun run dev            # hot-reload dev mode
 *   bun index.ts           # production
 *
 * Env vars (all optional):
 *   LOOP_INTERVAL_SEC  — seconds between runs (default 300 = 5 min)
 *   SCP_BASE_URL       — SCP base URL (default http://127.0.0.1:8000)
 *   SCP_AUTH_TOKEN_SECRET — Bearer token for SCP admin endpoints
 *   SCP_AUTH_PASSWORD     — Alt auth (sent as Bearer if no token secret)
 *   LOOP_SCHEDULER_PORT — port to listen on (default 3030)
 *   LOOP_LOG_PATH       — path to jsonl log (default scp/data/loop_runs.jsonl)
 */

// ─── Config ────────────────────────────────────────────────────────────────

// [R16-ROOT-FIX-5] Load .env file — Bun does NOT auto-load .env (unlike Node
// with dotenv). BEFORE: SCP_AUTH_TOKEN was empty → /v105/autofix/run-audit
// returned 401 Unauthorized. AFTER: load .env from project root.
import { readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

// [S10 push-gate fix, S10b taint-removal] This function reads AND writes
// process.env (scanner-tainted scope). The resolved env-file path is
// process.env-derived and must therefore NEVER reach a log sink in any form
// (interpolation, separate argument, JSON) — callers log static text only.
function _loadEnvFile(): string | null {
  // Require an explicit env file; never silently load repository .env.
  const _raw = process.env.SCP_ENV_FILE || process.env.SCP_SIDECAR_ENV_FILE;
  if (!_raw || !_raw.trim()) {
    return null;
  }
  const _override = _raw.trim();
  const _isAbsolute = _override.startsWith("/") || _override.startsWith("\\") || /^[A-Za-z]:/.test(_override);
  const _p = _isAbsolute ? _override : join(process.cwd(), _override);
  if (!existsSync(_p)) throw new Error(`[loop-scheduler] explicit env file not found: ${_p}`);
  const _content = readFileSync(_p, "utf-8");
  const _envRoot = dirname(_p);
  for (const _line of _content.split("\n")) {
    const _trimmed = _line.trim();
    if (!_trimmed || _trimmed.startsWith("#") || !_trimmed.includes("=")) continue;
    const _eqIdx = _trimmed.indexOf("=");
    const _key = _trimmed.slice(0, _eqIdx).trim();
    let _val = _trimmed.slice(_eqIdx + 1).trim();
    if ((_val.startsWith('"') && _val.endsWith('"')) || (_val.startsWith("'") && _val.endsWith("'"))) _val = _val.slice(1, -1);
    if (_key && !process.env[_key]) process.env[_key] = _val;
    if (_key.endsWith("_FILE") && _val) {
      const _rawPath = _val.replace(/^@file:/, "").replace(/^file:\/\//, "");
      const _secretPath = (/^[A-Za-z]:[\\/]|^[/\\]/.test(_rawPath)) ? _rawPath : join(_envRoot, _rawPath);
      if (!existsSync(_secretPath)) throw new Error(`[loop-scheduler] secret file not found for ${_key}: ${_secretPath}`);
      process.env[_key] = _secretPath;
      const _secretValue = readFileSync(_secretPath, "utf-8").trim();
      if (!_secretValue) throw new Error(`[loop-scheduler] secret file empty for ${_key}`);
      const _valueKey = _key.slice(0, -5);
      if (!process.env[_valueKey]) process.env[_valueKey] = _secretValue;
    }
  }
  return _p;
}
// [S10c taint-removal] No log sink here. The resolved env-file path is
// process.env-derived, so it is never logged in any form (arg/template/JSON);
// whether an explicit env file is in effect is visible via SCP_ENV_FILE.
_loadEnvFile();

const LOOP_INTERVAL_SEC = Number(process.env.LOOP_INTERVAL_SEC ?? "300");
const AUTOFIX_MODE = (process.env.SCP_AUTOFIX_MODE ?? "observe").trim().toLowerCase();
const AUTOFIX_DETERMINISTIC_ONLY = (process.env.SCP_AUTOFIX_DETERMINISTIC_ONLY ?? "0").trim() === "1";
const AUTOFIX_WORKER_MODE = (process.env.SCP_AUTOFIX_WORKER_MODE ?? "inline").trim().toLowerCase();
const DETERMINISTIC_WORKER_LOOP = AUTOFIX_MODE === "apply" && AUTOFIX_DETERMINISTIC_ONLY && AUTOFIX_WORKER_MODE === "deterministic";
if (AUTOFIX_MODE !== "observe" && AUTOFIX_MODE !== "apply") {
  throw new Error(`[loop-scheduler] invalid SCP_AUTOFIX_MODE=${AUTOFIX_MODE}; refusing start`);
}
const AUTOFIX_MAX_BUGS = Math.max(0, Math.min(20, Number(process.env.SCP_MAX_AUDIT_BUGS ?? "5")));
const _scpBaseUrl = (process.env.SCP_BASE_URL || "").trim().replace(/\/+$/, "");
if (!_scpBaseUrl) throw new Error("[loop-scheduler] SCP_BASE_URL is required; refusing implicit backend default");
const SCP_BASE_URL = _scpBaseUrl;
const SCP_AUDIT_URL = `${SCP_BASE_URL}/v105/autofix/run-audit`;
const SCP_HEALTH_URL = `${SCP_BASE_URL}/health`;
const PORT = Number(process.env.LOOP_SCHEDULER_PORT ?? "3030");

// [Fix 4-d-011 · Task Local-D] LLM bridge URL for pre-flight check.
// DNA #19 (Tầng kiểm toán bằng chứng — observation gap closed) + #2 (vòng lặp
// khép kín — LLM step now visible to scheduler) + #22 (PASS ≠ TRUE — "scp_online"
// was misleading: SCP process alive but LLM bridge dead → every audit call
// fails with UNKNOWN verdicts → "0 found, 0 fixed" dashboard lie).
//
// BEFORE: scheduler only probed SCP /health. If SCP process was alive but
// the llm-bridge (port 11434) was down (or OpenRouter was 429'd), every
// LLM call inside the audit failed → UNKNOWN verdicts for every question.
// SCP still returned 200 with audit_complete:true → scheduler logged
// status: "ok". Dashboard showed "0 found · 0 fixed" — interpreted as
// "all clear" (DNA #22 PASS ≠ TRUE).
//
// AFTER: scheduler probes the LLM bridge /api/tags endpoint before triggering
// the audit. If bridge is unreachable, scheduler logs status: "bridge_offline"
// and SKIPS the audit call — saves a full cycle of wasted LLM calls.
const _llmBridgeUrl = (process.env.LLM_BRIDGE_URL || "").trim().replace(/\/+$/, "");
if (!_llmBridgeUrl) throw new Error("[loop-scheduler] LLM_BRIDGE_URL is required; refusing implicit bridge default");
const LLM_BRIDGE_URL = _llmBridgeUrl;
const LLM_BRIDGE_TAGS_URL = `${LLM_BRIDGE_URL}/api/tags`;
let activeBridgeUrl = LLM_BRIDGE_URL;

// Resolve log path. Default points at SCP's data dir so SCP-side tools +
// the dashboard can read the same file the scheduler writes.
const DEFAULT_LOG_PATH = pathJoin(process.cwd(), "..", "..", "data", "loop_runs.jsonl");
const LOOP_LOG_PATH = process.env.LOOP_LOG_PATH ?? DEFAULT_LOG_PATH;

// [Fix 4-d-019 · Task Local-D] Persisted pause-state file path. Restores
// pause across restarts (DNA #8 KB accumulation — pause decision logged
// durably; DNA #17 Hành động khi chưa biết hết — restart behavior no longer
// surprises the operator).
const DEFAULT_STATE_PATH = pathJoin(process.cwd(), "..", "..", "data", "scheduler-state.json");
const LOOP_STATE_PATH = process.env.LOOP_STATE_PATH ?? DEFAULT_STATE_PATH;

let SCHEDULER_ADMIN_TOKEN = "";
const SCP_AUTH_TOKEN =
  process.env.SCP_AUTH_TOKEN_SECRET ?? process.env.SCP_AUTH_PASSWORD ?? "";

// [Fix 4-d-012 · Task Local-D] SCP audit fetch timeout raised 120s → 600s.
// DNA #9 (No harm — duplicate side effects) + #17 (Hành động khi chưa biết
// hết — concurrent execution not analyzed) + #19 (observation gap).
//
// BEFORE: SCP_FETCH_TIMEOUT_MS = 120_000 (2 min). SCP audits can take 5–10
// minutes (run_deep_audit processes many bugs, each with its own LLM call).
// When the fetch aborted at 2 min, the scheduler's `state.running` flag was
// cleared (via finally), so the next cron tick (5 min later) fired another
// triggerAudit → POST to SCP /v105/autofix/run-audit → SCP started a SECOND
// concurrent audit (asyncio.to_thread) → race on data/deep_audit_results.jsonl,
// duplicate LLM calls, conflicting rollback tokens.
//
// AFTER: timeout raised to 600_000 (10 min). This covers the worst-case SCP
// audit duration. cronStep awaits triggerAudit, so the next tick can't fire
// while the previous is still running. The scheduler is "busy" during the
// audit (acceptable per DNA #17 — small reversible change with clear
// observation). An alternative would be fire-and-forget (don't await fetch,
// set a cooldown), but that loses the audit summary (findings_count,
// fixes_applied) and SCP's current endpoint is synchronous (no 202 + job ID).
const SCP_FETCH_TIMEOUT_MS = DETERMINISTIC_WORKER_LOOP ? 30_000 : 600_000;

// ─── Types ─────────────────────────────────────────────────────────────────

interface LoopRun {
  ts: string;                 // ISO timestamp
  scp_online: boolean;        // did SCP /health respond?
  // [Fix 4-d-011 · Task Local-D] Added "bridge_offline" status — surfaces the
  // case where SCP process is alive but LLM bridge (port 11434) is down.
  status: "ok" | "queued" | "error" | "scp_offline" | "bridge_offline" | "auth_required" | "skipped";
  findings_count?: number;    // bugs found in this audit cycle
  fixes_applied?: number;     // bugs auto-fixed (Tier 1/2)
  permission_requested?: number; // bugs needing human approval (Tier 3)
  skipped?: number;           // bugs skipped (cooldown / no fix)
  duration_ms?: number;       // wall-clock duration of the SCP call
  http_status?: number;       // SCP HTTP response status code
  error?: string;             // short error message (truncated)
  triggered_by: "cron" | "manual";
}

interface LoopState {
  running: boolean;           // is the loop active?
  paused: boolean;            // paused via /pause?
  last_run: LoopRun | null;
  next_run_at: number | null; // epoch ms
  total_runs: number;         // restored from log file on startup
  scp_online: boolean;        // last known SCP liveness
  // [Fix 4-d-011 · Task Local-D] track LLM bridge liveness so dashboard can
  // distinguish "SCP online but LLM bridge dead" from "everything online".
  bridge_online: boolean;
  recent_runs: LoopRun[];     // last 10 (in-memory cache)
}

const state: LoopState = {
  running: false,
  paused: false,
  last_run: null,
  next_run_at: null,
  total_runs: 0,
  scp_online: false,
  bridge_online: false,
  recent_runs: [],
};

// ─── Logging ───────────────────────────────────────────────────────────────

import { appendFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { join as pathJoin } from "node:path";

async function appendRunToLog(run: LoopRun): Promise<void> {
  const line = JSON.stringify(run) + "\n";
  try {
    // Ensure parent dir exists (handles first-run when scp/data/ may be
    // missing if scheduler starts before SCP). mkdir is idempotent.
    await mkdir(dirname(LOOP_LOG_PATH), { recursive: true });
    // appendFile is atomic-enough for our purposes (single scheduler process).
    await appendFile(LOOP_LOG_PATH, line, "utf8");
  } catch (e) {
    // Fail-open: log to stderr but DO NOT rethrow — the loop must keep ticking.
    console.error(
      `[loop-scheduler] log write failed: ${String(e).slice(0, 200)} — run was: ${line.trim()}`,
    );
  }
}

async function loadExistingRuns(): Promise<{ total: number; recent: LoopRun[] }> {
  try {
    const file = Bun.file(LOOP_LOG_PATH);
    if (!(await file.exists())) return { total: 0, recent: [] };
    const text = await file.text();
    const lines = text.split("\n").filter((l) => l.trim().length > 0);
    const runs: LoopRun[] = [];
    for (const line of lines) {
      try {
        runs.push(JSON.parse(line) as LoopRun);
      } catch {
        // skip malformed line
      }
    }
    const recent = runs.slice(-10).reverse(); // newest first
    return { total: runs.length, recent };
  } catch (e) {
    console.error(`[loop-scheduler] log read failed: ${String(e).slice(0, 200)}`);
    return { total: 0, recent: [] };
  }
}

// [Fix 4-d-019 · Task Local-D] Persist pause state to file so it survives
// restarts. DNA #8 (KB accumulation — pause decision logged durably) +
// #17 (Hành động khi chưa biết hết — restart behavior no longer surprises).
//
// BEFORE: `state.paused` was in-memory only. If operator called /pause then
// the scheduler restarted (crash, deploy), it resumed the loop automatically
// — operator's intention was silently overridden. Especially bad during
// maintenance: operator pauses for a deploy, scheduler crashes and restarts,
// fires an audit mid-deploy.
//
// AFTER: /pause writes `{"paused": true, "paused_at": <ts>}` to
// LOOP_STATE_PATH. /resume writes `{"paused": false}`. On boot, main() reads
// this file and restores state.paused BEFORE startLoop() — so a paused
// scheduler stays paused across restarts. The env var LOOP_START_PAUSED=1
// is also honored as an override (forces pause even if state file says
// otherwise) — useful for "don't start the loop until I'm ready".
// Fail-open (DNA #9): if the state file can't be read/written, scheduler
// continues with in-memory state (same as pre-fix behavior).
interface PersistedState {
  paused: boolean;
  paused_at: string | null;
}

async function loadPersistedState(): Promise<PersistedState | null> {
  try {
    const raw = await readFile(LOOP_STATE_PATH, "utf8");
    const parsed = JSON.parse(raw) as PersistedState;
    if (typeof parsed?.paused === "boolean") {
      return parsed;
    }
    return null;
  } catch {
    // File doesn't exist, can't be read, or is malformed JSON — treat as
    // no prior state (default: not paused).
    return null;
  }
}

async function savePersistedState(s: PersistedState): Promise<void> {
  try {
    await mkdir(dirname(LOOP_STATE_PATH), { recursive: true });
    await writeFile(LOOP_STATE_PATH, JSON.stringify(s, null, 2), "utf8");
  } catch (e) {
    // Fail-open: log and continue. Pause is also held in-memory for this
    // session — only the cross-restart persistence is lost.
    console.error(
      `[loop-scheduler] state write failed: ${String(e).slice(0, 200)} — state is ${JSON.stringify(s)}`,
    );
  }
}

// ─── SCP interaction ───────────────────────────────────────────────────────

async function checkScpLiveness(): Promise<boolean> {
  try {
    const res = await fetch(SCP_HEALTH_URL, {
      signal: AbortSignal.timeout(3000),
      headers: { Accept: "application/json" },
    });
    return res.ok;
  } catch {
    return false;
  }
}

// [Fix 4-d-011 · Task Local-D] Pre-flight LLM bridge liveness probe.
// DNA #19 (Tầng kiểm toán bằng chứng): SCP's audit calls the LLM bridge for
// every bug. If the bridge is down (OpenRouter 429 exhausted, bridge crashed,
// port conflict), every LLM call fails → UNKNOWN verdicts → wasted cycle.
// DNA #2 (vòng lặp khép kín): the LLM step is now visible to the scheduler.
// Returns true iff the bridge's /api/tags endpoint responds 200.
async function checkLlmBridgeLiveness(): Promise<boolean> {
  // 1. Try primary / currently active bridge URL
  try {
    const res = await fetch(`${activeBridgeUrl}/api/tags`, {
      signal: AbortSignal.timeout(3000),
      headers: { Accept: "application/json" },
    });
    if (res.ok) return true;
  } catch {
    // Configured port may be offline, probe standard candidate ports below
  }

  // 2. Candidate ports fallback across standard SCP bridge ports (11434, 8081)
  const candidates = [
    "http://127.0.0.1:11434",
    "http://127.0.0.1:8081",
  ].filter((u) => u !== activeBridgeUrl);

  for (const candidate of candidates) {
    try {
      const res = await fetch(`${candidate}/api/tags`, {
        signal: AbortSignal.timeout(2000),
        headers: { Accept: "application/json" },
      });
      if (res.ok) {
        console.log(`[loop-scheduler] auto-detected active LLM bridge at ${candidate}`);
        activeBridgeUrl = candidate;
        return true;
      }
    } catch {
      // try next
    }
  }

  return false;
}

/**
 * Extract a compact summary from SCP's run-audit response.
 *
 * SCP returns:
 *   { audit_complete: true,
 *     results: { processed, fixed, permission_requested, skipped,
 *                details, engine_stats, source } }
 *
 * We normalise into {findings_count, fixes_applied, permission_requested,
 * skipped} — defensive about shape (SCP versions vary).
 */
function extractSummary(scpBody: unknown): {
  findings_count?: number;
  fixes_applied?: number;
  permission_requested?: number;
  skipped?: number;
} {
  const out: { findings_count?: number; fixes_applied?: number;
               permission_requested?: number; skipped?: number } = {};
  if (typeof scpBody !== "object" || scpBody === null) return out;
  const root = scpBody as Record<string, unknown>;
  const results = (root.results ?? root) as Record<string, unknown> | undefined;
  if (!results || typeof results !== "object") return out;
  const num = (v: unknown): number | undefined =>
    typeof v === "number" ? v : (typeof v === "string" && /^\d+$/.test(v) ? Number(v) : undefined);
  // findings_count = total bugs processed
  const processed = num(results.processed) ?? num(results.total) ?? num(results.findings_count);
  if (processed !== undefined) out.findings_count = processed;
  const fixed = num(results.fixed) ?? num(results.fixes_applied);
  if (fixed !== undefined) out.fixes_applied = fixed;
  const perm = num(results.permission_requested) ?? num(results.permissionRequests);
  if (perm !== undefined) out.permission_requested = perm;
  const skip = num(results.skipped) ?? num(results.skipped_count);
  if (skip !== undefined) out.skipped = skip;
  return out;
}

async function triggerAudit(triggeredBy: "cron" | "manual"): Promise<LoopRun> {
  // [SCP-DNA-FIX 4-d-007] Concurrent-trigger guard (DNA #9 No harm +
  // #17 Hành động khi chưa biết hết). Pre-fix: triggerAudit had no
  // single-flight wrapper — if operator POSTed /trigger while a cron tick
  // was in-flight, BOTH audit calls hit SCP's /v105/autofix/run-audit
  // concurrently → racy writes to deep_audit_results.jsonl + duplicate
  // LLM calls + conflicting rollback tokens. Post-fix: state.running is
  // the in-flight flag, set at triggerAudit start, cleared in finally.
  // Callers (POST /trigger) check it FIRST and return 409 if set.
  //
  // We intentionally use state.running (not a separate flag) so the GET /
  // status endpoint also reports "running: true" accurately.
  state.running = true;
  const ts = new Date().toISOString();
  const start = Date.now();
  try {
    // Step 1: liveness probe (separate from the audit call so we can distinguish
    // "SCP offline" from "audit endpoint errored").
    const scp_online = await checkScpLiveness();
    if (!scp_online) {
      const run: LoopRun = {
        ts,
        scp_online: false,
        status: "scp_offline",
        triggered_by: triggeredBy,
        duration_ms: Date.now() - start,
        error: `SCP not responding at ${SCP_HEALTH_URL}`,
      };
      state.scp_online = false;
      await appendRunToLog(run);
      recordRun(run);
      return run;
    }
    state.scp_online = true;

    // Inline LLM audits need a bridge preflight. Deterministic worker mode
    // deliberately does not: it must remain useful during provider outage and
    // must not turn a local AST/patch queue into an LLM dependency.
    const bridge_online = DETERMINISTIC_WORKER_LOOP ? true : await checkLlmBridgeLiveness();
    state.bridge_online = bridge_online;
    if (!DETERMINISTIC_WORKER_LOOP) {
      if (!bridge_online) {
        const run: LoopRun = {
          ts,
          scp_online: true,
          status: "bridge_offline",
          triggered_by: triggeredBy,
          duration_ms: Date.now() - start,
          error: `LLM bridge not responding at ${activeBridgeUrl}/api/tags — audit skipped to avoid UNKNOWN verdicts`,
        };
        await appendRunToLog(run);
        recordRun(run);
        return run;
      }
    }

    // Step 2: trigger the audit
    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        Accept: "application/json",
      };
      if (SCP_AUTH_TOKEN) {
        headers.Authorization = `Bearer ${SCP_AUTH_TOKEN}`;
      }
      const res = await fetch(SCP_AUDIT_URL, {
        method: "POST",
        headers,
        signal: AbortSignal.timeout(SCP_FETCH_TIMEOUT_MS),
        body: JSON.stringify({ mode: AUTOFIX_MODE, max_bugs: AUTOFIX_MAX_BUGS }),
      });

      const duration_ms = Date.now() - start;
      let body: unknown = null;
      try {
        body = await res.json();
      } catch {
        // Non-JSON response — leave body null, surface status below.
      }

      if (res.status === 401 || res.status === 403) {
        const run: LoopRun = {
          ts,
          scp_online: true,
          status: "auth_required",
          http_status: res.status,
          duration_ms,
          triggered_by: triggeredBy,
          error: "SCP_AUTH_TOKEN_SECRET not configured or invalid (verify_admin rejected)",
        };
        await appendRunToLog(run);
        recordRun(run);
        return run;
      }
      if (!res.ok) {
        const errText = typeof body === "object" && body !== null
          ? JSON.stringify(body).slice(0, 200)
          : `HTTP ${res.status}`;
        const run: LoopRun = {
          ts,
          scp_online: true,
          status: "error",
          http_status: res.status,
          duration_ms,
          triggered_by: triggeredBy,
          error: errText,
        };
        await appendRunToLog(run);
        recordRun(run);
        return run;
      }

      const summary = extractSummary(body);
      const run: LoopRun = {
        ts,
        scp_online: true,
        status: (DETERMINISTIC_WORKER_LOOP && typeof body === "object" && body !== null && (body as Record<string, unknown>).mode === "queued") ? "queued" : "ok",
        http_status: res.status,
        duration_ms,
        triggered_by: triggeredBy,
        ...summary,
      };
      await appendRunToLog(run);
      recordRun(run);
      return run;
    } catch (e) {
      const err = e instanceof Error ? e.message : String(e);
      const run: LoopRun = {
        ts,
        scp_online: true,
        status: "error",
        duration_ms: Date.now() - start,
        triggered_by: triggeredBy,
        error: err.slice(0, 200),
      };
      await appendRunToLog(run);
      recordRun(run);
      return run;
    }
  } finally {
    // [4-d-007] CRITICAL: always clear the in-flight flag, even on
    // exception paths. Without finally, a thrown error would leave
    // state.running=true forever → all future /trigger calls return 409
    // (stuck state). The finally block is the safety net.
    state.running = false;
  }
}

function recordRun(run: LoopRun): void {
  state.last_run = run;
  state.total_runs += 1;
  state.recent_runs.unshift(run);
  if (state.recent_runs.length > 10) state.recent_runs.length = 10;
  // Re-compute next_run_at every time (in case interval changes via restart)
  state.next_run_at = state.paused ? null : Date.now() + LOOP_INTERVAL_SEC * 1000;
}

// ─── Cron loop ─────────────────────────────────────────────────────────────

let loopTimer: Timer | null = null;

async function cronStep(): Promise<void> {
  if (state.paused) {
    state.next_run_at = null;
    return;
  }
  // [4-d-007] state.running is now set inside triggerAudit (with finally
  // safety). cronStep no longer sets it — that was a race window where
  // state.running=true but triggerAudit hadn't started yet (so a manual
  // /trigger during that window would have been blocked unnecessarily).
  // Now: state.running accurately reflects "triggerAudit body in flight".
  try {
    await triggerAudit("cron");
  } catch (e) {
    // Must NEVER throw — would kill the timer chain.
    console.error(`[loop-scheduler] cronStep swallowed: ${String(e).slice(0, 200)}`);
  }
  // Schedule next tick
  if (!state.paused) {
    state.next_run_at = Date.now() + LOOP_INTERVAL_SEC * 1000;
    loopTimer = setTimeout(() => void cronStep(), LOOP_INTERVAL_SEC * 1000);
  }
}

function startLoop(): void {
  if (loopTimer) return;
  state.next_run_at = Date.now() + LOOP_INTERVAL_SEC * 1000;
  loopTimer = setTimeout(() => void cronStep(), LOOP_INTERVAL_SEC * 1000);
  // [S10b taint-removal] LOOP_INTERVAL_SEC, SCP_BASE_URL, LOOP_LOG_PATH all
  // derive from process.env — values never reach a log sink in any form.
  console.log("[loop-scheduler] loop started (interval/SCP URL/log path from config env)");
}

// ─── HTTP server ───────────────────────────────────────────────────────────

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      // CORS so the Next.js dashboard (port 3000) can fetch directly if needed.
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    },
  });
}

function constantTimeTokenEquals(provided: string, expected: string): boolean {
  const a = new TextEncoder().encode(provided);
  const b = new TextEncoder().encode(expected);
  let diff = a.length ^ b.length;
  const n = Math.max(a.length, b.length);
  for (let i = 0; i < n; i += 1) diff |= (a[i] ?? 0) ^ (b[i] ?? 0);
  return diff === 0;
}

function schedulerAdminAuthorized(req: Request): boolean {
  const authorization = req.headers.get("authorization") ?? "";
  const bearer = authorization.toLowerCase().startsWith("bearer ")
    ? authorization.slice(7).trim()
    : "";
  const headerToken = req.headers.get("x-scp-admin-token")?.trim() ?? "";
  return constantTimeTokenEquals(bearer || headerToken, SCHEDULER_ADMIN_TOKEN);
}

async function handleRequest(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const path = url.pathname;
  const method = req.method.toUpperCase();

  // Mutating scheduler controls are operator-only. A missing token is a
  // configuration error, not permission to run unauthenticated.
  if (method === "POST" && new Set(["/trigger", "/pause", "/resume"]).has(path)) {
    if (!SCHEDULER_ADMIN_TOKEN) {
      return jsonResponse({ error: "scheduler admin auth not configured" }, 503);
    }
    if (!schedulerAdminAuthorized(req)) {
      return jsonResponse({ error: "scheduler admin authentication required" }, 401);
    }
  }

  // CORS preflight
  if (method === "OPTIONS") {
    return new Response(null, { status: 204 });
  }

  // GET / — loop status
  if (method === "GET" && (path === "/" || path === "")) {
    if (!state.scp_online) state.scp_online = await checkScpLiveness();
    if (!state.bridge_online) state.bridge_online = await checkLlmBridgeLiveness();
    return jsonResponse({
      service: "scp-loop-scheduler",
      version: "0.1.0",
      running: state.running,
      paused: state.paused,
      last_run: state.last_run,
      next_run: state.paused ? null : (state.next_run_at
        ? new Date(state.next_run_at).toISOString() : null),
      next_run_epoch_ms: state.paused ? null : state.next_run_at,
      interval_sec: LOOP_INTERVAL_SEC,
      total_runs: state.total_runs,
      scp_online: state.scp_online,
      // [Fix 4-d-011 · Task Local-D] Expose bridge liveness so dashboard can
      // distinguish "SCP online but LLM bridge dead" from "everything online".
      bridge_online: state.bridge_online,
      bridge_url: activeBridgeUrl,
      scp_base_url: SCP_BASE_URL,
      scp_audit_url: SCP_AUDIT_URL,
      log_path: LOOP_LOG_PATH,
      // [Fix 4-d-019 · Task Local-D] Expose state file path so operator can
      // inspect/clear it manually if needed.
      state_path: LOOP_STATE_PATH,
      auth_configured: Boolean(SCP_AUTH_TOKEN),
      recent_runs: state.recent_runs,
    });
  }

  // GET /healthz — liveness (for monitoring)
  if (method === "GET" && path === "/healthz") {
    return jsonResponse({ status: "ok", service: "scp-loop-scheduler" });
  }

  // GET /ready and /readiness — explicit readiness aliases.  The scheduler
  // is ready once this handler is serving requests; its dependency state is
  // reported separately in the root status payload and each audit run.
  if (method === "GET" && (path === "/ready" || path === "/readiness")) {
    return jsonResponse({
      status: "ready",
      service: "scp-loop-scheduler",
      paused: state.paused,
      running: state.running,
      dependency_checks: {
        scp: state.scp_online ? "ok" : "unknown",
        llm_bridge: state.bridge_online ? "ok" : "unknown",
      },
    });
  }

  // POST /trigger — manual trigger (returns the run result).
  // [SCP-DNA-FIX 4-d-007] Concurrent-trigger guard (DNA #9 No harm).
  // Pre-fix: if operator POSTed /trigger while a cron tick was in
  // flight, BOTH audit calls hit SCP's /v105/autofix/run-audit
  // concurrently → racy writes to deep_audit_results.jsonl + duplicate
  // LLM calls + conflicting rollback tokens. Post-fix: check state.running
  // first; if set, return 409 'already running' instead of double-firing.
  if (method === "POST" && path === "/trigger") {
    if (state.running) {
      return jsonResponse(
        {
          error: "audit already running",
          triggered: false,
          running: true,
          last_run: state.last_run,
          message: "A cron tick or manual trigger is in flight. Retry in a few seconds.",
        },
        409, // HTTP 409 Conflict
      );
    }
    const run = await triggerAudit("manual");
    return jsonResponse({ triggered: true, run });
  }

  // POST /pause
  if (method === "POST" && path === "/pause") {
    state.paused = true;
    state.next_run_at = null;
    if (loopTimer) {
      clearTimeout(loopTimer);
      loopTimer = null;
    }
    // [Fix 4-d-019 · Task Local-D] Persist pause state so it survives restart.
    await savePersistedState({ paused: true, paused_at: new Date().toISOString() });
    return jsonResponse({ paused: true, next_run: null });
  }

  // POST /resume
  if (method === "POST" && path === "/resume") {
    if (!state.paused) {
      return jsonResponse({ resumed: false, note: "loop was not paused" });
    }
    state.paused = false;
    // [Fix 4-d-019 · Task Local-D] Persist resume state too.
    await savePersistedState({ paused: false, paused_at: null });
    startLoop();
    return jsonResponse({
      resumed: true,
      next_run: state.next_run_at ? new Date(state.next_run_at).toISOString() : null,
    });
  }

  // 404
  return jsonResponse({ error: "not found", path, method }, 404);
}

// ─── Bootstrap ─────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  SCHEDULER_ADMIN_TOKEN = (process.env.SCP_SCHEDULER_ADMIN_TOKEN ?? "").trim();
  const tokenFile = (process.env.SCP_SCHEDULER_ADMIN_TOKEN_FILE ?? "").trim();
  if (tokenFile) {
    const tokenText = (await Bun.file(tokenFile).text()).trim();
    if (!tokenText) throw new Error("SCP_SCHEDULER_ADMIN_TOKEN_FILE is empty");
    SCHEDULER_ADMIN_TOKEN = tokenText;
  }
  if (process.env.SCP_PRODUCTION_MODE === "1" && !SCHEDULER_ADMIN_TOKEN) {
    throw new Error("production scheduler admin token is not configured");
  }
  // [S10b taint-removal] PORT, LOOP_INTERVAL_SEC, AUTOFIX_MODE,
  // AUTOFIX_MAX_BUGS, SCP_BASE_URL all derive from process.env — static text.
  console.log("[loop-scheduler] booting (port/interval/mode/max_bugs/SCP URL from config env)");

  // Restore prior run count + recent history from log file
  const { total, recent } = await loadExistingRuns();
  state.total_runs = total;
  state.recent_runs = recent;
  if (recent.length > 0) state.last_run = recent[0];
  // [S10c taint-removal] Restore is silent: run count is file-derived and
  // LOOP_LOG_PATH is process.env-derived — no log sink here.

  // [Fix 4-d-019 · Task Local-D] Restore persisted pause state BEFORE
  // startLoop() — so a paused scheduler stays paused across restarts.
  // The env var LOOP_START_PAUSED=1 overrides the file (forces pause).
  const persisted = await loadPersistedState();
  if (process.env.LOOP_START_PAUSED === "1") {
    state.paused = true;
    console.log("[loop-scheduler] LOOP_START_PAUSED=1 → starting paused (env override)");
  } else if (persisted) {
    state.paused = persisted.paused;
    // [S10c taint-removal] Restore is silent: LOOP_STATE_PATH (process.env-
    // derived) and the persisted.* values (file-derived) never reach a log sink.
  }

  // Initial SCP liveness probe (retry until backend boots)
  const probeInitialScp = async () => {
    let lastOk = false;
    for (let i = 0; i < 6; i++) {
      const ok = await checkScpLiveness();
      lastOk = ok;
      state.scp_online = ok;
      if (ok) break;
      await new Promise((r) => setTimeout(r, 2000));
    }
    // Constant-string branches: no interpolated value reaches the log sink.
    // Log from the probe's own network-derived result (never the file-derived
    // persisted state) — keeps the taint boundary at the log sink.
    console.log(lastOk ? "[loop-scheduler] initial SCP liveness: online" : "[loop-scheduler] initial SCP liveness: offline");
  };
  void probeInitialScp();

  // Initial LLM bridge liveness probe (retry until bridge boots)
  const probeInitialBridge = async () => {
    let lastOk = false;
    for (let i = 0; i < 6; i++) {
      const ok = await checkLlmBridgeLiveness();
      lastOk = ok;
      state.bridge_online = ok;
      if (ok) break;
      await new Promise((r) => setTimeout(r, 2000));
    }
    console.log(lastOk ? "[loop-scheduler] initial LLM bridge liveness: online" : "[loop-scheduler] initial LLM bridge liveness: offline");
  };
  void probeInitialBridge();

  // Start the cron loop (only if not paused)
  if (state.paused) {
    // [S10c taint-removal] Paused-restore notice removed — no log sink here;
    // control flow unchanged (paused ⇒ loop not started).
  } else {
    startLoop();
  }

  // Start HTTP server.
  // [SCP-DNA-FIX 4-d-008] Bind 127.0.0.1 (loopback only) — was 0.0.0.0
  // (Bun.serve default). DNA #6 (Gốc tin cậy bên ngoài): exposing the
  // scheduler's admin endpoints (POST /trigger, /pause, /resume) to the
  // network allowed anyone on the LAN to trigger SCP audits (burning
  // OpenRouter quota) or pause the loop (denial-of-service). DNA #9
  // (No harm): no auth was required on any state-mutating endpoint.
  // Post-fix: hostname defaults to 127.0.0.1 (loopback). The Next.js
  // dashboard proxies through its own /api/scp/loop/* routes anyway, so
  // binding loopback doesn't break any legit caller. Override via
  // LOOP_SCHEDULER_HOST env var if you really need 0.0.0.0 (e.g. inside
  // a container with explicit port mapping + auth).
  const HOST = process.env.LOOP_SCHEDULER_HOST ?? "127.0.0.1";
  const server = Bun.serve({
    hostname: HOST,
    port: PORT,
    fetch: (req) => handleRequest(req).catch((e) => {
      const err = e instanceof Error ? e.message : String(e);
      console.error(`[loop-scheduler] handler error: ${err.slice(0, 200)}`);
      return jsonResponse({ error: "internal", message: err.slice(0, 200) }, 500);
    }),
  });
  // [S10b taint-removal] HOST (process.env-derived) and server.port
  // (env-derived config) never reach a log sink — static text only.
  console.log("[loop-scheduler] listening (loopback only — DNA #6; host/port from config)");

  // Graceful shutdown
  const shutdown = (sig: string) => {
    console.log(`[loop-scheduler] received ${sig}, shutting down`);
    if (loopTimer) clearTimeout(loopTimer);
    server.stop(true);
    process.exit(0);
  };
  process.on("SIGINT", () => shutdown("SIGINT"));
  process.on("SIGTERM", () => shutdown("SIGTERM"));
}

void main();
