#!/usr/bin/env python3
"""RETIRED reality test 4-c-022 — target deleted by legitimate dead-code cleanup.

RETIREMENT (S17, 2026-09-13 — explicit, not silent):

This test verified the SA-4 correction (DNA #22 recursion level 3): that the
R7-2 fix — the `_tor_refresh_tasks: set` + `.add(_tor_task)` +
`add_done_callback(...discard)` GC-prevention pattern for the TOR refresh
task — genuinely existed in `scp/api/_lifespan.py:393-445`, grounding the
dashboard's SA-4 "CORRECTION" entry (dashboard/src/lib/audit-data/self-audit.ts)
in backend reality.

Reality changed: `scp/api/_lifespan.py` (764 LOC, dead code — no importer)
was deleted by the B2 dead-code cleanup:

  - 4e935a7 "chore(cleanup): remove dead _lifespan, relocate canary fixture,
    drop tier3bak (B2)"
  - c1dcde4 "chore(cleanup): commit B2 deletions missed from 4e935a7
    (V-TB follow-up — _lifespan dead-code + legacy tier3bak ...)"

The live lifespan is now `scp/api_server_parts/lifespan.py`, which does NOT
contain the TOR refresh loop or the `_tor_refresh_tasks` pattern: the R7-2
fix was removed together with the dead file that hosted it (repo-wide grep at
retirement time finds the pattern only inside tests/reality-tests/ scripts).
The check therefore has no living target. Repointing it to
`scp/api_server_parts/lifespan.py` would manufacture a PASS against a pattern
that no longer exists — so the test is retired instead, openly, per the
mandatory contract that a green result may never be manufactured.

FAIL-CLOSED GUARDS (this stub refuses to stay green if its premise breaks):
  1. If `scp/api/_lifespan.py` reappears -> FAIL: the retirement premise is
     void; restore/rewrite the original test from git history.
  2. If the `_tor_refresh_tasks` pattern reappears anywhere under `scp/` ->
     FAIL: that is a new R7-2-style fix and deserves a NEW reality test.

RUNNER INTEGRATION: listed in RETIRED_REALITY_TESTS in
tests/run-reality-tests.sh — skipped VISIBLY ("⊘ RETIRED"), never silently.
The original test body remains recoverable from git history (the commit that
retired it).

KNOWN STALE CITATION (flagged, out of S17 scope): the dashboard SA-4 entry
(self-audit.ts) still cites `scp/api/_lifespan.py` as a historical audit
record. Updating that audit narrative is a dashboard-data decision recorded
in reports/expert-panel/S-B3-print-logging.md (mục S17) for the owner.

Run:
    python3 tests/reality-tests/reality_4-c-022.py
"""

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    lifespan_path = root / "scp" / "api" / "_lifespan.py"

    # Guard 1 — the deleted file must stay deleted.
    assert not lifespan_path.exists(), (
        "RETIRED 4-c-022 premise void: scp/api/_lifespan.py exists again. "
        "The original SA-4 reality check must be restored/rewritten from git "
        "history instead of riding on this retirement stub."
    )

    # Guard 2 — the R7-2 pattern must not have been reintroduced anywhere
    # under product code (scp/). A reappearance means a new fix exists that
    # needs a NEW reality test, not a silent green from this stub.
    pattern_hits: list[str] = []
    for py in sorted((root / "scp").rglob("*.py")):
        try:
            src = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "_tor_refresh_tasks" in src or "tor_refresh_loop" in src:
            pattern_hits.append(str(py.relative_to(root)))
    assert not pattern_hits, (
        "RETIRED 4-c-022 premise void: the R7-2 `_tor_refresh_tasks` pattern "
        f"reappeared in product code: {pattern_hits}. Write a NEW reality "
        "test covering it; do not rely on this retired stub."
    )

    print("RETIRED [4-c-022]: SA-4 target scp/api/_lifespan.py was deleted as")
    print("  dead code (B2 cleanup: commits 4e935a7 + c1dcde4); the R7-2")
    print("  `_tor_refresh_tasks` fix no longer exists anywhere under scp/,")
    print("  so the check has no living target. See this file's docstring.")
    print("  Fail-closed guards verified: target still absent, pattern still")
    print("  absent under scp/ — retirement premise still holds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
