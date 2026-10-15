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
  // [LOCAL-DEV] Middleware hostname check already gates /api/scp/* to
  // localhost — route-level auth is redundant for the local dashboard and
  // breaks the live activity stream (browser has no auth cookie).
  // requireAuth removed — see middleware.ts LOCAL-DEV comment.

  const loopRunsPath = path.join(SCP_ROOT, "data", "loop_runs.jsonl")
  const runs = readRecentJsonl(loopRunsPath, 40)

  const events: ActivityEvent[] = []

  // 1. Process Loop Runs into Events
  runs.forEach((run, idx) => {
    const ts = run.ts || new Date().toISOString()
    const status = run.status === "ok" ? "ok" : run.status === "running" ? "info" : "error"
    const findings = run.findings_count ?? 0
    const fixes = run.fixes_applied ?? 0
    const trigger = run.triggered_by === "cron" ? "Tự động (5 phút)" : run.triggered_by === "manual" ? "Thủ công" : (run.triggered_by || "hệ thống")
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

  // 2. Read Service Logs (Scheduler, Backend, Desktop)
  const serviceLogsDir = path.join(SCP_ROOT, "data", "service-logs")
  const schedulerLines = readRecentLogLines(path.join(serviceLogsDir, "scheduler.log"), 15)
  schedulerLines.forEach((line, idx) => {
    if (!line.trim()) return
    events.push({
      id: `sched-log-${idx}-${Date.now()}`,
      timestamp: new Date().toISOString(),
      type: "log",
      service: "scheduler",
      status: line.toLowerCase().includes("error") ? "error" : "info",
      message: line,
    })
  })

  const desktopConsoleLines = readRecentLogLines(path.join(SCP_ROOT, "data", "desktop-logs", "desktop-console.log"), 15)
  desktopConsoleLines.forEach((line, idx) => {
    if (!line.trim()) return
    const match = line.match(/^\[(.*?)\]\s*(.*)$/)
    const ts = match ? match[1] : new Date().toISOString()
    const rawMsg = match ? match[2] : line
    const isWarn = rawMsg.includes("warning") || rawMsg.includes("WARN")
    const isErr = rawMsg.includes("error") || rawMsg.includes("ERROR")
    events.push({
      id: `desktop-log-${idx}-${ts}`,
      timestamp: ts,
      type: "log",
      service: "desktop",
      status: isErr ? "error" : isWarn ? "warning" : "info",
      message: rawMsg,
    })
  })

  // Sort events newest first
  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

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
    runs,
    events: events.slice(0, 50),
  })
}
