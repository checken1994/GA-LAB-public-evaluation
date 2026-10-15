"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BellRing,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  Clock3,
  Database,
  Eye,
  Gauge,
  GitBranch,
  Globe2,
  Info,
  Layers3,
  MessageCircle,
  Play,
  RefreshCw,
  ScanSearch,
  ServerCog,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Wrench,
  XCircle,
} from "lucide-react"
import { VideoCallPanel } from "@/components/dashboard/video-call-panel"
import { LiveActivityStream } from "@/components/dashboard/live-activity-stream"

type JsonRecord = Record<string, unknown>
type StatusKind = "online" | "degraded" | "offline" | "unknown"

type LiveSnapshot = {
  status: JsonRecord
  loop: JsonRecord
  health: JsonRecord
  metrics: JsonRecord
  checkedAt: string | null
  error: string | null
}

type MetricPoint = {
  time: string
  latencyMs: number
  cpuPercent: number
  memoryPercent: number
  loadPercent: number
}

type AlertSettings = {
  enabled: boolean
  soundEnabled: boolean
  notifyEnabled: boolean
  latencyThresholdMs: number
  cooldownMs: number
}

type DesktopBridge = {
  notifyCritical?: (payload: { title: string; body: string }) => Promise<boolean>
}

type SpeechRecognitionLike = {
  lang: string
  interimResults: boolean
  continuous: boolean
  start: () => void
  stop: () => void
  onstart: (() => void) | null
  onend: (() => void) | null
  onerror: ((event: { error?: string }) => void) | null
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike

type V31Snapshot = {
  pc: JsonRecord
  web: JsonRecord
  hands: JsonRecord
  checkedAt: string | null
}

const EMPTY_SNAPSHOT: LiveSnapshot = {
  status: {},
  loop: {},
  health: {},
  metrics: {},
  checkedAt: null,
  error: null,
}

function asRecord(value: unknown): JsonRecord {
  return value && typeof value === "object" ? (value as JsonRecord) : {}
}

function asText(value: unknown, fallback = "") {
  return typeof value === "string" || typeof value === "number" ? String(value) : fallback
}

function firstValue(source: JsonRecord, keys: string[], fallback = "") {
  for (const key of keys) {
    const value = source[key]
    if (value !== undefined && value !== null && value !== "") return asText(value, fallback)
  }
  return fallback
}

function asNumber(value: unknown, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function playCriticalTone() {
  if (typeof window === "undefined") return
  const AudioContextClass = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!AudioContextClass) return
  const context = new AudioContextClass()
  const now = context.currentTime
  ;[880, 660, 880].forEach((frequency, index) => {
    const oscillator = context.createOscillator()
    const gain = context.createGain()
    oscillator.type = "sine"
    oscillator.frequency.value = frequency
    gain.gain.setValueAtTime(0.0001, now + index * 0.18)
    gain.gain.exponentialRampToValueAtTime(0.14, now + index * 0.18 + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + index * 0.18 + 0.14)
    oscillator.connect(gain)
    gain.connect(context.destination)
    oscillator.start(now + index * 0.18)
    oscillator.stop(now + index * 0.18 + 0.15)
  })
  window.setTimeout(() => context.close().catch(() => undefined), 800)
}

function probeFrom(source: JsonRecord, keys: string[]) {
  for (const key of keys) {
    const value = source[key]
    if (value && typeof value === "object") return asRecord(value)
  }
  return {}
}

function probeKind(probe: JsonRecord): StatusKind {
  const state = asText(probe.status || probe.state || probe.health).toLowerCase()
  if (probe.ok === true || state === "online" || state === "ok" || state === "healthy") return "online"
  if (state === "degraded" || state === "warning") return "degraded"
  if (probe.ok === false || state === "offline" || state === "error" || state === "unhealthy") return "offline"
  return "unknown"
}

function statusLabel(kind: StatusKind) {
  return { online: "Đang hoạt động", degraded: "Có cảnh báo", offline: "Ngoại tuyến", unknown: "Chưa rõ" }[kind]
}

function statusTone(kind: StatusKind) {
  return {
    online: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
    degraded: "border-amber-400/30 bg-amber-400/10 text-amber-200",
    offline: "border-rose-400/30 bg-rose-400/10 text-rose-200",
    unknown: "border-slate-400/20 bg-slate-400/10 text-slate-300",
  }[kind]
}

function statusDot(kind: StatusKind) {
  return {
    online: "bg-emerald-400 shadow-[0_0_0_4px_rgba(52,211,153,0.12)]",
    degraded: "bg-amber-400 shadow-[0_0_0_4px_rgba(251,191,36,0.12)]",
    offline: "bg-rose-400 shadow-[0_0_0_4px_rgba(251,113,133,0.12)]",
    unknown: "bg-slate-400",
  }[kind]
}

function formatTime(value: string | null, fallback = "Chưa có dữ liệu") {
  if (!value) return fallback
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
}

function formatLatency(probe: JsonRecord) {
  const latency = Number(probe.latencyMs)
  return Number.isFinite(latency) ? `${Math.round(latency)} ms` : "—"
}

function MetricCard({ label, value, detail, icon: Icon, accent }: { label: string; value: string; detail: string; icon: typeof Activity; accent: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-4 shadow-lg shadow-black/10">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">{label}</span>
        <Icon className={`h-4 w-4 ${accent}`} aria-hidden="true" />
      </div>
      <div className="mt-3 text-2xl font-semibold tracking-tight text-white">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{detail}</div>
    </div>
  )
}

function LiveLineChart({ title, subtitle, lines, maxValue, unit }: { title: string; subtitle: string; lines: { label: string; color: string; values: number[] }[]; maxValue: number; unit: string }) {
  const width = 760
  const height = 220
  const left = 48
  const top = 18
  const right = 18
  const bottom = 30
  const innerWidth = width - left - right
  const innerHeight = height - top - bottom
  const safeMax = Math.max(1, maxValue)
  const pointString = (values: number[]) => values.map((value, index) => {
    const denominator = Math.max(1, values.length - 1)
    const x = left + (index / denominator) * innerWidth
    const y = top + innerHeight - (Math.max(0, Math.min(safeMax, value)) / safeMax) * innerHeight
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(" ")
  const tickValues = [safeMax, safeMax / 2, 0]

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-black/10 p-4 sm:p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div><div className="font-medium text-slate-100">{title}</div><div className="mt-1 text-xs text-slate-500">{subtitle}</div></div><div className="flex flex-wrap gap-3 text-[11px] text-slate-400">{lines.map((line) => <span key={line.label} className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ backgroundColor: line.color }} />{line.label}</span>)}</div></div>
      <div className="mt-4 overflow-x-auto"><svg viewBox={`0 0 ${width} ${height}`} className="h-auto min-w-[520px] w-full" role="img" aria-label={title}>
        {tickValues.map((tick, index) => { const y = top + (index / 2) * innerHeight; return <g key={tick}><line x1={left} x2={width - right} y1={y} y2={y} stroke="rgba(148,163,184,0.14)" strokeDasharray="3 5" /><text x={left - 8} y={y + 4} textAnchor="end" fill="rgba(148,163,184,0.65)" fontSize="10">{Math.round(tick)}{unit}</text></g> })}
        {lines.map((line) => <polyline key={line.label} fill="none" stroke={line.color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" points={pointString(line.values)} opacity={line.values.length ? 1 : 0} />)}
        <line x1={left} x2={width - right} y1={top + innerHeight} y2={top + innerHeight} stroke="rgba(148,163,184,0.25)" />
      </svg></div>
      {!lines.some((line) => line.values.length > 0) && <div className="-mt-12 pb-8 text-center text-xs text-slate-500">Đang chờ mẫu dữ liệu đầu tiên…</div>}
    </div>
  )
}

function ServiceStatusRow({ name, role, probe, icon: Icon }: { name: string; role: string; probe: JsonRecord; icon: typeof Activity }) {
  const kind = probeKind(probe)
  return (
    <tr className="border-t border-white/[0.07] align-middle">
      <td className="py-4 pr-4">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-white/[0.06] text-slate-300"><Icon className="h-4 w-4" /></span>
          <div><div className="font-medium text-slate-100">{name}</div><div className="text-xs text-slate-500">{role}</div></div>
        </div>
      </td>
      <td className="py-4 pr-4"><span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium ${statusTone(kind)}`}><span className={`h-1.5 w-1.5 rounded-full ${statusDot(kind)}`} />{statusLabel(kind)}</span></td>
      <td className="py-4 pr-4 text-sm text-slate-300">{formatLatency(probe)}</td>
      <td className="py-4 text-right text-xs text-slate-500">{asText(probe.hint, kind === "online" ? "Đã phản hồi" : "Cần kiểm tra")}</td>
    </tr>
  )
}

function SectionHeading({ eyebrow, title, description, icon: Icon }: { eyebrow: string; title: string; description: string; icon: typeof Activity }) {
  return (
    <div className="mb-5 flex items-start justify-between gap-4">
      <div className="flex items-start gap-3"><span className="mt-0.5 grid h-9 w-9 place-items-center rounded-xl border border-cyan-300/15 bg-cyan-300/10 text-cyan-200"><Icon className="h-4 w-4" /></span><div><div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-300/80">{eyebrow}</div><h2 className="mt-1 text-lg font-semibold text-white">{title}</h2><p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">{description}</p></div></div>
    </div>
  )
}

export function ScpOverview() {
  const [snapshot, setSnapshot] = useState<LiveSnapshot>(EMPTY_SNAPSHOT)
  const [v31Snapshot, setV31Snapshot] = useState<V31Snapshot>({ pc: {}, web: {}, hands: {}, checkedAt: null })
  const [metricHistory, setMetricHistory] = useState<MetricPoint[]>([])
  const [alertSettings, setAlertSettings] = useState<AlertSettings>({ enabled: true, soundEnabled: true, notifyEnabled: true, latencyThresholdMs: 1200, cooldownMs: 60000 })
  const [alertState, setAlertState] = useState("Chưa có cảnh báo nghiêm trọng")
  const [refreshing, setRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)
  const [now, setNow] = useState<Date | null>(null)
  const [activeTab, setActiveTab] = useState<"system" | "fix">("system")
  const [webQuery, setWebQuery] = useState("")
  const [webSearch, setWebSearch] = useState<JsonRecord>({})
  const [searchingWeb, setSearchingWeb] = useState(false)
  const [fixing, setFixing] = useState(false)
  const [chatQuestion, setChatQuestion] = useState("")
  const [chatAnswer, setChatAnswer] = useState<JsonRecord | null>(null)
  const [showTrace, setShowTrace] = useState(false)
  const [traceDetail, setTraceDetail] = useState<JsonRecord | null>(null)
  const [traceLoading, setTraceLoading] = useState(false)
  const [chatBusy, setChatBusy] = useState(false)
  const [micActive, setMicActive] = useState(false)
  const [cameraOpen, setCameraOpen] = useState(false)
  const [mediaStatus, setMediaStatus] = useState("Mic và camera chỉ hoạt động sau khi bạn bấm nút.")
  const sessionIdRef = useRef("")
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const cameraStreamRef = useRef<MediaStream | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const recorderChunksRef = useRef<Blob[]>([])
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const pendingImageRef = useRef<string | null>(null)
  const lastAlertKey = useRef("")
  const lastAlertAt = useRef(0)

  const triggerControlledFix = useCallback(async () => {
    if (fixing) return
    setFixing(true)
    setActiveTab("fix")
    setAlertState("Đang gửi yêu cầu sửa có kiểm soát…")
    try {
      const response = await fetch("/api/scp/loop/trigger", { method: "POST", cache: "no-store" })
      const data = await response.json().catch(() => ({})) as JsonRecord
      if (response.ok) {
        const jobId = firstValue(data, ["jobId", "job_id"], "đã nhận")
        setAlertState(`Đã gửi yêu cầu sửa có kiểm soát · mã việc: ${jobId}`)
      } else {
        setAlertState(`Không thể sửa có kiểm soát · HTTP ${response.status} · ${firstValue(data, ["error", "detail", "hint"], "xem log scheduler")}`)
      }
    } catch (error) {
      setAlertState(`Không thể kết nối tới scheduler · ${error instanceof Error ? error.message : "lỗi không rõ"}`)
    } finally {
      setFixing(false)
    }
  }, [fixing])
  const ensureSessionId = useCallback(() => {
    if (sessionIdRef.current) return sessionIdRef.current
    if (typeof window !== "undefined") {
      const key = "scp-desktop-chat-session-id"
      const old = window.sessionStorage.getItem(key)
      sessionIdRef.current = old || (window.crypto?.randomUUID?.() ?? `desktop-${Date.now()}`)
      window.sessionStorage.setItem(key, sessionIdRef.current)
    } else {
      sessionIdRef.current = `desktop-${Date.now()}`
    }
    return sessionIdRef.current
  }, [])

  const closeCamera = useCallback(() => {
    cameraStreamRef.current?.getTracks().forEach((track) => track.stop())
    cameraStreamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setCameraOpen(false)
  }, [])

  const transcribeMicBlob = useCallback(async (blob: Blob) => {
    setMediaStatus("Đang chuyển giọng nói thành chữ bằng SCP…")
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onloadend = () => resolve(String(reader.result || ""))
        reader.onerror = () => reject(new Error("Không đọc được audio"))
        reader.readAsDataURL(blob)
      })
      const audioBase64 = dataUrl.split(",", 2)[1] || ""
      const response = await fetch("/api/scp/voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio_base64: audioBase64 }),
        cache: "no-store",
      })
      const data = await response.json().catch(() => ({ error: "Không đọc được kết quả Mic" })) as JsonRecord
      if (data.jailbreak_detected === true) {
        setChatAnswer(data)
        setMediaStatus("Mic bị SCP chặn vì phát hiện nội dung nguy hiểm.")
        return
      }
      const transcript = firstValue(data, ["text_extracted", "transcript", "text"], "")
      if (transcript) {
        setChatQuestion(transcript)
        setMediaStatus("Đã nhận giọng nói. Kiểm tra câu chữ rồi bấm Gửi câu hỏi.")
      } else {
        setMediaStatus(firstValue(data, ["error"], `SCP không nhận được chữ · HTTP ${response.status}`))
      }
    } catch (error) {
      setMediaStatus(`Mic lỗi: ${error instanceof Error ? error.message : "không rõ"}`)
    }
  }, [])

  const toggleMic = useCallback(async () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
      setMicActive(false)
      setMediaStatus("Đã dừng mic.")
      return
    }
    if (recorderRef.current) {
      recorderRef.current.stop()
      setMediaStatus("Đã dừng ghi âm. Đang xử lý…")
      return
    }
    if (navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined") {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        const supportedType = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg"].find((type) => MediaRecorder.isTypeSupported(type))
        const recorder = supportedType ? new MediaRecorder(stream, { mimeType: supportedType }) : new MediaRecorder(stream)
        micStreamRef.current = stream
        recorderRef.current = recorder
        recorderChunksRef.current = []
        recorder.ondataavailable = (event) => { if (event.data.size > 0) recorderChunksRef.current.push(event.data) }
        recorder.onstop = () => {
          const audio = new Blob(recorderChunksRef.current, { type: recorder.mimeType || "audio/webm" })
          recorderRef.current = null
          micStreamRef.current?.getTracks().forEach((track) => track.stop())
          micStreamRef.current = null
          recorderChunksRef.current = []
          setMicActive(false)
          void transcribeMicBlob(audio)
        }
        recorder.start()
        setMicActive(true)
        setMediaStatus("Đang ghi âm một câu. Bấm Mic lần nữa để dừng.")
        return
      } catch (error) {
        setMediaStatus(`Không mở được mic: ${error instanceof Error ? error.message : "quyền bị từ chối"}`)
        return
      }
    }
    const speechWindow = window as Window & { SpeechRecognition?: SpeechRecognitionConstructor; webkitSpeechRecognition?: SpeechRecognitionConstructor }
    const SpeechRecognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setMediaStatus("Desktop chưa có bộ nhận giọng nói; hãy nhập chữ.")
      return
    }
    const recognition = new SpeechRecognition()
    recognition.lang = "vi-VN"
    recognition.interimResults = false
    recognition.continuous = false
    recognition.onstart = () => { setMicActive(true); setMediaStatus("Đang nghe một câu. Bấm lại để dừng.") }
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript
      if (transcript) setChatQuestion(transcript)
    }
    recognition.onerror = (event) => { setMediaStatus(`Mic lỗi: ${event.error || "không rõ"}`) }
    recognition.onend = () => { recognitionRef.current = null; setMicActive(false) }
    recognitionRef.current = recognition
    try { recognition.start() } catch { recognitionRef.current = null; setMicActive(false); setMediaStatus("Không thể khởi động mic.") }
  }, [transcribeMicBlob])

  const openCamera = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setMediaStatus("Desktop chưa hỗ trợ webcam.")
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      cameraStreamRef.current = stream
      setCameraOpen(true)
      setMediaStatus("Webcam đang bật. Chỉ chụp khi bạn bấm Chụp ảnh.")
      window.setTimeout(() => { if (videoRef.current) videoRef.current.srcObject = stream }, 0)
    } catch (error) {
      setMediaStatus(`Không mở được webcam: ${error instanceof Error ? error.message : "quyền bị từ chối"}`)
    }
  }, [])

  const captureImage = useCallback(() => {
    const video = videoRef.current
    if (!video || !cameraStreamRef.current) return
    const canvas = document.createElement("canvas")
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480
    canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height)
    pendingImageRef.current = canvas.toDataURL("image/jpeg", 0.82)
    setMediaStatus("Đã chụp ảnh. Ảnh sẽ gửi cùng câu hỏi tiếp theo.")
    closeCamera()
  }, [closeCamera])

  const toggleTrace = useCallback(async (traceId?: string) => {
    const nextShow = !showTrace
    setShowTrace(nextShow)
    if (nextShow && traceId && !traceDetail) {
      setTraceLoading(true)
      try {
        const response = await fetch(`/api/scp/v3/trace/${encodeURIComponent(traceId)}`, { cache: "no-store" })
        if (response.ok) {
          const data = await response.json().catch(() => null) as JsonRecord | null
          if (data) setTraceDetail(data)
        }
      } catch {
        // Fallback to inline chatAnswer data
      } finally {
        setTraceLoading(false)
      }
    }
  }, [showTrace, traceDetail])

  const sendChat = useCallback(async () => {
    const question = chatQuestion.trim()
    if (!question || chatBusy) return
    setChatBusy(true)
    setShowTrace(false)
    setTraceDetail(null)
    setMediaStatus("SCP đang kiểm tra câu hỏi…")
    try {
      const response = await fetch("/api/scp/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, domain: "general", session_id: ensureSessionId(), image_data: pendingImageRef.current }),
        cache: "no-store",
      })
      const data = await response.json().catch(() => ({ error: "Không đọc được câu trả lời" })) as JsonRecord
      setChatAnswer(data)
      if (response.ok) setChatQuestion("")
      pendingImageRef.current = null
      setMediaStatus(response.ok ? "SCP đã trả lời." : `SCP trả lỗi HTTP ${response.status}.`)
    } catch (error) {
      setMediaStatus(`Không kết nối được SCP: ${error instanceof Error ? error.message : "lỗi không rõ"}`)
    } finally {
      setChatBusy(false)
    }
  }, [chatBusy, chatQuestion, ensureSessionId])

  useEffect(() => () => {
    recognitionRef.current?.stop()
    recorderRef.current?.stop()
    micStreamRef.current?.getTracks().forEach((track) => track.stop())
    closeCamera()
  }, [closeCamera])

  const refresh = useCallback(async () => {
    setRefreshing(true)
    try {
      const [statusResponse, loopResponse, healthResponse, metricsResponse, pcResponse, webResponse, handsResponse] = await Promise.all([
        fetch("/api/scp/status", { cache: "no-store" }),
        fetch("/api/scp/loop", { cache: "no-store" }),
        fetch("/api/scp/health", { cache: "no-store" }),
        fetch("/api/scp/metrics", { cache: "no-store" }),
        fetch("/api/scp/v3/pc/status", { cache: "no-store" }),
        fetch("/api/scp/v3/web/status", { cache: "no-store" }),
        fetch("/api/scp/v3/hands/status", { cache: "no-store" }),
      ])
      const [status, loop, health, metrics, pc, web, hands] = await Promise.all([
        statusResponse.json().catch(() => ({})),
        loopResponse.json().catch(() => ({})),
        healthResponse.json().catch(() => ({})),
        metricsResponse.json().catch(() => ({})),
        pcResponse.json().catch(() => ({})),
        webResponse.json().catch(() => ({})),
        handsResponse.json().catch(() => ({})),
      ])
      setV31Snapshot({ pc: asRecord(pc), web: asRecord(web), hands: asRecord(hands), checkedAt: new Date().toISOString() })
      const statusData = asRecord(status)
      setSnapshot({
        status: statusData,
        loop: asRecord(loop),
        health: asRecord(health),
        metrics: asRecord(metrics),
        checkedAt: firstValue(statusData, ["checkedAt", "timestamp", "updatedAt"], new Date().toISOString()),
        error: null,
      })
      setLastRefresh(new Date())
    } catch (error) {
      setSnapshot((current) => ({ ...current, error: error instanceof Error ? error.message : "Không thể đọc trạng thái live" }))
      setLastRefresh(new Date())
    } finally {
      setRefreshing(false)
    }
  }, [])

  const searchInternet = useCallback(async () => {
    const query = webQuery.trim()
    if (!query) return
    setSearchingWeb(true)
    try {
      const response = await fetch("/api/scp/v3/web/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, maxResults: 8 }),
        cache: "no-store",
      })
      const data = await response.json().catch(() => ({ success: false, error: "Không đọc được kết quả tìm kiếm" }))
      setWebSearch(asRecord(data))
    } catch (error) {
      setWebSearch({ success: false, error: error instanceof Error ? error.message : "Không thể tìm kiếm Internet", results: [] })
    } finally {
      setSearchingWeb(false)
    }
  }, [webQuery])

  useEffect(() => {
    setNow(new Date())
    refresh()
    const refreshTimer = window.setInterval(refresh, 5000)
    const clockTimer = window.setInterval(() => setNow(new Date()), 1000)
    return () => { window.clearInterval(refreshTimer); window.clearInterval(clockTimer) }
  }, [refresh])

  const fastapi = useMemo(() => probeFrom(snapshot.status, ["fastapi", "scp", "api", "python"]), [snapshot.status])
  const loop = useMemo(() => probeFrom(snapshot.status, ["loopScheduler", "loop", "scheduler"]), [snapshot.status])
  const llm = useMemo(() => probeFrom(snapshot.status, ["llmBridge", "llm", "bridge"]), [snapshot.status])
  const healthFastapi = probeFrom(snapshot.health, ["fastapi", "scp", "api"])
  const healthLoop = probeFrom(snapshot.health, ["loopScheduler", "loop", "scheduler"])
  const healthLlm = probeFrom(snapshot.health, ["llmBridge", "llm", "bridge"])
  const combinedFastapi = Object.keys(fastapi).length ? fastapi : healthFastapi
  const combinedLoop = Object.keys(loop).length ? loop : healthLoop
  const combinedLlm = Object.keys(llm).length ? llm : healthLlm
  const kinds = [probeKind(combinedFastapi), probeKind(combinedLoop), probeKind(combinedLlm)]
  const onlineCount = kinds.filter((kind) => kind === "online").length
  const degradedCount = kinds.filter((kind) => kind === "degraded").length
  const overallKind: StatusKind = snapshot.status.scp === "online" ? "online" : degradedCount > 0 ? "degraded" : onlineCount === 3 ? "online" : onlineCount > 0 ? "degraded" : "unknown"
  const engine = asRecord(snapshot.status.engine)
  const loopData = asRecord(snapshot.loop)
  const lastRun = asRecord(loopData.last_run)
  const latestRunStatus = firstValue(lastRun, ["status", "state"], "")
  const runStatusLabel: Record<string, string> = {
    queued: "đã xếp hàng",
    running: "đang chạy",
    completed: "đã hoàn thành",
    complete: "đã hoàn thành",
    ok: "đã hoàn thành",
    failed: "bị lỗi",
    error: "bị lỗi",
    bridge_offline: "chờ kết nối LLM bridge — audit tạm bỏ qua",
    scp_offline: "SCP ngoại tuyến",
    auth_required: "bị chặn xác thực — SCP API từ chối token của scheduler (HTTP 401)",
  }
  // Scheduler payload thật (mini-services/loop-scheduler GET /): running,
  // paused, last_run, next_run, interval_sec, total_runs, auth_configured,
  // scp_online, bridge_online. Các key "currentActivity/activity/message/…"
  // không tồn tại trong payload — bản prior luôn rơi vào fallback chung chung
  // "đang chờ vòng kiểm tra tiếp theo" kể cả khi scheduler đang báo lỗi.
  const loopLink = firstValue(loopData, ["loop"], "offline")
  const schedulerReachable = loopLink === "online" || loopLink === "degraded"
  const lastRunTrigger = lastRun.triggered_by === "cron"
    ? "tự động"
    : lastRun.triggered_by === "manual"
      ? "thủ công"
      : firstValue(lastRun, ["triggered_by"], "hệ thống")
  const lastRunError = firstValue(lastRun, ["error"], "")
  const nextRunAt = firstValue(loopData, ["next_run"], "")
  const intervalSec = firstValue(loopData, ["interval_sec"], "")
  const totalRuns = firstValue(loopData, ["total_runs", "runsToday", "runCount", "totalRuns", "cycles"], "—")
  const activity = loopData.running === true
    ? "Scheduler đang chạy vòng kiểm tra ngay bây giờ"
    : loopData.paused === true
      ? "Scheduler đang tạm dừng theo lệnh người vận hành — không có chu kỳ nào được lên lịch"
      : latestRunStatus
        ? `Chu kỳ gần nhất (${lastRunTrigger} · ${formatTime(firstValue(lastRun, ["ts"], "") || null, "—")}) ${runStatusLabel[latestRunStatus.toLowerCase()] ?? `trạng thái "${latestRunStatus}"`}`
        : schedulerReachable
          ? "Scheduler trực tuyến, chưa ghi nhận chu kỳ nào — đang chờ chu kỳ kế tiếp"
          : "Không đọc được trạng thái scheduler — dịch vụ nền chưa phản hồi, xem gợi ý bên dưới"
  const loopState = loopData.running === true
    ? "đang chạy vòng kiểm tra"
    : loopData.paused === true
      ? "tạm dừng"
      : ({ online: "chạy nền định kỳ", degraded: "phản hồi lỗi", offline: "ngoại tuyến" }[loopLink] ?? (latestRunStatus || statusLabel(probeKind(combinedLoop))))
  const runCount = totalRuns
  const version = firstValue(engine, ["version", "engineVersion"], "SCP DNA")
  const loc = firstValue(engine, ["totalAutofixPyFiles", "autofixLoc", "totalLoc"], "—")
  const lastChecked = snapshot.checkedAt || lastRefresh?.toISOString() || null
  const statusTitle = overallKind === "online" ? "SCP đang vận hành bình thường" : overallKind === "degraded" ? "SCP đang vận hành nhưng có cảnh báo" : "Chưa xác định đầy đủ trạng thái SCP"
  const metrics = snapshot.metrics
  const latencyMs = Math.max(0, ...[combinedFastapi, combinedLoop, combinedLlm].map((probe) => asNumber(probe.latencyMs)))
  const cpuPercent = Math.max(0, Math.min(100, asNumber(metrics.cpuPercent)))
  const memoryPercent = Math.max(0, Math.min(100, asNumber(metrics.memoryPercent)))
  const loadPercent = Math.max(0, Math.min(100, asNumber(metrics.loadPercent, Math.max(cpuPercent, memoryPercent))))
  const latencyMax = Math.max(500, ...metricHistory.map((point) => point.latencyMs)) * 1.15
  const alertReasons = [
    snapshot.error ? "Dashboard không đọc được dữ liệu live" : "",
    kinds.some((kind) => kind === "offline") ? "Có dịch vụ SCP ngoại tuyến" : "",
    latencyMs >= alertSettings.latencyThresholdMs ? `Độ trễ tăng lên ${Math.round(latencyMs)} ms` : "",
  ].filter(Boolean)
  const pcController = v31Snapshot.pc
  const webControl = v31Snapshot.web
  const handsControl = v31Snapshot.hands
  const plannerStatus = asRecord(handsControl.planner)
  const plannerActive = asRecord(plannerStatus.activePlan)
  const plannerState = firstValue(plannerActive, ["state"], firstValue(plannerStatus, ["planner"], "offline"))
  const plannerGoal = firstValue(plannerActive, ["goal"], "Chưa có kế hoạch đang chạy")
  const plannerCurrentStep = firstValue(plannerActive, ["currentStepId"], "—")
  const plannerSteps = Array.isArray(plannerActive.steps) ? plannerActive.steps as JsonRecord[] : []
  const plannerStep = plannerSteps.find((step) => asText(step.stepId) === plannerCurrentStep) || {}
  const plannerAttempts = firstValue(plannerStep, ["attempts"], "0")
  const navigatorStatus = asRecord(webControl.navigator)
  const browserSession = asRecord(navigatorStatus.browserSession)
  const browserPages = Array.isArray(browserSession.pages) ? browserSession.pages : []
  const orchestratorStatus = asRecord(webControl.orchestrator)
  const pcOnline = firstValue(pcController, ["controller"], "offline") === "online"
  const browserOnline = browserSession.available === true

  useEffect(() => {
    if (!snapshot.checkedAt && !lastRefresh) return
    const point: MetricPoint = { time: formatTime(lastChecked, "—"), latencyMs, cpuPercent, memoryPercent, loadPercent }
    setMetricHistory((current) => [...current, point].slice(-36))
  }, [snapshot.checkedAt, lastChecked, latencyMs, cpuPercent, memoryPercent, loadPercent])

  useEffect(() => {
    if (!alertSettings.enabled || alertReasons.length === 0) {
      setAlertState("Không có lỗi nghiêm trọng")
      return
    }
    const key = alertReasons.join("|")
    const nowMs = Date.now()
    if (lastAlertKey.current === key && nowMs - lastAlertAt.current < alertSettings.cooldownMs) {
      setAlertState(`Đã cảnh báo · chờ cooldown ${Math.ceil((alertSettings.cooldownMs - (nowMs - lastAlertAt.current)) / 1000)}s`)
      return
    }
    lastAlertKey.current = key
    lastAlertAt.current = nowMs
    setAlertState(alertReasons.join(" · "))
    if (alertSettings.soundEnabled) playCriticalTone()
    const bridge = (window as Window & { scpDesktop?: DesktopBridge }).scpDesktop
    if (alertSettings.notifyEnabled && bridge?.notifyCritical) {
      void bridge.notifyCritical({ title: "SCP · Cảnh báo nghiêm trọng", body: alertReasons.join("\n") })
    } else if (alertSettings.notifyEnabled && typeof Notification !== "undefined" && Notification.permission === "granted") {
      new Notification("SCP · Cảnh báo nghiêm trọng", { body: alertReasons.join("\n") })
    }
  }, [alertSettings, alertReasons.join("|"), snapshot.checkedAt, snapshot.error, kinds.join("|"), latencyMs])

  return (
    <div className="min-h-screen bg-[#07111f] text-slate-100">
      <div className="mx-auto flex w-full max-w-[1500px]">
        <aside className="hidden min-h-screen w-64 shrink-0 border-r border-white/[0.08] bg-[#081525] px-5 py-7 lg:block">
          <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-2xl bg-cyan-300 text-slate-950 shadow-lg shadow-cyan-400/20"><ShieldCheck className="h-5 w-5" /></div><div><div className="text-sm font-bold tracking-wide text-white">SCP DNA</div><div className="text-xs text-slate-500">Desktop Control Center</div></div></div>
          <div className="mt-10 space-y-2"><div className="rounded-xl bg-cyan-300/10 px-3 py-2.5 text-sm font-medium text-cyan-200"><Activity className="mr-2 inline h-4 w-4" />Tổng quan live</div><button type="button" onClick={() => { setActiveTab("system"); void refresh(); }} className={`w-full rounded-xl px-3 py-2.5 text-left text-sm ${activeTab === "system" ? "bg-white/[0.08] text-slate-100" : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"}`}><ScanSearch className="mr-2 inline h-4 w-4" />Kiểm tra hệ thống</button><button type="button" onClick={() => void triggerControlledFix()} disabled={fixing} className={`w-full rounded-xl px-3 py-2.5 text-left text-sm ${activeTab === "fix" ? "bg-amber-300/10 text-amber-100" : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"} disabled:cursor-wait disabled:opacity-60`}><Wrench className="mr-2 inline h-4 w-4" />{fixing ? "Đang gửi yêu cầu…" : "Sửa có kiểm soát"}</button></div>
          <div className="mt-auto pt-24"><div className="rounded-2xl border border-white/[0.08] bg-white/[0.035] p-4"><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400"><CircleHelp className="h-4 w-4 text-cyan-300" />SCP là gì?</div><p className="mt-3 text-sm leading-6 text-slate-400">Một vòng lặp quan sát, kiểm chứng, sửa lỗi an toàn và ghi nhận bài học để hệ thống tự cải thiện có kiểm soát.</p></div></div>
        </aside>

        <main className="min-w-0 flex-1 px-4 py-5 sm:px-7 sm:py-8 lg:px-10">
          <header className="flex flex-col gap-5 border-b border-white/[0.08] pb-7 md:flex-row md:items-start md:justify-between"><div><div className="mb-3 inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1.5 text-xs font-medium text-cyan-200"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-300" />LIVE · tự làm mới mỗi 5 giây</div><h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">Trung tâm điều khiển SCP</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400 sm:text-base">Một màn hình duy nhất để biết hệ thống đang khỏe hay không, dịch vụ nào đang chạy và SCP hiện đang làm gì.</p></div><div className="flex items-center gap-3"><div className="hidden text-right sm:block"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">Giờ máy</div><div className="mt-1 font-mono text-sm text-slate-300" suppressHydrationWarning>{now ? now.toLocaleTimeString("vi-VN") : "--:--:--"}</div></div><button type="button" onClick={refresh} disabled={refreshing} className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.06] px-3.5 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-white/10 disabled:cursor-wait disabled:opacity-60" aria-label="Làm mới trạng thái"><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />Làm mới</button></div></header>
          <nav aria-label="SCP tabs" className="mt-5 flex flex-wrap gap-2"><button type="button" data-testid="system-tab" onClick={() => { setActiveTab("system"); void refresh(); }} className={`rounded-xl border px-4 py-2 text-sm ${activeTab === "system" ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-100" : "border-white/10 text-slate-200"}`}>Kiểm tra hệ thống · Chạy kiểm tra ngay</button><button type="button" data-testid="fix-tab" onClick={() => void triggerControlledFix()} disabled={fixing} className={`rounded-xl border px-4 py-2 text-sm ${activeTab === "fix" ? "border-amber-300/50 bg-amber-300/10 text-amber-100" : "border-amber-300/30 text-amber-100"} disabled:cursor-wait disabled:opacity-60`}>{fixing ? "Đang gửi yêu cầu…" : "Sửa có kiểm soát · Gửi yêu cầu sửa có kiểm soát"}</button></nav>

          <section aria-label="Chat với SCP" className="mt-5 rounded-3xl border border-cyan-300/20 bg-cyan-300/[0.06] p-5 sm:p-7"><SectionHeading eyebrow="00 · Giao tiếp trực tiếp" title="Hỏi SCP bằng chữ, mic hoặc webcam" description="Mic và camera chỉ hoạt động sau khi bạn bấm nút. SCP không tự ghi âm hoặc tự quay." icon={MessageCircle} /><div className="flex flex-col gap-3"><textarea value={chatQuestion} onChange={(event) => setChatQuestion(event.target.value)} onKeyDown={(event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") void sendChat() }} placeholder="Nhập câu hỏi cho SCP… (Ctrl+Enter để gửi)" rows={3} className="w-full resize-y rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-300/40" /><div className="flex flex-wrap items-center gap-2"><button type="button" onClick={() => void sendChat()} disabled={chatBusy || !chatQuestion.trim()} className="rounded-xl bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-slate-950 disabled:cursor-wait disabled:opacity-50">{chatBusy ? "Đang kiểm tra…" : "Gửi câu hỏi"}</button><button type="button" onClick={toggleMic} className={`rounded-xl border px-4 py-2.5 text-sm ${micActive ? "border-rose-300/50 bg-rose-300/10 text-rose-100" : "border-white/10 text-slate-200"}`}>{micActive ? "Dừng mic" : "Mic"}</button><button type="button" onClick={() => void openCamera()} className={`rounded-xl border px-4 py-2.5 text-sm ${cameraOpen ? "border-amber-300/50 bg-amber-300/10 text-amber-100" : "border-white/10 text-slate-200"}`}>Webcam</button><span className="text-xs text-slate-400">{mediaStatus}</span></div>{cameraOpen && <div className="mt-3 flex flex-wrap items-center gap-3 rounded-2xl border border-white/10 bg-black/20 p-3"><video ref={videoRef} autoPlay muted playsInline className="h-40 w-60 rounded-xl bg-black object-contain" /><button type="button" onClick={captureImage} className="rounded-xl bg-amber-300 px-4 py-2.5 text-sm font-semibold text-slate-950">Chụp ảnh</button><button type="button" onClick={closeCamera} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-200">Tắt webcam</button></div>}{chatAnswer && (
  <div className="mt-3 rounded-2xl border border-white/10 bg-black/20 p-4">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="text-xs uppercase tracking-[0.16em] text-cyan-200">
        {firstValue(chatAnswer, ["verdict"], "UNKNOWN")} · {firstValue(chatAnswer, ["domain"], "general")}
        {chatAnswer.elapsed_ms != null ? ` · ${chatAnswer.elapsed_ms}ms` : ""}
      </div>
      {Boolean(chatAnswer.trace_id) && (
        <button
          type="button"
          onClick={() => void toggleTrace(String(chatAnswer.trace_id))}
          className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-300/30 bg-cyan-300/10 px-2.5 py-1 text-xs font-medium text-cyan-200 transition hover:bg-cyan-300/20"
        >
          <GitBranch className="h-3.5 w-3.5" />
          <span>Truy vết quyết định (Trace Tree)</span>
          <ChevronDown className={`h-3 w-3 transition-transform ${showTrace ? "rotate-180" : ""}`} />
        </button>
      )}
    </div>
    <div className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-200">
      {firstValue(chatAnswer, ["final_answer", "answer", "error"], "Chưa có câu trả lời")}
    </div>
    {showTrace && (
      <div className="mt-4 rounded-xl border border-cyan-500/20 bg-slate-900/80 p-4 text-xs">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.08] pb-2 font-semibold text-cyan-300">
          <span className="flex items-center gap-1.5">
            <Layers3 className="h-4 w-4" /> Bằng chứng & Cây quyết định nguyên nhân (Causal Trace)
          </span>
          <span className="font-mono text-[11px] text-slate-400">{String(chatAnswer.trace_id || "")}</span>
        </div>
        {traceLoading ? (
          <div className="py-4 text-center text-slate-400 animate-pulse">Đang truy xuất sổ cái truy vết (TraceLedger)…</div>
        ) : (
          <>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <div className="rounded-lg bg-black/30 p-2.5">
                <span className="text-slate-400">Luồng xử lý (Routing Lane):</span>
                <div className="mt-1 font-mono text-cyan-200">{String(traceDetail?.lane || chatAnswer.lane || "LANE_CHATBOT")}</div>
              </div>
              <div className="rounded-lg bg-black/30 p-2.5">
                <span className="text-slate-400">Phán quyết & Độ tin cậy:</span>
                <div className="mt-1 font-mono text-emerald-300">{String(chatAnswer.verdict || "PASS")} · {Math.round(Number(chatAnswer.confidence || 1) * 100)}%</div>
              </div>
              <div className="rounded-lg bg-black/30 p-2.5">
                <span className="text-slate-400">Cổng Quản trị (Governance):</span>
                <div className="mt-1 font-mono text-slate-200">{String(traceDetail?.governance_decision || chatAnswer.governance_decision || "ALLOW")}</div>
              </div>
              <div className="rounded-lg bg-black/30 p-2.5">
                <span className="text-slate-400">Tra cứu nguồn ngoài:</span>
                <div className="mt-1 font-mono text-slate-200">{chatAnswer.web_fallback_used ? "Đã tra cứu Web độc lập" : "Bộ nhớ đàm thoại + LLM Reasoning"}</div>
              </div>
            </div>
            {Array.isArray(chatAnswer.slm_trace) && chatAnswer.slm_trace.length > 0 && (
              <div className="mt-3 rounded-lg bg-black/30 p-2.5">
                <span className="text-slate-400">Các bước thực thi & Suy luận:</span>
                <div className="mt-1 space-y-1">
                  {(chatAnswer.slm_trace as JsonRecord[]).map((step, idx) => (
                    <div key={idx} className="flex items-center justify-between text-[11px] font-mono text-slate-300">
                      <span>• {asText(step.slm_name || step.source || "reasoner")}</span>
                      <span className="text-slate-500">{step.time_ms ? `${step.time_ms}ms` : ""}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {Boolean(chatAnswer.run_id) && (
              <div className="mt-2 text-[11px] text-slate-500">
                Mã phiên (Run ID): <span className="font-mono text-slate-400">{String(chatAnswer.run_id)}</span>
              </div>
            )}
          </>
        )}
      </div>
    )}
  </div>
)}</div></section>

          <VideoCallPanel />

          <section className="mt-7 rounded-3xl border border-white/10 bg-gradient-to-br from-cyan-400/[0.14] via-white/[0.045] to-transparent p-5 shadow-2xl shadow-black/20 sm:p-7"><div className="flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between"><div className="flex items-start gap-4"><div className={`mt-1 grid h-12 w-12 shrink-0 place-items-center rounded-2xl ${overallKind === "online" ? "bg-emerald-400/15 text-emerald-300" : overallKind === "degraded" ? "bg-amber-400/15 text-amber-300" : "bg-slate-400/15 text-slate-300"}`}><Gauge className="h-6 w-6" /></div><div><div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Tình trạng tổng thể</div><h2 className="mt-1 text-2xl font-semibold text-white">{statusTitle}</h2><p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">{onlineCount}/3 dịch vụ nền tảng đang phản hồi. Kiểm tra gần nhất: <span className="text-slate-300">{formatTime(lastChecked)}</span>.</p></div></div><div className="grid grid-cols-2 gap-3 sm:grid-cols-3"><div className="rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.08] px-4 py-3"><div className="text-2xl font-semibold text-emerald-200">{onlineCount}</div><div className="mt-1 text-xs text-emerald-200/70">Đang chạy</div></div><div className="rounded-2xl border border-amber-300/15 bg-amber-300/[0.08] px-4 py-3"><div className="text-2xl font-semibold text-amber-200">{degradedCount}</div><div className="mt-1 text-xs text-amber-200/70">Cảnh báo</div></div><div className="rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3"><div className="text-2xl font-semibold text-slate-200">{3 - onlineCount - degradedCount}</div><div className="mt-1 text-xs text-slate-400">Chưa rõ</div></div></div></div></section>

          {snapshot.error && <div className="mt-5 flex items-start gap-3 rounded-2xl border border-rose-400/25 bg-rose-400/10 p-4 text-sm text-rose-100"><TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" /><div><div className="font-medium">Không đọc được toàn bộ dữ liệu live</div><div className="mt-1 text-rose-100/70">{snapshot.error}. Dashboard vẫn hiển thị lần đọc gần nhất.</div></div></div>}

          <section className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Vòng lặp hiện tại" value={loopState} detail={activity} icon={RefreshCw} accent="text-cyan-300" /><MetricCard label="Lần chạy hôm nay" value={runCount} detail="Theo dữ liệu scheduler" icon={Play} accent="text-violet-300" /><MetricCard label="Engine" value={version} detail="Phiên bản lõi đang quan sát" icon={BrainCircuit} accent="text-amber-300" /><MetricCard label="Độ mới dữ liệu" value={lastRefresh ? `${Math.max(0, Math.round((Date.now() - lastRefresh.getTime()) / 1000))}s` : "—"} detail="Từ lần đồng bộ gần nhất" icon={Clock3} accent="text-emerald-300" /></section>

                    <section className="mt-8 rounded-3xl border border-violet-300/15 bg-violet-300/[0.05] p-5 sm:p-7"><SectionHeading eyebrow="V3.1 · V3.5 · Control plane" title="SCP có tay chân ở đâu?" description="Khu vực này tách rõ suy luận, Action Registry và các công cụ SCP được phép dùng. Mỗi hành động cần policy, capability, verifier và audit." icon={GitBranch} /><div className="grid gap-4 lg:grid-cols-4">
<div className="rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.07] p-4"><div className="flex items-center justify-between gap-3"><div className="font-medium text-white">PC Controller</div><span className={`rounded-full px-2 py-1 text-[11px] ${pcOnline ? "bg-emerald-300/15 text-emerald-200" : "bg-rose-300/15 text-rose-200"}`}>{pcOnline ? "Đang hoạt động" : "Ngoại tuyến"}</span></div><p className="mt-2 text-xs leading-5 text-slate-400">Cấp quyền: {firstValue(pcController, ["policy"], "allowlist + approval")}</p><div className="mt-3 flex items-center justify-between text-xs text-slate-500"><span>Audit entries</span><span className="font-mono text-slate-200">{firstValue(pcController, ["auditEntries"], "—")}</span></div></div><div className="rounded-2xl border border-cyan-300/15 bg-cyan-300/[0.07] p-4"><div className="flex items-center justify-between gap-3"><div className="font-medium text-white">Web Navigator</div><span className={`rounded-full px-2 py-1 text-[11px] ${browserOnline ? "bg-cyan-300/15 text-cyan-200" : "bg-amber-300/15 text-amber-200"}`}>{browserOnline ? "Đã nối browser" : "Chưa nối browser"}</span></div><p className="mt-2 text-xs leading-5 text-slate-400">{browserOnline ? `${browserPages.length} trang đang quan sát` : "Cần phiên Chrome/Edge đã đăng nhập với DevTools cục bộ."}</p><div className="mt-3 text-xs text-slate-500">Chỉ đọc nguồn công khai hoặc phiên local được cấp quyền</div></div><div className="rounded-2xl border border-violet-300/15 bg-violet-300/[0.07] p-4"><div className="flex items-center justify-between gap-3"><div className="font-medium text-white">AI Orchestrator</div><span className="rounded-full bg-violet-300/15 px-2 py-1 text-[11px] text-violet-200">Browser-first</span></div><p className="mt-2 text-xs leading-5 text-slate-400">{firstValue(orchestratorStatus, ["apiFallback"], "explicit-only")}. Gửi câu hỏi qua AI đã đăng nhập chỉ khi có approval.</p><div className="mt-3 text-xs text-slate-500">Consensus không được coi là bằng chứng cuối cùng</div></div><div className="rounded-2xl border border-amber-300/15 bg-amber-300/[0.07] p-4"><div className="flex items-center justify-between gap-3"><div className="font-medium text-white">SCP Hands v3.7 Planner + DAG</div><span className={`rounded-full px-2 py-1 text-[11px] ${firstValue(handsControl, ["hands"], "offline") === "online" ? "bg-emerald-300/15 text-emerald-200" : "bg-amber-300/15 text-amber-200"}`}>{firstValue(handsControl, ["hands"], "offline") === "online" ? "Đang hoạt động" : "Chưa nối"}</span></div><p className="mt-2 text-xs leading-5 text-slate-400">Action Registry: {firstValue(handsControl, ["actionCount"], "—")} hành động · Planner: {plannerState}</p><div className="mt-3 line-clamp-2 text-xs leading-5 text-slate-300">{plannerGoal}</div><div className="mt-2 flex items-center justify-between text-xs text-slate-500"><span>Bước hiện tại</span><span className="font-mono text-slate-200">{plannerCurrentStep}</span></div><div className="mt-2 flex items-center justify-between text-xs text-slate-500"><span>Lần thử</span><span className="font-mono text-slate-200">{plannerAttempts}</span></div><div className="mt-2 flex items-center justify-between text-xs text-slate-500"><span>Processes sở hữu</span><span className="font-mono text-slate-200">{firstValue(handsControl, ["managedProcessCount"], "0")}</span></div><div className="mt-2 flex items-center justify-between text-xs text-slate-500"><span>Checkpoints</span><span className="font-mono text-slate-200">{firstValue(handsControl, ["checkpoints"], "—")}</span></div></div></div></section>

          <section className="mt-8 rounded-3xl border border-cyan-300/15 bg-cyan-300/[0.045] p-5 sm:p-7"><SectionHeading eyebrow="01 · Không phụ thuộc một AI" title="Tìm kiếm Internet độc lập" description="SCP có thể tìm nguồn công khai qua nhiều bộ chỉ mục. ChatGPT, Claude, Gemini hoặc mô hình cục bộ chỉ là các kênh tùy chọn; kết quả web luôn được đánh dấu là dữ liệu chưa kiểm chứng." icon={Globe2} /><div className="flex flex-col gap-3 sm:flex-row"><input value={webQuery} onChange={(event) => setWebQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void searchInternet() }} placeholder="Ví dụ: SCP self correcting process" className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-300/40" /><button type="button" onClick={() => void searchInternet()} disabled={searchingWeb || !webQuery.trim()} className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-300 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-wait disabled:opacity-50"><ScanSearch className="h-4 w-4" />{searchingWeb ? "Đang tìm…" : "Tìm trên Internet"}</button></div>{Array.isArray(webSearch.results) && webSearch.results.length > 0 ? <div className="mt-5 space-y-2">{(webSearch.results as JsonRecord[]).slice(0, 8).map((result, index) => <a key={`${asText(result.url)}-${index}`} href={asText(result.url)} target="_blank" rel="noreferrer" className="block rounded-xl border border-white/[0.08] bg-black/15 p-3 transition hover:border-cyan-300/30 hover:bg-cyan-300/[0.06]"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="truncate text-sm font-medium text-slate-100">{asText(result.title, "Không có tiêu đề")}</div><div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-400">{asText(result.snippet, "Không có mô tả")}</div></div><span className="shrink-0 rounded-full border border-white/10 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-cyan-200">{asText(result.provider, "web")}</span></div></a>)}</div> : <div className="mt-4 text-xs text-slate-500">{Object.keys(webSearch).length ? asText(webSearch.error, "Không có kết quả phù hợp") : "Nhập câu hỏi để SCP tự tìm nguồn công khai; kết quả không được coi là sự thật cuối cùng."}</div>}<div className="mt-4 flex flex-wrap gap-2 text-[11px] text-slate-500"><span className="rounded-full border border-white/10 px-2.5 py-1">DuckDuckGo</span><span className="rounded-full border border-white/10 px-2.5 py-1">Bing</span><span className="rounded-full border border-amber-300/20 bg-amber-300/[0.06] px-2.5 py-1 text-amber-200">Dữ liệu cần kiểm chứng</span></div></section>

          <section className="mt-8 rounded-3xl border border-white/10 bg-white/[0.035] p-5 sm:p-7"><SectionHeading eyebrow="02 · Hệ thống đang làm gì" title="Hoạt động thời gian thực" description="Đây là khu vực ưu tiên: đọc tín hiệu mới nhất từ scheduler và cho biết SCP đang chờ, đang kiểm tra hay đang xử lý." icon={Activity} /><div className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr]"><div className="rounded-2xl border border-cyan-300/15 bg-cyan-300/[0.07] p-5"><div className="flex items-start gap-3"><div className="mt-1 h-2.5 w-2.5 animate-pulse rounded-full bg-cyan-300 shadow-[0_0_0_5px_rgba(103,232,249,0.12)]" /><div className="min-w-0"><div className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200/80">Đang làm gì</div><div className="mt-2 text-lg font-medium leading-8 text-white">{activity}</div>{(lastRunError || !schedulerReachable) && <div className="mt-3 rounded-xl border border-amber-300/25 bg-amber-300/[0.08] p-3 text-xs leading-5 text-amber-100">{!schedulerReachable ? `Scheduler chưa phản hồi. Gợi ý: ${firstValue(loopData, ["hint"], "khởi động lại dịch vụ loop-scheduler")}${lastRunError ? ` · Lỗi chu kỳ gần nhất: ${lastRunError}` : ""}` : `Chi tiết chu kỳ gần nhất: ${lastRunError}`}</div>}<div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-400"><span>Tổng chu kỳ ghi nhận: <span className="font-mono text-slate-200">{totalRuns}</span></span><span>Chu kỳ kế tiếp: <span className="font-mono text-slate-200">{nextRunAt ? formatTime(nextRunAt, "—") : "—"}</span></span><span>Khoảng cách: <span className="font-mono text-slate-200">{intervalSec ? `${intervalSec}s` : "—"}</span></span></div><div className="mt-3 text-sm text-slate-400">SCP cập nhật bảng này tự động, không cần tải lại toàn bộ ứng dụng.</div></div></div></div><div className="rounded-2xl border border-white/[0.08] bg-black/10 p-5"><div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Mốc dữ liệu</div><div className="mt-3 space-y-3 text-sm"><div className="flex items-center justify-between gap-3"><span className="text-slate-500">Lần kiểm tra</span><span className="font-mono text-slate-200">{formatTime(lastChecked)}</span></div><div className="flex items-center justify-between gap-3"><span className="text-slate-500">Cập nhật UI</span><span className="font-mono text-slate-200" suppressHydrationWarning>{lastRefresh ? lastRefresh.toLocaleTimeString("vi-VN") : "—"}</span></div><div className="flex items-center justify-between gap-3"><span className="text-slate-500">Chu kỳ</span><span className="text-slate-200">5 giây</span></div></div></div></div></section>

          <LiveActivityStream />

          <section className="mt-8 rounded-3xl border border-white/10 bg-white/[0.035] p-5 sm:p-7"><SectionHeading eyebrow="02 · Live metrics" title="Độ trễ và tải hệ thống" description="Các mẫu đo mới nhất được giữ trong 36 điểm để nhìn xu hướng ngắn hạn mà không làm giao diện nặng hoặc rối." icon={BarChart3} /><div className="grid gap-4 xl:grid-cols-2"><LiveLineChart title="Độ trễ dịch vụ" subtitle="Độ trễ cao nhất giữa Python API, Scheduler và LLM Bridge" lines={[{ label: "ms", color: "#67e8f9", values: metricHistory.map((point) => point.latencyMs) }]} maxValue={latencyMax} unit=" ms" /><LiveLineChart title="Tải máy chạy SCP" subtitle="CPU, bộ nhớ và tải tổng hợp của host" lines={[{ label: "CPU", color: "#a78bfa", values: metricHistory.map((point) => point.cpuPercent) }, { label: "Bộ nhớ", color: "#fbbf24", values: metricHistory.map((point) => point.memoryPercent) }, { label: "Tổng hợp", color: "#34d399", values: metricHistory.map((point) => point.loadPercent) }]} maxValue={100} unit="%" /></div><div className="mt-4 flex flex-col gap-4 rounded-2xl border border-rose-300/15 bg-rose-300/[0.06] p-4 lg:flex-row lg:items-center lg:justify-between"><div className="flex items-start gap-3"><BellRing className="mt-0.5 h-5 w-5 shrink-0 text-rose-200" /><div><div className="text-sm font-medium text-rose-100">Cảnh báo nghiêm trọng</div><div className="mt-1 text-xs leading-5 text-rose-100/70">{alertState}. Âm thanh và thông báo chỉ phát lại sau cooldown để tránh spam.</div></div></div><div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-300"><label className="inline-flex items-center gap-2"><input type="checkbox" checked={alertSettings.enabled} onChange={(event) => setAlertSettings((current) => ({ ...current, enabled: event.target.checked }))} className="accent-cyan-300" />Bật cảnh báo</label><label className="inline-flex items-center gap-2"><input type="checkbox" checked={alertSettings.soundEnabled} onChange={(event) => setAlertSettings((current) => ({ ...current, soundEnabled: event.target.checked }))} className="accent-cyan-300" />Âm thanh</label><label className="inline-flex items-center gap-2"><input type="checkbox" checked={alertSettings.notifyEnabled} onChange={(event) => setAlertSettings((current) => ({ ...current, notifyEnabled: event.target.checked }))} className="accent-cyan-300" />Desktop notification</label><label className="inline-flex items-center gap-2">Ngưỡng <input type="number" min="100" step="100" value={alertSettings.latencyThresholdMs} onChange={(event) => setAlertSettings((current) => ({ ...current, latencyThresholdMs: Math.max(100, Number(event.target.value) || 1200) }))} className="w-20 rounded-lg border border-white/10 bg-black/20 px-2 py-1 text-right text-xs text-white" /> ms</label></div></div></section>

          <section className="mt-8 rounded-3xl border border-white/10 bg-white/[0.035] p-5 sm:p-7"><SectionHeading eyebrow="03 · Sức khỏe nền tảng" title="Ba dịch vụ cốt lõi" description="Bảng duy nhất cho tình trạng service, độ trễ và gợi ý xử lý. Các chi tiết kỹ thuật chỉ hiện khi cần." icon={ServerCog} /><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left"><thead><tr className="text-[11px] uppercase tracking-[0.16em] text-slate-500"><th className="pb-3 pr-4 font-medium">Dịch vụ</th><th className="pb-3 pr-4 font-medium">Tình trạng</th><th className="pb-3 pr-4 font-medium">Độ trễ</th><th className="pb-3 text-right font-medium">Ghi chú</th></tr></thead><tbody><ServiceStatusRow name="SCP Python API" role="Bộ não kiểm tra và tự sửa" probe={combinedFastapi} icon={ServerCog} /><ServiceStatusRow name="Loop Scheduler" role="Điều phối vòng lặp định kỳ" probe={combinedLoop} icon={RefreshCw} /><ServiceStatusRow name="LLM Bridge" role="Cầu nối mô hình ngôn ngữ" probe={combinedLlm} icon={BrainCircuit} /></tbody></table></div></section>

          <section className="mt-8 rounded-3xl border border-white/10 bg-white/[0.035] p-5 sm:p-7"><SectionHeading eyebrow="03 · SCP hoạt động như thế nào" title="Một vòng lặp, bốn bước dễ hiểu" description="Không cần đọc hàng chục bảng kỹ thuật để hiểu hệ thống. Hãy bắt đầu từ luồng hoạt động này." icon={Layers3} /><div className="grid gap-3 md:grid-cols-4"><div className="rounded-2xl border border-cyan-300/15 bg-cyan-300/[0.07] p-4"><div className="text-xs font-bold text-cyan-200">01</div><Eye className="mt-5 h-5 w-5 text-cyan-300" /><div className="mt-3 font-medium text-white">Quan sát</div><p className="mt-2 text-sm leading-6 text-slate-400">Theo dõi code, service, lỗi và tín hiệu bất thường.</p></div><div className="rounded-2xl border border-violet-300/15 bg-violet-300/[0.07] p-4"><div className="text-xs font-bold text-violet-200">02</div><ScanSearch className="mt-5 h-5 w-5 text-violet-300" /><div className="mt-3 font-medium text-white">Kiểm chứng</div><p className="mt-2 text-sm leading-6 text-slate-400">Không coi một kết quả PASS là đúng nếu chưa kiểm tra thực tế.</p></div><div className="rounded-2xl border border-amber-300/15 bg-amber-300/[0.07] p-4"><div className="text-xs font-bold text-amber-200">03</div><Wrench className="mt-5 h-5 w-5 text-amber-300" /><div className="mt-3 font-medium text-white">Sửa có kiểm soát</div><p className="mt-2 text-sm leading-6 text-slate-400">Đề xuất, xem xét và áp dụng thay đổi theo tầng an toàn.</p></div><div className="rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.07] p-4"><div className="text-xs font-bold text-emerald-200">04</div><Sparkles className="mt-5 h-5 w-5 text-emerald-300" /><div className="mt-3 font-medium text-white">Học lại</div><p className="mt-2 text-sm leading-6 text-slate-400">Ghi nhận kết quả để vòng sau phát hiện tốt hơn.</p></div></div></section>

          <section className="mt-8 grid gap-4 lg:grid-cols-2"><details className="group rounded-3xl border border-white/10 bg-white/[0.035] p-5 sm:p-7"><summary className="flex cursor-pointer list-none items-center justify-between gap-4"><div><div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Chi tiết kỹ thuật</div><div className="mt-2 text-lg font-semibold text-white">Engine và năng lực tự sửa</div></div><ChevronDown className="h-5 w-5 text-slate-500 transition group-open:rotate-180" /></summary><div className="mt-5 grid grid-cols-2 gap-3 text-sm"><div className="rounded-xl bg-black/15 p-3"><div className="text-xs text-slate-500">Autofix files</div><div className="mt-1 text-lg font-semibold text-white">{loc}</div></div><div className="rounded-xl bg-black/15 p-3"><div className="text-xs text-slate-500">Version</div><div className="mt-1 text-lg font-semibold text-white">{version}</div></div><div className="rounded-xl bg-black/15 p-3"><div className="text-xs text-slate-500">Model label</div><div className="mt-1 text-lg font-semibold text-white">1.6</div></div><div className="rounded-xl bg-black/15 p-3"><div className="text-xs text-slate-500">Data refresh</div><div className="mt-1 text-lg font-semibold text-white">5s</div></div></div></details><details className="group rounded-3xl border border-white/10 bg-white/[0.035] p-5 sm:p-7"><summary className="flex cursor-pointer list-none items-center justify-between gap-4"><div><div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Khi có vấn đề</div><div className="mt-2 text-lg font-semibold text-white">Cách đọc cảnh báo</div></div><ChevronDown className="h-5 w-5 text-slate-500 transition group-open:rotate-180" /></summary><div className="mt-5 space-y-3 text-sm leading-6 text-slate-400"><div className="flex gap-3"><CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-emerald-300" /><span><strong className="text-slate-200">Đang hoạt động:</strong> service trả lời và độ trễ có thể đo được.</span></div><div className="flex gap-3"><AlertTriangle className="mt-1 h-4 w-4 shrink-0 text-amber-300" /><span><strong className="text-slate-200">Có cảnh báo:</strong> SCP còn hoạt động nhưng một thành phần cần theo dõi.</span></div><div className="flex gap-3"><XCircle className="mt-1 h-4 w-4 shrink-0 text-rose-300" /><span><strong className="text-slate-200">Ngoại tuyến:</strong> cần kiểm tra log hoặc khởi động lại service liên quan.</span></div></div></details></section>

          <footer className="mt-8 flex flex-col gap-2 border-t border-white/[0.08] py-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between"><span>SCP DNA Desktop · mô hình 1.6</span><span className="inline-flex items-center gap-2" suppressHydrationWarning><Database className="h-3.5 w-3.5" />Dữ liệu live từ dashboard API · {lastRefresh ? `đồng bộ ${lastRefresh.toLocaleTimeString("vi-VN")}` : "đang kết nối"}</span></footer>
        </main>
      </div>
    </div>
  )
}
