import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ROUND7_FINDINGS } from "@/lib/audit-data/round7"
import { AlertTriangle, AlertCircle, Info, FileWarning, CheckCircle2, Clock } from "lucide-react"

const severityConfig = {
  CRITICAL: {
    tone: "border-rose-500/40 bg-rose-500/5",
    badge: "border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400",
    icon: AlertTriangle,
  },
  HIGH: {
    tone: "border-amber-500/40 bg-amber-500/5",
    badge: "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400",
    icon: AlertCircle,
  },
  MEDIUM: {
    tone: "border-yellow-500/30 bg-yellow-500/5",
    badge: "border-yellow-500/40 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400",
    icon: FileWarning,
  },
  LOW: {
    tone: "border-sky-500/30 bg-sky-500/5",
    badge: "border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400",
    icon: Info,
  },
} as const

export function Round7Findings() {
  return (
    <section id="audit" className="scroll-mt-20 border-b border-border/40 py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Section 03
          </p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
            Round 7 Findings · 14 bugs
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Fresh audit — KHÔNG tin R3-R6 reports. Mỗi bug có root cause, nguồn phát
            hiện, before/after code, và Reality test.{" "}
            <strong className="text-amber-600 dark:text-amber-400">
              9/14 bugs là R5/R6 fix KHÔNG HOÀN CHỈNH
            </strong>{" "}
            (DNA #22: PASS ≠ TRUE).
          </p>
        </div>

        <div className="space-y-4">
          {ROUND7_FINDINGS.map((f) => {
            const cfg = severityConfig[f.severity]
            const Icon = cfg.icon
            return (
              <Card key={f.id} className={`overflow-hidden ${cfg.tone}`}>
                <div className="flex flex-col gap-4 p-5 sm:p-6">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-background/60">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="outline" className={`gap-1 text-[10px] ${cfg.badge}`}>
                            <Icon className="h-3 w-3" />
                            {f.severity}
                          </Badge>
                          <Badge variant="secondary" className="font-mono text-[10px]">
                            {f.id}
                          </Badge>
                          {f.isR5R6Incomplete && (
                            <Badge
                              variant="outline"
                              className="gap-1 border-amber-500/40 bg-amber-500/10 text-[10px] text-amber-600 dark:text-amber-400"
                            >
                              <AlertTriangle className="h-3 w-3" />
                              R5/R6 INCOMPLETE
                            </Badge>
                          )}
                          {f.fixStatus === "fixed" && (
                            <Badge
                              variant="outline"
                              className="gap-1 border-emerald-500/40 bg-emerald-500/10 text-[10px] text-emerald-600 dark:text-emerald-400"
                            >
                              <CheckCircle2 className="h-3 w-3" />
                              FIXED
                            </Badge>
                          )}
                          {f.fixStatus === "needs-human" && (
                            <Badge
                              variant="outline"
                              className="gap-1 border-fuchsia-500/40 bg-fuchsia-500/10 text-[10px] text-fuchsia-600 dark:text-fuchsia-400"
                            >
                              <Clock className="h-3 w-3" />
                              NEEDS HUMAN
                            </Badge>
                          )}
                        </div>
                        <h3 className="text-base font-bold leading-snug">{f.title}</h3>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-3">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          File
                        </p>
                        <p className="mt-0.5 font-mono text-xs text-foreground">
                          {f.file}
                          <span className="text-muted-foreground">:{f.line}</span>
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Root cause
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {f.rootCause}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Tại sao R3-R6 bỏ sót
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {f.whyPreviousRoundsMissed}
                        </p>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Nguồn phát hiện
                        </p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {f.sources.map((s) => (
                            <Badge key={s} variant="secondary" className="text-[10px] font-mono">
                              {s}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Fix
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">{f.fix}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Reality test
                        </p>
                        <p className="mt-0.5 font-mono text-[11px] text-emerald-600 dark:text-emerald-400">
                          {f.realityTest}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      </div>
    </section>
  )
}
