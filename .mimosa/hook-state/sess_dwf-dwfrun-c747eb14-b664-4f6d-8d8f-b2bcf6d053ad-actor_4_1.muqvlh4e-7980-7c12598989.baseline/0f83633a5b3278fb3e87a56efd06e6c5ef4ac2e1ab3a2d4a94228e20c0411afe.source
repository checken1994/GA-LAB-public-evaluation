"use client"

import { useState, useEffect } from "react"
import { Menu } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetHeader, SheetDescription } from "@/components/ui/sheet"
import { CURRENT_ROUND } from "@/lib/audit-data/version"
import { SECTIONS } from "@/lib/audit-data/sections"

// [Fix 4-c-015 / 4-c-016 · Task Local-C] SECTIONS + getSectionNumber moved to
// src/lib/audit-data/sections.ts (non-client module) so both server components
// (bug sections) and client components (sidebar) can import the same data.
// Previously these were defined here, but sidebar.tsx has "use client" — server
// components can't import from client modules. DNA #14: single source of truth.

// Module-level NavList (declared outside component to satisfy
// react-hooks/static-components rule — components must not be created during render).
function NavList({
  active,
  onNav,
}: {
  active: string
  onNav?: () => void
}) {
  return (
    <nav className="flex flex-col gap-0.5">
      {SECTIONS.map((s) => (
        <a
          key={s.href}
          href={s.href}
          onClick={onNav}
          className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
            active === s.href
              ? "bg-foreground text-background"
              : "text-muted-foreground hover:bg-accent hover:text-foreground"
          }`}
        >
          <span
            className={`font-mono text-[10px] ${
              active === s.href ? "text-background/60" : "text-muted-foreground/50"
            }`}
          >
            {s.n}
          </span>
          <span className="font-medium">{s.label}</span>
          {"isNew" in s && s.isNew && (
            <span
              className={`ml-auto rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase ${
                active === s.href
                  ? "bg-background/20 text-background"
                  : "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
              }`}
            >
              NEW
            </span>
          )}
          {"isUpdated" in s && s.isUpdated && (
            <span
              className={`ml-auto rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase ${
                active === s.href
                  ? "bg-background/20 text-background"
                  : "bg-sky-500/15 text-sky-600 dark:text-sky-400"
              }`}
            >
              UPDATED
            </span>
          )}
        </a>
      ))}
    </nav>
  )
}

export function Sidebar() {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState<string>("")

  useEffect(() => {
    const onScroll = () => {
      let best = ""
      let bestTop = Infinity
      for (const s of SECTIONS) {
        const el = document.querySelector(s.href)
        if (!el) continue
        const top = Math.abs(el.getBoundingClientRect().top - 120)
        if (top < bestTop) {
          bestTop = top
          best = s.href
        }
      }
      if (best) setActive(best)
    }
    window.addEventListener("scroll", onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="sticky top-16 hidden h-[calc(100vh-4rem)] w-64 shrink-0 overflow-y-auto border-r border-border/40 px-3 py-6 lg:block scroll-thin">
        <div className="mb-3 px-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Mục lục
          </p>
        </div>
        <NavList active={active} />
      </aside>

      {/* Mobile sheet */}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="fixed bottom-4 right-4 z-40 gap-2 rounded-full shadow-lg lg:hidden"
          >
            <Menu className="h-4 w-4" />
            Mục lục
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-72 overflow-y-auto scroll-thin" aria-describedby={undefined}>
          <SheetHeader>
            <SheetTitle className="text-left">Mục lục Round {CURRENT_ROUND}</SheetTitle>
            <SheetDescription className="sr-only">
              {/* [Fix 4-c-016 · Task Local-C] count is computed from
                  SECTIONS.length, not the hardcoded "25" (off-by-one). */}
              Điều hướng nhanh đến {SECTIONS.length} phần của báo cáo audit Round {CURRENT_ROUND}.
            </SheetDescription>
          </SheetHeader>
          <div className="mt-4">
            <NavList active={active} onNav={() => setOpen(false)} />
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
