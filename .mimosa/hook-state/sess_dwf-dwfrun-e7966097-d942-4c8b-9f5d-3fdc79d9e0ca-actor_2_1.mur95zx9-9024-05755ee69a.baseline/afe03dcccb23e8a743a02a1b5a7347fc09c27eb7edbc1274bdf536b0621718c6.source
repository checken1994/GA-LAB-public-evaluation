// [Fix 4-c-015 / 4-c-016 · Task Local-C]
// Section definitions — extracted from sidebar.tsx to a shared non-client module.
//
// WHY: sidebar.tsx has "use client" (it uses useState/useEffect for mobile menu).
// Bug components (dead-controls.tsx, type-errors.tsx, etc.) are SERVER components
// (no "use client") — they can't import from a client module.
// Moving SECTIONS + getSectionNumber here allows both server + client components
// to import the same single source of truth.
//
// DNA #14: single source of truth for section numbering.
// DNA #22: claim (sidebar number) must match reality (section header number).

export interface SectionDef {
  href: string
  label: string
  n: string
  isNew?: boolean
  isUpdated?: boolean
}

export const SECTIONS: SectionDef[] = [
  { href: "#dashboard", label: "Dashboard", n: "01" },
  { href: "#scp-control-panel", label: "SCP Control Panel (live)", n: "02", isNew: true },
  { href: "#dna", label: "SCP DNA 26 nguyên tắc", n: "03" },
  { href: "#methodology", label: "Round 7 Methodology", n: "04" },
  { href: "#sources", label: "7 nguồn độc lập", n: "05" },
  { href: "#self-audit", label: "R8 Self-Audit (SA-1..8)", n: "06" },
  { href: "#audit", label: "R7 Findings (14 bugs)", n: "07" },
  { href: "#autofix", label: "Autofix Engine v2", n: "08" },
  { href: "#improvements", label: "v2 · 12 improvements", n: "09" },
  { href: "#v3-improvements", label: "v3 · 6 improvements (R8)", n: "10" },
  { href: "#v4-improvements", label: "v4 · 6 NEW improvements (R9)", n: "11", isNew: true },
  { href: "#world-tools", label: "World's best (v3+v4 = 15)", n: "12", isUpdated: true },
  { href: "#scanners", label: "25 scanners", n: "13" },
  { href: "#round8-audit", label: "R8 bugs (7)", n: "14" },
  { href: "#round9-audit", label: "R9 NEW bugs (7) R8 missed", n: "15", isNew: true },
  { href: "#round9-self-audit", label: "R9 Self-Audit (SA-R8)", n: "16" },
  { href: "#round10-self-audit", label: "Round 10 Self-Audit (SA-R9)", n: "17", isNew: true },
  { href: "#bugs-critical", label: "CRITICAL silent bugs", n: "18" },
  { href: "#bugs-dead", label: "Dead safety controls", n: "19" },
  { href: "#bugs-type", label: "TypeError cluster", n: "20" },
  { href: "#bugs-race", label: "Race conditions", n: "21" },
  { href: "#bugs-sql", label: "SQL injection", n: "22" },
  { href: "#bugs-resource", label: "Resource leaks", n: "23" },
  { href: "#download", label: "📥 Tải zip + báo cáo (R9)", n: "24" },
]

/**
 * Lookup table: section id (without #) → display number.
 * Bug components call getSectionNumber("bugs-dead") → "19".
 */
export const SECTIONS_BY_HREF: Record<string, string> = Object.fromEntries(
  SECTIONS.map((s) => [s.href.replace(/^#/, ""), s.n]),
)

/**
 * Get the display number for a section by its id (e.g., "bugs-dead" → "19").
 * Returns "??" if the section id is not found (makes misconfiguration visible).
 */
export function getSectionNumber(id: string): string {
  return SECTIONS_BY_HREF[id] ?? "??"
}
