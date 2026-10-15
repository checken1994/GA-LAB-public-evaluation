#!/usr/bin/env python3
"""Reality test for Fix 4-c-015: section numbering derived from sidebar SECTIONS
array — no hardcoded "Section 08" / "Section 18" contradictions.

DNA #14 (numbers must match) + #22 (PASS ≠ TRUE — the sidebar said 18 but
the rendered section said 08) + #26 (reality test).

Before fix:
  - sidebar.tsx SECTIONS array listed #bugs-critical as n: "18"
  - critical-silent.tsx:115 hardcoded sectionNumber="08"
  - dead-controls.tsx hardcoded sectionNumber="09" (sidebar: 19)
  - type-errors.tsx hardcoded sectionNumber="10" (sidebar: 20)
  - race-conditions.tsx hardcoded sectionNumber="11" (sidebar: 21)
  - sql-injection.tsx hardcoded sectionNumber="12" (sidebar: 22)
  - resource-leaks.tsx hardcoded sectionNumber="13" (sidebar: 23)
  Operator clicking sidebar "#18 CRITICAL silent bugs" landed on a section
  that labelled itself "Section 08".

After fix:
  - sidebar.tsx exports SECTIONS_BY_HREF + getSectionNumber(id).
  - Each bug component calls getSectionNumber(id) instead of hardcoding
    the number. Sidebar and component now agree.

Reality-test checks:
  1. No bug component hardcodes sectionNumber="08" / "09" / "10" / "11" /
     "12" / "13" (the old wrong numbers).
  2. sidebar.tsx exports SECTIONS array as the single source of truth.

Run:
    python3 tests/reality-tests/reality_4-c-015.py
"""

import re
import sys
from pathlib import Path

DASHBOARD_SRC = Path(str(Path(__file__).resolve().parents[2]) + '/dashboard/src')
SIDEBAR_PATH = DASHBOARD_SRC / "components" / "layout" / "sidebar.tsx"
BUG_COMPONENTS = [
    DASHBOARD_SRC / "components" / "bugs" / "critical-silent.tsx",
    DASHBOARD_SRC / "components" / "bugs" / "dead-controls.tsx",
    DASHBOARD_SRC / "components" / "bugs" / "type-errors.tsx",
    DASHBOARD_SRC / "components" / "bugs" / "race-conditions.tsx",
    DASHBOARD_SRC / "components" / "bugs" / "sql-injection.tsx",
    DASHBOARD_SRC / "components" / "bugs" / "resource-leaks.tsx",
]

# Old wrong section numbers (component's own numbering, contradicted sidebar).
OLD_WRONG_NUMBERS = ["08", "09", "10", "11", "12", "13"]


def main() -> int:
    assert SIDEBAR_PATH.exists(), f"FAIL: sidebar.tsx not found at {SIDEBAR_PATH}"
    sidebar_src = SIDEBAR_PATH.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # TEST 1 — SECTIONS + getSectionNumber available in shared module
    # (sections.ts — non-client, importable by both server + client components)
    # OR sidebar.tsx (backward-compat: previously exported from there)
    # -------------------------------------------------------------------------
    sections_module = DASHBOARD_SRC / "lib" / "audit-data" / "sections.ts"
    if sections_module.exists():
        sections_src = sections_module.read_text(encoding="utf-8")
        assert "SECTIONS" in sections_src, "FAIL: sections.ts has no SECTIONS array"
        assert "getSectionNumber" in sections_src, "FAIL: sections.ts has no getSectionNumber"
        assert re.search(r"export\s+(?:const\s+SECTIONS|function\s+getSectionNumber)", sections_src), (
            "FAIL: sections.ts does not export SECTIONS or getSectionNumber"
        )
        print("PASS [1/2]: lib/audit-data/sections.ts exports SECTIONS + getSectionNumber (shared module)")
    else:
        # Backward-compat: check sidebar.tsx (pre-fix location)
        assert (
            "SECTIONS_BY_HREF" in sidebar_src or "getSectionNumber" in sidebar_src
        ), (
            "FAIL: neither sections.ts nor sidebar.tsx exports section data"
        )
        print("PASS [1/2]: sidebar.tsx exports SECTIONS_BY_HREF / getSectionNumber (backward-compat)")

    # -------------------------------------------------------------------------
    # TEST 2 — no bug component hardcodes the OLD WRONG sectionNumber strings
    # ("08", "09", "10", "11", "12", "13") as sectionNumber="...".
    # -------------------------------------------------------------------------
    violations = []
    for comp in BUG_COMPONENTS:
        if not comp.exists():
            continue
        s = comp.read_text(encoding="utf-8")
        # Strip comments.
        no_c = re.sub(r"//[^\n]*", "", s)
        no_c = re.sub(r"/\*.*?\*/", "", no_c, flags=re.DOTALL)
        # Look for `sectionNumber="08"` etc.
        for num in OLD_WRONG_NUMBERS:
            pattern = re.compile(r'sectionNumber\s*=\s*["\']' + re.escape(num) + r'["\']')
            if pattern.search(no_c):
                violations.append((comp.name, num))

    assert not violations, (
        "FAIL: bug components still hardcode old wrong sectionNumbers:\n"
        + "\n".join(f"  {name}: sectionNumber=\"{num}\"" for name, num in violations)
        + "\nMust use getSectionNumber(id) instead."
    )
    print("PASS [2/2]: no bug component hardcodes old wrong sectionNumber strings")

    # -------------------------------------------------------------------------
    # TEST 3 (bonus) — at least one bug component imports getSectionNumber
    # -------------------------------------------------------------------------
    importers = []
    for comp in BUG_COMPONENTS:
        if not comp.exists():
            continue
        s = comp.read_text(encoding="utf-8")
        if "getSectionNumber" in s and "sidebar" in s:
            importers.append(comp.name)
    assert importers, (
        "FAIL: no bug component imports getSectionNumber — fix not wired"
    )
    print(f"  (getSectionNumber imported by: {importers})")

    print("\n✓ Reality test 4-c-015 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
