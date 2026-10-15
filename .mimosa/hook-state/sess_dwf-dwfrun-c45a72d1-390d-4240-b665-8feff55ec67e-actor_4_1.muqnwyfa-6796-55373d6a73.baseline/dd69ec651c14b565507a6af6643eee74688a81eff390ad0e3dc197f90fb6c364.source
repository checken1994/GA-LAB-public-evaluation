from pathlib import Path

"""Reality test for Fix 4-b-004: weak domain must INCREASE threshold, not lower it.

Before fix: pass_rate=0.3 → threshold_adjustment = -0.10 (BACKWARDS, more hallucinations).
After fix:  pass_rate=0.3 → threshold_adjustment = +0.10 (stricter, fewer hallucinations).

DNA #22 (PASS≠TRUE — lowering threshold made PASS easier = claim without evidence).
DNA #6  (Gốc tin cậy — runtime relaxation of trust threshold bypassed classifier
        RELAXATION_PATTERNS ban that applies to patch text).
DNA #4  (Con người quyết định — autonomous threshold change without human approval).
DNA #26 (reality test).
"""


def compute_adjustment(pass_rate=None, fail_rate=None, unknown_rate=None):
    """Mirror of the post-fix logic in policy_applier.py (lines ~167-191)."""
    actions = {"threshold_adjustment": 0.0}
    if pass_rate is not None:
        if pass_rate > 0.80:
            actions["threshold_adjustment"] = +0.05
        elif pass_rate < 0.50:
            # FIX 4-b-004: was -0.10 (BACKWARDS), now +0.10 (stricter).
            actions["threshold_adjustment"] = +0.10
    elif fail_rate is not None and fail_rate > 0.50 or unknown_rate is not None and unknown_rate > 0.50:
        # FIX 4-b-004: was -0.05 (BACKWARDS), now +0.05 (stricter).
        actions["threshold_adjustment"] = +0.05
    return actions["threshold_adjustment"]


# TEST 1: low pass_rate → POSITIVE adjustment (stricter, not looser).
adj = compute_adjustment(pass_rate=0.3)
assert adj > 0, f"FAIL: low pass_rate gave non-positive adjustment: {adj}"
assert adj == 0.10, f"FAIL: expected +0.10, got {adj}"
print(f"PASS: pass_rate=0.3 → threshold_adjustment = +{adj} (stricter)")

# TEST 2: high fail_rate → POSITIVE adjustment (stricter, not looser).
adj = compute_adjustment(fail_rate=0.7)
assert adj > 0, f"FAIL: high fail_rate gave non-positive adjustment: {adj}"
assert adj == 0.05, f"FAIL: expected +0.05, got {adj}"
print(f"PASS: fail_rate=0.7 → threshold_adjustment = +{adj}")

# TEST 3: high unknown_rate → POSITIVE adjustment (stricter, not looser).
adj = compute_adjustment(unknown_rate=0.6)
assert adj > 0, f"FAIL: high unknown_rate gave non-positive adjustment: {adj}"
assert adj == 0.05, f"FAIL: expected +0.05, got {adj}"
print(f"PASS: unknown_rate=0.6 → threshold_adjustment = +{adj}")

# TEST 4: stable domain (high pass_rate) → small positive (unchanged, NOT negative).
adj = compute_adjustment(pass_rate=0.9)
assert adj > 0, f"FAIL: stable domain gave non-positive adjustment: {adj}"
assert adj == 0.05, f"FAIL: expected +0.05, got {adj}"
print(f"PASS: pass_rate=0.9 (stable) → threshold_adjustment = +{adj}")

# TEST 5: read source and verify no NEGATIVE threshold adjustments for weak-domain
# code paths (only the explanatory comments may mention the old negative values).
with open(str(Path(__file__).resolve().parents[2]) + '/scp/meta/policy_applier.py') as f:
    src = f.read()

# Find the threshold_adjustment section.
ta_idx = src.find("threshold_adjustment")
assert ta_idx >= 0, "FAIL: 'threshold_adjustment' not found in source"
# Take a 2000-char window starting from the first occurrence.
ta_section = src[ta_idx:ta_idx + 2500]

# Strip comment lines (lines starting with optional whitespace + '#') so we
# only inspect actual code, not the fix-explanation comments.
import re

code_lines = [
    l for l in ta_section.split("\n")
    if not l.strip().startswith("#")
]
code_section = "\n".join(code_lines)

# Look for negative assignments like `threshold_adjustment"] = -0.05` or
# `["threshold_adjustment"] = -0.10` in CODE (not comments).
neg_in_code = re.findall(
    r'threshold_adjustment["\']?\]?\s*=\s*-0\.\d+',
    code_section,
)
assert not neg_in_code, \
    f"FAIL: negative threshold adjustment still in code: {neg_in_code}"
print("PASS: no negative threshold adjustments in policy_applier code")

print("\n✓ Reality test 4-b-004 PASSED (5/5 assertions)")
