import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AUDIT_SOURCES } from "@/lib/audit-data/sources"
import { CheckCircle2, Eye, EyeOff, Sparkles } from "lucide-react"

const categoryLabel: Record<string, string> = {
  syntax: "Cú pháp",
  semantic: "Ngữ nghĩa",
  type: "Hệ thống type",
  "dead-code": "Dead code",
  security: "Bảo mật",
  domain: "SCP domain",
  reality: "Reality log",
  property: "Property test",
}

const categoryTone: Record<string, string> = {
  syntax: "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20",
  semantic: "bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20",
  type: "bg-fuchsia-500/10 text-fuchsia-600 dark:text-fuchsia-400 border-fuchsia-500/20",
  "dead-code": "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
  security: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
  domain: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  reality: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20",
  property: "bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-500/20",
}

export function SourceComparison() {
  return (
    <section id="sources" className="scroll-mt-20 border-b border-border/40 py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Section 04
          </p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
            7 nguồn độc lập lineage
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            DNA #5 + #14: Không tin đa số đồng ý nếu cùng lineage. R7 dùng 7 nguồn
            (R6 dùng 6 — R7 thêm <strong className="text-teal-600 dark:text-teal-400">hypothesis property-based testing</strong>),
            mỗi nguồn có blind-spot được map rõ (DNA #19).
          </p>
        </div>

        <Card className="overflow-hidden">
          <div className="overflow-x-auto scroll-thin">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/60 bg-muted/40 text-left">
                  <th className="px-4 py-3 font-semibold">Nguồn</th>
                  <th className="px-4 py-3 font-semibold">Lineage</th>
                  <th className="hidden px-4 py-3 font-semibold md:table-cell">
                    Blind-spot
                  </th>
                  <th className="px-4 py-3 text-center font-semibold">R6</th>
                  <th className="px-4 py-3 text-center font-semibold">R7</th>
                  <th className="px-4 py-3 text-center font-semibold">Mới</th>
                </tr>
              </thead>
              <tbody>
                {AUDIT_SOURCES.map((s) => (
                  <tr
                    key={s.id}
                    className="border-b border-border/30 transition-colors last:border-0 hover:bg-muted/30"
                  >
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-semibold">{s.name}</span>
                          <span className="text-[10px] text-muted-foreground">
                            v{s.version}
                          </span>
                        </div>
                        <Badge
                          variant="outline"
                          className={`w-fit border text-[10px] ${categoryTone[s.category]}`}
                        >
                          {categoryLabel[s.category]}
                        </Badge>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {s.lineage}
                    </td>
                    <td className="hidden max-w-xs px-4 py-3 text-xs text-muted-foreground md:table-cell">
                      <div className="flex items-start gap-1.5">
                        <EyeOff className="mt-0.5 h-3 w-3 shrink-0 text-rose-500" />
                        <span>{s.blindSpot}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center font-mono tabular-nums">
                      {s.r6Findings}
                    </td>
                    <td className="px-4 py-3 text-center font-mono font-bold tabular-nums">
                      {s.r7Findings}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {s.isNewInR7 ? (
                        <Badge
                          variant="outline"
                          className="gap-1 border-teal-500/40 bg-teal-500/10 text-[10px] text-teal-600 dark:text-teal-400"
                        >
                          <Sparkles className="h-3 w-3" />
                          NEW
                        </Badge>
                      ) : (
                        <CheckCircle2 className="mx-auto h-4 w-4 text-muted-foreground/30" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <Card className="p-5">
            <div className="mb-2 flex items-center gap-2">
              <Eye className="h-4 w-4 text-emerald-500" />
              <p className="text-sm font-semibold">Khả năng quan sát</p>
            </div>
            <p className="text-xs text-muted-foreground">
              Mỗi nguồn có cửa sổ quan sát khác nhau. R7 map blind-spot của từng nguồn
              để biết cái gì KHÔNG bị nhìn thấy (DNA #19).
            </p>
          </Card>
          <Card className="p-5">
            <div className="mb-2 flex items-center gap-2">
              <EyeOff className="h-4 w-4 text-rose-500" />
              <p className="text-sm font-semibold">Ảo giác đồng thuận</p>
            </div>
            <p className="text-xs text-muted-foreground">
              ruff + pyflakes + pylint cùng dùng Python AST → không độc lập thật.
              R7 chỉ tin cross-lineage agreement (DNA #14).
            </p>
          </Card>
          <Card className="p-5">
            <div className="mb-2 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-teal-500" />
              <p className="text-sm font-semibold">Nguồn thứ 7 (R7 NEW)</p>
            </div>
            <p className="text-xs text-muted-foreground">
              hypothesis property-based testing — câu hỏi R3-R6 không đặt. Generate
              1000 random inputs, reproduce TypeError (DNA #24: đứa trẻ hỏi Tại sao).
            </p>
          </Card>
        </div>
      </div>
    </section>
  )
}
