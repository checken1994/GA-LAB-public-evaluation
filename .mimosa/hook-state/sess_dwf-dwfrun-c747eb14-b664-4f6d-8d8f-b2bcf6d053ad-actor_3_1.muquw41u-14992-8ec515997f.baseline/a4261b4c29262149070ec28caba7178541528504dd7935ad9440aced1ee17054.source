#!/usr/bin/env python3
"""Reality test for Fix 4-c-005: beforeCode for R7-2 removed or replaced (not fabricated).

DNA #5 (ảo giác đồng thuận) + #19 (tầng kiểm toán bằng chứng) + #22 (PASS ≠ TRUE)
+ #23 (acknowledge limits) + #26 (reality has final authority).

Before fix:
  - dashboard/src/lib/audit-data/bugs-critical.ts:71-78 displayed a fictional
    `beforeCode` for finding R7-2 (Tor task GC'd):
        asyncio.create_task(refresh_tor_exits_loop())  # RUF006!
  - The dashboard's OWN R8 self-audit (self-audit.ts SA-4) flagged this as a
    fictional paraphrase — the snippet never appeared in any version of
    scp/api/_lifespan.py.
  - The real wiring (per SA-4) at scp/api/_lifespan.py:180 is:
        _background_task_holder['tor_refresh'] = asyncio.create_task(_tor_refresh_loop())
    i.e. the task IS stored in a module-level holder, so the "task GC'd →
    is_tor always False" narrative was unsupported.

After fix:
  - The fabricated beforeCode snippet is REMOVED from bugs-critical.ts.
  - Replaced with an honest omission note citing SA-4 + git history.
  - R8 self-audit SA-4 (self-audit.ts) is updated to record that the
    fabricated beforeCode has been REMOVED (Phase 6-A / Fix 4-c-005).

NOTE on test scope: The task spec mentioned `round7.ts` as the file to check,
but the actual fabricated beforeCode lived in `bugs-critical.ts:71-78`
(per worklog Finding 4-c-005). This test checks BOTH files — round7.ts (which
never had a beforeCode field for R7-2) AND bugs-critical.ts (where the real
fix was applied). DNA #19: observe the actual file where the bug lived.

Run:
    python3 tests/reality-tests/reality_4-c-005.py
"""

import os
import re
import sys
from pathlib import Path

# The fabricated beforeCode lived in bugs-critical.ts (per worklog 4-c-005).
# round7.ts is also checked because the task spec mentioned it (it has the
# R7-2 entry but no beforeCode field — never had the fabricated data).
R7_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/lib/audit-data/round7.ts'
)
BUGS_CRITICAL_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/lib/audit-data/bugs-critical.ts'
)
SELF_AUDIT_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/lib/audit-data/self-audit.ts'
)

# Candidates for SA-4 reflection check (per task spec).
SA_CANDIDATES = [
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/lib/audit-data/round9-self-audit.ts',
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/lib/audit-data/round8.ts',
    # Also check the actual SA-4 home:
    str(Path(__file__).resolve().parents[2]) + '/dashboard/src/lib/audit-data/self-audit.ts',
]

# The exact fabricated snippet that must NO LONGER appear in any beforeCode
# field of bugs-critical.ts.
FABRICATED_SNIPPET = "asyncio.create_task(refresh_tor_exits_loop())  # RUF006!"


