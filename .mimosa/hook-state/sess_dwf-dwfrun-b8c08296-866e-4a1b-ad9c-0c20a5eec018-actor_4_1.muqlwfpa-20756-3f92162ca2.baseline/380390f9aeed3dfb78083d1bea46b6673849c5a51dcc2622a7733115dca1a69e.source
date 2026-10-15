import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  R9_FINDINGS,
  R9_STATS,
  R9_METHODOLOGY,
  type R9Severity,
} from "@/lib/audit-data/round9"
import {
  AlertTriangle,
  AlertCircle,
  Info,
  FileWarning,
  CheckCircle2,
  Bug,
  Microscope,
  ListChecks,
  FileSearch,
  Terminal,
  FlaskConical,
  Wrench,
  Recycle,
} from "lucide-react"

const severityConfig: Record<
  R9Severity,
  { tone: string; badge: string; icon: typeof AlertTriangle; label: string }
> = {
  critical: {
    tone: "border-rose-500/40 bg-rose-500/5",
    badge: "border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400",
    icon: AlertTriangle,
    label: "CRITICAL",
  },
  high: {
    tone: "border-amber-500/40 bg-amber-500/5",
    badge: "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400",
    icon: AlertCircle,
    label: "HIGH",
  },
  medium: {
    tone: "border-yellow-500/30 bg-yellow-500/5",
    badge: "border-yellow-500/40 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400",
    icon: FileWarning,
    label: "MEDIUM",
  },
  low: {
    tone: "border-sky-500/30 bg-sky-500/5",
    badge: "border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400",
    icon: Info,
    label: "LOW",
  },
}

const methodologyIcons = [Microscope, ListChecks, FileSearch, FlaskConical, Wrench]

