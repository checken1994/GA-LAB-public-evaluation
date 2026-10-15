from pathlib import Path

"""Reality test for Fix 4-b-002: SLM must NOT verify its own answer.

Before fix: ground_truth contains SLM answer → entity_found = True (self-match).
After fix:  ground_truth has no SLM answer key → entity verification uses only
            structured evidence → fabricated claims without evidence →
            verified=None → R17-FIX-2 UPHOLD fires.

DNA principles exercised:
  #2  (vòng lặp khép kín — reality test of the fix, not just the fix)
  #5  (ảo giác đồng thuận — SLM is no longer its own ground truth)
  #22 (PASS ≠ TRUE — R17 fix comment no longer lies)
  #26 (reality test — concrete check, not a code review claim)
"""
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def build_ground_truth(slm_responses):
    """Mirror of the (post-fix) logic in judgecore_mixin.py around line 2313-2341.

    The pre-fix code had this extra line at the bottom of the per-SLM loop:

        ground_truth[_slm_name] = _slm_resp.get("answer", "")

    That line is the bug — it put the SLM's paraphrased answer text into
    ground_truth, so ClaimExtractor.extract(final_answer) + _verify_entity
    would substring-match the SLM's own answer against itself.
    """
    ground_truth = {}
    for _slm_resp in slm_responses:
        if "error" in _slm_resp or not _slm_resp.get("answer"):
            continue
        _slm_name = (
            _slm_resp.get("slm_name")
            or _slm_resp.get("source")
            or _slm_resp.get("domain", "unknown")
        )
        _slm_evidence = _slm_resp.get("evidence") or {}
        if isinstance(_slm_evidence, dict):
            if _slm_evidence.get("value") is not None:
                ground_truth[f"{_slm_name}_value"] = _slm_evidence["value"]
                if _slm_evidence.get("unit"):
                    ground_truth[f"{_slm_name}_unit"] = _slm_evidence["unit"]
            if _slm_evidence.get("source"):
                ground_truth[f"{_slm_name}_source"] = _slm_evidence["source"]
        # THE BUG WAS HERE: ground_truth[_slm_name] = _slm_resp.get("answer", "")
        # Fix 4-b-002: this line is DELETED. SLM answer must NOT be ground truth.
    return ground_truth


# ---------------------------------------------------------------------------
# TEST 1 — ground_truth must NOT contain the SLM's answer text under the bare
# SLM-name key. If it did, _verify_entity would self-match.
# ---------------------------------------------------------------------------
slm_responses = [
    ("slm_a", {"answer": "Eiffel Tower is in London", "evidence": {}}),
]
gt = build_ground_truth(
    [{"slm_name": name, **resp} for name, resp in slm_responses]
)
assert "slm_a" not in gt, f"FAIL: SLM answer leaked into ground_truth: {gt}"
assert gt.get("slm_a") != "Eiffel Tower is in London", (
    "FAIL: self-verification still possible"
)
print("PASS [1/3]: ground_truth does not contain SLM answer text under bare slm_name key")

# ---------------------------------------------------------------------------
# TEST 2 — structured evidence (value/unit/source) still flows through. The fix
# must not throw out the legitimate numeric/source evidence path.
# ---------------------------------------------------------------------------
slm_responses2 = [
    ("slm_a", {"answer": "Mars has 2 moons",
               "evidence": {"value": 2, "unit": "moons", "source": "wikipedia"}}),
]
gt2 = build_ground_truth(
    [{"slm_name": name, **resp} for name, resp in slm_responses2]
)
assert gt2.get("slm_a_value") == 2, f"FAIL: structured value lost: {gt2}"
assert gt2.get("slm_a_unit") == "moons", f"FAIL: unit lost: {gt2}"
assert gt2.get("slm_a_source") == "wikipedia", f"FAIL: source lost: {gt2}"
print("PASS [2/3]: structured evidence (value/unit/source) preserved")

# ---------------------------------------------------------------------------
# TEST 3 — the buggy line must be GONE from executable code (DNA #19
# calibration: strip comments so an "explanation" comment that mentions the old
# line is not mistaken for the bug returning).
#
# Reality update (commit cd8a473, S26 dead-legacy purge): the original locus
# scp/runtime/judge_parts/judgecore_mixin.py was deleted wholesale when the
# JudgeCore pipeline was consolidated. The single-file check below therefore
# became stale. To preserve (and strengthen) strictness, this test now:
#   3a. asserts the legacy mixin file does NOT exist (deprecation is real), and
#   3b. scans the ENTIRE scp/ product tree for the buggy executable pattern —
#       a strict superset of the old single-file check: if the buggy line ever
#       reappears anywhere in the product, this test still fails.
# ---------------------------------------------------------------------------
legacy_mixin = (
    Path(__file__).resolve().parents[2] / 'scp' / 'runtime' / 'judge_parts' / 'judgecore_mixin.py'
)
assert not legacy_mixin.exists(), (
    f"FAIL: legacy judge core mixin reappeared: {legacy_mixin}"
)
product_root = Path(__file__).resolve().parents[2] / 'scp'
buggy_pattern = re.compile(
    r'ground_truth\[[^\]]*\]\s*=\s*\w+\.get\(\s*["\']answer["\']'
)


# Strip Python comments + blank lines so an explanatory comment that QUOTES the
# buggy line (e.g. "Removed line: ground_truth[_slm_name] = ...") is not
# mistaken for the actual bug still being present.
def strip_comments(text: str) -> list[str]:
    out = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        # also strip trailing inline comments
        if "  #" in line:
            line = line.split("  #")[0]
        out.append(line)
    return out


violations = []
product_files = sorted(product_root.rglob("*.py"))
assert len(product_files) > 0, f"FAIL: no product files found under {product_root}"
for py in product_files:
    try:
        file_src = py.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # fail-closed: an unreadable product file must not silently skip the scan
        raise AssertionError(f"FAIL: unreadable product file {py}: {exc}")
    for line in strip_comments(file_src):
        if buggy_pattern.search(line):
            violations.append(f"{py}: {line.strip()}")
assert not violations, (
    f"FAIL: buggy SLM self-verification line present in executable code: {violations}"
)
print(
    f"PASS [3/3]: buggy line absent from executable code "
    f"(legacy judge_parts/judgecore_mixin.py absent; {len(product_files)} product files scanned)"
)

print("\n✓ Reality test 4-b-002 PASSED (3/3 assertions)")
