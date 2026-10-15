"""HISTORICAL — M1..M6 migration script (2026-09), already applied and retired.

This one-off migration applied the R1..R6 remediation patches: mojibake
cleanup in scp/api, websocket auth hardening in chat.py, the zero_cost
reference removal from spec/, the audit_r8/audit_r9 relocation to
docs/audit_history/, the scp/tests -> tests/internal move, and the
requirements.txt additions. Every target was verified applied on main; the
executable write/patch logic was retired afterwards to eliminate its
unjailled variable-path write surface (Mimosa HIGH: path traversal).

The original body remains in git history:
    git log --follow -p -- tools/run_m3.py
"""
print("tools/run_m3.py is a retired historical migration; nothing to do.")
