import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AUTOFIX_IMPROVEMENTS, IMPROVEMENT_STATS } from "@/lib/audit-data/autofix-improvements"
import { Lightbulb, TrendingUp, CheckCircle2, Clock, Circle } from "lucide-react"

const statusConfig = {
  implemented: {
    icon: CheckCircle2,
    tone: "border-emerald-500/40 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400",
    badge: "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  },
  "in-progress": {
    icon: Clock,
    tone: "border-amber-500/40 bg-amber-500/5 text-amber-600 dark:text-amber-400",
    badge: "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400",
  },
  planned: {
    icon: Circle,
    tone: "border-muted-foreground/20 bg-muted/30 text-muted-foreground",
    badge: "border-muted-foreground/20 bg-muted/30 text-muted-foreground",
  },
} as const

export function AutofixImprovements() {
  return (
    <section id="improvements" className="scroll-mt-20 border-b border-border/40 py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Section 06 · THE UPDATE
          </p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
            12 cải tiến autofix — mạnh + chính xác + nhanh hơn
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            &ldquo;cập nhật autofix để autofix mạnh + chính xác hơn + fix lỗi chính xác
            và nhanh hơn, giống autofix của hệ thống tốt nhất khác của thế giới.&rdquo;
            Học từ Sentry Autofix, GitHub Copilot Autofix, Semgrep, Cursor Bugbot.
          </p>

          <div className="mt-4 rounded-lg border border-emerald-500/40 bg-emerald-500/5 p-3 text-xs">
            <p className="font-semibold text-emerald-700 dark:text-emerald-300">
              R7-Full update · 12/12 implemented as REAL Python code
            </p>
            <p className="mt-1 text-muted-foreground">
              R7 shipped 9 implemented + 1 in-progress + 2 planned. R7-Full closes all 3 gaps —
              IMP-9 (DryRunManager), IMP-11 (concurrent_runner.py), IMP-12 (diff_rescan.py) now
              land in <code className="rounded bg-muted/60 px-1 py-0.5 font-mono text-[10px]">scp/autofix/</code>.
              Verified by <code className="rounded bg-muted/60 px-1 py-0.5 font-mono text-[10px]">ast.parse</code> on all 51 files.
            </p>
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <Badge variant="outline" className="gap-1.5 border-emerald-500/40 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-3.5 w-3.5" />
              {IMPROVEMENT_STATS.implemented} implemented
            </Badge>
            <Badge variant="outline" className="gap-1.5 border-amber-500/40 bg-amber-500/5 text-amber-600 dark:text-amber-400">
              <Clock className="h-3.5 w-3.5" />
              {IMPROVEMENT_STATS.inProgress} in-progress
            </Badge>
            <Badge variant="outline" className="gap-1.5">
              <Circle className="h-3.5 w-3.5" />
              {IMPROVEMENT_STATS.planned} planned
            </Badge>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          {AUTOFIX_IMPROVEMENTS.map((imp) => {
            const cfg = statusConfig[imp.status]
            const StatusIcon = cfg.icon
            return (
              <Card key={imp.id} className={`flex flex-col gap-4 p-5 ${cfg.tone}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-background/60">
                      <Lightbulb className="h-5 w-5" />
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="font-mono text-[10px]">
                          {imp.id}
                        </Badge>
                        <Badge variant="outline" className={`gap-1 text-[10px] ${cfg.badge}`}>
                          <StatusIcon className="h-3 w-3" />
                          {imp.status}
                        </Badge>
                      </div>
                      <h3 className="text-sm font-bold leading-snug">{imp.name}</h3>
                    </div>
                  </div>
                </div>

                <div className="space-y-2.5 text-xs">
                  <div>
                    <span className="font-semibold text-fuchsia-600 dark:text-fuchsia-400">
                      Inspired by:{" "}
                    </span>
                    <span className="text-muted-foreground">{imp.inspiration}</span>
                  </div>
                  <div>
                    <span className="font-semibold">DNA: </span>
                    <div className="mt-0.5 flex flex-wrap gap-1">
                      {imp.dnaPrinciple.map((d) => (
                        <Badge key={d} variant="secondary" className="text-[9px] font-mono">
                          #{d}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <p className="text-muted-foreground">{imp.problem}</p>
                </div>

                <div className="grid gap-2 border-t border-border/40 pt-3 text-[11px] sm:grid-cols-2">
                  <div className="rounded-md border border-rose-500/20 bg-rose-500/5 p-2">
                    <p className="mb-0.5 font-semibold text-rose-600 dark:text-rose-400">
                      Before R6
                    </p>
                    <p className="text-muted-foreground">{imp.beforeR6}</p>
                  </div>
                  <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-2">
                    <p className="mb-0.5 font-semibold text-emerald-600 dark:text-emerald-400">
                      After R7
                    </p>
                    <p className="text-muted-foreground">{imp.afterR7}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 rounded-md bg-muted/40 p-2.5 text-[11px]">
                  <TrendingUp className="h-3.5 w-3.5 shrink-0 text-teal-500" />
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">{imp.metric.label}</p>
                    <p className="text-muted-foreground">
                      <span className="text-rose-500 line-through">{imp.metric.before}</span>
                      {" → "}
                      <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                        {imp.metric.after}
                      </span>
                    </p>
                  </div>
                </div>

                <div className="text-[10px] text-muted-foreground">
                  <span className="font-mono">📄 {imp.file}</span>
                </div>

                {imp.v2Note ? (
                  <div className="rounded-md border border-sky-500/30 bg-sky-500/5 p-2 text-[11px]">
                    <span className="font-semibold text-sky-600 dark:text-sky-400">
                      R7-Full:{" "}
                    </span>
                    <span className="text-muted-foreground">{imp.v2Note}</span>
                  </div>
                ) : null}
              </Card>
            )
          })}
        </div>
      </div>
    </section>
  )
}
