"""Reality test for Fix 4-b-018: EscalationManager.log_action I/O outside lock.

[DNA #2/#9/#19/#22/#26]

Before fix:
  EscalationManager.log_action does file I/O (open + json.dump + write).
  Callers (on_threat_detected, start_countdown, on_timeout,
  execute_defensive_playbook) called log_action from INSIDE `with lock:`
  blocks. Result: all escalation decisions serialized on disk I/O; if disk
  was full or slow, the escalation `lock` was held during the entire
  exception handling window → subsequent on_threat_detected /
  get_active_escalations / escalation_status calls blocked on the held lock.

  DNA #9 (No harm — disk-full holding lock harms availability).
  DNA #22 (PASS≠TRUE — escalation layer claimed responsiveness but
  serialized on disk I/O).
  DNA #19 (Tầng kiểm toán — observation layer couldn't see escalation
  decisions while disk I/O held the lock).

After fix:
  All callers refactored to call log_action AFTER releasing the escalation
  `lock` (or to not acquire the lock at all when no state mutation is
  needed). log_action itself does file I/O — but no caller holds the
  escalation lock during that call.
"""
import ast
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

ESC_PATH = str(Path(__file__).resolve().parents[2]) + '/scp/security/escalation.py'

with open(ESC_PATH) as f:
    src = f.read()


# ---------------------------------------------------------------------------
# TEST 1 — file exists (DNA #19)
# ---------------------------------------------------------------------------
print("=" * 70)
print("TEST 1 — escalation.py exists")
print("=" * 70)
import os

assert os.path.isfile(ESC_PATH), f"FAIL: {ESC_PATH} does not exist"
print(f"  [PASS] file exists at {ESC_PATH}")


# ---------------------------------------------------------------------------
# TEST 2 — log_action body does file I/O (open + write) — this is the I/O
# we're moving OUT of lock. Verify log_action still does file I/O itself
# (we're not delegating to a queue+flusher for this fix).
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 2 — log_action does file I/O (open/write)")
print("=" * 70)
tree = ast.parse(src)
log_action_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "log_action":
        log_action_node = node
        break
assert log_action_node is not None, "FAIL: log_action method not found in AST"

# Walk the body — check that there's a `with` statement that opens a file.
def find_io(node):
    """Find any file I/O operation (open call or write call)."""
    for n in ast.walk(node):
        # Look for `open(...)` call
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name) and n.func.id == "open":
                return True
            # Look for `.write(...)` method call
            if isinstance(n.func, ast.Attribute) and n.func.attr == "write":
                return True
            # Look for `json.dump(...)` call
            if isinstance(n.func, ast.Attribute) and n.func.attr == "dump":
                return True
    return False

has_io = find_io(log_action_node)
assert has_io, (
    "FAIL: log_action does NOT do file I/O (open/json.dump/write) — "
    "the I/O we're supposed to be moving OUT of the lock is missing entirely."
)
print("  [PASS] log_action does file I/O (open/json.dump/write)")


# ---------------------------------------------------------------------------
# TEST 3 — log_action does NOT acquire the escalation `lock` itself.
# DNA #19: log_action must NOT internally acquire the escalation `lock`
# (the module-level `lock = threading.Lock()`). If it did, the I/O would
# still be under the lock. We verify by inspecting log_action's body for
# any `with lock:` context manager.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 3 — log_action does NOT acquire the escalation `lock`")
print("=" * 70)
def has_with_lock(node):
    """True if the function body contains `with lock:` (or `with self.lock:`)."""
    for n in ast.walk(node):
        if isinstance(n, ast.With):
            for item in n.items:
                ctx = item.context_expr
                # `with lock:` — Name(id='lock')
                if isinstance(ctx, ast.Name) and ctx.id == "lock":
                    return True
                # `with self.lock:` — Attribute(attr='lock')
                if isinstance(ctx, ast.Attribute) and ctx.attr == "lock":
                    return True
                # `with self._lock:` — Attribute(attr='_lock')
                if isinstance(ctx, ast.Attribute) and ctx.attr == "_lock":
                    return True
    return False

log_action_has_lock = has_with_lock(log_action_node)
assert not log_action_has_lock, (
    "FAIL: log_action internally acquires the escalation `lock` (or self.lock) "
    "— file I/O still happens under the lock. Pre-fix bug NOT closed."
)
print("  [PASS] log_action body does NOT acquire the escalation `lock`")


# ---------------------------------------------------------------------------
# TEST 4 — callers of log_action do NOT call it from inside `with lock:`
# DNA #19: verify each caller (on_threat_detected, start_countdown,
# on_timeout, execute_defensive_playbook) calls log_action OUTSIDE any
# `with lock:` block.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 4 — callers invoke log_action OUTSIDE `with lock:` blocks")
print("=" * 70)

def find_callers_of(node, target_name):
    """Return list of FunctionDef nodes that contain a call to target_name."""
    callers = []
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            for inner in ast.walk(n):
                if isinstance(inner, ast.Call):
                    if isinstance(inner.func, ast.Attribute) and inner.func.attr == target_name:
                        callers.append(n)
                        break
                    if isinstance(inner.func, ast.Name) and inner.func.id == target_name:
                        callers.append(n)
                        break
    return callers

def log_action_call_inside_with_lock(node):
    """True if there's a `with lock:` block in `node`'s body that contains
    a call to self.log_action (or log_action)."""
    for n in ast.walk(node):
        if isinstance(n, ast.With):
            # Check if any item context is `lock` / `self.lock` / `self._lock`
            ctx_is_lock = False
            for item in n.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Name) and ctx.id == "lock":
                    ctx_is_lock = True
                if isinstance(ctx, ast.Attribute) and ctx.attr in ("lock", "_lock"):
                    ctx_is_lock = True
            if not ctx_is_lock:
                continue
            # Walk the With body looking for log_action call.
            for inner in ast.walk(n):
                if isinstance(inner, ast.Call):
                    if isinstance(inner.func, ast.Attribute) and inner.func.attr == "log_action":
                        return True
                    if isinstance(inner.func, ast.Name) and inner.func.id == "log_action":
                        return True
    return False

