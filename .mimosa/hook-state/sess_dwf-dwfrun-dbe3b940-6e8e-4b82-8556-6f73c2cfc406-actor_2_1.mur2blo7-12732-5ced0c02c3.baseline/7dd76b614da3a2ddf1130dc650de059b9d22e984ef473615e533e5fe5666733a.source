/**
 * API /api/scp/activity — real-time activity and log stream for SCP.
 *
 * Exposes:
 *   1. Recent loop scheduler audit runs from data/loop_runs.jsonl
 *   2. Recent service log entries from data/service-logs/ and data/desktop-logs/
 *   3. Aggregated timeline of events for the Live Activity Stream component
 */
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"
import { NextResponse } from "next/server"
// [AUDIT-R2 2026-10-01 · M-4] Log lines and run metadata are REDACTED and
// size-capped before leaving the server: raw service logs routinely embed
// credential material (Authorization headers, KEY=value boot dumps, provider
// tokens inside error messages). See lib/log-redaction.ts for the contract.
import { capEventsPayload, redactLogLine, redactLogText } from "../../../../lib/log-redaction"

export const dynamic = "force-dynamic"
export const revalidate = 0

function findScpRoot(): string {
  if (process.env.SCP_ROOT && existsSync(process.env.SCP_ROOT)) return process.env.SCP_ROOT
  let cur = process.cwd()
  for (let i = 0; i < 4; i++) {
    if (existsSync(path.join(cur, "data")) && (existsSync(path.join(cur, "spec")) || existsSync(path.join(cur, "scp")))) {
      return cur
    }
    cur = path.resolve(cur, "..")
  }
  return "D:\\scp"
}

const SCP_ROOT = findScpRoot()

interface LoopRunEntry {
  ts?: string
  scp_online?: boolean
  status?: string
  http_status?: number
  duration_ms?: number
  triggered_by?: string
  findings_count?: number
  fixes_applied?: number
  permission_requested?: number
  skipped?: number
  error?: string
}

interface ActivityEvent {
  id: string
  timestamp: string
  type: "loop" | "log" | "system"
  service: string
  status: "ok" | "warning" | "error" | "info"
  message: string
  details?: Record<string, unknown>
}

function readRecentJsonl(filePath: string, maxLines = 30): LoopRunEntry[] {
  if (!existsSync(filePath)) return []
  try {
    const raw = readFileSync(filePath, "utf8")
    const lines = raw.trim().split(/\r?\n/).filter(Boolean)
    const recent = lines.slice(-maxLines)
    const parsed: LoopRunEntry[] = []
    for (const line of recent) {
      try {
        parsed.push(JSON.parse(line))
      } catch {
        // Skip malformed JSON line
      }
    }
    return parsed.reverse() // Newest first
  } catch {
    return []
  }
}

function readRecentLogLines(filePath: string, maxLines = 25): string[] {
  if (!existsSync(filePath)) return []
  try {
    const raw = readFileSync(filePath, "utf8")
    const lines = raw.trim().split(/\r?\n/).filter(Boolean)
    return lines.slice(-maxLines)
  } catch {
    return []
  }
}

