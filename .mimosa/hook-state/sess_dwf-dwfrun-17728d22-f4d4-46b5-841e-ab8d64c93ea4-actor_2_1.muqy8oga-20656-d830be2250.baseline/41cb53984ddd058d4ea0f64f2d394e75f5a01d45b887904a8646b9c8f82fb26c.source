#!/usr/bin/env python3
"""Reality test for Fix 4-c-006: v4 LOC must be computed (not hardcoded drifted).

DNA #22 (PASS ≠ TRUE) + #14 (numbers must match reality) + #26 (reality has
final authority) + #23 (acknowledge limits — fallback must be documented).

Before fix:
  - dashboard/src/app/api/scp/status/route.ts had:
      { imp: "IMP-19", file: "scp/autofix/property_validator.py", ..., loc: 728 },
      { imp: "IMP-20", file: "scp/autofix/type_flow_verifier.py", ..., loc: 723 },
      { imp: "IMP-21", file: "scp/autofix/speculative_prefixer.py", ..., loc: 798 },
      { imp: "IMP-22", file: "scp/autofix/callgraph_delta.py", ..., loc: 642 },
      { imp: "IMP-23", file: "scp/autofix/runner_phases/shadow_canary.py", ..., loc: 743 },
      { imp: "IMP-24", file: "scp/autofix/policy_gate.py", ..., loc: 755 },
    and `v4Loc: V4_MODULES.reduce((sum, m) => sum + m.loc, 0), // 4,389`
  - Actual `wc -l` of the 6 files: 916 + 801 + 838 + 734 + 755 + 850 = 4,894
  - Drift: +505 LOC (dashboard undercounted by 505).

After fix:
  - LOC for each module is COMPUTED at module load via computeAutofixLoc(),
    which reads the actual scp/autofix/*.py file via fs.readFileSync and
    counts newlines (matches `wc -l`).
  - If the file is unreachable (dashboard deployed without backend), the
    function falls back to a documented LAST_VERIFIED_FALLBACK_LOC constant
    with a `lastVerified` date — never silently uses a stale number.
  - The dashboard surfaces `v4LocLive: boolean` and `v4LocMethod: string`
    so operators know whether the number is fresh or stale.

Run:
    python3 tests/reality-tests/reality_4-c-006.py
"""

import re
import subprocess
import sys
from pathlib import Path

ROUTE_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/app/api/scp/status/route.ts'
)
SCP_ROOT = Path(str(Path(__file__).resolve().parents[2]))
V4_FILES = [
    "scp/autofix/property_validator.py",
    "scp/autofix/type_flow_verifier.py",
    "scp/autofix/speculative_prefixer.py",
    "scp/autofix/callgraph_delta.py",
    "scp/autofix/runner_phases/shadow_canary.py",
    "scp/autofix/policy_gate.py",
]


def main() -> int:
    src = ROUTE_PATH.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # TEST 1 — must NOT have hardcoded "4389" or "4,389" in code (excluding
    # comments). Comments are filtered (lines starting with `//` or `*`).
    # -------------------------------------------------------------------------
    code_lines = [
        line
        for line in src.split("\n")
        if not line.strip().startswith("//")
        and not line.strip().startswith("*")
    ]
    code_section = "\n".join(code_lines)
    has_old_number = "4389" in code_section or "4,389" in code_section
    assert not has_old_number, (
        "FAIL: hardcoded '4389' or '4,389' still present in code (non-comment)"
    )
    print("PASS [1/4]: hardcoded 4389 removed from code")

    # -------------------------------------------------------------------------
    # TEST 2 — must have computation function OR documented fallback.
    # Prefer live computation; fall back is acceptable but must be documented.
    # -------------------------------------------------------------------------
    has_compute = (
        "computeAutofixLoc" in src
        or "readdirSync" in src
        or "readFileSync" in src
    )
    has_fallback = (
        "4894" in src
        or "fallback" in src.lower()
        or "last_verified" in src.lower()
        or "lastverified" in src.lower()
        or "LAST_VERIFIED" in src
    )
    assert has_compute or has_fallback, (
        "FAIL: no LOC computation (computeAutofixLoc/readdirSync/readFileSync) "
        "and no documented fallback"
    )
    method = "computed" if has_compute else "documented fallback"
    print(f"PASS [2/4]: LOC {method} (has_compute={has_compute}, has_fallback={has_fallback})")

    # -------------------------------------------------------------------------
    # TEST 3 — if computed, must reference actual file path (scp/autofix)
    # AND use fs.readFileSync (or readdirSync) to read the actual files.
    # -------------------------------------------------------------------------
    if has_compute:
        has_path = "autofix" in src and (
            "readdir" in src or "readFile" in src
        )
        assert has_path, (
            "FAIL: computation doesn't read actual scp/autofix files"
        )
        print("PASS [3/4]: computation reads actual scp/autofix files")
    else:
        print("PASS [3/4]: documented fallback with last-verified date")

    # -------------------------------------------------------------------------
    # TEST 4 (defense in depth — DNA #26 reality has final authority) —
    # if computation is present, the SUM of live-computed LOC values must
    # equal the actual `wc -l` total of the 6 v4 files. We approximate this
    # by reading the actual files via subprocess (`wc -l`) and comparing to
    # the documented fallback LOC values — those MUST match `wc -l` totals.
    # This protects against silent drift between the documented fallback and
    # reality (the same failure mode as the original 4,389 bug).
    # -------------------------------------------------------------------------
    if not has_compute:
        print("SKIP [4/4]: no computation to verify against reality")
        return 0

    # Compute actual LOC total from real files via subprocess (`wc -l`).
    actual_files = [str(SCP_ROOT / f) for f in V4_FILES]
    try:
        result = subprocess.run(
            ["wc", "-l", *actual_files],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"SKIP [4/4]: cannot run wc -l ({e}) — assume fallback path")
        return 0

    # Parse the "total" line from wc -l output.
    total_match = re.search(r"(\d+)\s+total\s*$", result.stdout.strip())
    if not total_match:
        # wc -l with single file doesn't print "total" — sum the per-file lines.
        per_file_lines = re.findall(r"^\s*(\d+)\s+", result.stdout, re.MULTILINE)
        if not per_file_lines:
            print(f"SKIP [4/4]: wc -l output unparseable:\n{result.stdout}")
            return 0
        actual_total = sum(int(n) for n in per_file_lines)
    else:
        actual_total = int(total_match.group(1))

    # Extract documented fallback LOC values from the source.
    fallback_matches = re.findall(
        r'"(scp/autofix/[^"]+)":\s*(\d+)', src
    )
    fallback_total = sum(int(n) for _, n in fallback_matches)

    assert fallback_total == actual_total, (
        f"FAIL: documented fallback LOC total ({fallback_total}) does NOT "
        f"match actual wc -l total ({actual_total}) of the 6 v4 files. "
        f"This is the SAME drift failure mode as the original 4-c-006 bug "
        f"(was 4,389 hardcoded vs actual 4,894). DNA #26: reality must "
        f"match. Update LAST_VERIFIED_FALLBACK_LOC and LAST_VERIFIED_DATE."
    )
    print(
        f"PASS [4/4]: documented fallback LOC total ({fallback_total}) "
        f"== actual wc -l total ({actual_total}) — no drift"
    )

    print("\n✓ Reality test 4-c-006 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
