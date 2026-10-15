import { BugCategorySection } from "./critical-silent"
import { DEAD_CONTROL_BUGS } from "@/lib/audit-data/bugs-dead-controls"
// [Fix 4-c-015 · Task Local-C] Section number is now looked up from the
// sidebar's SECTIONS array (single source of truth) — was hardcoded "09",
// but the sidebar lists #bugs-dead as n="19".
import { getSectionNumber } from "@/lib/audit-data/sections"

export function DeadControlsSection() {
  return (
    <BugCategorySection
      id="bugs-dead"
      sectionNumber={getSectionNumber("bugs-dead")}
      title="HIGH — Dead safety controls (wired-but-never-called)"
      description="Functions/methods defined but NEVER called by any runtime path. 'Wired-but-never-called' = vulture Category B. R6 found 9, R7 found 14 (deeper Category B/C + R-fix-completeness check). Tất cả 5 bugs này đều R5/R6 fix KHÔNG HOÀN CHỈNH."
      bugs={DEAD_CONTROL_BUGS}
      tone="warning"
    />
  )
}
