"""HISTORICAL — judge_async domain_override threading patch (2026-08-17), already applied and retired.

This one-off patch edited scp/runtime/judge.py to add ``domain_override`` to judge_async() and forward it to the JudgeCoreMixin judge call.
The change has long since been absorbed into the product; the
executable read-modify-write logic was retired in audit round 2
(2026-10-01) to remove dead one-off patch-tool write surfaces
(dead-path sweep A11 M-03; no test or product module imports this
file — verified 2026-10-01).

The original body remains in git history:
    git log --follow -p -- tools/patch_domain_async.py
"""
print("tools/patch_domain_async.py is a retired historical patch; nothing to do.")
