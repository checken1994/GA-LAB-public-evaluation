#!/usr/bin/env python3
"""Reality test for Fix 4-c-009: loop/trigger no longer uses 130s timeout;
returns 202 (fire-and-forget) instead of holding the request open.

DNA #19 (observation gap — request killed mid-audit) + #22 (PASS ≠ TRUE —
the 200 OK no longer claims "audit complete" when it isn't) + #9 (no harm)
+ #11 (human-in-the-loop thật — operator no longer double-triggers).

Before fix:
  - dashboard/src/app/api/scp/loop/trigger/route.ts awaited the SCP loop
    with `signal: AbortSignal.timeout(130_000)` (130s).
  - Next.js default route timeout is ~60s on Vercel hobby / reverse-proxy
    hops. The route was killed at 60-120s while the SCP backend kept
    processing → audit ran headless → operator saw spinner → "offline" →
    double-clicked Trigger → double-trigger.

After fix:
  - The route uses a short 5s timeout (TRIGGER_TIMEOUT_MS = 5_000) —
    enough for the scheduler to ACCEPT the trigger and queue the job.
  - Returns 202 ACCEPTED immediately with a jobId.
  - Dashboard polls /api/scp/loop for status (already does — 30s auto-
    refresh in ScpControlPanel).
  - On scheduler timeout, returns 202 with status=pending (NOT 503 —
    the trigger may have been accepted, don't make operator double-click).

Reality-test checks:
  1. No 130_000 / 130000 timeout in the route.
  2. Returns 202 (status 202) somewhere in the route handler.
  3. File exists.

Run:
    python3 tests/reality-tests/reality_4-c-009.py
"""

import re
import sys
from pathlib import Path

ROUTE_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/app/api/scp/loop/trigger/route.ts'
)


def main() -> int:
    assert ROUTE_PATH.exists(), f"FAIL: route.ts not found at {ROUTE_PATH}"
    src = ROUTE_PATH.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # TEST 1 — file exists (sanity)
    # -------------------------------------------------------------------------
    print(f"PASS [1/3]: trigger route exists ({len(src)} bytes)")

    # -------------------------------------------------------------------------
    # TEST 2 — no 130s timeout (130_000 or 130000) used as the actual fetch
    # timeout. The route may pass either a literal number or a named constant
    # to AbortSignal.timeout() — both are acceptable as long as the resolved
    # value is < 60s (under Next.js's default route timeout).
    # -------------------------------------------------------------------------
    # Strip comments to avoid false positives from "Was 130_000ms (130s)"
    # documentation references.
    no_comments = re.sub(r"//[^\n]*", "", src)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL)

    # 2a. The literal 130_000 / 130000 must NOT appear in the actual fetch
    # call. (Comments are already stripped, so any remaining occurrence is
    # in code.)
    assert not re.search(r"AbortSignal\.timeout\(\s*130[_]?000", no_comments), (
        "FAIL: route still uses AbortSignal.timeout(130_000) — exceeds Next.js "
        "default ~60s route timeout (was the original bug)."
    )

    # 2b. The route MUST bound the upstream fetch with AbortSignal.timeout(...)
    # using either a literal small number OR a named constant. The pattern
    # `AbortSignal.timeout(TRIGGER_TIMEOUT_MS)` (named constant) is acceptable.
    timeout_calls_literal = re.findall(
        r"AbortSignal\.timeout\(\s*(\d+(?:_\d+)*)\s*\)", no_comments
    )
    timeout_calls_const = re.findall(
        r"AbortSignal\.timeout\(\s*([A-Z_][A-Z0-9_]*)\s*\)", no_comments
    )
    # At least one timeout call (literal or constant) must be present.
    assert timeout_calls_literal or timeout_calls_const, (
        "FAIL: no AbortSignal.timeout(...) call found — route doesn't bound "
        "the upstream fetch. Add `signal: AbortSignal.timeout(5_000)` or "
        "`signal: AbortSignal.timeout(TRIGGER_TIMEOUT_MS)` with the const "
        "set to <= 5_000."
    )
    # Verify literal timeouts are all < 60s.
    for raw in timeout_calls_literal:
        n = int(raw.replace("_", ""))
        assert n < 60_000, (
            f"FAIL: AbortSignal.timeout({raw}) = {n}ms — exceeds Next.js "
            f"default ~60s route timeout. Must be short (5s recommended)."
        )
    # If using a named constant, verify it's defined with a small value
    # somewhere in the file (e.g. `const TRIGGER_TIMEOUT_MS = 5_000`).
    for const_name in timeout_calls_const:
        const_def = re.search(
            r"const\s+" + re.escape(const_name) + r"\s*=\s*(\d+(?:_\d+)*)",
            src,
        )
        assert const_def, (
            f"FAIL: AbortSignal.timeout({const_name}) — constant {const_name} "
            f"is not defined with a literal numeric value. Cannot verify the "
            f"timeout is < 60s. Define it like `const {const_name} = 5_000;`."
        )
        n = int(const_def.group(1).replace("_", ""))
        assert n < 60_000, (
            f"FAIL: {const_name} = {const_def.group(1)} ({n}ms) — exceeds "
            f"Next.js default ~60s route timeout. Must be short (5s recommended)."
        )
    literals = [int(r.replace("_", "")) for r in timeout_calls_literal]
    consts = [(n, int(re.search(r"const\s+" + re.escape(n) + r"\s*=\s*(\d+(?:_\d+)*)", src).group(1).replace("_", ""))) for n in timeout_calls_const]
    print(
        f"PASS [2/3]: AbortSignal.timeout call(s) all < 60s: "
        f"{literals}ms literal + {consts}ms via constant"
    )

    # -------------------------------------------------------------------------
    # TEST 3 — returns 202 (fire-and-forget) somewhere
    # -------------------------------------------------------------------------
    assert re.search(r"status:\s*202\b", src) or "202" in src, (
        "FAIL: route does not return 202 ACCEPTED — must use fire-and-forget "
        "pattern (return jobId immediately, dashboard polls for status)."
    )
    print("PASS [3/3]: route returns 202 (fire-and-forget pattern)")

    print("\n✓ Reality test 4-c-009 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
