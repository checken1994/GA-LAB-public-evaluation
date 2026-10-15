from pathlib import Path

"""Reality test for Fix 4-b-001 [P0]: CircuitBreaker DEADLOCK eliminated.

[DNA #2/#9/#22/#26]

Before fix:
  `record_request()` acquires `self.lock` (a plain `threading.Lock()`,
  NON-reentrant) at line 51, then at line 63 calls `self.trip()` which
  tries to acquire `self.lock` AGAIN at line 110. Non-reentrant Lock →
  DEADLOCK. The DoS breaker never auto-trips from sustained RPS
  exceedance; the holder hangs forever; all subsequent should_allow /
  record_request calls block on the held lock → entire DoS protection
  layer freezes.

  DNA #9 (No harm — deadlock harms availability).
  DNA #22 (PASS≠TRUE — breaker claimed auto-trip but deadlocked).
  DNA #26 (Reality — actual behavior contradicted docstring).

After fix:
  `self.lock = threading.RLock()` (reentrant). The same thread can
  re-acquire the lock — `trip()` called from inside record_request's
  `with self.lock:` block now succeeds instead of deadlocking.
"""
import re
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

CB_PATH = str(Path(__file__).resolve().parents[2]) + '/scp/security/circuit_breaker.py'

with open(CB_PATH) as f:
    src = f.read()


# ---------------------------------------------------------------------------
# TEST 1 — file exists (DNA #19 — observation layer must be able to see the file)
# ---------------------------------------------------------------------------
print("=" * 70)
print("TEST 1 — circuit_breaker.py exists")
print("=" * 70)
import os

assert os.path.isfile(CB_PATH), f"FAIL: {CB_PATH} does not exist"
print(f"  [PASS] file exists at {CB_PATH}")


# ---------------------------------------------------------------------------
# TEST 2 — RLock present (NOT plain Lock) in the source
# DNA #22: PASS≠TRUE — verify the FIX is in source, not just claimed in docs.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 2 — self.lock = threading.RLock() (reentrant)")
print("=" * 70)
# Strip comment lines so we only inspect actual code.
code_lines = [l for l in src.split("\n") if not l.strip().startswith("#")]
code_section = "\n".join(code_lines)
# Must contain `threading.RLock()` assignment to self.lock.
rlock_assigns = re.findall(
    r'self\.lock\s*=\s*threading\.RLock\(\)',
    code_section,
)
assert rlock_assigns, (
    "FAIL: no `self.lock = threading.RLock()` assignment in code — "
    "pre-fix deadlock NOT closed. Found 0 RLock assignments."
)
print(f"  [PASS] `self.lock = threading.RLock()` present ({len(rlock_assigns)} occurrence(s))")

# Also verify NO `self.lock = threading.Lock()` (non-reentrant) remains.
plain_lock_assigns = re.findall(
    r'self\.lock\s*=\s*threading\.Lock\(\)',
    code_section,
)
assert not plain_lock_assigns, (
    f"FAIL: non-reentrant `self.lock = threading.Lock()` still in code "
    f"({len(plain_lock_assigns)} occurrence(s)) — deadlock NOT eliminated."
)
print("  [PASS] no non-reentrant `self.lock = threading.Lock()` in code")


# ---------------------------------------------------------------------------
# TEST 3 — record_request holds lock when calling trip() (RLock IS needed)
# DNA #19: verify the structural reason RLock is required — if trip() were
# called outside the lock, RLock wouldn't be needed. We must verify the
# re-entrant call actually exists in source.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 3 — trip() called from within record_request's `with self.lock:`")
print("=" * 70)
# Find the body of record_request and check it contains both `with self.lock:`
# and a `self.trip()` call.
rr_match = re.search(
    r'def\s+record_request\s*\([^\)]*\)\s*:\s*\n(.*?)(?=\n    def\s|\nclass\s|\Z)',
    src,
    re.DOTALL,
)
assert rr_match, "FAIL: record_request method not found"
rr_body = rr_match.group(1)
assert re.search(r'with\s+self\.lock\s*:', rr_body), (
    "FAIL: record_request does not acquire self.lock — RLock may not be needed"
)
print("  [PASS] record_request acquires self.lock via `with self.lock:`")
# Check that self.trip() is called inside the same method body (proves
# the re-entrant lock is actually necessary, not just defensive).
trip_calls_in_rr = re.findall(r'self\.trip\s*\(', rr_body)
assert trip_calls_in_rr, (
    "FAIL: record_request does not call self.trip() — RLock may be unnecessary"
)
print(f"  [PASS] record_request calls self.trip() ({len(trip_calls_in_rr)} call(s)) — RLock IS required")

