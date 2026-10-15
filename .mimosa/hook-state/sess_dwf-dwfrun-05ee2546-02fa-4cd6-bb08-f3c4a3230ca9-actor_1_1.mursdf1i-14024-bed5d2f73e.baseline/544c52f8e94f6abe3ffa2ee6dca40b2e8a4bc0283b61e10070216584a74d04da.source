"""HISTORICAL — judge antibody check() call repair (2026-08), already applied and retired.

This one-off patch edited scp/runtime/judge_parts/judge_phases.py to replace the removed check_all() call with the current DomainAntibodySystem.check() interface and JSON-safe metadata.
The change has long since been absorbed into the product; the
executable read-modify-write logic was retired in audit round 2
(2026-10-01) to remove dead one-off patch-tool write surfaces
(dead-path sweep A11 M-03; no test or product module imports this
file — verified 2026-10-01).

The original body remains in git history:
    git log --follow -p -- scripts/fix_judge_antibody_block.py
"""
print("scripts/fix_judge_antibody_block.py is a retired historical patch; nothing to do.")