export async function GET(request: Request) {
  // [AUDIT-R2 2026-10-01] middleware.ts gates /api/scp/* fail-closed via the
  // trusted reverse-proxy shared secret (x-scp-proxy-secret, 403 on
  // missing/mismatch), with an explicit local-dev fallback (SCP_DEV_MODE=1 +
  // loopback Host + XFF-hop validation) and a hard 503 otherwise — there is
  // deliberately NO route-level credential gate (the browser holds no auth
  // cookie, so one would 401 the live activity stream) and no raw log
  // passthrough (redaction below is the data boundary, not the auth one).

  const loopRunsPath = path.join(SCP_ROOT, "data", "loop_runs.jsonl")
  const runs = readRecentJsonl(loopRunsPath, 40)

  const events: ActivityEvent[] = []

  // [AUDIT-R2 M-4] The jsonl `error` field is a raw scheduler/backend error
  // string — redact + truncate before anything reaches the browser (both the
  // event details and the top-level `runs` array below).
  const runsSafe = runs.map((run) =>
    typeof run.error === "string" && run.error
      ? { ...run, error: redactLogText(run.error) }
      : run,
  )

  // 1. Process Loop Runs into Events
  runsSafe.forEach((run, idx) => {
    const ts = run.ts || new Date().toISOString()
    const status = run.status === "ok" ? "ok" : run.status === "running" ? "info" : "error"
    const findings = run.findings_count ?? 0
    const fixes = run.fixes_applied ?? 0
    const trigger = run.triggered_by === "cron" ? "Tự động (5 phút)" : run.triggered_by === "manual" ? "Thủ công" : redactLogText(run.triggered_by || "hệ thống", 60)
    const dur = run.duration_ms ? `${run.duration_ms}ms` : "—"

    let msg = `[Scheduler] Chu kỳ ${trigger}: ${run.status ?? "hoàn tất"} trong ${dur}`
    if (findings > 0 || fixes > 0) {
      msg += ` · ${findings} phát hiện · ${fixes} bản vá`
    } else {
      msg += ` · 0 lỗi âm thầm`
    }

    events.push({
      id: `loop-${ts}-${idx}`,
      timestamp: ts,
      type: "loop",
      service: "loop-scheduler",
      status,
      message: msg,
      details: run as Record<string, unknown>,
    })
  })

  // 2. Read Service Logs (Scheduler, Backend, Desktop) — each line is
  // redacted + truncated; lines that still carry an unredactable secret
  // shape are DROPPED entirely (redactLogLine → null).
  const serviceLogsDir = path.join(SCP_ROOT, "data", "service-logs")
  const schedulerLines = readRecentLogLines(path.join(serviceLogsDir, "scheduler.log"), 15)
  schedulerLines.forEach((line, idx) => {
    if (!line.trim()) return
    const safeLine = redactLogLine(line)
    if (safeLine === null) return
    events.push({
      id: `sched-log-${idx}-${Date.now()}`,
      timestamp: new Date().toISOString(),
      type: "log",
      service: "scheduler",
      status: safeLine.toLowerCase().includes("error") ? "error" : "info",
      message: safeLine,
    })
  })

  const desktopConsoleLines = readRecentLogLines(path.join(SCP_ROOT, "data", "desktop-logs", "desktop-console.log"), 15)
  desktopConsoleLines.forEach((line, idx) => {
    if (!line.trim()) return
    const match = line.match(/^\[(.*?)\]\s*(.*)$/)
    const ts = match ? match[1] : new Date().toISOString()
    const rawMsg = match ? match[2] : line
    const safeMsg = redactLogLine(rawMsg)
    if (safeMsg === null) return
    const isWarn = safeMsg.includes("warning") || safeMsg.includes("WARN")
    const isErr = safeMsg.includes("error") || safeMsg.includes("ERROR")
    events.push({
      id: `desktop-log-${idx}-${ts}`,
      timestamp: ts,
      type: "log",
      service: "desktop",
      status: isErr ? "error" : isWarn ? "warning" : "info",
      message: safeMsg,
    })
  })

  // Sort events newest first
  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

  // [AUDIT-R2 M-4] Cap the total payload: the newest events are kept, older
  // ones beyond the byte budget are dropped and the overflow is reported so
  // the UI can say "older events hidden" instead of an unbounded stream.
  const capped = capEventsPayload(events.slice(0, 50), (event) => event)

  // Summary statistics
  const latestRun = runs[0] || null
  const summary = {
    totalRunsRecorded: runs.length,
    latestRunStatus: latestRun?.status || "chưa có",
    latestRunTimestamp: latestRun?.ts || null,
    latestRunDurationMs: latestRun?.duration_ms || 0,
    latestFindingsCount: latestRun?.findings_count || 0,
    latestFixesCount: latestRun?.fixes_applied || 0,
    triggerType: latestRun?.triggered_by || "—",
    serverTime: new Date().toISOString(),
  }

  return NextResponse.json({
    success: true,
    summary,
    runs: runsSafe,
    events: capped.events,
    payloadDroppedEvents: capped.dropped,
  })
}
