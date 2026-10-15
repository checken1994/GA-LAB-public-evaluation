import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  ROUND9_FINDINGS,
  ROUND9_STATS,
  ROUND9_METHODOLOGY,
  type SAR8Severity,
} from "@/lib/audit-data/round9-self-audit"
import {
  ShieldCheck,
  ShieldAlert,
  XCircle,
  CheckCircle2,
  AlertTriangle,
  FileSearch,
  ListChecks,
  Terminal,
  Microscope,
  Recycle,
  HelpCircle,
} from "lucide-react"

const severityConfig: Record<
  SAR8Severity,
  { tone: string; badge: string; icon: typeof AlertTriangle }
> = {
  critical: {
    tone: "border-rose-500/40 bg-rose-500/5",
    badge: "border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400",
    icon: AlertTriangle,
  },
  high: {
    tone: "border-amber-500/40 bg-amber-500/5",
    badge: "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400",
    icon: ShieldAlert,
  },
  medium: {
    tone: "border-yellow-500/30 bg-yellow-500/5",
    badge: "border-yellow-500/40 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400",
    icon: ShieldAlert,
  },
  low: {
    tone: "border-sky-500/30 bg-sky-500/5",
    badge: "border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400",
    icon: FileSearch,
  },
}

const verdictConfig = {
  FALSE: {
    badge: "border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400",
    icon: XCircle,
  },
  TRUE: {
    badge: "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    icon: CheckCircle2,
  },
  UNVERIFIABLE: {
    badge: "border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400",
    icon: HelpCircle,
  },
} as const

const methodologyIcons = [Microscope, Terminal, FileSearch, ListChecks, CheckCircle2]

