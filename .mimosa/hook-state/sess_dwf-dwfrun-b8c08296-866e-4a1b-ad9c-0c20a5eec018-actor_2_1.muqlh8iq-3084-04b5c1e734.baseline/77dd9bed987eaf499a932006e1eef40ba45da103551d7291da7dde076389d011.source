import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AUTOFIX_TIERS } from "@/lib/audit-data/autofix-engine"
import { Shield, ShieldAlert, ShieldCheck, ShieldX } from "lucide-react"

const tierIcons: Record<number, React.ReactNode> = {
  1: <ShieldCheck className="h-5 w-5" />,
  2: <Shield className="h-5 w-5" />,
  3: <ShieldAlert className="h-5 w-5" />,
  4: <ShieldX className="h-5 w-5" />,
}

const tierTone: Record<string, string> = {
  emerald: "border-emerald-500/40 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400",
  amber: "border-amber-500/40 bg-amber-500/5 text-amber-600 dark:text-amber-400",
  rose: "border-rose-500/40 bg-rose-500/5 text-rose-600 dark:text-rose-400",
  fuchsia: "border-fuchsia-500/40 bg-fuchsia-500/5 text-fuchsia-600 dark:text-fuchsia-400",
}

export function TierSystem() {
  return (
    <Card className="p-6 sm:p-8">
      <div className="mb-6">
        <h3 className="text-lg font-bold tracking-tight">4 Tier Autonomy System</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Classifier quyết định tier dựa trên LOGIC_PATTERNS + ATTACK_PATH_PATTERNS +
          RELAXATION_PATTERNS. DNA #4: con người quyết định — Tier-3 luôn require approval.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {AUTOFIX_TIERS.map((t) => (
          <Card key={t.id} className={`p-5 ${tierTone[t.guardColor]}`}>
            <div className="mb-3 flex items-start justify-between">
              <div className="flex items-center gap-2">
                {tierIcons[t.id]}
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                    Tier {t.id}
                  </p>
                  <h4 className="text-sm font-bold leading-tight">{t.name}</h4>
                </div>
              </div>
              <Badge variant="outline" className="text-[9px]">
                T{t.id}
              </Badge>
            </div>
            <p className="mb-3 text-xs text-muted-foreground">{t.description}</p>
            <div className="space-y-2 text-[11px]">
              <div>
                <span className="font-semibold">Autonomy: </span>
                <span className="text-muted-foreground">{t.autonomy}</span>
              </div>
              <div>
                <span className="font-semibold">Rate limit: </span>
                <span className="text-muted-foreground">{t.rateLimit}</span>
              </div>
              <div className="border-t border-border/40 pt-2">
                <p className="mb-1 font-semibold">Examples:</p>
                <ul className="space-y-0.5">
                  {t.examples.map((ex) => (
                    <li key={ex} className="text-muted-foreground">
                      • {ex}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </Card>
  )
}
