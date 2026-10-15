import { BugCategorySection } from "./critical-silent"
import { RACE_CONDITION_BUGS } from "@/lib/audit-data/bugs-race"
// [Fix 4-c-015 · Task Local-C] Section number is now looked up from the
// sidebar's SECTIONS array (single source of truth) — was hardcoded "11",
// but the sidebar lists #bugs-race as n="21".
import { getSectionNumber } from "@/lib/audit-data/sections"

export function RaceConditionsSection() {
  return (
    <BugCategorySection
      id="bugs-race"
      sectionNumber={getSectionNumber("bugs-race")}
      title="Race conditions — cross-thread + cross-process"
      description="SCP's own RaceConditionScanner catches same-process lock issues. R7-3 (WHY verification) is cross-process race — needs schema-level fix (claimed_by column + atomic UPDATE ... RETURNING). Hypothesis property test (R7 NEW) reproduce 8-thread concurrent double-execution."
      bugs={RACE_CONDITION_BUGS}
      tone="warning"
    />
  )
}
