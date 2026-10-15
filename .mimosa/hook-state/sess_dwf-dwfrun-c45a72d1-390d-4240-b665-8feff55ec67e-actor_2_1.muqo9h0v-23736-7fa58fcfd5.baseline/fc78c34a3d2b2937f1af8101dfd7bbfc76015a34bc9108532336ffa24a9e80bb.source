import { BugCategorySection } from "./critical-silent"
import { SQL_INJECTION_BUGS } from "@/lib/audit-data/bugs-sql"
// [Fix 4-c-015 · Task Local-C] Section number is now looked up from the
// sidebar's SECTIONS array (single source of truth) — was hardcoded "12",
// but the sidebar lists #bugs-sql as n="22".
import { getSectionNumber } from "@/lib/audit-data/sections"

export function SqlInjectionSection() {
  return (
    <BugCategorySection
      id="bugs-sql"
      sectionNumber={getSectionNumber("bugs-sql")}
      title="SQL injection — f-string (NEW R7) + % formatting"
      description="R7 IMPROVED SQLInjectionScanner to catch f-string pattern (R6 only caught % formatting). 3 NEW f-string findings + 2 existing % format + string concat. Total 5 SQL injection sites, all parameterized in R7."
      bugs={SQL_INJECTION_BUGS}
      tone="warning"
    />
  )
}
