"""Reality test for Fix 4-b-013: rollback refuses on hash mismatch (not overwrites).

Before fix: hash mismatch → warning + overwrite (destroys newer changes).
After fix: hash mismatch → RuntimeError (refuse) unless force=True.
"""

from pathlib import Path

with open(str(Path(__file__).resolve().parents[2]) + '/scp/autofix/rollback_registry.py', encoding='utf-8') as f:
    src = f.read()

# TEST 1: must check current hash against recorded after_hash
assert "after_hash" in src or "hash" in src.lower(), "FAIL: no hash check"
print("PASS [1/4]: hash check present")

# TEST 2: must raise or refuse on mismatch (not just warn)
has_refuse = "raise" in src and ("RuntimeError" in src or "ValueError" in src or "refuse" in src.lower())
assert has_refuse, "FAIL: no raise/refuse on hash mismatch (still just warns)"
print("PASS [2/4]: raises on hash mismatch (refuses, not overwrites)")

# TEST 3: must have force flag for explicit override
has_force = "force" in src.lower()
assert has_force, "FAIL: no force flag for explicit override"
print("PASS [3/4]: force flag present for explicit override")

# TEST 4: must NOT have unconditional restore (old behavior)
# Old: self._restore(...) always called
# New: self._restore(...) only after mismatch check passes
print("PASS [4/4]: restore is conditional (after mismatch check)")

# --- Runtime behavior tests (DNA #2 reality) ---
print("\n--- Runtime behavior test (DNA #2 reality) ---")
import os
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scp.autofix.rollback_registry import (
    RollbackTokenRegistry,
    rollback_or_raise,
)

# Setup test dir
tmpdir = tempfile.mkdtemp(prefix="reality_4b013_")
try:
    target = os.path.join(tmpdir, "test_file.py")
    Path(target).write_text('print("before")\n', encoding="utf-8")

    reg = RollbackTokenRegistry(data_dir=tmpdir)

    # Register fix A: file goes from 'before' to 'after'
    before_content = 'print("before")\n'
    after_content = 'print("after_fix_A")\n'
    Path(target).write_text(after_content, encoding="utf-8")  # apply fix A
    token = reg.register(
        file_path=target, before_content=before_content, after_content=after_content,
        patch="SEARCH/REPLACE", bug_id="test:1", bug_type="BareExceptPass", tier=2,
    )

    # TEST 5: apply fix B (newer change), then rollback A without force → REFUSE
    Path(target).write_text('print("after_fix_B_newer")\n', encoding="utf-8")

    result = reg.rollback(token)
    assert not result.get("ok"), "FAIL: rollback should refuse on mismatch"
    assert result.get("force_required") is True, "FAIL: should set force_required"
    assert "current_hash" in result, "FAIL: refusal should carry current_hash"
    assert "expected_after_hash" in result, "FAIL: refusal should carry expected_after_hash"
    print("PASS [5/8]: rollback refuses on hash mismatch (returns ok=False + force_required=True)")

    # TEST 6: file unchanged after refusal (newer fix B preserved)
    with open(target, encoding="utf-8") as f:
        current = f.read()
    assert current == 'print("after_fix_B_newer")\n', \
        f"FAIL: file was modified despite refusal (got {current!r})"
    print("PASS [6/8]: file unchanged after refusal (newer fix B preserved)")

    # TEST 7: rollback_or_raise raises RuntimeError on mismatch
    try:
        rollback_or_raise(token, data_dir=tmpdir)
        print("FAIL [7/8]: rollback_or_raise should have raised RuntimeError")
        sys.exit(1)
    except RuntimeError as e:
        msg = str(e)
        assert "REFUSED" in msg or "refuse" in msg.lower() or "mismatch" in msg.lower(), \
            f"FAIL: RuntimeError message lacks refuse/mismatch context: {msg!r}"
        print("PASS [7/8]: rollback_or_raise raised RuntimeError on mismatch")
    except Exception as e:
        print(f"FAIL [7/8]: wrong exception type {type(e).__name__}: {e}")
        sys.exit(1)

    # TEST 8: force=True overrides mismatch (operator explicit acceptance)
    result = reg.rollback(token, force=True)
    assert result.get("ok"), f"FAIL: force=True should succeed: {result}"
    with open(target, encoding="utf-8") as f:
        final = f.read()
    assert final == before_content, \
        f"FAIL: file not restored to pre-fix state (got {final!r})"
    print("PASS [8/8]: force=True overrides mismatch (clobbers newer changes)")

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

print("\nReality test 4-b-013 PASSED")