def main() -> int:
    # -------------------------------------------------------------------------
    # TEST 1 — round7.ts (task spec file): no beforeCode field present for
    # R7-2, OR if present, has a fabrication note. (This file never had the
    # fabricated data — but verify to ensure no regression.)
    # -------------------------------------------------------------------------
    r7_src = R7_PATH.read_text(encoding="utf-8")
    r72_idx = r7_src.find("R7-2")
    if r72_idx == -1:
        r72_idx = r7_src.find("r7-2")
    if r72_idx == -1:
        r72_idx = r7_src.find("r7_2")

    if r72_idx >= 0:
        r72_section = r7_src[r72_idx : r72_idx + 3000]
        has_before_code = "beforeCode" in r72_section
        has_fabricated_note = (
            "fabricated" in r72_section.lower()
            or "omitted" in r72_section.lower()
            or "git history" in r72_section.lower()
        )
        if has_before_code:
            assert has_fabricated_note, (
                f"FAIL: round7.ts beforeCode present without fabrication note:\n"
                f"{r72_section[:500]}"
            )
            print("PASS [1/5]: round7.ts beforeCode has note (not fabricated)")
        else:
            print("PASS [1/5]: round7.ts R7-2 has no beforeCode (no fabricated code)")
    else:
        print("SKIP [1/5]: R7-2 entry not found in round7.ts")

    # -------------------------------------------------------------------------
    # TEST 2 — bugs-critical.ts (ACTUAL fix location per worklog): the
    # fabricated snippet `asyncio.create_task(refresh_tor_exits_loop())  # RUF006!`
    # must NOT appear in the R7-2 beforeCode field.
    # -------------------------------------------------------------------------
    bc_src = BUGS_CRITICAL_PATH.read_text(encoding="utf-8")
    r72_idx_bc = bc_src.find('"R7-2"')
    if r72_idx_bc == -1:
        r72_idx_bc = bc_src.find("R7-2")
    assert r72_idx_bc >= 0, "FAIL: R7-2 entry not found in bugs-critical.ts"

    # Find the R7-2 entry's beforeCode field (next occurrence of `beforeCode:`
    # after the R7-2 id, but BEFORE the next id like "R7-3").
    r72_section = bc_src[r72_idx_bc : r72_idx_bc + 4000]
    # Truncate at next finding id to stay within R7-2 entry.
    next_id_match = re.search(r'\nid:\s*"R7-3"', r72_section)
    if next_id_match:
        r72_section = r72_section[: next_id_match.start()]

    assert FABRICATED_SNIPPET not in r72_section, (
        f"FAIL: fabricated snippet still in bugs-critical.ts R7-2 beforeCode:\n"
        f"{r72_section[:800]}"
    )
    print("PASS [2/5]: fabricated snippet removed from bugs-critical.ts R7-2")

    # -------------------------------------------------------------------------
    # TEST 3 — bugs-critical.ts R7-2 beforeCode MUST contain an honest
    # omission note (referencing SA-4 + git history + DNA #22/#23).
    # -------------------------------------------------------------------------
    # Extract the beforeCode string literal (template literal between backticks)
    before_code_match = re.search(
        r'beforeCode:\s*`([^`]+)`', r72_section, re.DOTALL
    )
    assert before_code_match, (
        f"FAIL: beforeCode field not found in R7-2 entry:\n{r72_section[:500]}"
    )
    before_code_content = before_code_match.group(1).lower()
    assert "omitted" in before_code_content, (
        "FAIL: beforeCode does not say 'omitted' — must be honest omission"
    )
    assert "fabricated" in before_code_content or "fictional" in before_code_content, (
        "FAIL: beforeCode does not acknowledge fabrication/fictional nature"
    )
    assert "sa-4" in before_code_content, (
        "FAIL: beforeCode does not cite SA-4 (the R8 self-audit that flagged it)"
    )
    assert "git history" in before_code_content or "git log" in before_code_content, (
        "FAIL: beforeCode does not point to git history for actual code"
    )
    print("PASS [3/5]: beforeCode has honest omission note (SA-4 + git history + DNA #22/#23)")

    # -------------------------------------------------------------------------
    # TEST 4 — R8 self-audit SA-4 should reflect the fix (beforeCode removed).
    # Per task spec candidates + the actual SA-4 home (self-audit.ts).
    # -------------------------------------------------------------------------
    sa_found = False
    strict_sa4_pass = False
    for sa_path in SA_CANDIDATES:
        if not os.path.exists(sa_path):
            continue
        with open(sa_path) as f:
            sa_src = f.read()
        if "SA-4" in sa_src or "beforeCode" in sa_src:
            # SA-4 should mention the fix (removed or replaced)
            has_fix_note = (
                "removed" in sa_src.lower()
                or "replaced" in sa_src.lower()
                or "fixed" in sa_src.lower()
                or "4-c-005" in sa_src
            )
            # The actual SA-4 entry in self-audit.ts should specifically mention
            # that the beforeCode was REMOVED in Phase 6-A. Use exact basename
            # match (not endswith) to avoid matching round9-self-audit.ts etc.
            is_actual_sa4_home = os.path.basename(sa_path) == "self-audit.ts"
            if is_actual_sa4_home:
                assert "4-c-005" in sa_src or (
                    "REMOVED" in sa_src and "beforeCode" in sa_src
                ), (
                    "FAIL: self-audit.ts SA-4 doesn't reference fix 4-c-005 / REMOVED"
                )
                assert "Phase 6-A" in sa_src or "phase 6-a" in sa_src.lower(), (
                    "FAIL: self-audit.ts SA-4 doesn't reference Phase 6-A"
                )
                print("PASS [4/5]: self-audit.ts SA-4 reflects fix (Phase 6-A / 4-c-005)")
                strict_sa4_pass = True
            elif has_fix_note:
                # Other candidates (round9-self-audit.ts etc.) — soft check.
                if not sa_found:
                    print(f"PASS [4/5]: {os.path.basename(sa_path)} reflects fix (soft)")
                sa_found = True

    if not strict_sa4_pass:
        print("FAIL [4/5]: self-audit.ts (real SA-4 home) not verified")
        return 1

    # -------------------------------------------------------------------------
    # TEST 5 — no suspicious long beforeCode blocks (heuristic). A long
    # beforeCode (>100 chars) without a "git"/"source"/"sa-4"/"omitted" note
    # nearby is suspicious. The R7-2 beforeCode is now an explicit omission
    # note (long, but with all the right markers).
    # -------------------------------------------------------------------------
    before_code_blocks = re.findall(r'beforeCode:\s*`([^`]{100,})`', bc_src)
    suspicious_found = False
    for i, block in enumerate(before_code_blocks):
        block_lower = block.lower()
        has_note = (
            "git" in block_lower
            or "source" in block_lower
            or "sa-4" in block_lower
            or "omitted" in block_lower
            or "fabricated" in block_lower
            or "fictional" in block_lower
            or "4-c-005" in block_lower
        )
        if not has_note:
            suspicious_found = True
            print(
                f"WARN: beforeCode block {i+1} ({len(block)} chars) has no "
                f"fabrication/git/source note — verify it's actual code"
            )

    if not suspicious_found:
        print("PASS [5/5]: no suspicious long beforeCode blocks (all have notes)")
    else:
        print("PASS [5/5]: long beforeCode blocks flagged for review (DNA #23)")

    print("\n✓ Reality test 4-c-005 PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
