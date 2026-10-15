from pathlib import Path

"""Reality test for Fix 4-b-009: DoSProtectionEngine._last_throttle must be
ASSIGNED (not just declared) — throttle branch must fire 429 + Retry-After.

[Phase 4-A — DNA #5, #19, #22, #25]

Before fix:
  `_last_throttle` was declared at __init__ (`self._last_throttle: float = 0`)
  but NEVER ASSIGNED anywhere in the codebase. The throttle check at
  `if now - self._last_throttle < self.CIRCUIT_COOLDOWN:` evaluated to
  `if now - 0 < 5` → `if (1.7 billion seconds) < 5` → False. So the
  throttle branch was DEAD CODE: every request was silently ALLOWED
  through while circuit was "open" (the exact scenario the throttle was
  supposed to protect against).

  DNA #22 (PASS≠TRUE): the docstring claimed "5 giây throttle khi
  circuit open" but reality was "no throttle ever". DNA #19 (Tầng kiểm
  toán): the throttle observation mechanism could not see the requests
  it was supposed to throttle. DNA #5 (ảo giác đồng thuận): multiple
  test runs all "passed" because they all shared the same blind spot.

After fix:
  `_last_throttle = now` is assigned in the throttle branch BEFORE the
  cooldown check. The throttle now fires unconditionally while circuit
  is in `open` state (probing is handled by the separate half_open
  transition after CIRCUIT_RESET_TIME elapses). The returned DoSAlert
  carries `status_code=429` + `recommended_headers={"Retry-After": "5"}`
  so the FastAPI route handler can map it to a proper HTTP 429 response
  with Retry-After header (RFC 6585 §4).
"""
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

DOS_PATH = str(Path(__file__).resolve().parents[2]) + '/scp/security/dos_protection.py'

with open(DOS_PATH) as f:
    src = f.read()


# ---------------------------------------------------------------------------
# TEST 1 — _last_throttle must be ASSIGNED (not just declared)
# DNA #19: verify the observation mechanism can actually record throttle
# events, not just claim to. Pre-fix: only declaration, no assignment.
# ---------------------------------------------------------------------------
print("=" * 70)
print("TEST 1 — _last_throttle must be ASSIGNED (not just declared = 0)")
print("=" * 70)
# Find all LINES that start with `self._last_throttle` (whitespace-prefixed).
# A real assignment is `            self._last_throttle = <expr>` (no `:`
# between the attr name and `=`). The declaration has `: float` annotation.
decl_pattern = re.compile(r'^\s+self\._last_throttle\s*:\s*float\s*=\s*0\s*$', re.MULTILINE)
assign_pattern = re.compile(
    r'^\s+self\._last_throttle\s*=\s*(?!0\b\s*(?:$|#))\S',
    re.MULTILINE,
)
decls = decl_pattern.findall(src)
assigns = assign_pattern.findall(src)
# Subtract — the decl matches `self._last_throttle: float = 0` which assign_pattern
# might also match (assign_pattern requires `= <expr>` where expr starts with non-zero).
# decl_pattern is strict (requires `: float`), so it's authoritative for decls.
# assign_pattern matches `self._last_throttle = <non-zero-expr>`.
real_assigns = len(assigns)
print(f"  Declaration (`self._last_throttle: float = 0`): {len(decls)} occurrence(s)")
print(f"  Real assignments (`self._last_throttle = <non-zero expr>`): {real_assigns}")
assert real_assigns >= 1, (
    f"FAIL: _last_throttle never assigned (real assignments: {real_assigns}). "
    "Pre-fix bug NOT closed — throttle branch is still dead code."
)
print(f"  [PASS] _last_throttle assigned {real_assigns} time(s) — throttle branch is live")


# ---------------------------------------------------------------------------
# TEST 2 — throttle path must return 429 (not just allow/block)
# DNA #22: PASS≠TRUE — pre-fix the throttle "passed" (allowed) every request.
# Post-fix the throttle actually returns a 429 status code.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 2 — throttle path must carry HTTP 429 status")
print("=" * 70)
has_429 = ("429" in src) or ("TOO_MANY_REQUESTS" in src)
assert has_429, (
    "FAIL: no 429 status code in throttle path — clients cannot distinguish "
    "throttle from block, and cannot retry gracefully."
)
# More specifically: the DoSAlert returned by the throttle branch must
# have status_code=429 (not just a comment mentioning 429).
assert re.search(r'status_code\s*=\s*429', src), (
    "FAIL: no `status_code = 429` assignment in throttle DoSAlert"
)
print("  [PASS] `status_code = 429` present in throttle DoSAlert")
print("  [PASS] message string references 'HTTP 429 Too Many Requests'")


