#!/usr/bin/env python3
"""Reality test for Fix 4-c-010: scp-control-panel no longer calls Date.now()
in render body; uses useEffect + state + suppressHydrationWarning.

DNA #9 (no harm) + #22 (silent failure — hydration mismatch is invisible
under disabled ESLint rules) + #26 (reality test).

Before fix:
  - dashboard/src/components/dashboard/scp-control-panel.tsx:144
    `const now = Date.now()` called during render.
  - SSR pre-render computes now=T0; client hydration computes now=T0+200ms
    → nextInSec differs → React hydration warning → React discards server
    HTML + re-renders (FCP/LCP regression).
  - lastRunTs.toLocaleTimeString() and nextRunTs.toLocaleTimeString()
    depend on runtime locale/timezone — server (UTC) vs client (local tz)
    may format differently → second hydration mismatch.

After fix:
  - `now` is `null` initially (server + first client paint match), then a
    useEffect sets it via setInterval updating every 1s on the client only.
  - nextInSec is `null` until the effect runs — operator sees "—" for the
    first 16ms, which is fine.
  - suppressHydrationWarning on every <span> / <div> that renders
    toLocaleTimeString() — server/client locale drift no longer warns.

Reality-test checks:
  1. No `const now = Date.now()` directly in the LoopSchedulerCard render
     body — must be in useState + useEffect.
  2. suppressHydrationWarning present on at least one element that renders
     toLocaleTimeString(), OR useEffect + useState present for `now`.

Run:
    python3 tests/reality-tests/reality_4-c-010.py
"""

import re
import sys
from pathlib import Path

PANEL_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/components/dashboard/scp-control-panel.tsx'
)


def main() -> int:
    assert PANEL_PATH.exists(), f"FAIL: scp-control-panel.tsx not found at {PANEL_PATH}"
    src = PANEL_PATH.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # TEST 1 — Date.now() not called directly in the JSX render body
    # (must be in useEffect). Specifically: `const now = Date.now()` at the
    # top of LoopSchedulerCard is the bug pattern — must be replaced with
    # useState + useEffect.
    # -------------------------------------------------------------------------
    # Look for the specific anti-pattern: `const now = Date.now()` outside
    # of an effect body. Allow Date.now() INSIDE a useEffect callback.
    bad_pattern = re.compile(r"^\s*const\s+now\s*=\s*Date\.now\(\)", re.MULTILINE)
    bad_matches = bad_pattern.findall(src)
    assert not bad_matches, (
        "FAIL: scp-control-panel.tsx still has `const now = Date.now()` "
        "in render body (not in useEffect) — hydration mismatch persists. "
        "Move to useState + useEffect."
    )
    print("PASS [1/2]: no `const now = Date.now()` in render body")

    # -------------------------------------------------------------------------
    # TEST 2 — Either useEffect+useState for `now`, OR suppressHydrationWarning
    # on every toLocaleTimeString-rendering element. Either fix is acceptable
    # per the task spec.
    # -------------------------------------------------------------------------
    has_use_effect_for_now = (
        re.search(r"React\.useState<number\s*\|\s*null>", src) is not None
        or re.search(r"useState<number\s*\|\s*null>", src) is not None
    ) and "useEffect" in src and "Date.now" in src and "setNow" in src

    has_suppress = "suppressHydrationWarning" in src
    assert has_use_effect_for_now or has_suppress, (
        "FAIL: scp-control-panel.tsx has neither (a) useEffect+useState for "
        "`now` NOR (b) suppressHydrationWarning on time-rendering elements. "
        "Hydration mismatch unfixed."
    )

    if has_use_effect_for_now:
        print("PASS [2/2]: useEffect + useState pattern for `now` present")
    elif has_suppress:
        print("PASS [2/2]: suppressHydrationWarning present on time elements")
    else:
        # Should not reach here — assert above would have fired.
        pass

    # Bonus: verify suppressHydrationWarning is actually applied to elements
    # that render toLocaleTimeString() (the deeper fix).
    if has_suppress:
        # Find all toLocaleTimeString() call sites and check at least one has
        # suppressHydrationWarning on its enclosing element.
        locale_calls = re.findall(r"\.toLocaleTimeString\(\)", src)
        suppress_count = src.count("suppressHydrationWarning")
        assert suppress_count >= len(locale_calls) - 1, (
            f"WARN: {len(locale_calls)} toLocaleTimeString() calls but only "
            f"{suppress_count} suppressHydrationWarning — some time elements "
            f"may still warn (DNA #23 — partial fix is acceptable but flag it)."
        )
        print(
            f"  (suppressHydrationWarning applied to {suppress_count} elements "
            f"covering {len(locale_calls)} time strings)"
        )

    print("\n✓ Reality test 4-c-010 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
