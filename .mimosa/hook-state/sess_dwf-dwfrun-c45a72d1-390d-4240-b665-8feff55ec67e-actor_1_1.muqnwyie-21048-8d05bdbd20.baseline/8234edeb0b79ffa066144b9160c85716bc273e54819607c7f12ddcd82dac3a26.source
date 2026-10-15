#!/usr/bin/env python3
"""Reality test for Fix 4-c-008: single ROUND constant — no contradictions.

DNA #22 (PASS ≠ TRUE) + #14 (evidence consistency) + #26 (reality test).

Before fix:
  - layout.tsx metadata.title said "Round 9"
  - header.tsx badge said "9" while subtitle said "Round 8"
  - hero.tsx h1 said "Round 9"
  - footer.tsx, sidebar.tsx, stats-grid.tsx each had their own copy
  - R10 dashboard further drifted to "Round 10" in places
  Three different numbers (8, 9, 10) visible simultaneously on the same page.

After fix:
  - dashboard/src/lib/audit-data/version.ts exports CURRENT_ROUND +
    CURRENT_ROUND_LABEL + CURRENT_ROUND_BADGE.
  - Every consumer imports from version.ts — bumping the round is a
    one-line change.

Reality-test checks:
  1. version.ts exists and exports CURRENT_ROUND.
  2. At least one consumer imports from version.ts.
  3. No contradictory hardcoded "Round 8" / "Round 9" / "Round 10"
     strings in the same file (header.tsx specifically — the original
     site of the 8-vs-9 contradiction).

Run:
    python3 tests/reality-tests/reality_4-c-008.py
"""

import re
import sys
from pathlib import Path

DASHBOARD_SRC = Path(str(Path(__file__).resolve().parents[2]) + '/dashboard/src')
VERSION_PATH = DASHBOARD_SRC / "lib" / "audit-data" / "version.ts"
HEADER_PATH = DASHBOARD_SRC / "components" / "layout" / "header.tsx"


def main() -> int:
    # -------------------------------------------------------------------------
    # TEST 1 — version.ts exists and exports CURRENT_ROUND
    # -------------------------------------------------------------------------
    assert VERSION_PATH.exists(), f"FAIL: version.ts not found at {VERSION_PATH}"
    version_src = VERSION_PATH.read_text(encoding="utf-8")
    assert re.search(r"export\s+const\s+CURRENT_ROUND\b", version_src), (
        "FAIL: version.ts does not export CURRENT_ROUND"
    )
    assert re.search(r"export\s+const\s+CURRENT_ROUND_LABEL\b", version_src), (
        "FAIL: version.ts does not export CURRENT_ROUND_LABEL"
    )
    print("PASS [1/4]: version.ts exports CURRENT_ROUND + CURRENT_ROUND_LABEL")

    # -------------------------------------------------------------------------
    # TEST 2 — header.tsx imports from version.ts
    # -------------------------------------------------------------------------
    assert HEADER_PATH.exists(), f"FAIL: header.tsx not found at {HEADER_PATH}"
    header_src = HEADER_PATH.read_text(encoding="utf-8")
    assert (
        "audit-data/version" in header_src
        and ("CURRENT_ROUND_LABEL" in header_src or "CURRENT_ROUND" in header_src)
    ), (
        "FAIL: header.tsx does not import CURRENT_ROUND / CURRENT_ROUND_LABEL "
        "from version.ts — round number is not single-sourced"
    )
    print("PASS [2/4]: header.tsx imports from version.ts")

    # -------------------------------------------------------------------------
    # TEST 3 — header.tsx has NO contradictory "Round 8" / "Round 9" /
    # "Round 10" string literals in JSX (single source of truth).
    # -------------------------------------------------------------------------
    # Strip comments + import lines + string-only-state, then look for
    # hardcoded "Round N" strings in JSX. The label "Round 8 · Full Package"
    # pattern was the original contradiction — must be gone.
    contrad = re.findall(r'["\']Round\s+(8|9|10)\b', header_src)
    # Filter out occurrences inside comments (// ... or /* ... */).
    # Remove // line comments and /* */ block comments.
    no_comments = re.sub(r"//[^\n]*", "", header_src)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL)
    contrad = re.findall(r'["\']Round\s+(8|9|10)\b', no_comments)
    assert not contrad, (
        f"FAIL: header.tsx still has contradictory hardcoded 'Round N' "
        f"strings in JSX: {contrad} — must use CURRENT_ROUND_LABEL instead"
    )
    print("PASS [3/4]: header.tsx has no contradictory 'Round 8/9/10' strings in JSX")

    # -------------------------------------------------------------------------
    # TEST 4 — at least 2 consumers import CURRENT_ROUND (single source is
    # actually used). layout.tsx + header.tsx + hero.tsx + footer.tsx +
    # stats-grid.tsx + sidebar.tsx should all import from version.ts.
    # -------------------------------------------------------------------------
    consumers = []
    for sub in [
        "app/layout.tsx",
        "components/layout/header.tsx",
        "components/layout/footer.tsx",
        "components/layout/sidebar.tsx",
        "components/dashboard/hero.tsx",
        "components/dashboard/stats-grid.tsx",
    ]:
        p = DASHBOARD_SRC / sub
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        if "audit-data/version" in s:
            consumers.append(sub)
    assert len(consumers) >= 2, (
        f"FAIL: only {len(consumers)} consumer(s) import from version.ts — "
        f"need at least 2 for single-source-of-truth: {consumers}"
    )
    print(f"PASS [4/4]: {len(consumers)} consumer(s) import from version.ts: {consumers}")

    print("\n✓ Reality test 4-c-008 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
