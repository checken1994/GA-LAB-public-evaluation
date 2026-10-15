"""HISTORICAL — browser worker cleanup patch (2026-09), already applied and retired.

This one-off patch injected the `_spawned_browsers` registry plus an
atexit-registered `_cleanup_browsers` handler into
scp/web_control/browser_session.py, so spawned browser subprocesses are
terminated when the parent process exits. The target was verified patched
on the live tree (the registry list, the atexit hook and the
`_spawned_browsers.append(p)` call all exist in
scp/web_control/browser_session.py); the executable read-modify-write
logic was retired afterwards to eliminate its unjailled variable-path
write surface (Mimosa HIGH: path traversal).

The original body remains in git history:
    git log --follow -p -- tools/fix_browser.py
"""
print("tools/fix_browser.py is a retired historical patch; nothing to do.")
