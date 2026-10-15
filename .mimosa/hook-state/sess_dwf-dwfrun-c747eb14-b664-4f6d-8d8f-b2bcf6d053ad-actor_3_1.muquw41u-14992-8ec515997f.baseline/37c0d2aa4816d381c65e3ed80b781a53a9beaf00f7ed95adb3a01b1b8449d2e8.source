import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { SCP_SCANNERS } from "@/lib/audit-data/scanners"
import { Sparkles, Eye, EyeOff } from "lucide-react"

const typeTone: Record<string, string> = {
  "scp-own": "border-emerald-500/30 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400",
  external: "border-sky-500/30 bg-sky-500/5 text-sky-600 dark:text-sky-400",
}

export function ScannerGrid() {
  const scpScanners = SCP_SCANNERS.filter((s) => s.type === "scp-own")
  const externalScanners = SCP_SCANNERS.filter((s) => s.type === "external")

  return (
    <section id="scanners" className="scroll-mt-20 border-b border-border/40 py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Section 07
          </p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
            25 scanners · 18 SCP own + 7 external
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            DNA #19: map blind-spot của từng scanner. DNA #21: audit chính SCP scanner.
            R7 cải thiện 5 scanner (null-safety, dead-code, resource-leak, sql-injection,
            + thêm hypothesis mới).
          </p>
        </div>

        <div className="mb-6">
          <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-muted-foreground">
            SCP&apos;s own scanners (18)
          </h3>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {scpScanners.map((s) => (
              <Card
                key={s.id}
                className={`flex flex-col gap-3 p-4 ${
                  false ? "border-teal-500/40 bg-teal-500/[0.03]" : ""
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-mono text-sm font-bold">{s.name}</h4>
                    <p className="text-[10px] text-muted-foreground">
                      {s.loc} LOC · {s.category}
                    </p>
                  </div>
                  {false && (
                    <Badge
                      variant="outline"
                      className="gap-1 border-teal-500/40 bg-teal-500/10 text-[9px] text-teal-600 dark:text-teal-400"
                    >
                      <Sparkles className="h-2.5 w-2.5" />
                      R7
                    </Badge>
                  )}
                </div>
                <div className="space-y-2 text-[11px]">
                  <div className="flex items-start gap-1.5">
                    <Eye className="mt-0.5 h-3 w-3 shrink-0 text-emerald-500" />
                    <span className="text-muted-foreground">{s.catchesWhat}</span>
                  </div>
                  <div className="flex items-start gap-1.5">
                    <EyeOff className="mt-0.5 h-3 w-3 shrink-0 text-rose-500" />
                    <span className="text-muted-foreground">{s.blindSpot}</span>
                  </div>
                </div>
                {false && s.improvement && (
                  <div className="rounded-md border border-teal-500/20 bg-teal-500/5 p-2 text-[10px]">
                    <p className="font-semibold text-teal-600 dark:text-teal-400">
                      R7 improvement:
                    </p>
                    <p className="mt-0.5 text-muted-foreground">{s.improvement}</p>
                  </div>
                )}
                <div className="mt-auto flex items-center justify-between border-t border-border/40 pt-2 text-[10px]">
                  <span className="text-muted-foreground">
                    R6: <span className="font-mono">{s.r6Findings}</span>
                  </span>
                  <span className="text-muted-foreground">
                    R7:{" "}
                    <span className="font-mono font-bold text-foreground">
                      {s.r7Findings}
                    </span>
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-muted-foreground">
            External tools (7)
          </h3>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            {externalScanners.map((s) => (
              <Card key={s.id} className={`p-4 ${typeTone[s.type]}`}>
                <div className="mb-2 flex items-start justify-between">
                  <div>
                    <h4 className="font-mono text-sm font-bold">{s.name}</h4>
                    <p className="text-[10px] opacity-70">v{"—"}</p>
                  </div>
                  {false && (
                    <Badge
                      variant="outline"
                      className="gap-1 border-teal-500/40 bg-teal-500/10 text-[9px] text-teal-600 dark:text-teal-400"
                    >
                      <Sparkles className="h-2.5 w-2.5" />
                      NEW
                    </Badge>
                  )}
                </div>
                <p className="text-[11px] text-muted-foreground">{s.catchesWhat}</p>
                <div className="mt-2 border-t border-border/40 pt-2 text-[10px]">
                  <p className="text-muted-foreground">
                    <EyeOff className="mr-1 inline h-2.5 w-2.5 text-rose-500" />
                    {s.blindSpot}
                  </p>
                </div>
                <div className="mt-2 flex items-center justify-between text-[10px]">
                  <span className="text-muted-foreground">
                    R6: <span className="font-mono">{s.r6Findings}</span>
                  </span>
                  <span className="font-mono font-bold">{s.r7Findings}</span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}


