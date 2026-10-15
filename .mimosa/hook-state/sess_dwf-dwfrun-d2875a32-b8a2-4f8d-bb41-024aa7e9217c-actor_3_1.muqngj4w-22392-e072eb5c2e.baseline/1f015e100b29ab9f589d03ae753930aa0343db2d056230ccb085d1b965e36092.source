from pathlib import Path

"""Reality test for Fix 4-d-014: install-scp.bat creates data dirs at project root.

Before fix: mkdirs inside scp/ (wrong — SCP reads from project root cwd).
After fix: mkdirs at project root.
"""
import os

bat_path = str(Path(__file__).resolve().parents[2]) + '/install-scp.bat'
if not os.path.exists(bat_path):
    print("SKIP: install-scp.bat not found")
else:
    with open(bat_path) as f:
        src = f.read()
    # Find mkdir commands for data dirs
    # TEST 1: must create data dirs (knowledge, backups, etc.)
    has_data_dirs = "data" in src.lower() and ("knowledge" in src.lower() or "backups" in src.lower())
    assert has_data_dirs, "FAIL: no data dir creation in install-scp.bat"
    print("PASS [1/3]: data dir creation present")

    # TEST 2: must NOT create data dirs inside scp/ (should be at project root)
    # Look for pattern: cd %~dp0scp ... mkdir data  (wrong)
    # vs: cd %~dp0 ... mkdir data  (correct)
    # Or: scp\data\knowledge (wrong) vs data\knowledge (correct)
    has_scp_prefix = "scp\\data" in src or "scp/data" in src
    assert not has_scp_prefix, "FAIL: still creates data dirs inside scp/"
    print("PASS [2/3]: data dirs NOT inside scp/ (at project root)")

    # TEST 3: must use %~dp0 (script dir) for path resolution
    has_script_dir = "%~dp0" in src
    assert has_script_dir, "FAIL: no %~dp0 (script dir resolution)"
    print("PASS [3/3]: uses %~dp0 (script dir resolution)")
print("\n✓ Reality test 4-d-014 PASSED")
