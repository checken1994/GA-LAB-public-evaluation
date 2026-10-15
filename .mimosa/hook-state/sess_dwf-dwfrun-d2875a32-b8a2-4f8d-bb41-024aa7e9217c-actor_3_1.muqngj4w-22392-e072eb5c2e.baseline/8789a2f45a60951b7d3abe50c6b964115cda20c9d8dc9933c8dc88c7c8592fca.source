import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AUTOFIX_PIPELINE } from "@/lib/audit-data/autofix-engine"
import { ArrowRight, Sparkles } from "lucide-react"

export function PipelineFlow() {
  return (
    <Card className="overflow-hidden p-6 sm:p-8">
      <div className="mb-6">
        <h3 className="text-lg font-bold tracking-tight">Autofix Pipeline · 7 phases</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Flow: detect → classify → permission → fix →{" "}
          <span className="font-semibold text-teal-600 dark:text-teal-400">
            post-fix verify (NEW R7)
          </span>{" "}
          → audit →{" "}
          <span className="font-semibold text-teal-600 dark:text-teal-400">
            reality test (NEW R7)
          </span>
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        {AUTOFIX_PIPELINE.map((phase, idx) => (
          <div key={phase.id} className="relative">
            <Card
              className={`h-full p-4 transition-colors ${
                phase.isNew
                  ? "border-teal-500/40 bg-teal-500/5"
                  : "border-border/60"
              }`}
            >
              <div className="mb-2 flex items-start justify-between gap-2">
                <span className="font-mono text-[10px] text-muted-foreground">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                {phase.isNew && (
                  <Badge
                    variant="outline"
                    className="gap-1 border-teal-500/40 bg-teal-500/10 text-[9px] text-teal-600 dark:text-teal-400"
                  >
                    <Sparkles className="h-2.5 w-2.5" />
                    R7 NEW
                  </Badge>
                )}
              </div>
              <h4 className="text-sm font-bold leading-tight">{phase.name}</h4>
              <p className="mt-1.5 text-xs text-muted-foreground">{phase.description}</p>
              <div className="mt-3 space-y-1 border-t border-border/40 pt-2 text-[10px]">
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground">⏱</span>
                  <span className="text-muted-foreground">{phase.duration}</span>
                </div>
                <div className="flex items-start gap-1.5">
                  <span className="text-muted-foreground">📄</span>
                  <span className="font-mono text-muted-foreground">{phase.file}</span>
                </div>
              </div>
            </Card>
            {idx < AUTOFIX_PIPELINE.length - 1 && (
              <ArrowRight className="absolute -right-2 top-1/2 hidden h-4 w-4 -translate-y-1/2 text-muted-foreground/40 lg:block" />
            )}
          </div>
        ))}
      </div>
    </Card>
  )
}
