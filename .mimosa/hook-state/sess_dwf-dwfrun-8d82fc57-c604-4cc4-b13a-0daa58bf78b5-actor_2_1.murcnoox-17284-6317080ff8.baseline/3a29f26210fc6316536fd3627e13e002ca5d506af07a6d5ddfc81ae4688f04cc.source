#!/usr/bin/env python3
"""Reality test for Fix 4-c-018: dead GitHub button removed from header.

DNA #11 (human-in-the-loop thật — every control must lead somewhere real)
+ #19 (observation gap — button LOOKS functional but isn't).

Before fix:
  - dashboard/src/components/layout/header.tsx:107 had `<a href="https://github.com">`
    with aria-label="Repository".
  - Clicking opened GitHub's homepage, not a repo. The aria-label was a
    false promise.

After fix:
  - The GitHub button is removed (no public repo exists for this project).
  - OR replaced with a meaningful link (worklog, scp-dna skill docs).
  - No bare `href="https://github.com"` (no org/repo path) remains.

Reality-test checks:
  1. No bare `href="https://github.com"` (without an org/repo path) in header.tsx.
  2. The `Github` lucide-react import is removed (button is gone).

Run:
    python3 tests/reality-tests/reality_4-c-018.py
"""

import re
import sys
from pathlib import Path

HEADER_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/components/layout/header.tsx'
)


def main() -> int:
    assert HEADER_PATH.exists(), f"FAIL: header.tsx not found at {HEADER_PATH}"
    src = HEADER_PATH.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # TEST 1 — no bare `https://github.com` link (without org/repo path).
    # A bare github.com link goes to the homepage, not a repo.
    # Allow `https://github.com/org/repo` (with a path) — that's a real repo link.
    # -------------------------------------------------------------------------
    # Strip comments.
    no_comments = re.sub(r"//[^\n]*", "", src)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL)

    # Find all href="https://github.com..." occurrences.
    github_hrefs = re.findall(r'href\s*=\s*["\'](https://github\.com[^"\']*)["\']', no_comments)
    bare_github = [u for u in github_hrefs if u.rstrip("/") in ("https://github.com", "https://github.com/")]
    # Also catch href="https://github.com" with no path.
    bare_github += [u for u in github_hrefs if re.match(r"^https://github\.com/?$", u)]
    assert not bare_github, (
        f"FAIL: header.tsx still has bare https://github.com links (no org/repo):\n"
        f"{bare_github}"
    )
    print("PASS [1/2]: no bare https://github.com link in header.tsx")

    # -------------------------------------------------------------------------
    # TEST 2 — Github lucide-react import removed (button is gone).
    # If the import is still there, the Github icon is being rendered somewhere
    # — the button may have been re-added.
    # -------------------------------------------------------------------------
    # Strip import lines and check.
    import_section = re.findall(r'^import\s+.*?from\s+["\']lucide-react["\']', src, re.MULTILINE)
    has_github_import = any("Github" in line for line in import_section)
    assert not has_github_import, (
        "FAIL: header.tsx still imports `Github` from lucide-react — the dead "
        "GitHub button is still rendered (or its icon is). Remove the import "
        "and the button."
    )
    print("PASS [2/2]: Github icon import removed from header.tsx (button gone)")

    print("\n✓ Reality test 4-c-018 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
