"""HISTORICAL — test polling-wait patch (2026-09), applied/superseded and retired.

This one-off patch converted fixed time.sleep() waits in
tests/T01_boot/test_flow_01_boot_background_scp_standard.py into
condition-polling loops. The essential fix landed in the same commit via
the `_poll_wait` helper that the live test now uses; the tool's remaining
search/replace bodies no longer reflect the restructured test file, so
re-running it could only corrupt the test (it would even drop an
assertion message). The script is referenced by no test, script or CI
job, so its unjailled variable-path write surface was retired
(Mimosa HIGH: path traversal).

The original body remains in git history:
    git log --follow -p -- tools/patch_polling.py
"""
print("tools/patch_polling.py is a retired historical patch; nothing to do.")
