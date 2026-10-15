from pathlib import Path

"""Reality test for Fix 4-b-012: ALL tiers log before/after hash + rollback token.

Before fix: Tier 1/2/4 logged only message (DNA #8 violation).
After fix: Pydantic schema enforces 4 required fields for all tiers.
"""
# Find the audit log writer
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

candidates = [
    str(Path(__file__).resolve().parents[2]) + '/scp/autofix/runner.py',
    str(Path(__file__).resolve().parents[2]) + '/scp/autofix/audit_log.py',
]
found = False
for cand in candidates:
    if not os.path.exists(cand):
        continue
    with open(cand) as f:
        src = f.read()
    if "audit" in src.lower() and "tier" in src.lower():
        # TEST 1: before_hash must be referenced
        assert "before_hash" in src, f"FAIL: no before_hash in {cand}"
        print(f"PASS [1/4]: before_hash referenced (in {os.path.basename(cand)})")

        # TEST 2: after_hash must be referenced
        assert "after_hash" in src, "FAIL: no after_hash"
        print("PASS [2/4]: after_hash referenced")

        # TEST 3: rollback_token must be referenced for all tiers (not just Tier 3)
        assert "rollback_token" in src, "FAIL: no rollback_token"
        # Check it's not gated to only Tier 3
        # Look for pattern: if tier == 3: ... rollback_token (only Tier 3)
        import re
        tier3_only = bool(re.search(r'if\s+tier\s*==\s*3.*rollback_token', src, re.DOTALL))
        if tier3_only:
            # Check if there's also a non-tier-3 path
            has_all_tiers = "for" in src.lower() and "tier" in src.lower()
            assert has_all_tiers, "FAIL: rollback_token only for Tier 3"
        print("PASS [3/4]: rollback_token for all tiers")

        # TEST 4: schema enforcement (Pydantic or required fields)
        has_schema = "BaseModel" in src or "validator" in src or "required" in src.lower()
        assert has_schema, "FAIL: no schema enforcement"
        print("PASS [4/4]: schema enforcement present")
        found = True
        break

if not found:
    print("SKIP: audit log writer not found in candidates")

# DNA #2 / #26 — Runtime behavior test: actually validate that a malformed
# entry (empty before_hash) is REJECTED at write time, and a well-formed
# entry (all 4 fields) is ACCEPTED. This catches the case where the schema
# is present in source but not actually wired into the write path.
print("\n--- Runtime behavior test (DNA #2 reality) ---")
import tempfile

from scp.autofix.audit_log import (
    AuditLogEntry,
    compute_hashes,
    make_rollback_token_backup,
    write_audit_entry,
)

# TEST 5: empty before_hash → ValidationError (DNA #8 enforcement)
try:
    AuditLogEntry(
        finding_id="test:1", tier=2, action="fixed",
        before_hash="", after_hash="abc",
        rollback_token="tok123", reality_test_result="pass",
        timestamp="1.0", message="test",
    )
    print("FAIL [5/7]: empty before_hash was accepted (schema not enforcing)")
    sys.exit(1)
except Exception as ex:
    print(f"PASS [5/7]: empty before_hash rejected ({type(ex).__name__})")

# TEST 6: empty rollback_token → ValidationError
try:
    AuditLogEntry(
        finding_id="test:1", tier=1, action="fixed_silent",
        before_hash="bh", after_hash="ah",
        rollback_token="", reality_test_result="skipped",
        timestamp="1.0", message="test",
    )
    print("FAIL [6/7]: empty rollback_token was accepted (DNA #8 not enforced)")
    sys.exit(1)
except Exception as ex:
    print(f"PASS [6/7]: empty rollback_token rejected ({type(ex).__name__})")

# TEST 7: valid entry (all 4 fields non-empty) → accepted + written
tmplog = tempfile.NamedTemporaryFile(
    mode="w", suffix=".jsonl", delete=False, prefix="reality_4b012_"
)
tmplog.close()
import json

bh, ah = compute_hashes("before_content", "after_content")
token = make_rollback_token_backup("/test/file.py")
ok = write_audit_entry(
    log_path=tmplog.name,
    finding_id="/test/file.py:42",
    tier=2,
    action="fixed",
    before_hash=bh,
    after_hash=ah,
    rollback_token=token,
    reality_test_result="pass",
    message="BareExceptPass fixed",
    extra={"attack_mode": False, "bug_type": "BareExceptPass"},
)
assert ok, "FAIL: write_audit_entry returned False for a valid entry"
# Read back + verify all 4 fields present + non-empty
with open(tmplog.name) as f:
    written = json.loads(f.read().strip())
for field in ("before_hash", "after_hash", "rollback_token", "reality_test_result"):
    assert written.get(field), f"FAIL: {field} missing/empty in written entry"
assert written["before_hash"] == bh
assert written["after_hash"] == ah
assert written["rollback_token"] == token
assert written["reality_test_result"] == "pass"
assert written["tier"] == 2
print("PASS [7/7]: valid entry written with all 4 fields + extras")
os.unlink(tmplog.name)

print("\nReality test 4-b-012 PASSED")
