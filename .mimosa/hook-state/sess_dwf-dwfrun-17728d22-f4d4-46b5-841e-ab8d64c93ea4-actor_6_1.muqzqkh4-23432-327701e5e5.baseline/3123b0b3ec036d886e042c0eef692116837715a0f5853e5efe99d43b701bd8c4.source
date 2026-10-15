#!/usr/bin/env python3
"""Reality test for Fix 4-c-019: favicon must be local, not external CDN.

DNA #6 (gốc tin cậy bên ngoài — không phụ thuộc nguồn bên ngoài) + #19
(tầng kiểm toán bằng chứng) + #22 (PASS ≠ TRUE).

Before fix:
  - dashboard/src/app/layout.tsx:34
        icon: "https://z-cdn.chatglm.cn/z-ai/static/logo.svg"
  - External CDN dependency for favicon. Referrer leak (every page load tells
    the CDN which page was visited). Single point of failure. Broken offline /
    air-gapped deployments (common for security-sensitive SCP deployments).
  - dashboard/public/logo.svg EXISTS but was unused — divergent: code pointed
    external when local existed.

After fix:
  - icon: "/logo.svg" — served from dashboard/public/logo.svg (verified exists).
  - No external CDN reference in layout.tsx. Self-hosted, offline-safe.

Honest limit (DNA #23): this is a static-source reality test (Tier A). Runtime
verification (Tier B) would require: start the dashboard, disconnect internet,
load the page in a browser, confirm favicon loads from /logo.svg (network tab
shows 200 for /logo.svg and NO request to z-cdn.chatglm.cn). Left to runtime
verification phase.

Run:
    python3 tests/reality-tests/reality_4-c-019.py
"""

import re
import sys
from pathlib import Path

LAYOUT_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/app/layout.tsx'
)
LOGO_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/public/logo.svg'
)


def main() -> int:
    src = LAYOUT_PATH.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # TEST 1 — layout.tsx must NOT reference the external CDN for favicon.
    # The CDN host z-cdn.chatglm.cn must be COMPLETELY GONE from the file
    # (not just in a comment — for a privacy/air-gap issue, even a comment
    # referencing the external URL is misleading and should be gone).
    # -------------------------------------------------------------------------
    assert "z-cdn.chatglm.cn" not in src, (
        "FAIL: external CDN host 'z-cdn.chatglm.cn' still referenced in "
        "layout.tsx (must be completely removed, including comments)"
    )
    print("PASS: no external CDN reference in layout.tsx")

    # -------------------------------------------------------------------------
    # TEST 2 — icon must point to local /logo.svg. Accept either single or
    # double quotes.
    # -------------------------------------------------------------------------
    has_local_icon = (
        'icon: "/logo.svg"' in src
        or "icon: '/logo.svg'" in src
        or 'icon:"/logo.svg"' in src
        or "icon:'/logo.svg'" in src
    )
    assert has_local_icon, (
        "FAIL: icons.icon does not point to '/logo.svg' "
        "(must be `icon: \"/logo.svg\"`)"
    )
    print("PASS: icons.icon points to local /logo.svg")

    # -------------------------------------------------------------------------
    # TEST 3 — logo.svg must actually exist in dashboard/public/. A reference
    # to a non-existent file would 404 at runtime (just as broken as the CDN
    # dependency it replaced — DNA #22 PASS ≠ TRUE).
    # -------------------------------------------------------------------------
    assert LOGO_PATH.exists(), (
        f"FAIL: {LOGO_PATH} does not exist — the new icon path would 404"
    )
    # Sanity: the logo file must not be empty (an empty file would also 404-ish
    # or render as a broken image).
    size = LOGO_PATH.stat().st_size
    assert size > 0, (
        f"FAIL: {LOGO_PATH} is empty (0 bytes) — would render as broken image"
    )
    print(f"PASS: {LOGO_PATH} exists ({size} bytes)")

    # -------------------------------------------------------------------------
    # TEST 4 (defense in depth) — no OTHER external CDN references for icons.
    # Look for `icon:` or `icons:` blocks with http(s):// URLs in code.
    # -------------------------------------------------------------------------
    code_lines = [
        line
        for line in src.split("\n")
        if not line.strip().startswith("//")
        and not line.strip().startswith("*")
    ]
    code_section = "\n".join(code_lines)
    # Find any `icon:` assignment that points to http(s)://
    external_icon_re = re.compile(
        r'icon\s*:\s*["\']https?://[^"\']+["\']'
    )
    external_matches = external_icon_re.findall(code_section)
    assert not external_matches, (
        f"FAIL: external http(s) URL still used for icon: {external_matches}"
    )
    print("PASS: no external http(s) icon URL in code")

    print("\n✓ Reality test 4-c-019 PASSED (4/4 assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