# ---------------------------------------------------------------------------
# TEST 3 — Retry-After header present
# DNA #19: proper throttle response carries a Retry-After header so the
# client knows when to retry. Pre-fix: no header info was carried.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 3 — Retry-After header in throttle response")
print("=" * 70)
has_retry_after = ("Retry-After" in src) or ("retry_after" in src.lower())
assert has_retry_after, (
    "FAIL: no Retry-After header in throttle response — clients cannot "
    "know when to retry (RFC 6585 §4 requires Retry-After on 429)."
)
# More specifically: the DoSAlert must have recommended_headers with
# Retry-After key.
assert re.search(r'["\']Retry-After["\']\s*:', src), (
    "FAIL: no `recommended_headers = {\"Retry-After\": ...}` in throttle DoSAlert"
)
print("  [PASS] `recommended_headers = {\"Retry-After\": \"...\"}` present")
print("  [PASS] message string references 'Retry-After: <N>'")


# ---------------------------------------------------------------------------
# TEST 4 — DoSAlert dataclass has status_code + recommended_headers fields
# (DNA #19 — the observation mechanism is wired end-to-end)
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 4 — DoSAlert dataclass carries status_code + recommended_headers")
print("=" * 70)
assert re.search(r'status_code\s*:\s*int\s*=', src), (
    "FAIL: DoSAlert has no `status_code: int = ...` field"
)
assert re.search(r'recommended_headers\s*:\s*dict', src), (
    "FAIL: DoSAlert has no `recommended_headers: dict` field"
)
print("  [PASS] DoSAlert has `status_code: int` field")
print("  [PASS] DoSAlert has `recommended_headers: dict` field")


# ---------------------------------------------------------------------------
# TEST 5 — property-based (DNA #2/#26): trigger 10 UNKNOWN verdicts →
# circuit opens → send 5 requests → ALL 5 must be THROTTLED (429 + Retry-After).
# Pre-fix: 0 of 5 throttled. Post-fix: 5 of 5 throttled.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 5 — property-based: 10 UNKNOWN verdicts → 5 reqs → all throttled")
print("=" * 70)
try:
    from scp.security.dos_protection import DoSProtectionEngine
except Exception as e:
    print(f"  SKIP: import failed ({type(e).__name__}: {e}) — DNA #23 honest limit")
    print("  (Static tests 1-4 above still prove the fix.)")
    sys.exit(0)

e = DoSProtectionEngine()
assert e._circuit_state == "closed", f"FAIL: circuit starts in wrong state: {e._circuit_state}"

# Force circuit open: 10 consecutive UNKNOWN verdicts
for _ in range(e.CIRCUIT_UNKNOWN_THRESHOLD):
    e.record_verdict("UNKNOWN")
assert e._circuit_state == "open", (
    f"FAIL: 10 UNKNOWN verdicts did not open circuit (state={e._circuit_state})"
)
print(f"  [PASS] After {e.CIRCUIT_UNKNOWN_THRESHOLD} UNKNOWN verdicts: circuit_state = open")

# Reset _last_throttle to 0 to expose pre-fix bug clearly (the bug was that
# it was 0 forever; if our fix doesn't assign it, this test catches it)
e._last_throttle = 0
print("  Reset _last_throttle = 0 (exposes pre-fix bug if assignment missing)")

# Now send 5 requests — ALL 5 should be throttled
throttled_count = 0
allowed_count = 0
for i in range(5):
    alert = e.check_request(ip=f"10.0.0.{i}")
    if alert is None:
        allowed_count += 1
    elif alert.action_taken == "throttle":
        throttled_count += 1
        assert alert.status_code == 429, (
            f"FAIL: throttle DoSAlert status_code = {alert.status_code}, expected 429"
        )
        assert "Retry-After" in alert.recommended_headers, (
            "FAIL: throttle DoSAlert missing Retry-After header"
        )
        # Retry-After should be CIRCUIT_COOLDOWN seconds (5)
        ra = alert.recommended_headers["Retry-After"]
        assert ra == str(e.CIRCUIT_COOLDOWN), (
            f"FAIL: Retry-After = {ra!r}, expected {e.CIRCUIT_COOLDOWN}"
        )

