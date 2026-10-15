import { AlertTriangle, Zap } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { CURRENT_ROUND } from "@/lib/audit-data/version"

export function Hero() {
  return (
    <section id="dashboard" className="relative overflow-hidden border-b border-border/40">
      <div className="absolute inset-0 grid-bg" aria-hidden />
      <div className="relative mx-auto max-w-5xl px-4 py-16 sm:px-6 sm:py-24">
        <div className="flex flex-col items-start gap-6">
          <Badge
            variant="outline"
            className="gap-2 border-rose-500/40 bg-rose-500/5 text-rose-700 dark:text-rose-400"
          >
            <Zap className="h-3.5 w-3.5" />
            DNA #22 · PASS ≠ TRUE (recursive, level 4)
          </Badge>

          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            SCP DNA Audit{" "}
            <span className="relative inline-block">
              <span className="relative z-10 bg-gradient-to-br from-rose-500 via-fuchsia-500 to-emerald-500 bg-clip-text text-transparent">
                {/* [Fix 4-c-008 · Task Local-C] Round number reads from
                    CURRENT_ROUND (single source of truth in version.ts).
                    Previously hardcoded "Round 9" — disagreed with header
                    badge "9", header subtitle "Round 8", and the metadata
                    title "Round 9". */}
                Round {CURRENT_ROUND}
              </span>
              <span className="absolute -bottom-1 left-0 right-0 h-3 bg-rose-500/20 blur-md" />
            </span>
          </h1>

          <p className="max-w-2xl text-base text-muted-foreground sm:text-lg">
            <span className="font-semibold text-foreground">Không tin các báo cáo.</span>{" "}
            Dùng autofix của SCP + công cụ tốt nhất thế giới + DNA của SCP để tìm lỗi
            từ gốc + fix lỗi từ gốc. R9 không tin R8 — audit lại chính R8 (Round 10
            Self-Audit), tìm{" "}
            <strong className="text-rose-600 dark:text-rose-400">7 bug gốc mới R8 bỏ sót</strong>,
            nâng cấp autofix{" "}
            <strong className="text-emerald-600 dark:text-emerald-400">v3 → v4</strong> (4,894 LOC — live count at /api/scp/status).
          </p>

          <div className="flex flex-wrap items-center gap-3 text-sm">
            <div className="flex items-center gap-2 rounded-full border border-rose-500/30 bg-rose-500/5 px-4 py-2">
              <AlertTriangle className="h-4 w-4 text-rose-500" />
              <span className="font-medium">
                R9-7: R8-1&apos;s fix INTRODUCED a regression (SA-R9-2 HIGH)
              </span>
            </div>
            <div className="flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/5 px-4 py-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              <span className="font-medium">7 NEW root-cause bugs R8 MISSED</span>
            </div>
            <div className="flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/5 px-4 py-2">
              <AlertTriangle className="h-4 w-4 text-emerald-500" />
              <span className="font-medium">Autofix v4 — 6 NEW improvements (4,894 LOC, live at /api/scp/status)</span>
            </div>
          </div>

          <blockquote className="mt-4 max-w-2xl border-l-2 border-rose-500 pl-4 text-sm italic text-muted-foreground">
            &ldquo;R7 audited SCP → 14 bugs. R7-Full audited R7 → 8 discrepancies.
            R8 audited R7-Full → 10 discrepancies + 7 NEW bugs. R9 audited R8 →
            6 discrepancies + 7 NEW bugs + autofix v4. The process never terminates —
            that is the feature.&rdquo;
            <footer className="mt-1 text-xs not-italic">
              — DNA SCP #21 + #22 + #23 · the auditor&apos;s paradox (recursive, level 4)
            </footer>
          </blockquote>

          <div className="flex flex-wrap gap-3 pt-2">
            <a
              href="#round9-audit"
              className="inline-flex h-10 items-center justify-center rounded-md bg-foreground px-6 text-sm font-medium text-background transition-transform hover:scale-[1.02]"
            >
              Xem R9 findings (7 bugs) →
            </a>
            <a
              href="#v4-improvements"
              className="inline-flex h-10 items-center justify-center rounded-md border border-border bg-background px-6 text-sm font-medium transition-colors hover:bg-accent"
            >
              Autofix v4 UPDATE
            </a>
            <a
              href="#round10-self-audit"
              className="inline-flex h-10 items-center justify-center rounded-md border border-border bg-background px-6 text-sm font-medium transition-colors hover:bg-accent"
            >
              Round 10 Self-Audit
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
