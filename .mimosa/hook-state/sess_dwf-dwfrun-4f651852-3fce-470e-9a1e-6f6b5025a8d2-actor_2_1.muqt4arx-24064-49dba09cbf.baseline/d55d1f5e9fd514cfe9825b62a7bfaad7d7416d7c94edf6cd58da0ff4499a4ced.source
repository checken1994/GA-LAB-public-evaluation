import { BugCategorySection } from "./critical-silent"
import { RESOURCE_LEAK_BUGS } from "@/lib/audit-data/bugs-resource-leaks"
// [Fix 4-c-015 · Task Local-C] Section number is now looked up from the
// sidebar's SECTIONS array (single source of truth) — was hardcoded "13",
// but the sidebar lists #bugs-resource as n="23".
import { getSectionNumber } from "@/lib/audit-data/sections"

export function ResourceLeaksSection() {
  return (
    <BugCategorySection
      id="bugs-resource"
      sectionNumber={getSectionNumber("bugs-resource")}
      title="Resource leaks — file/HTTP/DB/tempfile"
      description="open()/connect()/acquire() without close()/release()/context manager. R7 refresh scanner path (remove scp/old_module stale path from R6, add new scp/runtime/slms_parts/ and scp/api_server_parts/ paths). 4 findings, all Tier-1 auto-fix."
      bugs={RESOURCE_LEAK_BUGS}
      tone="info"
    />
  )
}
