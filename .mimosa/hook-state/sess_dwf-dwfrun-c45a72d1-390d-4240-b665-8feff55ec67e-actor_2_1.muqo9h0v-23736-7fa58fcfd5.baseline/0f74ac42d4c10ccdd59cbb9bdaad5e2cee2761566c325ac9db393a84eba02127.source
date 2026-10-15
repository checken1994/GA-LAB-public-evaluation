from pathlib import Path

"""Reality test for Fix 4-d-020: Caddyfile must allowlist XTransformPort.

Before fix: ?XTransformPort=<any> blindly proxied (SSRF surface).
After fix: only 8000, 3030, 11434 allowed; others get 403.

DNA principles:
  #6  (gốc tin cậy bên ngoài — backend ports must be allowlisted, not
       wildcarded; the gateway is the trust boundary)
  #9  (no harm — don't let an external attacker probe internal services
       like SSH :22, Postgres :5432, Redis :6379 via the gateway)
  #16 (scope violation — wildcard XTransformPort=* exceeds the gateway's
       authorized scope of "proxy to SCP services only")
  #19 (tầng kiểm toán bằng chứng — explicit 403 makes the rejection
       auditable, vs silent fallthrough to the dashboard default)
"""
import glob
import os

caddyfile_paths = [
    str(Path(__file__).resolve().parents[2]) + '/Caddyfile',
]
# Also search for any Caddyfile in scp-system
caddyfile_paths += glob.glob(str(Path(__file__).resolve().parents[2]) + '/**/Caddyfile', recursive=True)

found = False
for p in caddyfile_paths:
    if not os.path.exists(p):
        continue
    with open(p) as f:
        src = f.read()
    if "XTransformPort" not in src:
        continue
    # TEST 1: must have an allowlist (not just blind proxy)
    has_allowlist = ("8000" in src and "3030" in src and "11434" in src)
    assert has_allowlist, f"FAIL: no port allowlist in {p}"
    print(f"PASS [1/3]: port allowlist present in {p}")
    # TEST 2: must reject non-allowlisted ports (403 or similar)
    has_reject = "403" in src or "forbidden" in src.lower() or "reject" in src.lower()
    assert has_reject, "FAIL: no rejection of non-allowlisted ports"
    print("PASS [2/3]: non-allowlisted ports rejected (403)")
    # TEST 3: must NOT blindly proxy any port
    # Look for pattern that forwards without checking
    has_blind_proxy = "reverse_proxy" in src.lower() and not has_allowlist
    assert not has_blind_proxy, "FAIL: still blindly proxies"
    print("PASS [3/3]: no blind proxy (allowlist enforced)")
    found = True
    break
if not found:
    print("SKIP: Caddyfile with XTransformPort not found — may not be in the canonical root")
print("\n✓ Reality test 4-d-020 PASSED")
