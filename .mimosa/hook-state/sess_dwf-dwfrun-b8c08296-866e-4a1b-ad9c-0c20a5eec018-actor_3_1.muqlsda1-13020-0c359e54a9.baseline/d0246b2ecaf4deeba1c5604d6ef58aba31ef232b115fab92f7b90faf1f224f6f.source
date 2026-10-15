"""HISTORICAL — web-fallback consistency patch (2026-08), already applied and retired.

This one-off patch edited scp/api_server_parts/helpers.py (speculative/web_fallback fields) so web-fallback state stayed consistent across ask paths.
The change has long since been absorbed into the product; the
executable read-modify-write logic was retired in audit round 2
(2026-10-01) to remove dead one-off patch-tool write surfaces
(dead-path sweep A11 M-03; no test or product module imports this
file — verified 2026-10-01).

The original body remains in git history:
    git log --follow -p -- scripts/maintenance/patch_web_fallback_consistency.py
"""
print("scripts/maintenance/patch_web_fallback_consistency.py is a retired historical patch; nothing to do.")
