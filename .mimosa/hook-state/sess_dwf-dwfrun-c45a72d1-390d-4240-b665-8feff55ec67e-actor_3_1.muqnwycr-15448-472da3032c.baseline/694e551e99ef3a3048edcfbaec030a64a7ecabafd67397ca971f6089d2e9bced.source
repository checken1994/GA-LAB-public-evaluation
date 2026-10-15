"use client"

import { useState } from "react"
import { SCP_DNA } from "@/lib/audit-data/dna"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Search } from "lucide-react"

export function DnaGrid() {
  const [q, setQ] = useState("")

  const filtered = SCP_DNA.filter(
    (d) =>
      !q ||
      d.title.toLowerCase().includes(q.toLowerCase()) ||
      d.shortName.toLowerCase().includes(q.toLowerCase()) ||
      d.principle.toLowerCase().includes(q.toLowerCase()),
  )

  return (
    <section id="dna" className="scroll-mt-20 border-b border-border/40 py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Section 02
            </p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
              SCP DNA · 26 nguyên tắc cốt lõi
            </h2>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Compass cho Round 7 audit. Mỗi nguyên tắc là một &ldquo;missing piece&rdquo;
              SCP đã phát hiện qua 13+ năm — bắt đầu từ câu hỏi &ldquo;Tại sao?&rdquo;
              của Gà (The Why Man).
            </p>
          </div>
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Tìm nguyên tắc..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((dna) => (
            <Card
              key={dna.id}
              className="group relative flex flex-col gap-3 overflow-hidden p-5 transition-all hover:shadow-md"
            >
              <div className="absolute right-3 top-3 font-mono text-5xl font-bold text-foreground/[0.04] transition-colors group-hover:text-foreground/[0.06]">
                {dna.id.toString().padStart(2, "0")}
              </div>
              <div className="flex items-start justify-between gap-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted text-lg">
                  {dna.emoji}
                </div>
                <Badge variant="secondary" className="text-[10px]">
                  #{dna.id}
                </Badge>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">
                  {dna.shortName}
                </p>
                <h3 className="text-sm font-bold leading-snug">{dna.title}</h3>
              </div>
              <p className="line-clamp-3 text-xs text-muted-foreground">
                {dna.principle}
              </p>
              <div className="mt-auto space-y-2 border-t border-border/40 pt-3 text-[11px]">
                <div>
                  <span className="font-semibold text-rose-500">Anti-pattern: </span>
                  <span className="text-muted-foreground">{dna.antiPattern}</span>
                </div>
                <div>
                  <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                    R7 apply:{" "}
                  </span>
                  <span className="text-muted-foreground">{dna.round7Application}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="py-16 text-center text-sm text-muted-foreground">
            Không tìm thấy nguyên tắc nào cho &ldquo;{q}&rdquo;.
          </div>
        )}
      </div>
    </section>
  )
}
