import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
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
  Zap,
} from "lucide-react"
import {
  selfAuditFindings,
  selfAuditStats,
  round8Methodology,
  type SelfAuditSeverity,
} from "@/lib/audit-data/self-audit"

const severityConfig: Record<
  SelfAuditSeverity,
  {
    tone: string
    badge: string
    icon: typeof AlertTriangle
  }
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
    icon: Zap,
  },
  low: {
    tone: "border-sky-500/30 bg-sky-500/5",
    badge: "border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400",
    icon: FileSearch,
  },
}

const methodologyIcons = [Microscope, ListChecks, FileSearch, Terminal, CheckCircle2]

export function SelfAuditSection() {
  return (
    <section
      id="self-audit"
      className="scroll-mt-20 border-b border-border/40 bg-gradient-to-b from-fuchsia-500/[0.03] to-transparent py-14"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        {/* Header */}
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Section 16 · Round 8
          </p>
          <h2 className="mt-1 flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
            <ShieldCheck className="h-7 w-7 text-fuchsia-500" />
            Round 8 Self-Audit · auditing the auditor
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            DNA #22 (PASS ≠ TRUE): the R7 dashboard makes claims about itself.
            Round 8 does not trust those claims — it audits each one against
            Reality (the actual files).{" "}
            <strong className="text-fuchsia-600 dark:text-fuchsia-400">
              {selfAuditStats.claimsFoundFalse} of {selfAuditStats.claimsVerified}{" "}
              audited claims were FALSE
            </strong>{" "}
            — including a CRITICAL one (SA-5) where the auditor missed a real
            unfixed bug while overstating a previous round&apos;s incompleteness.
          </p>
        </div>

        {/* Stats strip */}
        <div className="mb-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card className="border-border/60 p-4">
            <div className="flex items-center gap-2">
              <FileSearch className="h-4 w-4 text-muted-foreground" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Claims verified
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums">
              {selfAuditStats.claimsVerified}
            </p>
          </Card>
          <Card className="border-emerald-500/30 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Confirmed TRUE
              </p>
            </div>
            <p className="mt-2 text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
              {selfAuditStats.claimsConfirmedTrue}
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
              {selfAuditStats.claimsFoundFalse}
            </p>
          </Card>
          <Card className="border-fuchsia-500/30 bg-fuchsia-500/5 p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              By severity (CRIT/HIGH/MED/LOW)
            </p>
            <p className="mt-2 text-sm font-bold tabular-nums">
              <span className="text-rose-600 dark:text-rose-400">
                {selfAuditStats.bySeverity.critical}
              </span>
              {" / "}
              <span className="text-amber-600 dark:text-amber-400">
                {selfAuditStats.bySeverity.high}
              </span>
              {" / "}
              <span className="text-yellow-600 dark:text-yellow-400">
                {selfAuditStats.bySeverity.medium}
              </span>
              {" / "}
              <span className="text-sky-600 dark:text-sky-400">
                {selfAuditStats.bySeverity.low}
              </span>
            </p>
          </Card>
        </div>

        {/* Methodology */}
        <Card className="mb-10 border-border/60 bg-background/40 p-5 sm:p-6">
          <div className="mb-4 flex items-center gap-2">
            <Microscope className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              Round 8 methodology — how we audited
            </h3>
          </div>
          <ol className="space-y-3">
            {round8Methodology.map((m, i) => {
              const Icon = methodologyIcons[i] ?? FileSearch
              return (
                <li key={m.step} className="flex gap-3">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-fuchsia-500/10 text-fuchsia-600 dark:text-fuchsia-400">
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
          {selfAuditFindings.map((f) => {
            const cfg = severityConfig[f.severity]
            const Icon = cfg.icon
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
                          <Badge
                            variant="secondary"
                            className="gap-1 font-mono text-[10px]"
                          >
                            {f.id}
                          </Badge>
                          <Badge variant="outline" className={`gap-1 text-[10px] ${cfg.badge}`}>
                            <Icon className="h-3 w-3" />
                            {f.severity.toUpperCase()}
                          </Badge>
                          <Badge
                            variant="outline"
                            className="gap-1 border-fuchsia-500/40 bg-fuchsia-500/10 text-[10px] text-fuchsia-600 dark:text-fuchsia-400"
                          >
                            <ShieldCheck className="h-3 w-3" />
                            {f.dnaPrinciple}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    {/* R7 claim — strikethrough on the FALSE clause */}
                    <div className="space-y-2 rounded-lg border border-rose-500/20 bg-rose-500/[0.04] p-3">
                      <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400">
                        <XCircle className="h-3 w-3" />
                        R7 claim (audited)
                      </p>
                      <p className="text-xs leading-relaxed text-muted-foreground">
                        <span className="line-through decoration-rose-500/60 decoration-1">
                          {f.r7Claim}
                        </span>
                      </p>
                    </div>

                    {/* Reality — green */}
                    <div className="space-y-2 rounded-lg border border-emerald-500/20 bg-emerald-500/[0.04] p-3">
                      <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" />
                        Reality (what&apos;s actually true)
                      </p>
                      <p className="text-xs leading-relaxed text-foreground">
                        {f.reality}
                      </p>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-1">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Root cause — why R7 got this wrong
                      </p>
                      <p className="text-xs text-muted-foreground">{f.rootCause}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Fix — what Round 8 did
                      </p>
                      <p className="text-xs text-muted-foreground">{f.fix}</p>
                    </div>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Closing note */}
        <div className="mt-10 rounded-lg border border-fuchsia-500/30 bg-fuchsia-500/[0.04] p-5">
          <p className="text-xs leading-relaxed text-muted-foreground">
            <strong className="text-fuchsia-600 dark:text-fuchsia-400">
              The auditor&apos;s paradox (DNA #21 + #22):
            </strong>{" "}
            Round 7 audited the SCP codebase and found 14 bugs. Round 8 audited
            the Round 7 dashboard and found {selfAuditStats.claimsFoundFalse}{" "}
            discrepancies in its own claims — including one (SA-5) where R7 missed
            a real unfixed bug while documenting a fictional one. If we apply
            DNA #22 recursively: a Round 9 audit of this Round 8 self-audit would
            likely find its own discrepancies. The process never terminates —
            that is the feature, not the bug. (DNA #23: KHÔNG HOÀN THIỆN.
            KHÔNG HOÀN TẤT. ĐANG HOẠT ĐỘNG.)
          </p>
        </div>
      </div>
    </section>
  )
}
