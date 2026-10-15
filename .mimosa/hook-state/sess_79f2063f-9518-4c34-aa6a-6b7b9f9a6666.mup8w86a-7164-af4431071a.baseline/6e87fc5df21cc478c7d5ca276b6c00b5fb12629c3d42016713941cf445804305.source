from pathlib import Path

"""Reality test for Fix 4-d-015: SCP_INTERNAL_URL + LOOP_SCHEDULER_URL in .env.example.

Before fix: env vars referenced by dashboard but not documented.
After fix: both in .env.example with documented defaults.

DNA principles:
  #16 (học nói phạm vi — env vars must be documented in the template that
       operators copy; silent fallback hides scope of behavior)
  #19 (tầng kiểm toán bằng chứng — env.example is the documented evidence
       layer for what env vars the system reads)
  #22 (PASS ≠ TRUE — defaults "work locally" but the gap is invisible until
       a non-local deploy; documenting them closes the silent-failure gap)
"""
import os

env_example_paths = [
    str(Path(__file__).resolve().parents[2]) + '/.env.example',
    str(Path(__file__).resolve().parents[2]) + '/scp/.env.example',
]
found = False
for p in env_example_paths:
    if not os.path.exists(p):
        continue
    with open(p) as f:
        src = f.read()
    # TEST 1: SCP_INTERNAL_URL must be in .env.example
    assert "SCP_INTERNAL_URL" in src, f"FAIL: SCP_INTERNAL_URL not in {p}"
    print(f"PASS [1/3]: SCP_INTERNAL_URL in {os.path.basename(p)}")
    # TEST 2: LOOP_SCHEDULER_URL must be in .env.example
    assert "LOOP_SCHEDULER_URL" in src, f"FAIL: LOOP_SCHEDULER_URL not in {p}"
    print(f"PASS [2/3]: LOOP_SCHEDULER_URL in {os.path.basename(p)}")
    # TEST 3: documented defaults present
    assert "127.0.0.1:8000" in src or "localhost:8000" in src or "127.0.0.1:8000" in src or "localhost:8000" in src, "FAIL: no canonical default for SCP_INTERNAL_URL"
    assert "127.0.0.1:3030" in src or "localhost:3030" in src, "FAIL: no default for LOOP_SCHEDULER_URL"
    print("PASS [3/3]: documented defaults present")
    found = True
    break
if not found:
    # Maybe .env.example doesn't exist — check .env itself (less ideal)
    assert False, "FAIL: no .env.example found in expected locations"
print("\n✓ Reality test 4-d-015 PASSED")
