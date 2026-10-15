"""HISTORICAL — explicit domain_override routing patch (2026-08-17), already applied and retired.

This one-off patch edited scp/runtime/judge_parts/judgeroute_mixin.py, judgecore_mixin.py and scp/api_server.py so a trusted caller could pin the judge domain.
The change has long since been absorbed into the product; the
executable read-modify-write logic was retired in audit round 2
(2026-10-01) to remove dead one-off patch-tool write surfaces
(dead-path sweep A11 M-03; no test or product module imports this
file — verified 2026-10-01).

The original body remains in git history:
    git log --follow -p -- tools/patch_explicit_domain_override.py
"""
print("tools/patch_explicit_domain_override.py is a retired historical patch; nothing to do.")
