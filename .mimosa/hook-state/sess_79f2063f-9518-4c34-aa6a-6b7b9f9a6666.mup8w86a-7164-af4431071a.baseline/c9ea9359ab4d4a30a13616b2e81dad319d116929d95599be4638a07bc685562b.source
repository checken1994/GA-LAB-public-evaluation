#!/usr/bin/env python3
"""Reality test for Fix 4-c-016: sidebar count derived from SECTIONS.length
(not hardcoded "25").

DNA #14 (numbers must match) + #22 (PASS ≠ TRUE — comment said 25, array
had 24) + #26 (reality test).

Before fix:
  - sidebar.tsx comment said "25 sections total = 20 R8 + 4 NEW R9 + 1 SCP"
  - SECTIONS array actually had 24 entries.
  - Off-by-one in the displayed count.

After fix:
  - Comment about "25 sections" removed (or no longer authoritative).
  - SheetDescription uses `{SECTIONS.length}` (computed value).

Reality-test checks:
  1. SECTIONS.length is referenced in the JSX (count is computed, not a
     hardcoded literal).
  2. The hardcoded "25 sections" string is gone from sidebar.tsx
     (or downgraded to a historical comment).

Run:
    python3 tests/reality-tests/reality_4-c-016.py
"""

import re
import sys
from pathlib import Path

SIDEBAR_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/components/layout/sidebar.tsx'
)


def main() -> int:
    assert SIDEBAR_PATH.exists(), f"FAIL: sidebar.tsx not found at {SIDEBAR_PATH}"
    src = SIDEBAR_PATH.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # TEST 1 — SECTIONS.length referenced in JSX (computed count)
    # -------------------------------------------------------------------------
    assert "SECTIONS.length" in src, (
        "FAIL: sidebar.tsx does not reference SECTIONS.length — section count "
        "is hardcoded, not computed from the array. Off-by-one risk persists."
    )
    print("PASS [1/2]: sidebar.tsx references SECTIONS.length (computed count)")

    # -------------------------------------------------------------------------
    # TEST 2 — no authoritative "25 sections" / "25 phần" claim in the
    # SheetDescription or visible UI text. (Comments documenting history
    # are OK — the test strips them.)
    # -------------------------------------------------------------------------
    # Strip // line comments and /* */ block comments.
    no_comments = re.sub(r"//[^\n]*", "", src)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL)

    # Look for "25 phần" / "25 sections" / "25 mục" in the visible JSX text.
    bad_25 = re.findall(r'["\'`]?\s*25\s+(phần|sections|mục)', no_comments, re.IGNORECASE)
    assert not bad_25, (
        f"FAIL: sidebar.tsx visible UI text still claims '25 phần/sections/mục' "
        f"(actual array length is 24): {bad_25}"
    )
    print("PASS [2/2]: no authoritative '25 phần/sections' claim in sidebar UI text")

    # -------------------------------------------------------------------------
    # TEST 3 — sanity: count the SECTIONS array entries directly and confirm
    # the SheetDescription would render that count.
    # -------------------------------------------------------------------------
    # Find the SECTIONS array literal and count top-level objects.
    # Pattern: SECTIONS = [ {...}, {...}, ... ]
    m = re.search(r"SECTIONS\s*=\s*\[(.*?)^\]", src, re.MULTILINE | re.DOTALL)
    if m:
        body = m.group(1)
        # Count `{ href:` occurrences (each entry is one object).
        entries = re.findall(r"\{\s*href:", body)
        print(f"  (SECTIONS array has {len(entries)} entries — SheetDescription will show this number)")
        assert len(entries) == 24, (
            f"WARN: SECTIONS array has {len(entries)} entries — comment said "
            f"25. This is the original bug. If 24 is correct, update the "
            f"comment; if 25, add the missing entry. DNA #23."
        )

    print("\n✓ Reality test 4-c-016 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
