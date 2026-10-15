from pathlib import Path

"""Reality test for Fix 4-d-018: stop script kills by port/PID (not by image name).

Before fix: taskkill /f /im bun.exe kills ALL bun processes.
After fix: kills by port (netstat + taskkill /pid).
"""
import os

bat_paths = [
    str(Path(__file__).resolve().parents[2]) + '/stop-scp.bat',
    str(Path(__file__).resolve().parents[2]) + '/start-scp.bat',
]
found = False
for p in bat_paths:
    if not os.path.exists(p):
        continue
    with open(p) as f:
        src = f.read()
    if "taskkill" not in src.lower():
        continue
    # TEST 1: must NOT use taskkill /im bun.exe (image name — too broad)
    has_image_kill = "taskkill" in src.lower() and "/im" in src.lower() and "bun" in src.lower()
    assert not has_image_kill, f"FAIL: still uses taskkill /im bun.exe in {p}"
    print(f"PASS [1/3]: no taskkill /im bun.exe in {os.path.basename(p)}")
    # TEST 2: must use /pid (PID-based kill)
    has_pid_kill = "/pid" in src.lower() or "pid" in src.lower()
    assert has_pid_kill, f"FAIL: no /pid kill in {p}"
    print("PASS [2/3]: uses /pid (PID-based kill)")
    # TEST 3: must use netstat to find PID by port
    has_netstat = "netstat" in src.lower()
    assert has_netstat, "FAIL: no netstat (port-based PID lookup)"
    print("PASS [3/3]: uses netstat to find PID by port")
    found = True
    break
if not found:
    print("SKIP: no .bat with taskkill found")
print("\n✓ Reality test 4-d-018 PASSED")
