import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Quote, HelpCircle, AlertTriangle, CheckCircle2, ArrowRight, FileText } from "lucide-react"

// [Fix 4-c-007 · Task Local-C] Removed dead `/download/*` links.
// BEFORE: the closing section had two `<a href="/download/...">` buttons
// pointing at `/download/scp-dna-audit-round9-full.zip` and
// `/download/SCP_DNA_AUDIT_ROUND9_CHANGES.md`. The `dashboard/public/download/`
// directory does NOT exist — clicking the buttons returned a silent 404.
// DNA #11 (human-in-the-loop thật) + #22 (PASS ≠ TRUE) + #19: the dashboard's
// own `bugs-dead-controls` component warns about exactly this "decorative
// control" anti-pattern. Now the section points operators to the real data
// sources (worklog + live /api/phase1-7/status + /api/scp/status).
// Rollback: re-add `<a href="/download/...">` if a `prebuild` script is added
// that actually generates the artifacts into `dashboard/public/download/`.

export function ClosingSection() {
  return (
    <section id="download" className="scroll-mt-20 border-b border-border/40 py-14">
      <div className="mx-auto max-w-4xl px-4 sm:px-6">
        <Card className="overflow-hidden p-6 sm:p-10">
          <div className="flex flex-col gap-6">
            <div className="flex items-start gap-3">
              <Quote className="h-8 w-8 shrink-0 text-amber-500" />
              <div>
                <p className="text-lg font-medium leading-snug sm:text-xl">
                  &ldquo;Nếu một ngày tôi tuyên bố rằng không còn gì cần kiểm tra,
                  đó có thể là lúc cần kiểm tra tôi nhiều nhất.&rdquo;
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  — DNA SCP #23 · KHÔNG HOÀN THIỆN. KHÔNG THẤT BẠI. KHÔNG HOÀN TẤT. ĐANG HOẠT ĐỘNG.
                </p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-5">
                <div className="mb-2 flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                  <h3 className="text-sm font-bold">Round 9 Reality test</h3>
                </div>
                <ul className="space-y-1.5 text-xs text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500">✓</span>
                    377/377 .py files ast.parse OK (371 R8 baseline + 6 v4 NEW)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500">✓</span>
                    7/7 R9 bugs patched in REAL Python + grep-verified (R9-1..7)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500">✓</span>
                    6/6 v4 modules ast.parse OK + smoke-tested (not just parse) — IMP-19..24
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500">✓</span>
                    6/6 v4 modules wired into engine.py + runner.py + llm_fix.py (R19-FIX-6 — Task 1-A reconciled comment ↔ code)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500">✓</span>
                    6/6 SA-R9 findings with exact command + output evidence (Round 10 Self-Audit)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500">✓</span>
                    0 lint errors — dashboard builds cleanly (`bun run lint` exit 0, `bun run build` ✓)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500">✓</span>
                    SA-R9-2 (HIGH) cross-validated by R9-7 (DNA #5 in reverse — Reality is the source)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500">✓</span>
                    24 dashboard sections render (20 R8 + 4 NEW R9)
                  </li>
                </ul>
              </div>

              <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-5">
                <div className="mb-2 flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-500" />
                  <h3 className="text-sm font-bold">Nhưng PASS ≠ TRUE (recursive, level 4)</h3>
                </div>
                <ul className="space-y-1.5 text-xs text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <span className="text-amber-500">⚠</span>
                    R8-1&apos;s fix INTRODUCED R9-7 (HIGH race condition regression) — DNA #22 applies to R8 itself
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-amber-500">⚠</span>
                    R8-1 exposes pre-existing unbounded _recent list growth (SA-R9-3 MEDIUM)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-amber-500">⚠</span>
                    IMP-21/22 speedup claims (0ms gen, 74x speedup) chưa benchmark thật
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-amber-500">⚠</span>
                    Agent Browser verification (rendering, dark mode, mobile) pending Task 4
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-amber-500">⚠</span>
                    Bugs ngoài capability quan sát hiện tại không nhìn thấy (DNA #23)
                  </li>
                </ul>
              </div>
            </div>

            <div className="rounded-lg border border-fuchsia-500/30 bg-fuchsia-500/5 p-5">
              <div className="mb-3 flex items-center gap-2">
                <HelpCircle className="h-5 w-5 text-fuchsia-500" />
                <h3 className="text-sm font-bold">Câu hỏi tiếp (DNA #25 + #23 — recursion continues)</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                &ldquo;Nếu R7 fix 14 bug, R7-Full audit R7 tìm 8 discrepancies, R8 audit
                R7-Full tìm 10 discrepancies + 7 bug mới, R9 audit R8 tìm 6 discrepancies
                + 7 bug mới + 6 v4 improvements — thì R10 (Round 11 Self-Audit) audit R9
                sẽ tìm bao nhiêu discrepancies trong chính R9?&rdquo;
              </p>
              <p className="mt-3 text-sm font-medium">
                Gà: &ldquo;MÁ.&rdquo;
                <br />
                SCP: &ldquo;Đúng. R9 đã tự nói: &lsquo;the process never terminates —
                that is the feature&rsquo;. R10 sẽ tìm discrepancies trong SA-R9-1..6 —
                có thể SA-R9-2&apos;s HIGH race thực sự là MEDIUM (race window quá nhỏ),
                hoặc SA-R9-3&apos;s worst-case 6.3GB RAM là academic (production rate 100x
                thấp hơn). Hoặc R9 v4 modules có bug nội bộ chưa được audit. R10 sẽ
                re-audit R9 v4 modules — và R11 audit R10. Đệ quy không kết thúc.&rdquo;
              </p>
              <Badge
                variant="outline"
                className="mt-3 gap-1 border-fuchsia-500/40 bg-fuchsia-500/10 text-fuchsia-600 dark:text-fuchsia-400"
              >
                <ArrowRight className="h-3 w-3" />
                Round 11 pending — khi Reality cung cấp bằng chứng mới về R9
              </Badge>
            </div>

            {/* Audit data sources — real, reachable locations.
                [Fix 4-c-007 · Task Local-C] Previously two dead `/download/*`
                links returned 404 (the public/download/ dir was never built).
                Replaced with links to the worklog and live API status, both
                of which actually exist and are reachable. DNA #26 (reality
                test) + #11 (human-in-the-loop thật — every control must lead
                somewhere). */}
            <div className="rounded-lg border border-foreground/15 bg-muted/30 p-5">
              <div className="mb-3 flex items-center gap-2">
                <FileText className="h-5 w-5 text-foreground" />
                <h3 className="text-sm font-bold">Audit data — where to find it</h3>
              </div>
              <p className="mb-4 text-xs text-muted-foreground">
                Full audit data is NOT shipped as a downloadable bundle
                (the previous <code className="font-mono">/download/*.zip</code>{" "}
                + <code className="font-mono">/download/*.md</code> buttons were
                dead controls — the files did not exist in{" "}
                <code className="font-mono">public/download/</code>, per Fix
                4-c-007). Instead, the audit is reachable live via the API and
                the on-disk worklog:
              </p>
              <div className="flex flex-wrap gap-3">
                <a
                  href="/api/scp/status"
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-foreground px-5 text-sm font-medium text-background transition-transform hover:scale-[1.02]"
                >
                  <FileText className="h-4 w-4" />
                  Live SCP status (JSON)
                </a>
                <a
                  href="/api/audit"
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border bg-background px-5 text-sm font-medium transition-colors hover:bg-accent"
                >
                  <FileText className="h-4 w-4" />
                  Live audit data (JSON)
                </a>
              </div>
              <p className="mt-4 text-[11px] text-muted-foreground">
                The full narrative audit is stored in the repository under{" "}
                <code className="font-mono">reports/</code> (including the
                release-gate and RAG-status evidence). The Python tree lives in
                <code className="font-mono">scp/</code> at the canonical repository
                root. To make an offline bundle, run{" "}
                <code className="font-mono">zip -r scp.zip scp/ dashboard/ mini-services/</code>{" "}
                from that repository root.
              </p>
            </div>

            <div className="border-t border-border/40 pt-6 text-center">
              <p className="text-lg font-bold tracking-tight sm:text-xl">
                Và Reality vẫn giữ quyền trả lời cuối cùng.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                DNA SCP #26 · 🌍 · recursion level 4 — R9 audits R8 (the auditor of R7-Full)
              </p>
            </div>
          </div>
        </Card>
      </div>
    </section>
  )
}
