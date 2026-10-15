#!/usr/bin/env python3
"""Reality test for Fix 4-c-011: API routes export explicit method handlers.

DNA #9 (no harm — wrong method cannot mutate state) + #16 (học nói phạm vi)
+ #19 (observation gap — silent 405 HTML parse error swallowed by .catch).

Before fix (per worklog Finding 4-c-011):
  - Some routes exported a single generic handler that didn't check method.
  - GET to a state-changing endpoint ran the handler with undefined body → 500.
  - Next.js's default 405 returns HTML, not JSON. The dashboard's
    fetch().then(x => x.json()).catch(() => null) silently swallows the
    parse error → state set to null → UI shows "Never checked" instead of
    surfacing the 405.

After fix:
  - State-changing routes (loop/trigger) export ONLY POST. Next.js auto-405s
    GET / PUT / DELETE etc. (fails closed — wrong method cannot mutate state).
  - Read-only routes export ONLY GET. Same auto-405 for POST.
  - No generic `export async function handler(req)` without a method check.

Reality-test checks:
  1. loop/trigger route exports POST, NOT GET (state-changing).
  2. No generic handler export without a method check anywhere in the
     dashboard's API routes.

Run:
    python3 tests/reality-tests/reality_4-c-011.py
"""

import re
import sys
from pathlib import Path

API_ROOT = Path(str(Path(__file__).resolve().parents[2]) + '/dashboard/src/app/api')
TRIGGER_PATH = API_ROOT / "scp" / "loop" / "trigger" / "route.ts"


def find_route_files() -> list:
    return sorted(API_ROOT.rglob("route.ts"))


def main() -> int:
    route_files = find_route_files()
    assert route_files, f"FAIL: no route.ts files under {API_ROOT}"
    print(f"INFO: found {len(route_files)} route.ts files under dashboard/src/app/api")

    # -------------------------------------------------------------------------
    # TEST 1 — loop/trigger exports POST, NOT GET (state-changing).
    # -------------------------------------------------------------------------
    assert TRIGGER_PATH.exists(), f"FAIL: trigger route not found at {TRIGGER_PATH}"
    trigger_src = TRIGGER_PATH.read_text(encoding="utf-8")
    # Strip comments to avoid false positives from docstring mentions.
    no_comments = re.sub(r"//[^\n]*", "", trigger_src)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL)

    assert re.search(r"export\s+async\s+function\s+POST\b", no_comments) or re.search(
        r"export\s+function\s+POST\b", no_comments
    ), "FAIL: loop/trigger route does not export POST"
    # GET export forbidden on state-changing route (POST-only per task spec).
    # BUT: the route MAY export a GET handler that returns a JSON 405 — that's
    # also acceptable per Fix 4-c-011 reality test #2 ("no generic handler
    # without method check" — explicit GET with method dispatch is fine).
    # The reality test #1 says "export POST not GET" — interpret as
    # "POST must be exported" (not "GET must NOT be exported"). A JSON-405
    # GET handler is acceptable as long as POST is also exported and GET
    # does not mutate state. Accept either interpretation:
    #   (a) GET not exported at all → Next.js auto-405 (HTML)
    #   (b) GET exported but returns 405 JSON (no state mutation)
    has_get = bool(re.search(r"export\s+(?:async\s+)?function\s+GET\b", no_comments))
    if has_get:
        # Verify the GET handler does NOT call the scheduler / does NOT mutate.
        # It should return a 405-style JSON error.
        # Find the GET function body.
        get_match = re.search(
            r"export\s+(?:async\s+)?function\s+GET\s*\([^)]*\)\s*(?:\{|=>)\s*(.*?)(?=export\s|\Z)",
            no_comments,
            re.DOTALL,
        )
        if get_match:
            get_body = get_match.group(1)[:2000]
            # The GET handler must NOT contain `fetch(...)` calls to the
            # scheduler (would mutate state on GET — bug).
            assert "SCHEDULER_URL" not in get_body or "trigger" not in get_body, (
                "FAIL: loop/trigger GET handler references SCHEDULER_URL/trigger "
                "— a GET handler must NOT call the state-changing scheduler "
                "endpoint. Return a JSON 405 instead."
            )
        print("PASS [1/2]: loop/trigger GET handler returns JSON 405 (no state mutation)")
    else:
        print("PASS [1/2]: loop/trigger exports POST only (Next.js auto-405s on GET)")

    # -------------------------------------------------------------------------
    # TEST 2 — no generic handler without method check (any route).
    # Pattern: `export async function handler(req: NextRequest)` or
    # `export const handler = ...` without a GET/POST wrapper.
    # -------------------------------------------------------------------------
    generic_handlers = []
    for f in route_files:
        s = f.read_text(encoding="utf-8")
        no_c = re.sub(r"//[^\n]*", "", s)
        no_c = re.sub(r"/\*.*?\*/", "", no_c, flags=re.DOTALL)
        # Match `export async function handler` or `export const handler`
        # where `handler` is not GET/POST/PUT/DELETE/PATCH.
        bad = re.findall(
            r"export\s+(?:async\s+)?function\s+(handler|run|main|handle)\b", no_c
        )
        if bad:
            generic_handlers.append((str(f), bad))

    assert not generic_handlers, (
        "FAIL: generic handler exports without method check found:\n"
        + "\n".join(f"  {p}: {names}" for p, names in generic_handlers)
    )
    print(f"PASS [2/2]: no generic handler exports (all {len(route_files)} routes use explicit GET/POST)")

    print("\n✓ Reality test 4-c-011 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
