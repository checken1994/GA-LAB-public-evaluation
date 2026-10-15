"use client"

import { useSyncExternalStore, useCallback } from "react"
import { Shield, Moon, Sun, Activity } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { CURRENT_ROUND_LABEL, CURRENT_ROUND_BADGE } from "@/lib/audit-data/version"

/**
 * Theme store — single source of truth lives in <html class="dark"> + localStorage.
 * Components subscribe via useSyncExternalStore (React 19 idiom for external systems).
 * This avoids the `set-state-in-effect` lint error that the R7 dashboard shipped with
 * (R8 self-audit finding SA-1: R7 claimed "0 lint errors" but actually had 1).
 */

const THEME_KEY = "scp-theme"

function subscribeTheme(cb: () => void) {
  const mql = window.matchMedia("(prefers-color-scheme: dark)")
  mql.addEventListener("change", cb)
  window.addEventListener("scp-theme-change", cb)
  return () => {
    mql.removeEventListener("change", cb)
    window.removeEventListener("scp-theme-change", cb)
  }
}

function readTheme(): boolean {
  return document.documentElement.classList.contains("dark")
}

// On the server we always report `false`; the inline script in layout.tsx
// corrects the <html> class before hydration, so the client snapshot will
// match the painted DOM (no hydration mismatch).
function readThemeServer(): boolean {
  return false
}

export function Header() {
  const dark = useSyncExternalStore(subscribeTheme, readTheme, readThemeServer)

  const toggle = useCallback(() => {
    const next = !document.documentElement.classList.contains("dark")
    document.documentElement.classList.toggle("dark", next)
    try {
      localStorage.setItem(THEME_KEY, next ? "dark" : "light")
    } catch {
      /* ignore quota / privacy-mode errors */
    }
    window.dispatchEvent(new Event("scp-theme-change"))
  }, [])

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/60 bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-foreground text-background">
              <Shield className="h-5 w-5" strokeWidth={2.2} />
            </div>
            {/* [Fix 4-c-008 · Task Local-C] Round badge reads CURRENT_ROUND_BADGE
                from version.ts (single source of truth). Previously hardcoded
                "9" while subtitle said "Round 8" + tab said "Round 9". */}
            <span className="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[9px] font-bold text-white">
              {CURRENT_ROUND_BADGE}
            </span>
          </div>
          <div className="flex flex-col leading-tight">
            <span className="text-sm font-bold tracking-tight sm:text-base">
              SCP DNA Audit
            </span>
            {/* [Fix 4-c-008 · Task Local-C] Subtitle now derives from
                CURRENT_ROUND_LABEL — no longer a separate "Round 8" string
                that contradicts the badge. */}
            <span className="text-[11px] text-muted-foreground">
              {CURRENT_ROUND_LABEL} · Full Package
            </span>
          </div>
          <Badge variant="outline" className="ml-2 hidden gap-1 sm:flex">
            <Activity className="h-3 w-3 text-emerald-500" />
            <span className="text-emerald-600 dark:text-emerald-400">LIVE</span>
          </Badge>
        </div>

        <nav className="hidden items-center gap-1 md:flex">
          {[
            { href: "#dashboard", label: "Dashboard" },
            { href: "#dna", label: "DNA" },
            { href: "#audit", label: "R7" },
            { href: "#self-audit", label: "R8 SA" },
            { href: "#round8-audit", label: "R8 Bugs" },
            { href: "#round9-self-audit", label: "R9 SA" },
            { href: "#v3-improvements", label: "Autofix v3" },
            { href: "#world-tools", label: "World Tools" },
          ].map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {/* [Fix 4-c-018 · Task Local-C] Removed the dead GitHub button.
              BEFORE: a link to `https://github.com` (no org/repo) — opening
              it landed on GitHub's homepage, not a repo. The aria-label
              "Repository" was a false promise (DNA #11: human-in-the-loop
              thật — every control must lead somewhere real). There is no
              public repo for this project, so the button was removed rather
              than pointed at a placeholder. Rollback: re-add the button if a
              real repo URL is published. */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggle}
            aria-label="Toggle theme"
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </header>
  )
}
