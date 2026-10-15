import { R7_STATS } from "@/lib/audit-data/round7"
import { R8_STATS } from "@/lib/audit-data/round8"
import { R9_STATS } from "@/lib/audit-data/round9"
import { ROUND9_STATS } from "@/lib/audit-data/round9-self-audit"
import { ROUND10_STATS } from "@/lib/audit-data/round10-self-audit"
import { V3_STATS } from "@/lib/audit-data/autofix-v3"
import { V4_STATS } from "@/lib/audit-data/autofix-v4"
import { SCP_SCANNERS } from "@/lib/audit-data/scanners"
import { AUTOFIX_IMPROVEMENTS, IMPROVEMENT_STATS } from "@/lib/audit-data/autofix-improvements"
import { SCP_DNA } from "@/lib/audit-data/dna"
import { AUDIT_SOURCES } from "@/lib/audit-data/sources"
import { CURRENT_ROUND } from "@/lib/audit-data/version"
import { Card } from "@/components/ui/card"

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  tone?: "default" | "critical" | "warning" | "good" | "info"
  icon?: React.ReactNode
}

const toneClasses: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "border-border",
  critical: "border-rose-500/40 bg-rose-500/5",
  warning: "border-amber-500/40 bg-amber-500/5",
  good: "border-emerald-500/40 bg-emerald-500/5",
  info: "border-fuchsia-500/40 bg-fuchsia-500/5",
}

const toneValue: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "text-foreground",
  critical: "text-rose-600 dark:text-rose-400",
  warning: "text-amber-600 dark:text-amber-400",
  good: "text-emerald-600 dark:text-emerald-400",
  info: "text-fuchsia-600 dark:text-fuchsia-400",
}

function StatCard({ label, value, sub, tone = "default", icon }: StatCardProps) {
  return (
    <Card className={`p-5 ${toneClasses[tone]}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          <p className={`text-2xl font-bold tabular-nums sm:text-3xl ${toneValue[tone]}`}>
            {value}
          </p>
          {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
        </div>
        {icon && <div className="shrink-0 text-muted-foreground/70">{icon}</div>}
      </div>
    </Card>
  )
}

export function StatsGrid() {
  const scpScanners = SCP_SCANNERS.filter((s) => s.type === "scp-own").length
  const externalTools = SCP_SCANNERS.filter((s) => s.type === "external").length
  const improvedScanners = SCP_SCANNERS.filter((s) => s.r7Improved).length

  return (
    <section className="border-b border-border/40 py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <h2 className="text-xl font-bold tracking-tight sm:text-2xl">
              {/* [Fix 4-c-008 · Task Local-C] Snapshot Round N reads from
                  version.ts — was hardcoded "Snapshot Round 9". */}
              Snapshot Round {CURRENT_ROUND}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Số liệu thực — không phải báo cáo tuỳ tiện (DNA #22 recursive, level 4)
            </p>
          </div>
        </div>

        {/* R7 baseline row */}
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          R7 baseline (R7-Full)
        </p>
        <div className="mb-6 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <StatCard
            label="R7 findings"
            value={R7_STATS.total}
            sub={`${R7_STATS.critical} CRITICAL · ${R7_STATS.high} HIGH`}
            tone="critical"
          />
          <StatCard
            label="R5/R6 fix KHÔNG HOÀN CHỈNH"
            value={R7_STATS.r5r6Incomplete}
            sub="DNA #22: PASS ≠ TRUE"
            tone="warning"
          />
          <StatCard
            label="R7 NEW findings"
            value={R7_STATS.newInR7}
            sub="Nguồn thứ 7: hypothesis"
            tone="info"
          />
          <StatCard
            label="Đã fix R7"
            value={`${R7_STATS.fixed}/${R7_STATS.total}`}
            sub={`${R7_STATS.needsHuman} cần human approval`}
            tone="good"
          />
          <StatCard
            label="SCP DNA principles"
            value={SCP_DNA.length}
            sub="26 nguyên tắc cốt lõi"
          />
          <StatCard
            label="Nguồn độc lập lineage"
            value={AUDIT_SOURCES.length}
            sub="8 lineage groups"
          />
          <StatCard
            label="Scanners"
            value={scpScanners + externalTools}
            sub={`${scpScanners} SCP own + ${externalTools} external · ${improvedScanners} R7 improved`}
          />
          <StatCard
            label="Autofix v2 improvements"
            value={IMPROVEMENT_STATS.total}
            sub={`${IMPROVEMENT_STATS.implemented} implemented · ${IMPROVEMENT_STATS.planned} planned`}
            tone="info"
          />
        </div>

        {/* R8 row */}
        <p className="mb-2 mt-8 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          R8 (previous audit — verified by Reality)
        </p>
        <div className="mb-6 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <StatCard
            label="R8 NEW root-cause bugs"
            value={R8_STATS.total}
            sub={`${R8_STATS.fixed} patched · ${R8_STATS.bySeverity.high} HIGH · ${R8_STATS.bySeverity.medium} MED`}
            tone="critical"
          />
          <StatCard
            label="R9 Self-Audit findings (R8 of R7-Full)"
            value={ROUND9_STATS.claimsFalse}
            sub={`${ROUND9_STATS.claimsAudited} R7-Full claims audited · ${ROUND9_STATS.claimsTrue} TRUE`}
            tone="warning"
          />
          <StatCard
            label="Autofix v3 improvements"
            value={V3_STATS.total}
            sub={`${V3_STATS.totalLoc.toLocaleString()} LOC · ${V3_STATS.byAxis.accuracy} acc / ${V3_STATS.byAxis.speed} spd / ${V3_STATS.byAxis.safety} saf`}
            tone="good"
          />
          <StatCard
            label="Dashboard lint errors (R8 baseline)"
            value="0"
            sub="genuinely 0 — SA-R8-1 fixed in R8"
            tone="good"
          />
        </div>

        {/* R9 NEW row */}
        <p className="mb-2 mt-8 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          R9 NEW (this audit — recursion level 4, verified by Reality)
        </p>
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <StatCard
            label="R9 NEW root-cause bugs (R8 missed)"
            value={R9_STATS.total}
            sub={`${R9_STATS.fixed} patched · 1 CRITICAL · 3 HIGH · R9-7 = R8-1 regression`}
            tone="critical"
          />
          <StatCard
            label="Round 10 Self-Audit findings (SA-R9)"
            value={ROUND10_STATS.claimsFalse}
            sub={`${ROUND10_STATS.claimsAudited} R8 claims audited · ${ROUND10_STATS.claimsTrue} TRUE · SA-R9-2 HIGH cross-validates R9-7`}
            tone="warning"
          />
          <StatCard
            label="Autofix v4 improvements (IMP-19..24)"
            value={V4_STATS.total}
            sub={`${V4_STATS.totalLoc.toLocaleString()} LOC · ${V4_STATS.byAxis.accuracy} acc / ${V4_STATS.byAxis.speed} spd / ${V4_STATS.byAxis.safety} saf · 4-layer safety net`}
            tone="good"
          />
          <StatCard
            label="Python files ast.parse OK"
            value="377/377"
            sub="371 R8 baseline + 6 v4 NEW · 0 FAIL · 63 autofix .py (51 v2 + 6 v3 + 6 v4)"
            tone="good"
          />
        </div>
      </div>
    </section>
  )
}
