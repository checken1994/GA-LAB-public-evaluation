"use client"

/**
 * SCP Control Panel — dashboard widget showing live SCP status.
 *
 * This component turns the dashboard from a static report into a CONTROL
 * PANEL by actually fetching SCP Python's `/health` endpoint (through
 * the Next.js `/api/scp/health` proxy). If SCP is offline, shows a clear
 * "Run: python3 -m scp" hint instead of crashing (fail-open).
 *
 * Wiring (Task 7.5):
 *   - GET /api/scp/health      → liveness + version
 *   - GET /api/scp/routes      → route listing (static)
 *   - GET /api/scp/status      → engine + audit metadata
 *
 * Refresh button re-fetches `/api/scp/health` on demand. Auto-refresh
 * every 30 seconds while the panel is mounted.
 */
import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RefreshCw, Server, ServerOff, Terminal, Activity, ShieldAlert, Repeat, Play, Loader2 } from "lucide-react"
import { CURRENT_ROUND } from "@/lib/audit-data/version"

interface ScpHealth {
  scp: "online" | "degraded" | "offline"
  hint?: string
  error?: string
  checkedAt?: string
  [k: string]: unknown
}

interface LoopRun {
  ts: string
  scp_online: boolean
  status: "ok" | "error" | "scp_offline" | "auth_required" | "skipped" | string
  findings_count?: number
  fixes_applied?: number
  permission_requested?: number
  skipped?: number
  duration_ms?: number
  http_status?: number
  error?: string
  triggered_by?: "cron" | "manual" | string
}

interface LoopStatus {
  loop: "online" | "degraded" | "offline"
  service?: string
  running?: boolean
  paused?: boolean
  last_run?: LoopRun | null
  next_run?: string | null
  next_run_epoch_ms?: number | null
  interval_sec?: number
  total_runs?: number
  scp_online?: boolean
  scp_base_url?: string
  scp_audit_url?: string
  log_path?: string
  auth_configured?: boolean
  bridge_online?: boolean
  bridge_url?: string
  recent_runs?: LoopRun[]
  error?: string
  hint?: string
}

interface ScpRoute {
  method: string
  path: string
  desc: string
  group: string
  authRequired: boolean
  wired: boolean
}

interface ScpStatus {
  scp: "online" | "degraded" | "offline"
  engine: {
    version: string
    modelId?: string
    release?: string
    auditRound?: number
    expertTerm?: string
    legacyProtocols?: readonly string[]
    totalAutofixPyFiles: number
    modulesByGeneration: { v2_count: number; v3_count: number; v4_count: number }
    modulesWired: { v3: number; v4: number }
    modulesStandalone: { v3: number; v4: number }
    v4Loc: number
    // [4-c-006] Live-computed LOC indicators. v4LocLive=true means the number
    // was computed from actual scp/autofix/*.py files at module load; false
    // means it fell back to the documented last-verified constant.
    v4LocLive?: boolean
    v4LocLastVerifiedDate?: string
    v4LocMethod?: string
  }
  audit: {
    auditRound?: number
    historicalEvidenceRound?: number
    evidenceLabel?: string
    pythonFilesAstParseOk: string
    r9BugsFound: number
    r9BugsPatched: number
    saR9Findings: number
    r8ClaimsVerifiedTrue: number
    r8ClaimsVerifiedFalse: number
    crossValidation: string
  }
}

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
  POST: "bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-500/30",
  PUT: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
  DELETE: "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30",
  PATCH: "bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-300 border-fuchsia-500/30",
}

/**
 * LoopSchedulerCard — R10 Task 14.A.
 *
 * Self-contained card showing live status of the loop-scheduler mini-service
 * (port 3030). Calls /api/scp/loop (Next.js proxy → 127.0.0.1:3030) on every
 * refresh. The "Trigger now" button POSTs /api/scp/loop/trigger which fires
 * a manual SCP audit cycle and returns the run result.
 *
 * Fail-open: if the scheduler is offline, the card shows a red "offline"
 * badge + a hint to start it. Does NOT crash the rest of the control panel.
 */
