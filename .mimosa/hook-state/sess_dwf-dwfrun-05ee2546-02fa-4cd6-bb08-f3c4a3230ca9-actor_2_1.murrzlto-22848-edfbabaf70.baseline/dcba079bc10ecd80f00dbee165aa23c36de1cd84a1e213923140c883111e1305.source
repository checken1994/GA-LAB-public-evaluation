import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { WORLD_TOOLS } from "@/lib/audit-data/autofix-v3"
import { V4_WORLD_TOOLS as V4_TOOLS } from "@/lib/audit-data/autofix-v4"
import { Globe, ArrowRight, Building2, Sparkles, Layers } from "lucide-react"

export function WorldToolsComparison() {
  const totalTools = WORLD_TOOLS.length + V4_TOOLS.length

  return (
    <section
      id="world-tools"
      className="scroll-mt-20 border-b border-border/40 bg-gradient-to-b from-sky-500/[0.04] to-transparent py-14"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        {/* Header */}
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Section 24 · World&apos;s best · UPDATED for v4
          </p>
          <h2 className="mt-1 flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
            <Globe className="h-7 w-7 text-sky-500" />
            Học từ hệ thống tốt nhất thế giới (v3 + v4)
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            &ldquo;dùng autofix của SCP + công cụ tốt nhất thế giới + DNA của SCP.&rdquo;
            Mỗi improvement của SCP (v2 + v3 + v4) được inspire bởi một hệ thống
            autofix world-class. v3 học từ{" "}
            <strong className="text-sky-600 dark:text-sky-400">{WORLD_TOOLS.length} hệ thống</strong>;
            v4 thêm{" "}
            <strong className="text-emerald-600 dark:text-emerald-400">{V4_TOOLS.length} more</strong>{" "}
            (15 total). Bảng dưới map mỗi hệ thống → cải tiến SCP nào adopt pattern đó.
          </p>
        </div>

        {/* Stats strip */}
        <div className="mb-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card className="border-sky-500/30 bg-sky-500/5 p-4">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-sky-500" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                v3 systems learned from
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums text-sky-600 dark:text-sky-400">
              {WORLD_TOOLS.length}
            </p>
          </Card>
          <Card className="border-emerald-500/30 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-emerald-500" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                v4 NEW systems (R9)
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
              {V4_TOOLS.length}
            </p>
          </Card>
          <Card className="border-border/60 p-4">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-muted-foreground" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Total systems synthesized
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums">{totalTools}</p>
          </Card>
          <Card className="border-fuchsia-500/30 bg-fuchsia-500/5 p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              SCP DNA synthesis
            </p>
            <p className="mt-2 text-xs font-medium text-foreground">
              Reality &gt; Model · Audit the auditor · Fail loudly
            </p>
          </Card>
        </div>

        {/* v3 tools section */}
        <div className="mb-10">
          <div className="mb-4 flex items-center gap-2">
            <Badge variant="outline" className="gap-1 border-sky-500/40 bg-sky-500/10 text-[11px] text-sky-600 dark:text-sky-400">
              v3 · 7 systems
            </Badge>
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              v3 — R8 baseline (IMP-1..18)
            </h3>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {WORLD_TOOLS.map((tool) => (
              <Card key={`v3-${tool.name}`} className="flex flex-col gap-3 border-border/60 p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400">
                      <Building2 className="h-5 w-5" />
                    </div>
                    <div className="space-y-0.5">
                      <h4 className="text-base font-bold leading-snug">{tool.name}</h4>
                      <p className="text-[11px] font-medium text-muted-foreground">
                        {tool.vendor}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Specialty
                  </p>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {tool.specialty}
                  </p>
                </div>

                <div className="space-y-1.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    SCP adoption
                  </p>
                  <p className="text-xs leading-relaxed text-foreground">{tool.scpAdoption}</p>
                </div>

                <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-2">
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  {tool.relatedImp.map((imp) => (
                    <Badge
                      key={imp}
                      variant="outline"
                      className="gap-1 font-mono text-[10px] border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400"
                    >
                      {imp}
                    </Badge>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* v4 NEW tools section */}
        <div className="mb-10">
          <div className="mb-4 flex items-center gap-2">
            <Badge variant="outline" className="gap-1 border-emerald-500/40 bg-emerald-500/10 text-[11px] text-emerald-600 dark:text-emerald-400">
              v4 · 8 NEW systems (R9)
            </Badge>
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              v4 — R9 NEW additions (IMP-19..24)
            </h3>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {V4_TOOLS.map((tool) => (
              <Card key={`v4-${tool.name}`} className="flex flex-col gap-3 border-emerald-500/30 bg-emerald-500/[0.02] p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                      <Sparkles className="h-5 w-5" />
                    </div>
                    <div className="space-y-0.5">
                      <h4 className="text-base font-bold leading-snug">{tool.name}</h4>
                      <p className="text-[11px] font-medium text-muted-foreground">
                        {tool.vendor}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline" className="gap-1 border-emerald-500/40 bg-emerald-500/10 text-[10px] text-emerald-600 dark:text-emerald-400">
                    NEW
                  </Badge>
                </div>

                <div className="space-y-1.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Specialty
                  </p>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {tool.specialty}
                  </p>
                </div>

                <div className="space-y-1.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    SCP adoption (v4)
                  </p>
                  <p className="text-xs leading-relaxed text-foreground">{tool.scpAdoption}</p>
                </div>

                <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-2">
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  {tool.relatedImp.map((imp) => (
                    <Badge
                      key={imp}
                      variant="outline"
                      className="gap-1 font-mono text-[10px] border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                    >
                      {imp}
                    </Badge>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Closing note */}
        <div className="mt-10 rounded-lg border border-sky-500/30 bg-sky-500/[0.04] p-5">
          <p className="text-xs leading-relaxed text-muted-foreground">
            <strong className="text-sky-600 dark:text-sky-400">
              DNA #24 (đứa trẻ 20 năm sau):
            </strong>{" "}
            Khi một kỹ sư 20 năm sau hỏi &ldquo;tại sao SCP tự fix được mà các công cụ
            thế giới không?&rdquo; — câu trả lời là: SCP không_thể_fix_được thứ công cụ
            thế giới không bắt được, nhưng SCP adopt pattern của tất cả chúng (15 hệ
            thống: 7 từ v3 + 8 từ v4) + thêm DNA của chính nó (Reality &gt; Model,
            audit the auditor, fail loudly). SCP là hợp nhất (synthesis), không phải
            thay thế (replacement). Công cụ thế giới giỏi một thứ; SCP giỏi học từ tất
            cả + tự nghi ngờ chính mình (DNA #22). v4 đặc biệt adopt pattern Constitutional
            AI (Anthropic) + AWS SCP + OPA/Rego → IMP-24 Policy Gate là &ldquo;bản hiến
            pháp&rdquo; hardcoded không thể bị bỏ qua bởi confidence score (DNA #4 + #22).
          </p>
        </div>
      </div>
    </section>
  )
}
