import { Card } from "@/components/ui/card"
import { BugDiffShowcase } from "@/components/autofix/fix-diff-viewer"
import { AUTOFIX_TIERS, AUTOFIX_CONFIG } from "@/lib/audit-data/autofix-engine"
import { PipelineFlow } from "@/components/autofix/pipeline-flow"
import { TierSystem } from "@/components/autofix/tier-system"
import { Badge } from "@/components/ui/badge"
import { Settings2, Terminal, GitBranch, RefreshCw } from "lucide-react"

export function AutofixSection() {
  return (
    <section id="autofix" className="scroll-mt-20 border-b border-border/40 py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Section 05 · THE UPDATE
          </p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
            Autofix Engine · mạnh + chính xác + nhanh hơn
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Engine file:{" "}
            <span className="font-mono text-xs">scp/autofix/engine.py (1341 LOC)</span>.
            R7 thêm 2 phase mới (post-fix verify + reality test), 12 improvements,
            học từ Sentry/Copilot/Semgrep/Cursor.
          </p>
        </div>

        <div className="space-y-6">
          <PipelineFlow />
          <TierSystem />

          <Card className="p-6">
            <div className="mb-4 flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-muted-foreground" />
              <h3 className="text-lg font-bold tracking-tight">
                Engine Config · 9 settings
              </h3>
            </div>
            <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
              {AUTOFIX_CONFIG.map((c) => (
                <div
                  key={c.key}
                  className="rounded-md border border-border/40 bg-muted/20 p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <code className="text-[11px] font-semibold">{c.key}</code>
                    <Badge
                      variant="outline"
                      className={`text-[9px] ${
                        c.key.includes("R7")
                          ? "border-teal-500/40 bg-teal-500/10 text-teal-600 dark:text-teal-400"
                          : ""
                      }`}
                    >
                      {c.value}
                    </Badge>
                  </div>
                  <p className="mt-1.5 text-[11px] text-muted-foreground">
                    {c.description}
                  </p>
                  {c.key.includes("R7") && (
                    <p className="mt-1 text-[10px] font-semibold text-teal-600 dark:text-teal-400">
                      ✓ R7 NEW
                    </p>
                  )}
                </div>
              ))}
            </div>
          </Card>

          <Card className="overflow-hidden p-6">
            <div className="mb-4 flex items-center gap-2">
              <Terminal className="h-4 w-4 text-muted-foreground" />
              <h3 className="text-lg font-bold tracking-tight">
                Fix Diff Viewer · before/after code
              </h3>
            </div>
            <p className="mb-4 text-sm text-muted-foreground">
              Click vào bug ID để xem diff before/after + Reality test. DNA #11:
              human-in-the-loop thật — operator phải hiểu điều mình phê duyệt.
            </p>
            <BugDiffShowcase />
          </Card>

          <div className="grid gap-4 md:grid-cols-3">
            <Card className="p-5">
              <div className="mb-2 flex items-center gap-2">
                <RefreshCw className="h-4 w-4 text-emerald-500" />
                <p className="text-sm font-semibold">Self-healing</p>
              </div>
              <p className="text-xs text-muted-foreground">
                Post-fix verify + reality test → rollback nếu fix sai. Tự phục hồi
                khi LLM fix xấu.
              </p>
            </Card>
            <Card className="p-5">
              <div className="mb-2 flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-fuchsia-500" />
                <p className="text-sm font-semibold">Lineage-aware</p>
              </div>
              <p className="text-xs text-muted-foreground">
                Cross-lineage validation. Không tin 3 scanner cùng Python-AST —
                chỉ tin cross-lineage agreement (DNA #14).
              </p>
            </Card>
            <Card className="p-5">
              <div className="mb-2 flex items-center gap-2">
                <Settings2 className="h-4 w-4 text-amber-500" />
                <p className="text-sm font-semibold">Rollback token</p>
              </div>
              <p className="text-xs text-muted-foreground">
                Mỗi fix có UUID rollback token. Operator có thể revert单个 fix
                mà không mất fix khác (R7 NEW — DNA #8 + #9).
              </p>
            </Card>
          </div>
        </div>
      </div>
    </section>
  )
}