function LoopSchedulerCard({
  loop,
  triggering,
  onTrigger,
}: {
  loop: LoopStatus | null
  triggering: boolean
  onTrigger: () => void
}) {
  const online = loop?.loop === "online"
  const degraded = loop?.loop === "degraded"
  const state = online ? "online" : degraded ? "degraded" : "offline"
  const color = online
    ? "border-emerald-500/30 bg-emerald-500/5"
    : degraded
      ? "border-amber-500/40 bg-amber-500/5"
      : "border-rose-500/40 bg-rose-500/5"

  const lastRun = loop?.last_run
  const lastRunTs = lastRun?.ts ? new Date(lastRun.ts) : null
  const nextRunTs = loop?.next_run ? new Date(loop.next_run) : null

  // [Fix 4-c-010 · Task Local-C] Hydration mismatch fix.
  // BEFORE: `const now = Date.now()` was called during render. SSR
  // pre-render computes `now` at request time, client hydration computes
  // `now` at hydration time — the values differ by N ms, causing
  // `nextInSec` to differ between server and client → React hydration
  // warning → React discards server HTML + re-renders (FCP/LCP regression).
  // AFTER: `now` is `null` initially (server + first client paint match),
  // then a `useEffect` starts a 1s interval updating `now` on the client
  // only. `nextInSec` is `null` until the client effect runs — operator
  // sees "—" instead of "in Ns" for the first 16ms, which is fine. DNA #9
  // (no harm) + #22 (PASS ≠ TRUE — the hydration mismatch is a silent
  // failure under disabled ESLint rules).
  const [now, setNow] = React.useState<number | null>(null)
  React.useEffect(() => {
    setNow(Date.now())
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  const nextInSec =
    nextRunTs && now !== null
      ? Math.max(0, Math.round((nextRunTs.getTime() - now) / 1000))
      : null

  const runStatusColor =
    lastRun?.status === "ok"
      ? "text-emerald-700 dark:text-emerald-300"
      : lastRun?.status === "scp_offline" || lastRun?.status === "auth_required"
        ? "text-amber-700 dark:text-amber-300"
        : lastRun?.status
          ? "text-rose-700 dark:text-rose-300"
          : "text-muted-foreground"

  return (
    <Card className={`mt-6 p-5 ${color}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Repeat className={`h-4 w-4 ${online ? "text-emerald-600 dark:text-emerald-400" : degraded ? "text-amber-600 dark:text-amber-400" : "text-rose-600 dark:text-rose-400"}`} />
          <span className="text-sm font-medium">Loop Scheduler</span>
          <Badge
            variant="outline"
            className={`ml-1 ${color}`}
            title={loop?.hint ?? "mini-services/loop-scheduler on port 3030"}
          >
            {state.toUpperCase()}
          </Badge>
          {online && loop?.paused && (
            <Badge variant="outline" className="border-amber-500/40 text-amber-700 dark:text-amber-300">
              PAUSED
            </Badge>
          )}
          {online && !loop?.paused && (
            <Badge variant="outline" className="border-sky-500/40 text-sky-700 dark:text-sky-300">
              every {loop?.interval_sec ?? 300}s
            </Badge>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void onTrigger()}
          disabled={!online || triggering}
          className="shrink-0"
          title={!online ? (loop?.hint ?? "Scheduler offline — start with: cd mini-services/loop-scheduler && bun run dev") : "Trigger an SCP audit cycle now"}
        >
          {triggering ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          Trigger now
        </Button>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <div className="rounded-md border border-border/60 bg-background/40 p-3">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Total runs</div>
          <div className="mt-1 text-xl font-bold font-mono">
            {loop?.total_runs ?? 0}
          </div>
        </div>
        <div className="rounded-md border border-border/60 bg-background/40 p-3">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Last run</div>
          <div className="mt-1 text-sm font-mono" suppressHydrationWarning>
            {lastRunTs ? lastRunTs.toLocaleTimeString() : "—"}
          </div>
          <div className={`mt-0.5 text-[11px] font-medium ${runStatusColor}`}>
            {lastRun?.status ?? "no runs yet"}
            {lastRun?.duration_ms ? ` · ${Math.round(lastRun.duration_ms / 100) / 10}s` : ""}
          </div>
        </div>
        <div className="rounded-md border border-border/60 bg-background/40 p-3">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Next run</div>
          <div className="mt-1 text-sm font-mono" suppressHydrationWarning>
            {online && !loop?.paused && nextRunTs ? nextRunTs.toLocaleTimeString() : "—"}
          </div>
          <div className="mt-0.5 text-[11px] text-muted-foreground">
            {online && !loop?.paused && nextInSec !== null
              ? `in ${nextInSec}s`
              : online && loop?.paused
                ? "paused"
                : "scheduler offline"}
          </div>
        </div>
        <div className="rounded-md border border-border/60 bg-background/40 p-3">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Last findings</div>
          <div className="mt-1 text-sm font-mono">
            {lastRun?.findings_count !== undefined ? (
              <>
                <span className="text-amber-700 dark:text-amber-300">{lastRun.findings_count}</span>
                {" found · "}
                <span className="text-emerald-700 dark:text-emerald-300">{lastRun.fixes_applied ?? 0}</span>
                {" fixed"}
              </>
            ) : (
              "—"
            )}
          </div>
          {lastRun?.permission_requested !== undefined && lastRun.permission_requested > 0 && (
            <div className="mt-0.5 text-[11px] text-fuchsia-700 dark:text-fuchsia-300">
              {lastRun.permission_requested} awaiting approval
            </div>
          )}
        </div>
      </div>

      {/* SCP liveness + auth indicator (from scheduler's view) */}
      {online && (
        <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1">
            SCP:
            <span className={loop?.scp_online ? "text-emerald-700 dark:text-emerald-300" : "text-rose-700 dark:text-rose-300"}>
              {loop?.scp_online ? "online" : "offline"}
            </span>
          </span>
          <span className="flex items-center gap-1">
            LLM Bridge:
            <span className={loop?.bridge_online ? "text-emerald-700 dark:text-emerald-300" : "text-rose-700 dark:text-rose-300"}>
              {loop?.bridge_online ? "online" : "offline"}
            </span>
          </span>
          <span className="flex items-center gap-1">
            Auth:
            <span className={loop?.auth_configured ? "text-emerald-700 dark:text-emerald-300" : "text-amber-700 dark:text-amber-300"}>
              {loop?.auth_configured ? "configured" : "not configured (run-audit will 503)"}
            </span>
          </span>
          {loop?.scp_audit_url && (
            <span className="flex items-center gap-1">
              Endpoint:
              <code className="rounded bg-muted px-1 py-0.5 text-[10px]">
                POST {loop.scp_audit_url.replace(/^https?:\/\/[^/]+/, "")}
              </code>
            </span>
          )}
          {loop?.log_path && (
            <span className="flex items-center gap-1">
              Log:
              <code className="rounded bg-muted px-1 py-0.5 text-[10px]">
                {loop.log_path.replace(/^.*\/scp\//, "scp/")}
              </code>
            </span>
          )}
        </div>
      )}

      {/* Recent runs (compact list) */}
      {online && loop?.recent_runs && loop.recent_runs.length > 0 && (
        <details className="mt-3 text-xs">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            Recent runs ({loop.recent_runs.length})
          </summary>
          <ul className="mt-2 space-y-1">
            {loop.recent_runs.slice(0, 5).map((r, i) => (
              <li key={`${r.ts}-${i}`} className="flex items-center gap-2 font-mono text-[11px]">
                <span className="text-muted-foreground" suppressHydrationWarning>
                  {new Date(r.ts).toLocaleTimeString()}
                </span>
                <span className={
                  r.status === "ok" ? "text-emerald-700 dark:text-emerald-300"
                  : r.status === "scp_offline" || r.status === "auth_required"
                    ? "text-amber-700 dark:text-amber-300"
                    : "text-rose-700 dark:text-rose-300"
                }>
                  {r.status}
                </span>
                {r.findings_count !== undefined && (
                  <span className="text-muted-foreground">
                    {r.findings_count} found · {r.fixes_applied ?? 0} fixed
                  </span>
                )}
                {r.triggered_by === "manual" && (
                  <span className="rounded bg-sky-500/15 px-1 text-[10px] text-sky-700 dark:text-sky-300">
                    manual
                  </span>
                )}
                {r.error && (
                  <span className="truncate text-rose-600 dark:text-rose-400">
                    {r.error.slice(0, 80)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* Offline / degraded hint */}
      {!online && (loop?.hint || loop?.error) && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 p-2 text-xs">
          <Terminal className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
          <code className="break-all">{loop.hint ?? loop.error}</code>
        </div>
      )}
    </Card>
  )
}

export function ScpControlPanel() {
  const [health, setHealth] = React.useState<ScpHealth | null>(null)
  const [status, setStatus] = React.useState<ScpStatus | null>(null)
  const [routes, setRoutes] = React.useState<ScpRoute[]>([])
  const [routeCount, setRouteCount] = React.useState(0)
  const [loop, setLoop] = React.useState<LoopStatus | null>(null)
  const [loopTriggering, setLoopTriggering] = React.useState(false)
  const [loading, setLoading] = React.useState(false)
  const [showAllRoutes, setShowAllRoutes] = React.useState(false)
  const [filter, setFilter] = React.useState<string>("all")

  const refresh = React.useCallback(async () => {
    setLoading(true)
    try {
      const [h, s, r, l] = await Promise.all([
        fetch("/api/scp/health", { cache: "no-store" }).then((x) => x.json() as Promise<ScpHealth>).catch(() => null),
        fetch("/api/scp/status", { cache: "no-store" }).then((x) => x.json() as Promise<ScpStatus>).catch(() => null),
        fetch("/api/scp/routes", { cache: "no-store" }).then((x) => x.json()).catch(() => null),
        fetch("/api/scp/loop", { cache: "no-store" }).then((x) => x.json() as Promise<LoopStatus>).catch(() => null),
      ])
      if (h) setHealth(h)
      if (s) setStatus(s)
      if (r && Array.isArray((r as { routes?: ScpRoute[] }).routes)) {
        setRoutes((r as { routes: ScpRoute[] }).routes)
        setRouteCount((r as { total: number }).total ?? (r as { routes: ScpRoute[] }).routes.length)
      }
      if (l) setLoop(l)
    } finally {
      setLoading(false)
    }
  }, [])

  const triggerLoop = React.useCallback(async () => {
    setLoopTriggering(true)
    try {
      const res = await fetch("/api/scp/loop/trigger", { method: "POST" })
      const data = (await res.json()) as LoopStatus & { triggered?: boolean; run?: LoopRun }
      // Refresh full status next tick so last_run + total_runs update
      void refresh()
      return data
    } catch (e) {
      // Surface the error on the loop card via a synthetic status update
      setLoop((prev) => ({
        ...prev,
        loop: "offline",
        error: e instanceof Error ? e.message.slice(0, 200) : String(e).slice(0, 200),
      } as LoopStatus))
      return null
    } finally {
      setLoopTriggering(false)
    }
  }, [refresh])

  // Initial fetch + auto-refresh every 30s
  React.useEffect(() => {
    void refresh()
    const id = setInterval(() => void refresh(), 30_000)
    return () => clearInterval(id)
  }, [refresh])

  const scpState = health?.scp ?? "offline"
  const scpColor =
    scpState === "online"
      ? "border-emerald-500/40 bg-emerald-500/5"
      : scpState === "degraded"
        ? "border-amber-500/40 bg-amber-500/5"
        : "border-rose-500/40 bg-rose-500/5"

  const scpIcon =
    scpState === "online" ? (
      <Server className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
    ) : (
      <ServerOff className="h-4 w-4 text-rose-600 dark:text-rose-400" />
    )

  const filteredRoutes = React.useMemo(() => {
    if (filter === "all") return routes
    if (filter === "public") return routes.filter((r) => !r.authRequired)
    if (filter === "auth") return routes.filter((r) => r.authRequired)
    if (filter === "live") return routes.filter((r) => r.wired)
    if (filter === "dead") return routes.filter((r) => !r.wired)
    return routes.filter((r) => r.group === filter)
  }, [routes, filter])

  const visibleRoutes = showAllRoutes ? filteredRoutes : filteredRoutes.slice(0, 12)

  const groupOptions = React.useMemo(() => {
    const set = new Set(routes.map((r) => r.group))
    return ["all", "public", "auth", "live", "dead", ...Array.from(set).sort()]
  }, [routes])

  return (
    <section
      id="scp-control-panel"
      className="scroll-mt-20 border-b border-border/40 py-14"
    >
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
              SCP Control Panel
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Live status của SCP Python FastAPI server (port 8000). Dashboard
              gọi <code className="rounded bg-muted px-1.5 py-0.5 text-xs">/api/scp/health</code>{" "}
              → proxy tới <code className="rounded bg-muted px-1.5 py-0.5 text-xs">http://127.0.0.1:8000/health</code>.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void refresh()}
            disabled={loading}
            className="shrink-0"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {/* Status row */}
        <div className="grid gap-4 md:grid-cols-3">
          {/* SCP liveness */}
          <Card className={`p-5 ${scpColor}`}>
            <div className="flex items-center gap-2">
              {scpIcon}
              <span className="text-sm font-medium">SCP Server</span>
              <Badge
                variant="outline"
                className={`ml-auto ${scpColor}`}
              >
                {scpState.toUpperCase()}
              </Badge>
            </div>
            <div className="mt-3 text-2xl font-bold">
              {scpState === "online" ? "Running" : scpState === "degraded" ? "Degraded" : "Not running"}
            </div>
            <div className="mt-1 text-xs text-muted-foreground" suppressHydrationWarning>
              {health?.checkedAt
                ? `Checked: ${new Date(health.checkedAt).toLocaleTimeString()}`
                : "Never checked"}
            </div>
            {scpState !== "online" && health?.hint && (
              <div className="mt-3 flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 p-2 text-xs">
                <Terminal className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
                <code className="break-all">{health.hint}</code>
              </div>
            )}
            {health?.error && (
              <div className="mt-2 truncate text-xs text-rose-600 dark:text-rose-400">
                {health.error}
              </div>
            )}
          </Card>

          {/* Engine metadata */}
          <Card className="p-5 border-fuchsia-500/30 bg-fuchsia-500/5">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-fuchsia-600 dark:text-fuchsia-400" />
              <span className="text-sm font-medium">Autofix Engine</span>
              <Badge variant="outline" className="ml-auto border-fuchsia-500/40 text-fuchsia-700 dark:text-fuchsia-300">
                {status?.engine.version ?? "v4"}
              </Badge>
            </div>
            <div className="mt-3 text-2xl font-bold">
              {status?.engine.totalAutofixPyFiles ?? 63} .py
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {/* [4-c-006] v4 LOC is now live-computed from actual scp/autofix/*.py.
                  Was hardcoded 4,389 — drifted +505 from actual 4,894. UI fallback
                  below is the documented last-verified value (matches LAST_VERIFIED_FALLBACK_LOC
                  in route.ts); when API loads, the live number is shown along with
                  a freshness indicator. */}
              51 v2 + 6 v3 + 6 v4 (
              <span title={status?.engine.v4LocMethod ?? "loading…"}>
                {status?.engine.v4Loc ?? 4894} v4 LOC
                {status?.engine.v4LocLive === false && (
                  <span className="ml-1 text-amber-600 dark:text-amber-400" title={status?.engine.v4LocMethod}>
                    (stale)
                  </span>
                )}
                {status?.engine.v4LocLive === true && (
                  <span className="ml-1 text-emerald-600 dark:text-emerald-400" title="computed from scp/autofix/*.py at module load">
                    (live)
                  </span>
                )}
              </span>
              )
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-2">
                <div className="font-mono text-emerald-700 dark:text-emerald-300">
                  v3 wired: {status?.engine.modulesWired.v3 ?? 6}/6
                </div>
              </div>
              <div className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2">
                <div className="font-mono text-amber-700 dark:text-amber-300">
                  v4 wired: {status?.engine.modulesWired.v4 ?? 0}/6
                </div>
              </div>
            </div>
          </Card>

          {/* Historical R9 audit evidence */}
          <Card className="p-5 border-sky-500/30 bg-sky-500/5">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-sky-600 dark:text-sky-400" />
              <span className="text-sm font-medium">Historical R9 evidence</span>
              <Badge variant="outline" className="ml-auto border-sky-500/40 text-sky-700 dark:text-sky-300">
                Audit Round {status?.audit.auditRound ?? CURRENT_ROUND}
              </Badge>
            </div>
            <div className="mt-3 text-2xl font-bold">
              {status?.audit.r9BugsPatched ?? 7}/{status?.audit.r9BugsFound ?? 7} patched
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              Historical R9: {status?.audit.pythonFilesAstParseOk ?? "377/377"} .py ast.parse OK
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              <span className="font-mono">{status?.audit.r8ClaimsVerifiedTrue ?? 19}</span> TRUE
              <span className="mx-1">·</span>
              <span className="font-mono">{status?.audit.r8ClaimsVerifiedFalse ?? 6}</span> FALSE
            </div>
          </Card>
        </div>

        {/* Loop Scheduler card — R10 Task 14.A */}
        <LoopSchedulerCard
          loop={loop}
          triggering={loopTriggering}
          onTrigger={triggerLoop}
        />

        {/* Route listing */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>SCP API Routes ({routeCount} total)</span>
              <div className="flex items-center gap-2">
                <select
                  value={filter}
                  onChange={(e) => {
                    setFilter(e.target.value)
                    setShowAllRoutes(false)
                  }}
                  className="rounded-md border border-input bg-background px-2 py-1 text-xs"
                  aria-label="Filter routes"
                >
                  {groupOptions.map((g) => (
                    <option key={g} value={g}>
                      {g === "all"
                        ? "All routes"
                        : g === "public"
                          ? "Public only"
                          : g === "auth"
                            ? "Auth required"
                            : g === "live"
                              ? "✅ Live only (wired)"
                              : g === "dead"
                                ? "⚠️ Dead code (not wired)"
                                : g}
                    </option>
                  ))}
                </select>
              </div>
            </CardTitle>
            <CardDescription>
              All 73 SCP routes (defined in <code>scp/api_server.py</code> +
              <code>scp/api/routes/*.py</code>). Access through gateway: append
              <code className="ml-1 rounded bg-muted px-1.5 py-0.5">?XTransformPort=8000</code>
              to any path.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-border/60 text-[10px] uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-2 py-1.5">Method</th>
                    <th className="px-2 py-1.5">Path</th>
                    <th className="px-2 py-1.5">Description</th>
                    <th className="px-2 py-1.5">Group</th>
                    <th className="px-2 py-1.5">Auth</th>
                    <th className="px-2 py-1.5">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRoutes.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-2 py-6 text-center text-muted-foreground">
                        {routes.length === 0 ? "Loading routes…" : "No routes match this filter."}
                      </td>
                    </tr>
                  ) : (
                    visibleRoutes.map((r) => (
                      <tr
                        key={`${r.method}-${r.path}`}
                        className="border-b border-border/30 hover:bg-muted/30"
                      >
                        <td className="px-2 py-1.5">
                          <span
                            className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-bold ${
                              METHOD_COLORS[r.method] ?? "bg-muted text-muted-foreground"
                            }`}
                          >
                            {r.method}
                          </span>
                        </td>
                        <td className="px-2 py-1.5 font-mono text-[11px]">
                          {r.path}
                        </td>
                        <td className="px-2 py-1.5 text-muted-foreground">
                          {r.desc}
                        </td>
                        <td className="px-2 py-1.5">
                          <Badge variant="secondary" className="text-[10px]">
                            {r.group}
                          </Badge>
                        </td>
                        <td className="px-2 py-1.5">
                          {r.authRequired ? (
                            <Badge variant="outline" className="border-amber-500/40 text-amber-700 dark:text-amber-300 text-[10px]">
                              required
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="border-emerald-500/40 text-emerald-700 dark:text-emerald-300 text-[10px]">
                              public
                            </Badge>
                          )}
                        </td>
                        <td className="px-2 py-1.5">
                          {r.wired ? (
                            <Badge variant="outline" className="border-emerald-500/40 text-emerald-700 dark:text-emerald-300 text-[10px]">
                              live
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="border-rose-500/40 text-rose-700 dark:text-rose-300 text-[10px]" title="Router not registered in api_server.py — code exists but route is unreachable">
                              dead
                            </Badge>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {filteredRoutes.length > 12 && (
              <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
                <span>
                  Showing {visibleRoutes.length} of {filteredRoutes.length} routes
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAllRoutes((v) => !v)}
                >
                  {showAllRoutes ? "Show less" : `Show all ${filteredRoutes.length}`}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Cross-validation callout (DNA #5) */}
        {status?.audit?.crossValidation && (
          <div className="mt-4 rounded-lg border border-fuchsia-500/30 bg-fuchsia-500/5 p-4 text-xs">
            <div className="mb-1 font-medium text-fuchsia-700 dark:text-fuchsia-300">
              DNA #5 Cross-validation
            </div>
            <p className="text-muted-foreground">{status.audit.crossValidation}</p>
          </div>
        )}
      </div>
    </section>
  )
}
