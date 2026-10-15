"""HISTORICAL — top-context-only patch (2026-08-17), already applied and retired.

This one-off patch edited _extractive_rag_answer() body assembly in scp/api_server.py to use only the highest-ranked chunk for answer text.
The change has long since been absorbed into the product; the
executable read-modify-write logic was retired in audit round 2
(2026-10-01) to remove dead one-off patch-tool write surfaces
(dead-path sweep A11 M-03; no test or product module imports this
file — verified 2026-10-01).

The original body remains in git history:
    git log --follow -p -- tools/patch_rag_top_context_only_v1.py
"""
print("tools/patch_rag_top_context_only_v1.py is a retired historical patch; nothing to do.")
