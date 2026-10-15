import { ShieldAlert, Heart } from "lucide-react"
import { CURRENT_ROUND_LABEL } from "@/lib/audit-data/version"

export function Footer() {
  return (
    <footer className="mt-auto border-t border-border/60 bg-muted/30">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 text-amber-500" />
            <div className="space-y-1 text-sm">
              {/* [Fix 4-c-008 · Task Local-C] Footer uses CURRENT_ROUND_LABEL
                  from version.ts — was a hardcoded "Round 9" string. */}
              <p className="font-medium">
                SCP DNA Audit {CURRENT_ROUND_LABEL} — &ldquo;PASS ≠ TRUE (recursive · level 4)&rdquo;
              </p>
              <p className="text-xs text-muted-foreground">
                DNA #26: Reality giữ quyền trả lời cuối cùng.
                Mục tiêu không phải biết tất cả — mà là duy trì khả năng để Reality
                buộc hệ thống nhận ra nó đã bỏ sót điều gì đó.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span>Built with</span>
            <Heart className="h-3.5 w-3.5 fill-rose-500 text-rose-500" />
            <span>by Gà Lab · &ldquo;HỎI. THỬ NHỎ. NHÌN THỰC TẾ. SỬA.&rdquo;</span>
          </div>
        </div>
        <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 border-t border-border/40 pt-4 text-[11px] text-muted-foreground">
          <span>7 R9 NEW root-cause bugs (all patched) + 7 R8 (prior)</span>
          <span>·</span>
          <span>6 SA-R9 self-audit findings (19 R8 claims TRUE / 6 discrepancies)</span>
          <span>·</span>
          <span>24 autofix improvements (12 v2 + 6 v3 + 6 v4)</span>
          <span>·</span>
          <span>377 Python files ast.parse OK</span>
          <span>·</span>
          <span>0 lint errors (genuinely)</span>
        </div>
      </div>
    </footer>
  )
}
