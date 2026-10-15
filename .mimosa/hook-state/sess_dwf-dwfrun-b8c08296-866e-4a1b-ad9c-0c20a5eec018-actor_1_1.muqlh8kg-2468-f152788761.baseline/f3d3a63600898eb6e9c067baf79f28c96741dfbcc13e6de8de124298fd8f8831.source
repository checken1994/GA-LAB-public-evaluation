"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CRITICAL_BUGS } from "@/lib/audit-data/bugs-critical"
import type { BugDetail } from "@/lib/audit-data/bugs-critical"
import { BugDiffViewer } from "@/components/autofix/fix-diff-viewer"
import { AlertTriangle, Bug } from "lucide-react"
// [Fix 4-c-015 · Task Local-C] Section number is now looked up from the
// sidebar's SECTIONS array (single source of truth) — was hardcoded "08",
// but the sidebar lists #bugs-critical as n="18".
import { getSectionNumber } from "@/lib/audit-data/sections"

interface BugCategorySectionProps {
  id: string
  sectionNumber: string
  title: string
  description: string
  bugs: BugDetail[]
  tone?: "critical" | "warning" | "info"
}

const toneCfg = {
  critical: { border: "border-rose-500/30", icon: "text-rose-500", badge: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30" },
  warning: { border: "border-amber-500/30", icon: "text-amber-500", badge: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30" },
  info: { border: "border-sky-500/30", icon: "text-sky-500", badge: "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/30" },
}

export function BugCategorySection({
  id,
  sectionNumber,
  title,
  description,
  bugs,
  tone = "warning",
}: BugCategorySectionProps) {
  const cfg = toneCfg[tone]
  return (
    <section id={id} className={`scroll-mt-20 border-b border-border/40 py-14 ${cfg.border}`}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Section {sectionNumber}
          </p>
          <div className="mt-1 flex items-start gap-3">
            <Bug className={`mt-1 h-6 w-6 ${cfg.icon}`} />
            <div>
              <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">{title}</h2>
              <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{description}</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge variant="outline" className={`gap-1 ${cfg.badge}`}>
              <AlertTriangle className="h-3 w-3" />
              {bugs.length} bugs
            </Badge>
            <Badge variant="outline" className="gap-1 border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400">
              {bugs.filter((b) => b.isR5R6Incomplete).length} R5/R6-incomplete
            </Badge>
          </div>
        </div>

        <div className="space-y-4">
          {bugs.map((bug) => (
            <Card key={bug.id} className="overflow-hidden">
              <div className="p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary" className="font-mono text-[10px]">
                    {bug.id}
                  </Badge>
                  <Badge
                    variant="outline"
                    className={`text-[10px] ${
                      bug.severity === "CRITICAL"
                        ? "border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400"
                        : bug.severity === "HIGH"
                          ? "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          : bug.severity === "MEDIUM"
                            ? "border-yellow-500/40 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400"
                            : "border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400"
                    }`}
                  >
                    {bug.severity}
                  </Badge>
                  <Badge variant="outline" className="text-[10px]">
                    Tier {bug.tier}
                  </Badge>
                  {bug.isR5R6Incomplete && (
                    <Badge
                      variant="outline"
                      className="gap-1 border-amber-500/40 bg-amber-500/10 text-[10px] text-amber-600 dark:text-amber-400"
                    >
                      <AlertTriangle className="h-3 w-3" />
                      R5/R6 INCOMPLETE
                    </Badge>
                  )}
                </div>
                <h3 className="mt-2 text-base font-bold leading-snug">{bug.title}</h3>
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  {bug.file}:{bug.line}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">{bug.rootCause}</p>
              </div>
              <div className="border-t border-border/40 bg-muted/20 p-4">
                <BugDiffViewer bug={bug} />
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

export function CriticalBugsSection() {
  return (
    <BugCategorySection
      id="bugs-critical"
      sectionNumber={getSectionNumber("bugs-critical")}
      title="CRITICAL — Silent security/feature bypass"
      description="Bugs mà try/except nuốt exception → feature chết âm thầm. Operator không thấy traceback → tưởng hệ thống OK (DNA #22: PASS ≠ TRUE). 4 CRITICAL bugs, tất cả đều R5/R6 fix KHÔNG HOÀN CHỈNH."
      bugs={CRITICAL_BUGS}
      tone="critical"
    />
  )
}
