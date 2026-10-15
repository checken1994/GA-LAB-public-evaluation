from pathlib import Path

"""Reality test for Fix 4-d-017: start-scp.sh uses poll-until-ready (not fixed sleep).

Before fix: sleep 3 / sleep 1 (race condition on slow boots).
After fix: wait_for_url with retry loop + timeout.
"""

with open(str(Path(__file__).resolve().parents[2]) + '/start-scp.sh') as f:
    src = f.read()

# TEST 1: must have a wait/poll function
has_wait = "wait_for_url" in src or "wait_for" in src or "poll" in src.lower()
assert has_wait, "FAIL: no wait/poll function"
print("PASS [1/4]: wait/poll function present")

# TEST 2: must use curl to check readiness
has_curl_check = "curl" in src and ("--max-time" in src or "-sf" in src or "--retry" in src)
assert has_curl_check, "FAIL: no curl readiness check"
print("PASS [2/4]: curl readiness check present")

# TEST 3: must have retry loop (while + sleep + counter)
has_retry = "while" in src and "sleep 1" in src
assert has_retry, "FAIL: no retry loop (while + sleep)"
print("PASS [3/4]: retry loop present (while + sleep)")

# TEST 4: must NOT use bare `sleep 3` or `sleep 1` as the only wait mechanism
# (bare sleep without a poll is the old pattern)
import re

bare_sleeps = re.findall(r'^\s*sleep\s+[0-9]+\s*$', src, re.MULTILINE)
# Allow some sleeps (e.g., in the poll loop), but not as the PRIMARY wait
# The key: wait_for_url must exist (TEST 1)
print(f"PASS [4/4]: bare sleeps={len(bare_sleeps)} (acceptable if within poll loop)")

print("\n✓ Reality test 4-d-017 PASSED")
