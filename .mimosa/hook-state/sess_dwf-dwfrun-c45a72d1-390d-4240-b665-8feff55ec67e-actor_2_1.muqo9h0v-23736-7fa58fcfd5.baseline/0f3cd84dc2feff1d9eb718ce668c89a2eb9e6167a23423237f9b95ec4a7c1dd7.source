import { BugCategorySection } from "./critical-silent"
import { TYPE_ERROR_BUGS } from "@/lib/audit-data/bugs-type-errors"
// [Fix 4-c-015 · Task Local-C] Section number is now looked up from the
// sidebar's SECTIONS array (single source of truth) — was hardcoded "10",
// but the sidebar lists #bugs-type as n="20".
import { getSectionNumber } from "@/lib/audit-data/sections"

export function TypeErrorsSection() {
  return (
    <BugCategorySection
      id="bugs-type"
      sectionNumber={getSectionNumber("bugs-type")}
      title="TypeError cluster — None-comparison (8 sites + 1 NEW R7)"
      description="None-dereference, Optional narrowing, union-attr cluster. Caught primarily by mypy (type system) + hypothesis (property test). R6-1 only fixed 2 crypto sites — R7 fixes all 8 sites (5 files). R7 IMPROVED NullSafetyScanner to catch dict.get().attr chain."
      bugs={TYPE_ERROR_BUGS}
      tone="critical"
    />
  )
}
