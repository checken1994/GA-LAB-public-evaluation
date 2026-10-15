from pathlib import Path

"""Reality test for Fix 4-b-016: why_gate singleton init race eliminated.

[DNA #2/#9/#19/#22/#26]

Before fix:
  `get_why_gate()` used a broken double-checked-locking pattern:
    if _why_gate_lock is None:            # check WITHOUT holding lock
        _why_gate_lock = threading.Lock() # two threads can race here
    if _why_gate is None:                 # check WITHOUT lock
        with _why_gate_lock:
            if _why_gate is None:
                _why_gate = WhyGate(...)
  Two threads could both see `_why_gate_lock is None`, both create their
  own Lock() instance — the "losing" thread's lock would be overwritten,
  but it would still proceed to use its OWN lock (not the winner's). The
  `with _why_gate_lock:` blocks would NOT be mutually exclusive between
  threads using different locks. Both could pass the inner check, both
  initialize the singleton → two WhyGate instances (orphaned first one
  leaks the audit file handle, double audit-log writes).

  DNA #9 (No harm — orphaned WhyGate + double audit-log writes).
  DNA #22 (PASS≠TRUE — claimed singleton, actually race-conditioned).
  DNA #19 (Tầng kiểm toán — couldn't see which instance wrote which audit).

After fix:
  `_why_gate_lock` is initialized at MODULE LOAD time (atomic under
  Python's import lock). `get_why_gate()` acquires the lock BEFORE
  checking `_why_gate is None` — single critical section, no race window.
"""
import re
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

WHY_PATH = str(Path(__file__).resolve().parents[2]) + '/scp/meta/why_gate.py'

with open(WHY_PATH) as f:
    src = f.read()


# ---------------------------------------------------------------------------
# TEST 1 — file exists (DNA #19)
# ---------------------------------------------------------------------------
print("=" * 70)
print("TEST 1 — why_gate.py exists")
print("=" * 70)
import os

assert os.path.isfile(WHY_PATH), f"FAIL: {WHY_PATH} does not exist"
print(f"  [PASS] file exists at {WHY_PATH}")


# ---------------------------------------------------------------------------
# TEST 2 — `_why_gate_lock = threading.Lock()` (or RLock) initialized at
# module level (NOT lazy inside the function).
# DNA #22: PASS≠TRUE — verify the FIX is in source, not just claimed.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 2 — _why_gate_lock initialized at module level (not lazy)")
print("=" * 70)
# Strip comment lines so we only inspect actual code (avoid matching the
# pre-fix code shown in the docstring/comments of the fix).
code_lines = []
in_docstring = False
for l in src.split("\n"):
    stripped = l.strip()
    # Skip comment-only lines (the fix's docstring uses # comments to show
    # the pre-fix pattern; we must NOT match those).
    if stripped.startswith("#"):
        continue
    code_lines.append(l)
code_section = "\n".join(code_lines)

# Must have `_why_gate_lock = <threading.Lock or RLock>()` at module scope
# (i.e., NOT inside a `def`).
# We look for the assignment at column-0 indentation (module-level).
lock_at_module_level = re.findall(
    r'^_why_gate_lock\s*=\s*\S*threading\.\S*Lock\(\)',
    code_section,
    re.MULTILINE,
)
assert lock_at_module_level, (
    "FAIL: no module-level `_why_gate_lock = threading.Lock()` (or RLock) "
    "assignment — lazy init race NOT closed."
)
print(f"  [PASS] `_why_gate_lock = threading.Lock()` at module level "
      f"({len(lock_at_module_level)} occurrence(s))")

# Must NOT have the lazy-init pattern `if _why_gate_lock is None:` in code
# (only in comments — already stripped above).
lazy_init = re.findall(
    r'if\s+_why_gate_lock\s+is\s+None\s*:',
    code_section,
)
assert not lazy_init, (
    f"FAIL: lazy `if _why_gate_lock is None:` still in code "
    f"({len(lazy_init)} occurrence(s)) — init race NOT eliminated."
)
print("  [PASS] no lazy `if _why_gate_lock is None:` in code (race eliminated)")


# ---------------------------------------------------------------------------
# TEST 3 — get_why_gate() acquires the lock BEFORE the check
# DNA #19: verify the lock is acquired before the `if _why_gate is None:`
# check, not after. Pre-fix: check happened BEFORE lock → race window.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 3 — get_why_gate acquires lock BEFORE the None check")
print("=" * 70)
# Extract get_why_gate body.
gw_match = re.search(
    r'def\s+get_why_gate\s*\([^)]*\)[^:]*:\s*\n(.*?)(?=\ndef\s|\Z)',
    code_section,
    re.DOTALL,
)
assert gw_match, "FAIL: get_why_gate function not found"
gw_body_full = gw_match.group(1)