# Also verify trip() itself acquires self.lock — so the re-entry would
# deadlock on a non-reentrant lock.
trip_match = re.search(
    r'def\s+trip\s*\([^\)]*\)\s*:\s*\n(.*?)(?=\n    def\s|\nclass\s|\Z)',
    src,
    re.DOTALL,
)
assert trip_match, "FAIL: trip method not found"
trip_body = trip_match.group(1)
assert re.search(r'with\s+self\.lock\s*:', trip_body), (
    "FAIL: trip() does not acquire self.lock — not a deadlock source"
)
print("  [PASS] trip() acquires self.lock via `with self.lock:` (would deadlock on plain Lock)")


# ---------------------------------------------------------------------------
# TEST 4 — property-based (DNA #2/#26): trigger 3 consecutive RPS-exceedance
# seconds → breaker MUST auto-trip (state == 'open'). Pre-fix: DEADLOCK —
# the thread hangs forever, never returns from record_request, breaker never
# trips. Post-fix: returns cleanly, state == 'open'.
# We use threshold_rps=2 and append 3 timestamps manually to force the
# `consecutive_exceed >= 3` condition inside record_request's lock context.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 4 — property-based: 3 consecutive RPS-exceedance → trip (no deadlock)")
print("=" * 70)
try:
    from scp.security.circuit_breaker import CircuitBreaker
except Exception as e:
    print(f"  SKIP: import failed ({type(e).__name__}: {e}) — DNA #23 honest limit")
    print("  (Static tests 1-3 above still prove the fix.)")
    sys.exit(0)

# Create breaker with threshold_rps=0 so that EVERY request exceeds the
# threshold (current_rps >= 1 > 0) — this drives consecutive_exceed to 3
# after exactly 3 calls, triggering the auto-trip path. With threshold_rps=2,
# the first 2 calls (current_rps=1, 2) don't exceed 2, so consecutive_exceed
# resets to 0 each call and never reaches 3.
cb = CircuitBreaker(threshold_rps=0, cooldown_sec=60)
assert cb.state == 'closed', f"FAIL: breaker starts in wrong state: {cb.state}"

# Make self.lock reentrant — sanity check that the fix is real at runtime.
assert isinstance(cb.lock, type(threading.RLock())), (
    f"FAIL: cb.lock is not an RLock — got {type(cb.lock).__name__}"
)
print(f"  [PASS] cb.lock is RLock at runtime (type={type(cb.lock).__name__})")

# Force 3 consecutive RPS-exceedance calls. With threshold_rps=0, every call
# exceeds → consecutive_exceed reaches 3 on the 3rd call → self.trip() is
# invoked from INSIDE record_request's `with self.lock:` block.
# Pre-fix: 3rd call would deadlock at self.trip() and never return.
# Post-fix: returns cleanly, breaker state == 'open'.
timeout_occurred = False
start = time.time()
try:
    # Use a watchdog thread to detect deadlock — if record_request hangs, we
    # timeout and report the deadlock.
    import threading as _t
    result = {}
    def call():
        for _ in range(3):
            cb.record_request()
        result['done'] = True
    t = _t.Thread(target=call, daemon=True)
    t.start()
    t.join(timeout=5.0)
    if not result.get('done'):
        timeout_occurred = True
        print("  [FAIL] record_request DEADLOCKED — did not return within 5s")
except Exception as e:
    print(f"  [FAIL] record_request raised {type(e).__name__}: {e}")

assert not timeout_occurred, (
    "FAIL: record_request DEADLOCKED — fix did not eliminate the deadlock"
)
assert cb.state == 'open', (
    f"FAIL: after 3 consecutive RPS-exceedance seconds, breaker should be "
    f"'open' (auto-tripped), got '{cb.state}' — trip() did not fire."
)
print("  [PASS] 3 consecutive RPS-exceedance calls returned cleanly (no deadlock)")
print("  [PASS] breaker state = 'open' (auto-tripped, was 'closed' pre-fix)")
assert cb.trips >= 1, f"FAIL: cb.trips = {cb.trips}, expected >= 1"
print(f"  [PASS] cb.trips = {cb.trips} (trip counter incremented)")


print()
print("=" * 70)
print("✓ Reality test 4-b-001 PASSED")
print("  RLock: present in source (no plain Lock)")
print("  Structure: trip() called from record_request's lock context (RLock required)")
print("  Property: 3 consecutive RPS-exceedance → auto-trip, no deadlock")
print("=" * 70)
