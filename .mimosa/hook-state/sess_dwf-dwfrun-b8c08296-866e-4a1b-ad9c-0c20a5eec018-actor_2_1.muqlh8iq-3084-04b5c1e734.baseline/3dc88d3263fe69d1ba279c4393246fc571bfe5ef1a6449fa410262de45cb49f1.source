#!/usr/bin/env python3
"""Reality test for Fix 4-c-007: closing-section download buttons no longer dead.

DNA #11 (human-in-the-loop thật — every control must lead somewhere real)
+ #22 (PASS ≠ TRUE) + #19 (observation gap — silent 404) + #26 (reality test).

Before fix:
  - dashboard/src/components/dashboard/closing-section.tsx had two <a> tags:
      href="/download/scp-dna-audit-round9-full.zip"
      href="/download/SCP_DNA_AUDIT_ROUND9_CHANGES.md"
  - dashboard/public/download/ directory does NOT exist
  - Clicking returned Next.js 404 silently. The dashboard's OWN
    bugs-dead-controls component warns about this exact "decorative control"
    anti-pattern — but the dashboard itself shipped decorative download
    controls. Meta-bug: auditor's blind spot.

After fix:
  - All `/download/...` hrefs removed from closing-section.tsx.
  - Replaced with links to real, reachable resources:
      /api/scp/status  (live JSON, always exists)
      /api/audit       (live JSON, always exists)
  - Plus a note pointing operators to repository-relative reports/ and scp/
    paths at the canonical root.

Run:
    python3 tests/reality-tests/reality_4-c-007.py
"""

import re
import sys
from pathlib import Path

CLOSING_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/components/dashboard/closing-section.tsx'
)


def main() -> int:
    assert CLOSING_PATH.exists(), f"FAIL: closing-section.tsx not found at {CLOSING_PATH}"
    src = CLOSING_PATH.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # TEST 1 — file exists (sanity)
    # -------------------------------------------------------------------------
    print(f"PASS [1/3]: closing-section.tsx exists ({len(src)} bytes)")

    # -------------------------------------------------------------------------
    # TEST 2 — no `/download/` href in the JSX.
    # Strip comments first (// line comments and /* */ block comments) so that
    # documentation references like `// BEFORE: had <a href="/download/...">`
    # don't trigger false positives.
    # -------------------------------------------------------------------------
    no_comments = re.sub(r"//[^\n]*", "", src)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL)

    download_hrefs = re.findall(r'href\s*=\s*["\'](/download/[^"\']*)["\']', no_comments)
    assert not download_hrefs, (
        f"FAIL: closing-section.tsx still has /download/ hrefs (dead controls):\n"
        f"{download_hrefs}"
    )
    print("PASS [2/3]: no /download/ href in closing-section.tsx (dead controls removed)")

    # -------------------------------------------------------------------------
    # TEST 3 — replacement links point to real, reachable resources
    # (repository-relative reports/ and scp/ note)
    # -------------------------------------------------------------------------
    api_links = re.findall(r'href\s*=\s*["\'](/api/[^"\']*)["\']', no_comments)
    assert api_links, (
        "FAIL: closing-section.tsx has no /api/... links to replace the dead "
        "/download/ buttons — operator has no live data source"
    )
    # Must mention the repository evidence/source tree without a machine-specific
    # absolute path. The UI now points to reports/ and scp/ at the canonical root.
    assert "reports/" in src and "scp/" in src, (
        "FAIL: closing-section.tsx does not reference repository reports/ and "
        "scp/ paths — operator has no path to the audit data"
    )
    print(f"PASS [3/3]: replacement links present ({len(api_links)} /api/* links + repo-relative evidence reference)")

    print("\n✓ Reality test 4-c-007 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
