import { AlertTriangle, ArrowRight } from "lucide-react"
import { Card } from "@/components/ui/card"

export function DnaBanner() {
  return (
    <Card className="glow-critical mx-auto my-12 max-w-4xl border-rose-500/40 bg-rose-500/5 p-6 sm:p-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-rose-500/15 text-rose-600 dark:text-rose-400">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <div className="space-y-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400">
              DNA SCP #22 · Goodhart&apos;s Law
            </p>
            <h3 className="mt-1 text-xl font-bold tracking-tight sm:text-2xl">
              PASS ≠ TRUE
            </h3>
          </div>
          <p className="text-sm text-muted-foreground sm:text-base">
            Round 5 PASS với 6 nguồn. Round 6 cũng PASS — nhưng phát hiện 9 bug SILENT
            mà Round 5 bỏ sót (2 bug R5 fix KHÔNG HOÀN CHỈNH). Round 7 quay lại,
            không tin PASS, đào sâu hơn — phát hiện thêm:{" "}
            <strong className="text-foreground">9/14 R7 findings đều là R5/R6-incomplete</strong>.
          </p>
          <blockquote className="border-l-2 border-rose-500/50 pl-3 text-sm italic">
            &ldquo;Một quy trình chống tự lừa dối cũng có thể bị dùng để tạo ra bằng
            chứng rằng chúng ta không tự lừa dối.&rdquo;
          </blockquote>
          <a
            href="#audit"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-rose-600 hover:gap-2.5 dark:text-rose-400"
          >
            Xem 14 findings Round 7
            <ArrowRight className="h-4 w-4 transition-all" />
          </a>
        </div>
      </div>
    </Card>
  )
}
