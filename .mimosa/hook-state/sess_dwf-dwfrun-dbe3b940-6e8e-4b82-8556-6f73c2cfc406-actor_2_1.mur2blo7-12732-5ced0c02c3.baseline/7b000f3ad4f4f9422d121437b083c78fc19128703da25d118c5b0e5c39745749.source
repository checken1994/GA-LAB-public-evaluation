"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  Activity,
  AlertCircle,
  ArrowDown,
  ArrowDownUp,
  ArrowUp,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Filter,
  Play,
  RefreshCw,
  Terminal,
  Trash2,
  Zap,
} from "lucide-react"

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

interface ActivityResponse {
  success: boolean
  summary: {
    totalRunsRecorded: number
    latestRunStatus: string
    latestRunTimestamp: string | null
    latestRunDurationMs: number
    latestFindingsCount: number
    latestFixesCount: number
    triggerType: string
    serverTime: string
  }
  runs: LoopRunEntry[]
  events: ActivityEvent[]
}

type FilterCategory = "all" | "loop" | "log" | "error"

const FILTER_LABELS: Record<FilterCategory, string> = {
  all: "Tất cả",
  loop: "Vòng lặp & Tự sửa",
  log: "Log hệ thống",
  error: "Cảnh báo & Lỗi",
}

// Nhãn ngắn cho trạng thái chu kỳ ghi trong loop_runs.jsonl
const RUN_STATUS_SHORT: Record<string, string> = {
  ok: "hoàn tất",
  running: "đang chạy",
  auth_required: "bị chặn xác thực",
  bridge_offline: "chờ LLM bridge",
  scp_offline: "SCP ngoại tuyến",
  error: "bị lỗi",
  failed: "bị lỗi",
}

