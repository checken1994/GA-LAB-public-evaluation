from pathlib import Path

"""Reality test for Fix 4-a-018: _fact_check_retract_queue uses deque (O(1) popleft).

Before fix: Queue was a `list[dict]` with `pop(0)` to evict oldest entries
when queue exceeded 1000. `list.pop(0)` is O(N) — copies every element after
the popped index. Under high retract volume (burst of FALSE claims) the
copy on every eviction becomes a bottleneck on the event loop.

After fix: Queue is a `collections.deque(maxlen=1000)`. `append()` auto-evicts
the oldest entry when full — no explicit `pop()` or `len()` check needed.
popleft on a deque is O(1).

DNA principles exercised:
  #2  (vòng lặp khép kín — reality test of the fix, not just the fix)
  #9  (no harm — O(N) pop stalls the event loop under load)
  #22 (PASS ≠ TRUE — old code "worked" but degraded under load)
  #26 (reality test — AST checks + behavioral queue eviction test)
"""
import os
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Hermetic boot (S17 contract, GAP-09): scp.core.capability_token fail-closes at
# import when SCP_CAPABILITY_SECRET is missing. The portable runner provides an
# isolated env (no repo .env), so generate a random per-run secret here instead
# of reading the repo .env. AST + behavioral assertions below are unchanged.
os.environ.setdefault("SCP_CAPABILITY_SECRET", secrets.token_hex(32))

FILE = str(Path(__file__).resolve().parents[2]) + '/scp/api_server.py'


def test_reality_4_a_018_ast():
    """Verify AST queue declaration uses collections.deque."""
    assert os.path.isfile(FILE), f"FAIL: file missing: {FILE}"
    with open(FILE, encoding="utf-8") as f:
        src = f.read()

    assert "_fact_check_retract_queue" in src
    assert "deque(" in src


def test_fact_check_retract_queue_deque_eviction():
    """Behavioral test: append 1005 items, verify bounded to 1000, oldest evicted, popleft O(1)."""
    from collections import deque

    from scp.api_server import _fact_check_retract_queue

    assert isinstance(_fact_check_retract_queue, deque), (
        f"Expected deque, got {type(_fact_check_retract_queue)}"
    )
    assert _fact_check_retract_queue.maxlen == 1000

    original_items = list(_fact_check_retract_queue)
    try:
        _fact_check_retract_queue.clear()
        for i in range(1005):
            _fact_check_retract_queue.append({"id": i, "claim": f"claim_{i}"})

        # Length is capped at maxlen=1000
        assert len(_fact_check_retract_queue) == 1000

        # Oldest 5 items (0..4) were automatically evicted; oldest remaining is id=5
        assert _fact_check_retract_queue[0]["id"] == 5
        assert _fact_check_retract_queue[-1]["id"] == 1004

        # popleft() is O(1) and removes the oldest remaining item
        popped = _fact_check_retract_queue.popleft()
        assert popped["id"] == 5
        assert len(_fact_check_retract_queue) == 999
        assert _fact_check_retract_queue[0]["id"] == 6
    finally:
        _fact_check_retract_queue.clear()
        _fact_check_retract_queue.extend(original_items)


if __name__ == "__main__":
    test_reality_4_a_018_ast()
    test_fact_check_retract_queue_deque_eviction()
    print("PASS: reality_4-a-018 behavioral test succeeded")