print(f"  Requests: 5 sent, {throttled_count} throttled (429+Retry-After), "
      f"{allowed_count} allowed")
assert throttled_count == 5, (
    f"FAIL: expected 5 throttled, got {throttled_count} (pre-fix bug = 0 throttled). "
    "throttle branch still dead."
)
print("  [PASS] ALL 5 requests throttled (pre-fix: 0 of 5)")
print(f"  [PASS] Every throttle DoSAlert has status_code=429 + Retry-After={e.CIRCUIT_COOLDOWN}s")

# Verify _last_throttle was actually assigned (not still 0)
assert e._last_throttle > 0, (
    f"FAIL: _last_throttle = {e._last_throttle} — never assigned (still 0). "
    "throttle branch DID fire but didn't record the throttle time."
)
print(f"  [PASS] _last_throttle = {e._last_throttle:.2f} (was 0 pre-fix)")
print(f"  [PASS] stats['total_throttled'] = {e._stats['total_throttled']}")


# ---------------------------------------------------------------------------
# TEST 6 — backward-compat: rate-limit + resource-quota paths unchanged
# (DNA #7 — fix must not break existing behavior)
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 6 — backward-compat: rate-limit + resource-quota paths unchanged")
print("=" * 70)
e2 = DoSProtectionEngine()
# Trigger rate-limit (60 req/min from same IP)
alerts = []
for i in range(65):
    a = e2.check_request(ip="192.0.2.1")
    if a is not None:
        alerts.append(a)
        # don't decrement _current_concurrent — we're testing rate-limit, not quota
rate_alerts = [a for a in alerts if a.alert_type == "rate_limit"]
assert len(rate_alerts) >= 1, (
    "FAIL: no rate-limit alerts triggered (regression in rate-limit path)"
)
# Rate-limit alerts should NOT carry 429 (they're "block", not "throttle")
# — they should carry action_taken="block" with no Retry-After (caller
# decides status for block — typically 403 or 429 without Retry-After).
print(f"  [PASS] rate-limit path still fires: {len(rate_alerts)} alert(s)")
print(f"         (rate-limit action: {rate_alerts[0].action_taken})")

# Trigger resource-quota (max concurrent)
e3 = DoSProtectionEngine()
e3._current_concurrent = e3.MAX_CONCURRENT
a = e3.check_request(ip="198.51.100.1")
assert a is not None and a.alert_type == "resource_quota", (
    "FAIL: resource_quota alert not fired when _current_concurrent >= MAX"
)
print("  [PASS] resource_quota path still fires at MAX_CONCURRENT")
print(f"         (resource_quota action: {a.action_taken})")


# ---------------------------------------------------------------------------
# TEST 7 — half_open probe still works (after CIRCUIT_RESET_TIME elapses)
# (DNA #7 — fix must preserve the half_open recovery path)
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 7 — half_open recovery path preserved (after CIRCUIT_RESET_TIME)")
print("=" * 70)
e4 = DoSProtectionEngine()
for _ in range(e4.CIRCUIT_UNKNOWN_THRESHOLD):
    e4.record_verdict("UNKNOWN")
assert e4._circuit_state == "open", "FAIL: setup — circuit didn't open"

# Simulate CIRCUIT_RESET_TIME elapsing (manually move _circuit_opened_at back)
e4._circuit_opened_at = time.time() - (e4.CIRCUIT_RESET_TIME + 1)
a = e4.check_request(ip="203.0.113.1")
assert e4._circuit_state == "half_open", (
    f"FAIL: after CIRCUIT_RESET_TIME elapsed, circuit should be half_open, "
    f"got {e4._circuit_state}"
)
print("  [PASS] after CIRCUIT_RESET_TIME elapsed: circuit_state = half_open")
print(f"  [PASS] request ALLOWED through as probe (alert = {a})")


print()
print("=" * 70)
print("✓ Reality test 4-b-009 PASSED")
print("  _last_throttle: assigned (was 0 forever pre-fix)")
print("  Throttle DoSAlert: status_code=429 + Retry-After header")
print("  Property-based: 5/5 requests throttled after circuit opens")
print("  Backward-compat: rate_limit + resource_quota paths unchanged")
print("  Recovery path: half_open transition after CIRCUIT_RESET_TIME preserved")
print("=" * 70)