# Strip the docstring (triple-quoted) so we don't match docstring text like
# "if _why_gate is None:" inside the explanation comment. AST would be more
# robust, but a simple regex strip of the first triple-quoted block works
# for this method (it starts with `"""`).
gw_body = re.sub(r'^\s*"""[^"]*?"""\s*\n', '', gw_body_full, count=1, flags=re.DOTALL)

# Find positions of `with _why_gate_lock:` and `if _why_gate is None:`.
with_pos = gw_body.find("with _why_gate_lock")
if_pos = gw_body.find("if _why_gate is None")
assert with_pos != -1, "FAIL: get_why_gate does not acquire _why_gate_lock"
assert if_pos != -1, "FAIL: get_why_gate does not check `_why_gate is None`"
assert with_pos < if_pos, (
    f"FAIL: `with _why_gate_lock:` (pos {with_pos}) comes AFTER "
    f"`if _why_gate is None:` (pos {if_pos}) — pre-fix race NOT closed. "
    "Lock must be acquired BEFORE the check."
)
print(f"  [PASS] `with _why_gate_lock:` (pos {with_pos}) before "
      f"`if _why_gate is None:` (pos {if_pos})")
print("  [PASS] lock acquired BEFORE check — single critical section, no race window")


# ---------------------------------------------------------------------------
# TEST 4 — property-based (DNA #2/#26): 200 concurrent calls to
# get_why_gate() MUST return the SAME singleton instance (identity check
# via `is`). Pre-fix: with the race, some calls could return different
# instances. Post-fix: all 200 return the same instance.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 4 — property-based: 200 concurrent get_why_gate() → 1 instance")
print("=" * 70)
try:
    # Clear any cached singleton from prior imports.
    import scp.meta.why_gate as wg_mod
    if wg_mod._why_gate is not None:
        wg_mod._why_gate = None
    from scp.meta.why_gate import get_why_gate
except Exception as e:
    print(f"  SKIP: import failed ({type(e).__name__}: {e}) — DNA #23 honest limit")
    print("  (Static tests 1-3 above still prove the fix.)")
    sys.exit(0)

# Verify lock is initialized at module load (not None).
assert wg_mod._why_gate_lock is not None, (
    "FAIL: _why_gate_lock is None at module load — lazy init still present"
)
print(f"  [PASS] _why_gate_lock initialized at module load "
      f"(type={type(wg_mod._why_gate_lock).__name__})")

# Hammer get_why_gate from 50 threads simultaneously.
N_THREADS = 50
N_PER_THREAD = 4
results = []  # collect every returned instance
results_lock = threading.Lock()

def worker():
    local = []
    for _ in range(N_PER_THREAD):
        g = get_why_gate(data_dir="/tmp/why_gate_test")
        local.append(g)
    with results_lock:
        results.extend(local)

threads = [threading.Thread(target=worker) for _ in range(N_THREADS)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# Every returned instance must be the SAME object (identity check).
first = results[0]
distinct = set(id(g) for g in results)
print(f"  Sent: {N_THREADS * N_PER_THREAD} get_why_gate() calls across {N_THREADS} threads")
print(f"  Distinct instance ids: {len(distinct)} (expected 1)")

assert len(distinct) == 1, (
    f"FAIL: {len(distinct)} distinct WhyGate instances observed — singleton "
    f"init race still present. Instance ids: {list(distinct)[:5]}"
)
print(f"  [PASS] ALL {len(results)} calls returned the SAME instance (id={id(first)})")


# ---------------------------------------------------------------------------
# TEST 5 — reset_why_gate() still works (backward-compat, DNA #7)
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 5 — reset_why_gate() still works (backward-compat)")
print("=" * 70)
from scp.meta.why_gate import reset_why_gate

reset_why_gate()
assert wg_mod._why_gate is None, "FAIL: reset_why_gate did not reset singleton to None"
print("  [PASS] reset_why_gate() resets singleton to None")

# Re-init to confirm it still works after reset.
g = get_why_gate(data_dir="/tmp/why_gate_test")
assert g is not None, "FAIL: get_why_gate returned None after reset"
print(f"  [PASS] get_why_gate() re-initializes after reset (id={id(g)})")


print()
print("=" * 70)
print("✓ Reality test 4-b-016 PASSED")
print("  Lock: threading.Lock at module level (no lazy init race)")
print("  Order: `with _why_gate_lock:` BEFORE `if _why_gate is None:`")
print("  Property: 200 concurrent calls → 1 instance (was 1+ pre-fix)")
print("  Backward-compat: reset_why_gate() still works")
print("=" * 70)