export function LiveActivityStream() {
  const [data, setData] = useState<ActivityResponse | null>(null)
  const [fetchFailed, setFetchFailed] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [triggering, setTriggering] = useState(false)
  const [triggerResult, setTriggerResult] = useState<string | null>(null)
  const [filter, setFilter] = useState<FilterCategory>("all")
  const [autoScroll, setAutoScroll] = useState(true)
  const [sortOrder, setSortOrder] = useState<"newest" | "oldest">("newest")
  const [isScrolledAway, setIsScrolledAway] = useState(false)
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null)
  const [clearedBefore, setClearedBefore] = useState<number>(0)
  const terminalBoxRef = useRef<HTMLDivElement | null>(null)

  const fetchActivity = useCallback(async () => {
    try {
      const res = await fetch("/api/scp/activity", { cache: "no-store" })
      if (res.ok) {
        const json = (await res.json()) as ActivityResponse
        setData(json)
        setFetchFailed(null)
      } else {
        setFetchFailed(res.status)
      }
    } catch {
      // Network error handled silently in live loop
      setFetchFailed(-1)
    }
  }, [])

  // Auto-fetch every 3 seconds for true live feeling
  useEffect(() => {
    void fetchActivity()
    const timer = setInterval(() => {
      void fetchActivity()
    }, 3000)
    return () => clearInterval(timer)
  }, [fetchActivity])

  // Smart auto-pin: keep newest in view WITHOUT dragging user down to the wrong end
  useEffect(() => {
    if (!autoScroll || !terminalBoxRef.current) return
    const el = terminalBoxRef.current
    if (sortOrder === "newest") {
      // "Mới nhất ở trên": tin mới nằm ở ĐỈNH danh sách (scrollTop = 0).
      // Chỉ ghim nếu người dùng đang ở gần đỉnh (<= 80px). Nếu đang cuộn xuống đọc lịch sử thì không quấy rầy.
      if (el.scrollTop <= 80) {
        el.scrollTop = 0
      }
    } else {
      // "Cũ nhất ở trên" (kiểu terminal cổ điển): tin mới nằm ở ĐÁY.
      // Chỉ ghim xuống đáy nếu người dùng đang ở sát đáy.
      const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= 80
      if (isNearBottom) {
        el.scrollTop = el.scrollHeight
      }
    }
  }, [data?.events, autoScroll, sortOrder])

  const handleJumpToLatest = () => {
    if (!terminalBoxRef.current) return
    if (sortOrder === "newest") {
      terminalBoxRef.current.scrollTo({ top: 0, behavior: "smooth" })
    } else {
      terminalBoxRef.current.scrollTo({ top: terminalBoxRef.current.scrollHeight, behavior: "smooth" })
    }
    setIsScrolledAway(false)
  }

  const handleContainerScroll = () => {
    if (!terminalBoxRef.current) return
    const el = terminalBoxRef.current
    if (sortOrder === "newest") {
      setIsScrolledAway(el.scrollTop > 80)
    } else {
      setIsScrolledAway(el.scrollHeight - el.scrollTop - el.clientHeight > 80)
    }
  }

  const handleTriggerAudit = async () => {
    if (triggering) return
    setTriggering(true)
    setTriggerResult("Đang gửi yêu cầu kích hoạt chu kỳ audit…")
    try {
      const res = await fetch("/api/scp/loop/trigger", { method: "POST", cache: "no-store" })
      const resJson = await res.json().catch(() => ({}))
      if (res.ok) {
        setTriggerResult("Đã kích hoạt thành công! Đang quan sát tiến trình…")
        // Immediate poll
        setTimeout(() => void fetchActivity(), 1000)
        setTimeout(() => void fetchActivity(), 3000)
      } else {
        setTriggerResult(`Lỗi kích hoạt: HTTP ${res.status}`)
      }
    } catch (e) {
      setTriggerResult(`Lỗi kết nối: ${e instanceof Error ? e.message : "không rõ"}`)
    } finally {
      setTriggering(false)
      setTimeout(() => setTriggerResult(null), 5000)
    }
  }

  const events = data?.events ?? []
  const filteredEvents = events.filter((e) => {
    const eventTime = new Date(e.timestamp).getTime()
    if (clearedBefore && eventTime <= clearedBefore) return false
    if (filter === "loop") return e.type === "loop"
    if (filter === "log") return e.type === "log"
    if (filter === "error") return e.status === "error" || e.status === "warning"
    return true
  })

  const displayEvents = useMemo(() => {
    return [...filteredEvents].sort((a, b) => {
      const timeA = new Date(a.timestamp).getTime()
      const timeB = new Date(b.timestamp).getTime()
      return sortOrder === "newest" ? timeB - timeA : timeA - timeB
    })
  }, [filteredEvents, sortOrder])

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts)
      return d.toLocaleTimeString("vi-VN", { hour12: false })
    } catch {
      return ts
    }
  }

  return (
    <section
      aria-label="SCP Live Activity"
      className="mt-8 rounded-3xl border border-cyan-400/20 bg-gradient-to-b from-[#081525] to-[#06101d] p-5 shadow-xl shadow-black/30 sm:p-7"
    >
      {/* Header bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/[0.08] pb-5">
        <div className="flex items-start gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-2xl border border-cyan-300/30 bg-cyan-400/10 text-cyan-300">
            <Terminal className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-white">
                Live Activity & Event Stream
              </h2>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-300 border border-emerald-500/30">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Quan sát hoạt động bên trong SCP: chu kỳ tự sửa, scheduler và log thời gian thực
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleTriggerAudit}
            disabled={triggering}
            className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-400/40 bg-cyan-500/20 px-3 py-1.5 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-500/30 active:scale-95 disabled:opacity-50"
          >
            {triggering ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            Chạy Audit ngay
          </button>

          <button
            type="button"
            onClick={() => void fetchActivity()}
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-white/[0.06]"
            title="Làm mới dữ liệu thủ công"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>

          <button
            type="button"
            onClick={() => setClearedBefore((current) => (current ? 0 : Date.now()))}
            className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-medium transition ${
              clearedBefore
                ? "border-amber-400/40 bg-amber-400/15 text-amber-200 hover:bg-amber-400/25"
                : "border-white/[0.08] bg-white/[0.03] text-slate-300 hover:bg-white/[0.06] hover:text-rose-300"
            }`}
            title={clearedBefore ? "Hiện lại các sự kiện đã xóa" : "Xóa danh sách hiển thị tạm thời"}
          >
            <Trash2 className="h-3.5 w-3.5" />
            {clearedBefore ? "Hiện lại đã xóa" : ""}
          </button>
        </div>
      </div>

      {/* Trigger alert notification */}
      {triggerResult && (
        <div className="mt-4 rounded-xl border border-cyan-400/30 bg-cyan-950/40 p-3 text-xs text-cyan-200 flex items-center gap-2">
          <Zap className="h-4 w-4 text-cyan-400 shrink-0" />
          <span>{triggerResult}</span>
        </div>
      )}

      {/* Summary KPI cards */}
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-2xl border border-white/[0.08] bg-black/20 p-3.5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400">Chu kỳ gần nhất</div>
          <div className="mt-1.5 flex items-center gap-1.5 text-sm font-semibold text-white">
            {data?.summary.latestRunStatus === "ok" ? (
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            ) : (
              <AlertCircle className="h-4 w-4 text-amber-400" />
            )}
            <span>
              {RUN_STATUS_SHORT[data?.summary.latestRunStatus ?? ""] ?? data?.summary.latestRunStatus ?? "chưa có"}
            </span>
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            {data?.summary.latestRunDurationMs ? `${data.summary.latestRunDurationMs}ms` : "—"}
          </div>
        </div>

        <div className="rounded-2xl border border-white/[0.08] bg-black/20 p-3.5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400">Kiểu kích hoạt</div>
          <div className="mt-1.5 text-sm font-semibold text-white">
            {data?.summary.triggerType === "cron"
              ? "Tự động (5 phút)"
              : data?.summary.triggerType === "manual"
              ? "Thủ công"
              : data?.summary.triggerType ?? "—"}
          </div>
          <div className="mt-1 text-[11px] text-slate-500">Vòng lặp độc lập</div>
        </div>

        <div className="rounded-2xl border border-white/[0.08] bg-black/20 p-3.5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400">Tự sửa & Bản vá</div>
          <div className="mt-1.5 text-sm font-semibold text-emerald-400">
            {data?.summary.latestFindingsCount ?? 0} phát hiện · {data?.summary.latestFixesCount ?? 0} sửa
          </div>
          <div className="mt-1 text-[11px] text-slate-500">Từ chu kỳ gần nhất trong loop_runs.jsonl</div>
        </div>

        <div className="rounded-2xl border border-white/[0.08] bg-black/20 p-3.5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400">Tổng chu kỳ ghi nhận</div>
          <div className="mt-1.5 text-sm font-semibold text-white">
            {data?.summary.totalRunsRecorded ?? 0} lượt
          </div>
          <div className="mt-1 text-[11px] text-slate-500">Dữ liệu từ loop_runs.jsonl</div>
        </div>
      </div>

      {/* Filter and control bar */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.06] pt-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-slate-400 mr-1 inline-flex items-center gap-1">
            <Filter className="h-3 w-3" /> Lọc:
          </span>
          {(
            [
              { key: "all", label: "Tất cả" },
              { key: "loop", label: "Vòng lặp & Tự sửa" },
              { key: "log", label: "Log hệ thống" },
              { key: "error", label: "Cảnh báo & Lỗi" },
            ] as const
          ).map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                filter === key
                  ? "border border-cyan-400/40 bg-cyan-400/15 text-cyan-200"
                  : "border border-transparent text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Quick jump to latest button when user scrolled into history */}
          {isScrolledAway && (
            <button
              type="button"
              onClick={handleJumpToLatest}
              className="inline-flex items-center gap-1 rounded-lg border border-cyan-400/40 bg-cyan-500/15 px-2.5 py-1 text-xs font-medium text-cyan-200 hover:bg-cyan-500/25 transition shadow-sm"
              title="Cuộn tới sự kiện mới nhất"
            >
              {sortOrder === "newest" ? (
                <>
                  <ArrowUp className="h-3 w-3" /> Lên tin mới nhất
                </>
              ) : (
                <>
                  <ArrowDown className="h-3 w-3" /> Xuống tin mới nhất
                </>
              )}
            </button>
          )}

          {/* Sort order toggle button */}
          <button
            type="button"
            onClick={() => {
              const next = sortOrder === "newest" ? "oldest" : "newest"
              setSortOrder(next)
              setIsScrolledAway(false)
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.03] px-2.5 py-1 text-xs text-slate-300 hover:bg-white/[0.08] hover:text-white transition"
            title="Đổi chiều sắp xếp sự kiện"
          >
            <ArrowDownUp className="h-3 w-3 text-cyan-400" />
            <span>{sortOrder === "newest" ? "Mới nhất ở trên" : "Cũ nhất ở trên"}</span>
          </button>

          <label className="inline-flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="accent-cyan-400 rounded"
            />
            Tự động ghim mới
          </label>
        </div>
      </div>

      {/* Terminal log container */}
      <div
        ref={terminalBoxRef}
        onScroll={handleContainerScroll}
        className="mt-3 rounded-2xl border border-white/[0.08] bg-[#030812] p-3 font-mono text-xs shadow-inner max-h-[380px] overflow-y-auto"
      >
        {displayEvents.length === 0 ? (
          <div className="py-10 text-center text-xs leading-6 text-slate-500">
            {fetchFailed !== null ? (
              <p>
                Không đọc được sự kiện từ dashboard API ({fetchFailed === -1 ? "lỗi mạng" : `HTTP ${fetchFailed}`}).
                Đang tự thử lại mỗi 3 giây — nếu lặp lại, kiểm tra dashboard middleware gate hoặc route /api/scp/activity.
              </p>
            ) : events.length === 0 ? (
              <p>
                Chưa có chu kỳ nào được ghi nhận trong data/loop_runs.jsonl (scheduler chưa chạy lần nào hoặc file chưa tồn tại).
                Bấm &quot;Chạy Audit ngay&quot; ở trên để tạo sự kiện đầu tiên.
              </p>
            ) : clearedBefore ? (
              <p>
                Bạn đã xóa danh sách lúc {new Date(clearedBefore).toLocaleTimeString("vi-VN")} — các sự kiện cũ bị ẩn và sự kiện
                mới (chu kỳ 5 phút) sẽ tự xuất hiện tại đây.{" "}
                <button type="button" onClick={() => setClearedBefore(0)} className="underline decoration-dotted hover:text-cyan-300">
                  Hiện lại lịch sử đã xóa
                </button>
              </p>
            ) : (
              <p>
                Đang có {events.length} sự kiện nhưng bộ lọc &quot;{FILTER_LABELS[filter]}&quot; đang ẩn tất cả.{" "}
                <button type="button" onClick={() => setFilter("all")} className="underline decoration-dotted hover:text-cyan-300">
                  Xem tất cả sự kiện
                </button>
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-1.5">
            {displayEvents.map((evt) => {
              const isExpanded = expandedEventId === evt.id
              const hasDetails = !!evt.details

              return (
                <div
                  key={evt.id}
                  className="rounded-lg border border-white/[0.03] bg-white/[0.02] p-2 transition hover:bg-white/[0.05]"
                >
                  <div className="flex items-start gap-2">
                    <span className="shrink-0 text-slate-500 select-none">
                      {formatTimestamp(evt.timestamp)}
                    </span>

                    {/* Service badge */}
                    <span
                      className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                        evt.type === "loop"
                          ? "bg-cyan-500/20 text-cyan-300"
                          : evt.service === "desktop"
                          ? "bg-violet-500/20 text-violet-300"
                          : "bg-emerald-500/20 text-emerald-300"
                      }`}
                    >
                      {evt.service}
                    </span>

                    {/* Status badge */}
                    <span
                      className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                        evt.status === "ok"
                          ? "bg-emerald-400/15 text-emerald-300"
                          : evt.status === "warning"
                          ? "bg-amber-400/15 text-amber-300"
                          : evt.status === "error"
                          ? "bg-rose-400/15 text-rose-300"
                          : "bg-slate-400/15 text-slate-300"
                      }`}
                    >
                      {evt.status}
                    </span>

                    {/* Message text */}
                    <span className="min-w-0 flex-1 break-words text-slate-200">
                      {evt.message}
                    </span>

                    {/* Details toggle */}
                    {hasDetails && (
                      <button
                        type="button"
                        onClick={() => setExpandedEventId(isExpanded ? null : evt.id)}
                        className="shrink-0 text-slate-500 hover:text-cyan-300"
                        title="Xem chi tiết dữ liệu JSON"
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3.5 w-3.5" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5" />
                        )}
                      </button>
                    )}
                  </div>

                  {/* Expanded JSON details */}
                  {isExpanded && evt.details && (
                    <div className="mt-2 rounded bg-black/40 p-2 text-[11px] text-cyan-200/90 overflow-x-auto border border-cyan-400/15">
                      <pre>{JSON.stringify(evt.details, null, 2)}</pre>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Footer hint */}
      <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
        <span>Cập nhật liên tục mỗi 3 giây · Lưu trữ tại data/loop_runs.jsonl</span>
        <span>SCP Engine v14.0.0 (API-Only)</span>
      </div>
    </section>
  )
}
