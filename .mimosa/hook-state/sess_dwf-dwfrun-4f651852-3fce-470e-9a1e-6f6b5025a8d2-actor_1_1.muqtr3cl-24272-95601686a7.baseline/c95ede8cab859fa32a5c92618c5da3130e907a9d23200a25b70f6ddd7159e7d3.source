"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { CRITICAL_BUGS } from "@/lib/audit-data/bugs-critical"
import { DEAD_CONTROL_BUGS } from "@/lib/audit-data/bugs-dead-controls"
import { TYPE_ERROR_BUGS } from "@/lib/audit-data/bugs-type-errors"
import { RESOURCE_LEAK_BUGS } from "@/lib/audit-data/bugs-resource-leaks"
import { RACE_CONDITION_BUGS } from "@/lib/audit-data/bugs-race"
import { SQL_INJECTION_BUGS } from "@/lib/audit-data/bugs-sql"
import type { BugDetail } from "@/lib/audit-data/bugs-critical"
import { ChevronDown, ChevronUp, GitCompare } from "lucide-react"

interface BugDiffViewerProps {
  bug?: BugDetail
}

export function BugDiffViewer({ bug }: BugDiffViewerProps) {
  const [open, setOpen] = useState(false)

  if (!bug) return null

  const beforeLines = bug.beforeCode.split("\n")
  const afterLines = bug.afterCode.split("\n")

  return (
    <Card className="overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/40"
      >
        <div className="flex items-center gap-2">
          <GitCompare className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Before / After diff</span>
          <Badge variant="secondary" className="text-[10px] font-mono">
            {bug.id}
          </Badge>
        </div>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {open && (
        <div className="grid gap-px border-t border-border/40 bg-border/40 md:grid-cols-2">
          <div className="bg-background">
            <div className="flex items-center justify-between border-b border-border/40 px-4 py-2">
              <span className="flex items-center gap-1.5 text-xs font-semibold text-rose-600 dark:text-rose-400">
                <span className="h-2 w-2 rounded-full bg-rose-500" />
                Before (BUG)
              </span>
              <span className="font-mono text-[10px] text-muted-foreground">
                {bug.file}:{bug.line}
              </span>
            </div>
            <pre className="max-h-80 overflow-y-auto bg-rose-500/[0.02] p-3 scroll-thin">
              <code className="text-[11px] leading-relaxed">
                {beforeLines.map((line, i) => (
                  <div key={i} className="diff-line diff-line-del">
                    <span className="mr-3 select-none text-rose-500/50">-</span>
                    {line}
                  </div>
                ))}
              </code>
            </pre>
          </div>
          <div className="bg-background">
            <div className="flex items-center justify-between border-b border-border/40 px-4 py-2">
              <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                After (FIXED)
              </span>
              <span className="font-mono text-[10px] text-emerald-600 dark:text-emerald-400">
                Tier-{bug.tier}
              </span>
            </div>
            <pre className="max-h-80 overflow-y-auto bg-emerald-500/[0.02] p-3 scroll-thin">
              <code className="text-[11px] leading-relaxed">
                {afterLines.map((line, i) => (
                  <div key={i} className="diff-line diff-line-add">
                    <span className="mr-3 select-none text-emerald-500/50">+</span>
                    {line}
                  </div>
                ))}
              </code>
            </pre>
          </div>
        </div>
      )}

      {open && (
        <div className="border-t border-border/40 p-4">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Reality test
          </p>
          <ul className="space-y-1">
            {bug.realityTest.map((t) => (
              <li
                key={t}
                className="flex items-start gap-2 font-mono text-[11px] text-emerald-600 dark:text-emerald-400"
              >
                <span className="mt-0.5">✓</span>
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  )
}

// Demo viewer that cycles through categories
export function BugDiffShowcase() {
  const allBugs: BugDetail[] = [
    ...CRITICAL_BUGS.slice(0, 2),
    ...DEAD_CONTROL_BUGS.slice(0, 1),
    ...TYPE_ERROR_BUGS.slice(2, 4),
    ...SQL_INJECTION_BUGS.slice(0, 1),
    ...RACE_CONDITION_BUGS.slice(0, 1),
    ...RESOURCE_LEAK_BUGS.slice(0, 1),
  ]

  const [idx, setIdx] = useState(0)
  const bug = allBugs[idx]

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {allBugs.map((b, i) => (
          <Button
            key={b.id}
            size="sm"
            variant={i === idx ? "default" : "outline"}
            className="h-7 px-2.5 text-[10px] font-mono"
            onClick={() => setIdx(i)}
          >
            {b.id}
          </Button>
        ))}
      </div>
      <BugDiffViewer bug={bug} />
    </div>
  )
}
