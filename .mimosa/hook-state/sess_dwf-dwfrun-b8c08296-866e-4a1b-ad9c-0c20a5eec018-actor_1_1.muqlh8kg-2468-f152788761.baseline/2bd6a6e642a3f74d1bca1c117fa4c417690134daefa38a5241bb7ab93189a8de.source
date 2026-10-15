import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Search, GitBranch, FlaskConical, ShieldCheck, ArrowLeftRight } from "lucide-react"

const steps = [
  {
    n: "01",
    title: "Không tin R3-R6 reports",
    description:
      "DNA #22: PASS ≠ TRUE. R7 bắt đầu bằng cách giả định R3-R6 đều có thể incomplete. Chạy lại từ đầu, không đọc kết luận R6 trước.",
    icon: Search,
    dna: [22],
  },
  {
    n: "02",
    title: "Cùng 6 nguồn lineage + nguồn thứ 7 mới",
    description:
      "ruff, pyflakes, pylint, vulture, mypy, bandit (same versions R6). + hypothesis property-based testing (NEW R7 — câu hỏi R3-R6 không đặt).",
    icon: GitBranch,
    dna: [5, 14, 24],
  },
  {
    n: "03",
    title: "Cross-file vulture verification",
    description:
      "Chạy vulture trên WHOLE scp/ directory (không per-file). Xác nhận dead methods thực sự dead — không chỉ per-file dead.",
    icon: ArrowLeftRight,
    dna: [19, 20],
  },
  {
    n: "04",
    title: "R-fix-completeness check",
    description:
      "Round N+1 STARTS by re-running all Round N fixes through post_fix_verify + reality_test. Any fix that fails → re-opened as Round N+1 bug with is_rN_incomplete=true.",
    icon: ShieldCheck,
    dna: [22, 23, 9],
  },
  {
    n: "05",
    title: "Hypothesis property-based testing",
    description:
      "Generate 1000 random inputs (None, edge-case floats, empty). Reproduce TypeError mà static analysis miss. Catches R7-1 None-comparison, R7-3 race condition, R7-4 cold-start.",
    icon: FlaskConical,
    dna: [24, 25, 5],
  },
]

export function Round7Methodology() {
  return (
    <section id="methodology" className="scroll-mt-20 border-b border-border/40 py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Methodology
          </p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
            Phương pháp Round 7 — 5 bước
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            5 khác biệt chiều sâu so với R6. Mỗi bước áp dụng ≥1 DNA principle.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {steps.map((s) => {
            const Icon = s.icon
            return (
              <Card key={s.n} className="flex flex-col gap-3 p-5">
                <div className="flex items-start justify-between">
                  <span className="font-mono text-3xl font-bold text-foreground/[0.08]">
                    {s.n}
                  </span>
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                    <Icon className="h-5 w-5 text-muted-foreground" />
                  </div>
                </div>
                <h3 className="text-sm font-bold leading-snug">{s.title}</h3>
                <p className="text-xs text-muted-foreground">{s.description}</p>
                <div className="mt-auto flex flex-wrap gap-1 border-t border-border/40 pt-2">
                  {s.dna.map((d) => (
                    <Badge key={d} variant="secondary" className="text-[9px] font-mono">
                      DNA #{d}
                    </Badge>
                  ))}
                </div>
              </Card>
            )
          })}
        </div>
      </div>
    </section>
  )
}