export function Round9SelfAuditSection() {
  return (
    <section
      id="round9-self-audit"
      className="scroll-mt-20 border-b border-border/40 bg-gradient-to-b from-rose-500/[0.03] to-transparent py-14"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        {/* Header */}
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Section 18 · Round 9 (R8 self-audit)
          </p>
          <h2 className="mt-1 flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
            <Recycle className="h-7 w-7 text-rose-500" />
            Round 9 Self-Audit · auditing the auditor&apos;s auditor
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            DNA #22 applied recursively (level 3): R7 audited SCP → 14 bugs.
            R7-Full audited R7 → 8 discrepancies.{" "}
            <strong className="text-rose-600 dark:text-rose-400">
              R8 audits R7-Full → {ROUND9_STATS.claimsFalse} of {ROUND9_STATS.claimsAudited}{" "}
              audited claims were FALSE
            </strong>{" "}
            — including a CRITICAL (SA-R8-1): R7-Full claimed &ldquo;0 lint errors&rdquo;
            but shipped 2 more instances of the EXACT bug its own SA-1 finding raised
            against R7. The auditor&apos;s paradox made flesh.
          </p>
        </div>

        {/* Stats strip */}
        <div className="mb-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card className="border-border/60 p-4">
            <div className="flex items-center gap-2">
              <FileSearch className="h-4 w-4 text-muted-foreground" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                R7-Full claims audited
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums">{ROUND9_STATS.claimsAudited}</p>
          </Card>
          <Card className="border-emerald-500/30 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Confirmed TRUE
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
              {ROUND9_STATS.claimsTrue}
            </p>
          </Card>
          <Card className="border-rose-500/30 bg-rose-500/5 p-4">
            <div className="flex items-center gap-2">
              <XCircle className="h-4 w-4 text-rose-600 dark:text-rose-400" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Found FALSE
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums text-rose-600 dark:text-rose-400">
              {ROUND9_STATS.claimsFalse}
            </p>
          </Card>
          <Card className="border-amber-500/30 bg-amber-500/5 p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Severity (C/H/M/L)
            </p>
            <p className="mt-2 text-sm font-bold tabular-nums">
              <span className="text-rose-600 dark:text-rose-400">
                {ROUND9_STATS.bySeverity.critical}
              </span>
              {" / "}
              <span className="text-amber-600 dark:text-amber-400">
                {ROUND9_STATS.bySeverity.high}
              </span>
              {" / "}
              <span className="text-yellow-600 dark:text-yellow-400">
                {ROUND9_STATS.bySeverity.medium}
              </span>
              {" / "}
              <span className="text-sky-600 dark:text-sky-400">
                {ROUND9_STATS.bySeverity.low}
              </span>
            </p>
          </Card>
        </div>

        {/* Methodology */}
        <Card className="mb-10 border-border/60 bg-background/40 p-5 sm:p-6">
          <div className="mb-4 flex items-center gap-2">
            <Microscope className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              Round 9 methodology — how R8 audited R7-Full
            </h3>
          </div>
          <ol className="space-y-3">
            {ROUND9_METHODOLOGY.map((m, i) => {
              const Icon = methodologyIcons[i] ?? FileSearch
              return (
                <li key={m.step} className="flex gap-3">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-rose-500/10 text-rose-600 dark:text-rose-400">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-xs font-semibold text-foreground">{m.step}</p>
                    <p className="text-xs text-muted-foreground">{m.detail}</p>
                  </div>
                </li>
              )
            })}
          </ol>
        </Card>

        {/* Finding cards */}
        <div className="space-y-4">
          {ROUND9_FINDINGS.map((f) => {
            const cfg = severityConfig[f.severity]
            const Icon = cfg.icon
            const vCfg = verdictConfig[f.verdict]
            const VIcon = vCfg.icon
            return (
              <Card key={f.id} className={`overflow-hidden ${cfg.tone}`}>
                <div className="flex flex-col gap-4 p-5 sm:p-6">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-background/60">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="secondary" className="gap-1 font-mono text-[10px]">
                            {f.id}
                          </Badge>
                          <Badge variant="outline" className={`gap-1 text-[10px] ${cfg.badge}`}>
                            <Icon className="h-3 w-3" />
                            {f.severity.toUpperCase()}
                          </Badge>
                          <Badge
                            variant="outline"
                            className="gap-1 border-rose-500/40 bg-rose-500/10 text-[10px] text-rose-600 dark:text-rose-400"
                          >
                            <Recycle className="h-3 w-3" />
                            {f.dna}
                          </Badge>
                          <Badge variant="outline" className={`gap-1 text-[10px] ${vCfg.badge}`}>
                            <VIcon className="h-3 w-3" />
                            {f.verdict}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    {/* R7-Full claim — strikethrough on FALSE */}
                    <div className="space-y-2 rounded-lg border border-rose-500/20 bg-rose-500/[0.04] p-3">
                      <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400">
                        <XCircle className="h-3 w-3" />
                        R7-Full claim (audited)
                      </p>
                      <p className="text-xs leading-relaxed text-muted-foreground">
                        <span className="line-through decoration-rose-500/60 decoration-1">
                          {f.r7FullClaim}
                        </span>
                      </p>
                    </div>

                    {/* Reality — green */}
                    <div className="space-y-2 rounded-lg border border-emerald-500/20 bg-emerald-500/[0.04] p-3">
                      <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" />
                        Reality (R8 verified)
                      </p>
                      <p className="text-xs leading-relaxed text-foreground">{f.reality}</p>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-1">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Evidence (exact command + output)
                      </p>
                      <pre className="overflow-auto rounded-md border border-border/60 bg-muted/40 p-2.5 text-[11px] leading-relaxed text-muted-foreground scroll-thin">
                        <code className="font-mono">{f.evidence}</code>
                      </pre>
                    </div>
                    <div className="space-y-1">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Fix — what R8 did
                      </p>
                      <p className="text-xs text-muted-foreground">{f.fix}</p>
                    </div>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* The recursion insight */}
        <div className="mt-10 rounded-lg border border-rose-500/30 bg-rose-500/[0.04] p-5">
          <p className="text-xs leading-relaxed text-muted-foreground">
            <strong className="text-rose-600 dark:text-rose-400">
              The recursion is now visible at 3 levels (DNA #21 + #22 + #23):
            </strong>{" "}
            R7 (fictional beforeCode per SA-5) → R7-Full (claimed &ldquo;0 lint errors&rdquo;
            without re-running lint, documented SA-8 fix but never applied it, R7-6 wrong
            file:line, R7-4 &ldquo;Bayesian prior&rdquo; fictional — the SAME failure modes
            R7-Full flagged in R7) → R8 (this audit, also incomplete per DNA #23). Each
            round finds the previous round&apos;s PASS-without-TRUE violations.{" "}
            <strong className="text-foreground">
              The process never terminates — that is the feature.
            </strong>{" "}
            A Round 10 audit of THIS Round 9 self-audit would find its own discrepancies.
          </p>
        </div>
      </div>
    </section>
  )
}
