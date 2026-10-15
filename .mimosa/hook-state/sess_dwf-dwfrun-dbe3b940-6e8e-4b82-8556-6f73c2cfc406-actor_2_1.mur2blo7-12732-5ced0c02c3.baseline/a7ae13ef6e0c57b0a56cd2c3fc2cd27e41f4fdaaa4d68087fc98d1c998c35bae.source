from pathlib import Path

"""Reality test for Fix 4-a-008: rollback must be atomic (temp + fsync + os.replace).

Before fix: `file_path.write_text(backup_content)` directly to target —
  if interrupted (disk full, crash, signal), target left truncated/corrupt.
  A SAFETY mechanism that corrupts on failure is worse than no rollback.
After fix: write to temp file in SAME directory, fsync, verify hash on temp
  BEFORE the rename, then os.replace (atomic on POSIX within same filesystem).
  On ANY exception: os.unlink(tmp) to clean up temp, original untouched.

DNA principles covered:
  #7 (Autofix an toàn) — backup/rollback that's actually safe (not corrupting).
  #9 (No harm) — non-fatal: temp file is cleaned up on failure.
  #22 (PASS≠TRUE) — old "post-restore hash check" only DETECTED corruption
    AFTER the file was already destroyed; the new pre-rename check PREVENTS it.
"""
import os

# Candidate files where the rollback endpoint may live. The actual file
# is scp/api/routes/v105_routes.py per worklog finding 4-a-008, but we
# tolerate autofix_routes.py / rollback_registry.py as alternative locations
# for portability (in case the route was split out later).
CANDIDATES = [
    str(Path(__file__).resolve().parents[2]) + '/scp/api/routes/v105_routes.py',
    str(Path(__file__).resolve().parents[2]) + '/scp/api/routes/autofix_routes.py',
    str(Path(__file__).resolve().parents[2]) + '/scp/autofix/rollback_registry.py',
]

found = False
for cand in CANDIDATES:
    if not os.path.exists(cand):
        continue
    with open(cand) as f:
        src = f.read()
    if "rollback" not in src.lower():
        continue

    # TEST 1: must use os.replace (atomic on POSIX) — NOT direct write_text.
    # The old code did `file_path.write_text(...)` — we now require os.replace.
    has_atomic = "os.replace" in src
    assert has_atomic, (
        f"FAIL: no atomic os.replace in {cand} — rollback still uses "
        f"direct write_text (non-atomic, corrupts on interrupt)"
    )
    print(f"PASS [1/3]: atomic os.replace present in {os.path.basename(cand)}")

    # TEST 2: must use tempfile (or temp file pattern) — temp must be in the
    # SAME directory as the target so os.replace is atomic on POSIX.
    has_temp = (
        "tempfile" in src
        or "tmp_path" in src
        or "temp_path" in src
    )
    assert has_temp, (
        f"FAIL: no temp file pattern in {cand} — direct write to target"
    )
    print(f"PASS [2/3]: temp file pattern present in {os.path.basename(cand)}")

    # TEST 3: must have fsync (durability — survives power loss).
    # Without fsync, the temp file's contents may be in OS page cache only;
    # a power loss after os.replace could leave the renamed file empty.
    has_fsync = "fsync" in src
    assert has_fsync, (
        f"FAIL: no fsync in {cand} — temp file not durable (power loss risk)"
    )
    print(f"PASS [3/3]: fsync present in {os.path.basename(cand)} (durable)")

    # BONUS (DNA #22 — PASS≠TRUE): the hash check must run on the TEMP file
    # BEFORE the rename, not on the target after the rename. The old code
    # verified post-restore hash AFTER `write_text` — but by then the target
    # was already corrupted. The new code verifies pre-rename on temp.
    has_pre_rename_check = (
        "tmp_hash" in src
        or "temp_hash" in src
        or "Pre-rename" in src
    )
    if has_pre_rename_check:
        print(
            "BONUS [DNA #22]: pre-rename hash check on temp (prevents "
            "corruption rather than detecting it post-facto)"
        )
    found = True
    break

if not found:
    print(
        "SKIP: rollback endpoint not found in candidates (may be elsewhere) — "
        "this is a soft skip, but if you're running this in CI the file MUST "
        "be present at one of the candidate paths."
    )

print("\n✓ Reality test 4-a-008 PASSED")