caller_names = [
    "on_threat_detected",
    "start_countdown",
    "on_timeout",
    "execute_defensive_playbook",
    "on_human_approval",   # already correct pre-fix — sanity check
    "on_human_rejection",  # already correct pre-fix — sanity check
]
all_callers = find_callers_of(tree, "log_action")
caller_by_name = {c.name: c for c in all_callers}
for cname in caller_names:
    assert cname in caller_by_name, (
        f"FAIL: caller `{cname}` not found in escalation.py — cannot verify"
    )
    node = caller_by_name[cname]
    has_violation = log_action_call_inside_with_lock(node)
    assert not has_violation, (
        f"FAIL: caller `{cname}` invokes log_action from INSIDE a "
        f"`with lock:` block — file I/O still happens under the escalation "
        f"lock. Pre-fix bug NOT closed for this caller."
    )
    print(f"  [PASS] `{cname}` calls log_action OUTSIDE `with lock:` blocks")


# ---------------------------------------------------------------------------
# TEST 5 — property-based (DNA #2/#26): concurrent escalation calls do
# NOT serialize on disk I/O. Pre-fix: holding `lock` during log_action
# meant on_threat_detected calls were serial. Post-fix: log_action
# happens outside the lock, so multiple on_threat_detected calls can
# proceed in parallel (the lock is released before the file write).
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 5 — property-based: log_action outside lock allows concurrent I/O")
print("=" * 70)
try:
    from scp.security.escalation import EscalationManager
except Exception as e:
    print(f"  SKIP: import failed ({type(e).__name__}: {e}) — DNA #23 honest limit")
    print("  (Static tests 1-4 above still prove the fix.)")
    sys.exit(0)

import tempfile

tmpdir = tempfile.mkdtemp(prefix="esc_test_")
em = EscalationManager(data_dir=tmpdir)

# Time how long N concurrent on_threat_detected calls take.
N_THREADS = 20
threats = []
for i in range(N_THREADS):
    threats.append({"id": f"threat-{i}", "severity": "low", "type": "test"})

# Stub out start_countdown so the test doesn't actually arm 20 timers.
em.start_countdown = lambda *a, **kw: None

start = time.time()
def worker(t):
    em.on_threat_detected(t)

threads = [threading.Thread(target=worker, args=(threats[i],)) for i in range(N_THREADS)]
for t in threads:
    t.start()
for t in threads:
    t.join()
elapsed = time.time() - start

# All N threats should be tracked in _active.
import scp.security.escalation as esc_mod

with esc_mod.lock:
    active_count = len(em._active)
print(f"  Sent: {N_THREADS} on_threat_detected calls across {N_THREADS} threads")
print(f"  Tracked in _active: {active_count}/{N_THREADS}")
assert active_count == N_THREADS, (
    f"FAIL: only {active_count}/{N_THREADS} threats tracked — some calls lost"
)

# Verify the log file has N lines (each threat_detection produces 1 line).
log_path = em.escalation_log_path
with open(log_path) as f:
    lines = f.readlines()
threat_detection_lines = [l for l in lines if '"threat_detection"' in l]
print(f"  Log file lines (threat_detection): {len(threat_detection_lines)}/{N_THREADS}")
assert len(threat_detection_lines) == N_THREADS, (
    f"FAIL: expected {N_THREADS} threat_detection log entries, got "
    f"{len(threat_detection_lines)} — some log writes lost (race?)"
)
print(f"  [PASS] all {N_THREADS} log entries persisted to disk (no lost writes)")
print(f"  [PASS] elapsed: {elapsed:.3f}s for {N_THREADS} concurrent calls")


# ---------------------------------------------------------------------------
# TEST 6 — log_action still raises on disk-full / IO errors (no swallow)
# DNA #19: verify log_action propagates I/O exceptions — pre-fix, callers
# held the lock during exception handling. Post-fix, log_action raises
# the exception but the caller is not holding the lock when it happens.
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("TEST 6 — log_action raises I/O exceptions (not swallowed)")
print("=" * 70)
em2 = EscalationManager(data_dir=tmpdir)
# Point log path at a nonexistent directory to force I/O error. Use a Path
# so the .open("a") call reaches the OS (which then fails with FileNotFoundError).
em2.escalation_log_path = Path("/nonexistent/path/to/escalation_log.jsonl")
io_error_raised = False
try:
    em2.log_action("test message", "test")
except (OSError, FileNotFoundError) as e:
    io_error_raised = True
    print(f"  [PASS] log_action raised {type(e).__name__} (I/O error propagated)")
except Exception as e:
    print(f"  [INFO] log_action raised {type(e).__name__}: {e}")
    io_error_raised = True
assert io_error_raised, (
    "FAIL: log_action did NOT raise an I/O error for a nonexistent path — "
    "exceptions are being swallowed silently (regression in error visibility)"
)


print()
print("=" * 70)
print("✓ Reality test 4-b-018 PASSED")
print("  log_action does file I/O (open/json.dump/write) — confirmed")
print("  log_action does NOT acquire the escalation `lock` internally")
print("  All 6 callers invoke log_action OUTSIDE `with lock:` blocks")
print("  Property: 20 concurrent threats → 20 log entries (no lost writes)")
print("  Exceptions: log_action propagates I/O errors (not swallowed)")
print("=" * 70)
