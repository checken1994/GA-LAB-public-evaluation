"""HISTORICAL — kb_evolve.sqlite R37 row-count diagnostic (2026-08), already applied and retired.

This one-off patch edited data/kb_evolve.sqlite to print per-table row counts during the R37 knowledge-base sweep.
The change has long since been absorbed into the product; the
executable read-modify-write logic was retired in audit round 2
(2026-10-01) to remove dead one-off patch-tool write surfaces
(dead-path sweep A11 M-03; no test or product module imports this
file — verified 2026-10-01).

The original body remains in git history:
    git log --follow -p -- scripts/diagnostics/count_kb_r37.py
"""
# [SEC-S4] Guard: this retired stub performs no file I/O, no SQL execution,
# and no deserialization — the historical read-modify-write surface was
# removed in audit round 2 (2026-10-01), so the containment guard below is
# the absence of any executable side effect.
print("scripts/diagnostics/count_kb_r37.py is a retired historical patch; nothing to do.")
