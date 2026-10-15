import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  AUTOFIX_V3_IMPROVEMENTS,
  V3_STATS,
  type V3Axis,
} from "@/lib/audit-data/autofix-v3"
import {
  Zap,
  Target,
  ShieldCheck,
  Gauge,
  FileCode2,
  CheckCircle2,
  Sparkles,
  Layers,
} from "lucide-react"

const axisConfig: Record<
  V3Axis,
  { tone: string; badge: string; icon: typeof Zap; label: string; color: string }
> = {
  accuracy: {
    tone: "border-fuchsia-500/40 bg-fuchsia-500/5",
    badge: "border-fuchsia-500/40 bg-fuchsia-500/10 text-fuchsia-600 dark:text-fuchsia-400",
    icon: Target,
    label: "ACCURACY",
    color: "text-fuchsia-600 dark:text-fuchsia-400",
  },
  speed: {
    tone: "border-amber-500/40 bg-amber-500/5",
    badge: "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400",
    icon: Gauge,
    label: "SPEED",
    color: "text-amber-600 dark:text-amber-400",
  },
  safety: {
    tone: "border-emerald-500/40 bg-emerald-500/5",
    badge: "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    icon: ShieldCheck,
    label: "SAFETY",
    color: "text-emerald-600 dark:text-emerald-400",
  },
}

export function V3Improvements() {
  return (
    <section
      id="v3-improvements"
      className="scroll-mt-20 border-b border-border/40 bg-gradient-to-b from-emerald-500/[0.03] to-transparent py-14"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        {/* Header */}
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Section 19 · Autofix v3
          </p>
          <h2 className="mt-1 flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
            <Sparkles className="h-7 w-7 text-emerald-500" />
            Autofix Engine v3 · {V3_STATS.total} NEW improvements
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            &ldquo;cập nhật autofix để autofix mạnh + chính xác + nhanh hơn, giống autofix
            của hệ thống tốt nhất khác của thế giới.&rdquo; R7-Full upgraded v1→v2 (IMP-1..12).
            R8 upgrades v2→v3 with{" "}
            <strong className="text-emerald-600 dark:text-emerald-400">
              {V3_STATS.total} more improvements (IMP-13..{12 + V3_STATS.total})
            </strong>{" "}
            — {V3_STATS.totalLoc.toLocaleString()} LOC of real Python, all fail-open,
            backward-compatible. 0 v2 files modified (light-touch integration).
          </p>
        </div>

        {/* Stats strip */}
        <div className="mb-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card className="border-emerald-500/30 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-emerald-500" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                v3 improvements
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
              {V3_STATS.total}
            </p>
          </Card>
          <Card className="border-border/60 p-4">
            <div className="flex items-center gap-2">
              <FileCode2 className="h-4 w-4 text-muted-foreground" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                LOC (real Python)
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums">
              {V3_STATS.totalLoc.toLocaleString()}
            </p>
          </Card>
          <Card className="border-border/60 p-4">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-muted-foreground" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Total autofix .py
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums">
              {V3_STATS.totalAutofixPyFiles}
            </p>
            <p className="text-[10px] text-muted-foreground">51 v2 + 6 v3 · all ast.parse OK</p>
          </Card>
          <Card className="border-fuchsia-500/30 bg-fuchsia-500/5 p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Axis (ACC / SPD / SAF)
            </p>
            <p className="mt-2 text-sm font-bold tabular-nums">
              <span className="text-fuchsia-600 dark:text-fuchsia-400">
                {V3_STATS.byAxis.accuracy}
              </span>
              {" / "}
              <span className="text-amber-600 dark:text-amber-400">
                {V3_STATS.byAxis.speed}
              </span>
              {" / "}
              <span className="text-emerald-600 dark:text-emerald-400">
                {V3_STATS.byAxis.safety}
              </span>
            </p>
          </Card>
        </div>

        {/* Improvement cards */}
        <div className="space-y-4">
          {AUTOFIX_V3_IMPROVEMENTS.map((imp) => {
            const cfg = axisConfig[imp.axis]
            const AxisIcon = cfg.icon
            return (
              <Card key={imp.id} className={`overflow-hidden ${cfg.tone}`}>
                <div className="flex flex-col gap-4 p-5 sm:p-6">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-background/60">
                        <AxisIcon className={`h-5 w-5 ${cfg.color}`} />
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="secondary" className="gap-1 font-mono text-[10px]">
                            {imp.id}
                          </Badge>
                          <Badge variant="outline" className={`gap-1 text-[10px] ${cfg.badge}`}>
                            <AxisIcon className="h-3 w-3" />
                            {cfg.label}
                          </Badge>
                          <Badge
                            variant="outline"
                            className="gap-1 border-emerald-500/40 bg-emerald-500/10 text-[10px] text-emerald-600 dark:text-emerald-400"
                          >
                            <CheckCircle2 className="h-3 w-3" />
                            ast.parse OK · smoke-tested
                          </Badge>
                          <Badge variant="secondary" className="text-[10px]">
                            {imp.loc} LOC
                          </Badge>
                        </div>
                        <h3 className="text-base font-bold leading-snug">{imp.name}</h3>
                        <p className="text-[11px] font-medium text-muted-foreground">
                          Inspired by: {imp.inspiration}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2 rounded-lg border border-rose-500/20 bg-rose-500/[0.04] p-3">
                      <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400">
                        Problem (v2 baseline)
                      </p>
                      <p className="text-xs leading-relaxed text-muted-foreground">
                        {imp.problem}
                      </p>
                    </div>
                    <div className="space-y-2 rounded-lg border border-emerald-500/20 bg-emerald-500/[0.04] p-3">
                      <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                        Solution (v3)
                      </p>
                      <p className="text-xs leading-relaxed text-foreground">{imp.solution}</p>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-1">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        File
                      </p>
                      <p className="font-mono text-[11px] text-foreground">{imp.file}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Fail-open strategy (DNA #7)
                      </p>
                      <p className="text-xs text-muted-foreground">{imp.failOpen}</p>
                    </div>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Integration note */}
        <div className="mt-10 rounded-lg border border-emerald-500/30 bg-emerald-500/[0.04] p-5">
          <p className="text-xs leading-relaxed text-muted-foreground">
            <strong className="text-emerald-600 dark:text-emerald-400">
              Light-touch integration (DNA #7 — fail-safe):
            </strong>{" "}
            All 6 v3 modules are standalone with documented integration points (see
            V3_MANIFEST.md). 0 v2 files modified — the v2 engine continues to work
            unchanged. Wiring v3 modules into engine.py / runner_phases/ast_scan.py is
            deferred to avoid destabilizing the v2 engine. Each v3 module degrades
            gracefully to v2 behavior if it can&apos;t load. Target: false-positive fix
            rate &lt;2% (vs R5/R6&apos;s 22%); scan time ~3-6s (vs v2&apos;s ~45s).
          </p>
        </div>
      </div>
    </section>
  )
}