export function Round9Findings() {
  return (
    <section
      id="round9-audit"
      className="scroll-mt-20 border-b border-border/40 bg-gradient-to-b from-rose-500/[0.04] to-transparent py-14"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        {/* Header */}
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Section 21 · Round 9 · NEW
          </p>
          <h2 className="mt-1 flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
            <Bug className="h-7 w-7 text-rose-500" />
            Round 9 Findings · {R9_STATS.total} NEW root-cause bugs R8 MISSED
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            DNA #22 recursive (level 3): &ldquo;R8 found 7 bugs&rdquo; doesn&apos;t mean 7
            were the ONLY bugs. R9 ran strengthened scanners + world-tool patterns
            (ruff ASYNC100, semgrep async-blocking-call + race-condition,
            inter-procedural tracing for chat_sync → future.result) and found{" "}
            <strong className="text-rose-600 dark:text-rose-400">
              {R9_STATS.total} NEW bugs R8 MISSED
            </strong>{" "}
            — 1 CRITICAL (R9-1 blocking-in-async), 3 HIGH, 1 MEDIUM, 2 LOW.{" "}
            <span className="text-emerald-600 dark:text-emerald-400">
              All PATCHED in real Python (see FIXES_APPLIED_R9.md).{" "}
              {R9_STATS.astParseOk}/{R9_STATS.total} ast.parse OK.
            </span>
          </p>
        </div>

        {/* Stats strip */}
        <div className="mb-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card className="border-rose-500/30 bg-rose-500/5 p-4">
            <div className="flex items-center gap-2">
              <Bug className="h-4 w-4 text-rose-500" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                NEW bugs R8 missed
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums text-rose-600 dark:text-rose-400">
              {R9_STATS.total}
            </p>
          </Card>
          <Card className="border-emerald-500/30 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Patched in real .py
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
              {R9_STATS.fixed}/{R9_STATS.total}
            </p>
          </Card>
          <Card className="border-fuchsia-500/30 bg-fuchsia-500/5 p-4">
            <div className="flex items-center gap-2">
              <Recycle className="h-4 w-4 text-fuchsia-500" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                R8-1 regression (DNA #22)
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums text-fuchsia-600 dark:text-fuchsia-400">
              {R9_STATS.regressions.length}
            </p>
            <p className="text-[10px] text-muted-foreground">R9-7 · R8-1 fix introduced it</p>
          </Card>
          <Card className="border-border/60 p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Severity (C/H/M/L)
            </p>
            <p className="mt-2 text-sm font-bold tabular-nums">
              <span className="text-rose-600 dark:text-rose-400">
                {R9_STATS.bySeverity.critical}
              </span>
              {" / "}
              <span className="text-amber-600 dark:text-amber-400">
                {R9_STATS.bySeverity.high}
              </span>
              {" / "}
              <span className="text-yellow-600 dark:text-yellow-400">
                {R9_STATS.bySeverity.medium}
              </span>
              {" / "}
              <span className="text-sky-600 dark:text-sky-400">
                {R9_STATS.bySeverity.low}
              </span>
            </p>
          </Card>
        </div>

        {/* Methodology */}
        <Card className="mb-10 border-border/60 bg-background/40 p-5 sm:p-6">
          <div className="mb-4 flex items-center gap-2">
            <Microscope className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              How R9 found them — strengthened patterns + inter-procedural tracing
            </h3>
          </div>
          <ol className="space-y-3">
            {R9_METHODOLOGY.map((m, i) => {
              const Icon = methodologyIcons[i] ?? FileSearch
              return (
                <li key={m.step} className="flex gap-3">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-rose-500/10 text-rose-600 dark:text-rose-400">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-xs font-semibold text-foreground">{m.step}</p>
                    <p className="text-xs text-muted-foreground">{m.detail}</p>
                  </div>
                </li>
              )
            })}
          </ol>
        </Card>

        {/* Finding cards */}
        <div className="space-y-4">
          {R9_FINDINGS.map((f) => {
            const cfg = severityConfig[f.severity]
            const Icon = cfg.icon
            const isRegression = R9_STATS.regressions.includes(f.id)
            return (
              <Card key={f.id} className={`overflow-hidden ${cfg.tone}`}>
                <div className="flex flex-col gap-4 p-5 sm:p-6">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-background/60">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="secondary" className="gap-1 font-mono text-[10px]">
                            {f.id}
                          </Badge>
                          <Badge variant="outline" className={`gap-1 text-[10px] ${cfg.badge}`}>
                            <Icon className="h-3 w-3" />
                            {cfg.label}
                          </Badge>
                          <Badge
                            variant="outline"
                            className="gap-1 border-fuchsia-500/40 bg-fuchsia-500/10 text-[10px] text-fuchsia-600 dark:text-fuchsia-400"
                          >
                            {f.bugClass}
                          </Badge>
                          {f.fixStatus === "fixed" && (
                            <Badge
                              variant="outline"
                              className="gap-1 border-emerald-500/40 bg-emerald-500/10 text-[10px] text-emerald-600 dark:text-emerald-400"
                            >
                              <CheckCircle2 className="h-3 w-3" />
                              FIXED · ast.parse OK
                            </Badge>
                          )}
                          {isRegression && (
                            <Badge
                              variant="outline"
                              className="gap-1 border-rose-500/50 bg-rose-500/15 text-[10px] text-rose-700 dark:text-rose-300"
                            >
                              <Recycle className="h-3 w-3" />
                              REGRESSION · R8-1 introduced
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-3">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          File:line
                        </p>
                        <p className="mt-0.5 font-mono text-xs text-foreground">
                          {f.file}
                          <span className="text-muted-foreground">:{f.line}</span>
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Root cause (TẠI SAO — DNA #1)
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">{f.rootCause}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          World tool that catches this
                        </p>
                        <p className="mt-0.5 font-mono text-[11px] text-fuchsia-600 dark:text-fuchsia-400">
                          {f.worldTool}
                        </p>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Repro hypothesis (DNA #17)
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">{f.reproHypothesis}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Why R8 missed it
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">{f.whyR8Missed}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          DNA principles
                        </p>
                        <p className="mt-0.5 text-[11px] text-foreground">{f.dnaPrinciples}</p>
                      </div>
                    </div>
                  </div>

                  {/* Before / After code */}
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="space-y-1.5">
                      <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400">
                        <AlertCircle className="h-3 w-3" />
                        Before (buggy — R8 missed)
                      </p>
                      <pre className="max-h-72 overflow-auto rounded-md border border-rose-500/20 bg-rose-500/[0.04] p-3 text-[11px] leading-relaxed text-muted-foreground scroll-thin">
                        <code className="font-mono">{f.beforeCode}</code>
                      </pre>
                    </div>
                    <div className="space-y-1.5">
                      <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" />
                        After (R9 patch — real .py)
                      </p>
                      <pre className="max-h-72 overflow-auto rounded-md border border-emerald-500/20 bg-emerald-500/[0.04] p-3 text-[11px] leading-relaxed text-foreground scroll-thin">
                        <code className="font-mono">{f.afterCode}</code>
                      </pre>
                    </div>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Closing note */}
        <div className="mt-10 rounded-lg border border-rose-500/30 bg-rose-500/[0.04] p-5">
          <p className="text-xs leading-relaxed text-muted-foreground">
            <strong className="text-rose-600 dark:text-rose-400">
              DNA #22 applied recursively to R8 (the bug-finder itself):
            </strong>{" "}
            R8 found 7 bugs and patched them. R9 did NOT trust that 7 was
            exhaustive — it re-ran the scanners + world-tool patterns and found{" "}
            {R9_STATS.total} more. Notably, <strong>R9-7 is a regression INTRODUCED
            by R8-1&apos;s fix</strong> — R8-1 replaced a dead SQLite query with
            direct list iteration without a lock, recreating the same silent-failure
            pattern R8-1 was supposed to fix. This proves DNA #22 applies to R8
            itself: PASS ≠ TRUE, even for the auditor. Every R9 bug is patched in
            real Python with ast.parse verification. A Round 10 bug-finder would
            find bugs R9 missed — that is the feature, not the failure. (DNA #23 + #26.)
          </p>
        </div>
      </div>
    </section>
  )
}
