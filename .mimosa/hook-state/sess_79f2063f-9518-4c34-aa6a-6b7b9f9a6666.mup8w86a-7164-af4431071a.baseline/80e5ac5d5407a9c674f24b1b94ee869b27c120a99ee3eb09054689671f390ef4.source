#!/usr/bin/env python3
"""Reality test for Fix 4-c-020: api/route.ts leftover "Hello, world!" scaffold
removed.

DNA #3 (câu hỏi tối hậu — audit the auditor: the dashboard's own self-audit
SA-3 flags this exact pattern, but the file still existed) + #19 (observation
gap — confuses API consumers who hit /api expecting a route listing).

Before fix:
  - dashboard/src/app/api/route.ts:4 `return NextResponse.json({ message: "Hello, world!" });`
  - The dashboard's OWN self-audit (self-audit.ts SA-3) explicitly flags:
    "`api/route.ts` is a leftover 'Hello, world' scaffold, not R7"
  - But the file was never deleted (R8 self-audit documented the issue but
    didn't apply the fix).

After fix:
  - The file is deleted (Next.js default 404 for /api — cleaner than scaffold).
  - OR replaced with a proper API index / redirect.
  - If the file exists, it does NOT contain "Hello, world" or "Hello" scaffold.

Reality-test checks:
  1. The file either does not exist, OR does not contain "Hello, world" /
     "Hello" scaffold message.

Run:
    python3 tests/reality-tests/reality_4-c-020.py
"""

import re
import sys
from pathlib import Path

ROUTE_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/app/api/route.ts'
)


def main() -> int:
    # -------------------------------------------------------------------------
    # TEST 1 — file either deleted OR doesn't contain scaffold message.
    # -------------------------------------------------------------------------
    if not ROUTE_PATH.exists():
        print("PASS [1/1]: api/route.ts deleted (no scaffold route polluting /api)")
        print("\n✓ Reality test 4-c-020 PASSED")
        return 0

    src = ROUTE_PATH.read_text(encoding="utf-8")
    # Strip comments to avoid false positives from docstring mentions.
    no_comments = re.sub(r"//[^\n]*", "", src)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL)

    # The scaffold message is "Hello, world!" or "Hello" + "world".
    scaffold_patterns = [
        r'"Hello,\s*world!"',
        r"'Hello,\s*world!'",
        r'"Hello"',
        r"'Hello'",
        r"`Hello,?\s*world!?`",
        r'message:\s*"Hello',
        r'message:\s*\'Hello',
    ]
    for pat in scaffold_patterns:
        assert not re.search(pat, no_comments), (
            f"FAIL: api/route.ts still contains scaffold message pattern: {pat}\n"
            f"File content (first 500 chars):\n{src[:500]}"
        )
    print("PASS [1/1]: api/route.ts exists but no scaffold 'Hello, world!' message")

    print("\n✓ Reality test 4-c-020 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
