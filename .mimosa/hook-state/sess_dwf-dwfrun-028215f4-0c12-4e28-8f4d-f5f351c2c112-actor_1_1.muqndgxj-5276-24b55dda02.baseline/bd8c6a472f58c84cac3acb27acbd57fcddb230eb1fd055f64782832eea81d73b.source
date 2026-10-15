"""HISTORICAL — mojibake cleanup sweep (2026-09), already applied and retired.

This one-off sweep replaced double-encoded UTF-8 mojibake sequences with
em-dashes across scp/api_server_parts/_ask_impl.py, scp/api/chat.py,
scp/api/webhook.py, scp/api/routes/v105_routes.py,
scp/api_server_parts/lifespan.py, scp/api_server_parts/_async_fact_check.py
and COMPREHENSIVE_AUDIT_REPORT.md. A verification pass over the live tree
found zero remaining occurrences of the tool's mojibake list; the
executable read-modify-write logic was retired afterwards to eliminate
its unjailled variable-path write surface (Mimosa HIGH: path traversal).

The original body remains in git history:
    git log --follow -p -- tools/fix_mojibake.py
"""
print("tools/fix_mojibake.py is a retired historical patch; nothing to do.")
