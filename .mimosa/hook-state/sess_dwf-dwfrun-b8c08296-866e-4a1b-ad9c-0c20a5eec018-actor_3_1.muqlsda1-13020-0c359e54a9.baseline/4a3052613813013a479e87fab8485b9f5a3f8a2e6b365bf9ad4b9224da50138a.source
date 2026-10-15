from pathlib import Path

"""Reality test for Fix 4-b-017: 'fix' keyword must NOT bypass falsification rejection.

Before fix: any action_desc containing 'fix' (anywhere, case-insensitive) → bypassed
           action_desc falsification rejection (only PATCH text was checked).
After fix:  'fix' and 'replace' removed from _BUG_DESCRIPTION_WHITELIST — generic
           keywords no longer bypass; only specific bug-type identifiers bypass.

DNA #22 (PASS≠TRUE — WHY "approved" via substring match, didn't actually check).
DNA #19 (Tầng kiểm toán — observation layer blind to patches that match relaxation).
DNA #26 (reality test).
"""

import re

# Read source and check the bypass is removed.
with open(str(Path(__file__).resolve().parents[2]) + '/scp/meta/why_gate.py') as f:
    src = f.read()

# The bypass logic was: `if "fix" in desc_lower for kw in self._BUG_DESCRIPTION_WHITELIST`
# After fix, "fix" and "replace" should NOT be in _BUG_DESCRIPTION_WHITELIST.
# The current code uses `any(kw in desc_lower for kw in self._BUG_DESCRIPTION_WHITELIST)`.
# That alone wouldn't match the strict regex `if "fix" in <word>.lower()` (it's
# `kw in desc_lower`), but the *intent* is to verify the bypass keyword list no
# longer contains "fix" / "replace".

# Strip comment lines (lines starting with optional whitespace + '#') so we
# only inspect actual code.
code_lines = [l for l in src.split("\n") if not l.strip().startswith("#")]
code_section = "\n".join(code_lines)

# Look for any broad `if "fix" in <something>.lower()` pattern — direct bypass.
broad_bypass = re.findall(
    r'if\s+["\']fix["\']\s+in\s+\w+.*lower\(\)',
    code_section,
    re.IGNORECASE,
)
assert not broad_bypass, \
    f"FAIL: broad 'fix' keyword bypass still in code: {broad_bypass}"
print("PASS: no broad 'if \"fix\" in <x>.lower()' bypass in code")

# Check that "fix" and "replace" are NOT in the _BUG_DESCRIPTION_WHITELIST tuple
# literal. Find the whitelist assignment in code and inspect the literal.
wl_match = re.search(
    r'_BUG_DESCRIPTION_WHITELIST\s*=\s*\[([^\]]*)\]',
    code_section,
    re.DOTALL,
)
assert wl_match, "FAIL: _BUG_DESCRIPTION_WHITELIST not found in code section"
wl_literal = wl_match.group(1)
# Extract each quoted string from the whitelist literal.
wl_entries = re.findall(r'["\']([^"\']+)["\']', wl_literal)
print(f"INFO: current whitelist entries = {wl_entries}")

# The bare generic words "fix" and "replace" must NOT be in the whitelist.
assert "fix" not in wl_entries, \
    "FAIL: bare 'fix' keyword still in _BUG_DESCRIPTION_WHITELIST"
assert "replace" not in wl_entries, \
    "FAIL: bare 'replace' keyword still in _BUG_DESCRIPTION_WHITELIST"
print("PASS: bare 'fix' and 'replace' removed from _BUG_DESCRIPTION_WHITELIST")

# A stricter commit-style `startswith("fix:")` pattern is acceptable (allowed).
strict_pattern = re.findall(r'startswith\(["\']fix:["\']\)', code_section)
if strict_pattern:
    print(
        f"PASS: stricter 'fix:' prefix pattern present "
        f"({len(strict_pattern)} occurrences — allowed as stricter alternative)"
    )
else:
    print("PASS: no 'fix' bypass at all (strictest — preferred)")

# Additional functional check: an action_desc like "lower threshold to fix rate
# limit issue" should now NOT match the whitelist (since "fix" was removed) and
# SHOULD therefore be checked against FALSIFICATION_REJECT_PATTERNS — which
# would catch "lower.*threshold" and REJECT. We can't import the module here
# (scp module path setup), so we re-implement the check inline using the
# extracted whitelist + the FALSIFICATION_REJECT_PATTERNS from source.

# Pull FALSIFICATION_REJECT_PATTERNS literal.
fp_match = re.search(
    r'FALSIFICATION_REJECT_PATTERNS\s*=\s*\[([^\]]*)\]',
    code_section,
    re.DOTALL,
)
assert fp_match, "FAIL: FALSIFICATION_REJECT_PATTERNS not found in code"
fp_literal = fp_match.group(1)
fp_patterns = re.findall(r'r"([^"]+)"', fp_literal)

# Simulate: action_desc containing "lower threshold" + "fix" keyword.
test_desc = "lower threshold to fix rate limit issue"
desc_lower = test_desc.lower()

# Should the whitelist bypass fire? No — "fix" no longer in whitelist.
is_bug_fix = any(kw in desc_lower for kw in wl_entries)
assert not is_bug_fix, (
    "FAIL: action_desc containing 'fix' still triggers whitelist bypass "
    f"(matched by: {[kw for kw in wl_entries if kw in desc_lower]})"
)
print("PASS: 'lower threshold to fix rate limit issue' no longer bypasses whitelist")

# Should FALSIFICATION_REJECT_PATTERNS fire now? Yes — "lower.*threshold" matches.
matched_reject = [p for p in fp_patterns if re.search(p, desc_lower)]
assert matched_reject, (
    "FAIL: action_desc 'lower threshold to fix...' did NOT match any "
    "FALSIFICATION_REJECT_PATTERNS — fix-4-b-017 did not actually restore the check."
)
print(
    f"PASS: 'lower threshold to fix rate limit issue' now matches reject patterns: "
    f"{matched_reject} — falsification check restored"
)

print("\n✓ Reality test 4-b-017 PASSED (4/4 assertions)")
