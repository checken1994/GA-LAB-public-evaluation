import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml

from tools.scp_release_verdict import compute

# ==============================================================================
# T00 - HARD RULE: SUITE PASS != COMPLETE SCP ARCHITECTURE
# ==============================================================================
# "T04+T09 23 passed" or "T00 54 passed" proves ONLY that those individual
# tests passed within their asserted scope. It says NOTHING about the
# Complete SCP architecture. Completion requires machine-computed facts:
# every required capability at EVIDENCE_VERIFIED with same-SHA provenance.
# These tests make that rule UNBREAKABLE - no session (human, GLM, Gemini)
# can claim completion while the counts say otherwise.
# ==============================================================================


def _verdict() -> dict:
    binding = yaml.safe_load((ROOT / "spec" / "scp_target_test_coverage.yaml").read_text(encoding="utf-8"))
    reference = yaml.safe_load((ROOT / "spec" / "complete_scp_reference.yaml").read_text(encoding="utf-8"))
    return compute(binding, reference)


def test_green_suite_counts_can_never_satisfy_completion():
    """Even with the whole suite green: completion requires EVIDENCE_VERIFIED
    on EVERY required capability. Anything less keeps the claim FORBIDDEN.
    No skip: the guard must stay executable in BOTH states - a conditional
    skip would make this guard vanish silently exactly when the state flips."""
    v = _verdict()
    completion_satisfied = (
        v["evidence_verified_count"] >= v["required_capabilities"]
        and not v["required_still_missing"]
    )
    if completion_satisfied:
        assert v["complete_scp_claim"] != "FORBIDDEN", (
            "counts say completion but claim still FORBIDDEN - verdict tool is broken"
        )
    else:
        assert v["complete_scp_claim"] == "FORBIDDEN", (
            "required capabilities are not all EVIDENCE_VERIFIED, "
            "so any complete-SCP claim must stay FORBIDDEN"
        )


def test_handoff_and_readme_carry_no_unqualified_complete_scp_claim():
    """Language gate: any 'Complete SCP achieved/done/passed/verified' statement
    in GA.md or README.md MUST carry a within-scope/negation qualifier on the
    same line. Unqualified claims are forbidden (owner rule: PASS is PASS,
    never architecture achievement)."""
    forbidden = re.compile(
        r"complete[\s_-]*scp.{0,60}?(achieved|hoan thien xong|completed|done|passed|verified|production[- ]ready)"
        r"|(achieved|completed|done|passed|verified|production[- ]ready).{0,60}?complete[\s_-]*scp",
        re.IGNORECASE,
    )
    qualifier = re.compile(
        r"within(\s+the\s+declared)?(\s+\w+)?\s+scope|PASS_WITHIN_SCOPE|scope only"
        r"|not\s+proof|chua|khong phai|not yet|NOT\s+COVERAGE_PROOF|FORBIDDEN|khong phai",
        re.IGNORECASE,
    )
    offenders = []
    for doc in (ROOT / "GA.md", ROOT / "README.md"):
        if not doc.is_file():
            continue
        for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
            if forbidden.search(line) and not qualifier.search(line):
                offenders.append(f"{doc.name}:{number}: {line.strip()[:140]}")
    assert not offenders, (
        "Unqualified 'Complete SCP achieved/passed' claim found - every such "
        f"statement must carry an explicit within-scope qualifier: {offenders}"
    )


def test_release_verdict_tool_is_the_single_completion_authority():
    """The completion question may only be answered by the machine verdict
    tool over the binding + reference - never by prose, vibes or pass counts."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "scp_release_verdict.py")],
        capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    assert proc.returncode == 0, f"verdict tool crashed: {proc.stderr[:300]}"
    payload = json.loads(proc.stdout)
    assert payload["suite_pass_means"].startswith("PASS_WITHIN_SCOPE only")
    assert payload["complete_scp_claim"] == "FORBIDDEN" or payload["evidence_verified_count"] >= payload["required_capabilities"]
    assert "snapshot" in payload["allowed_claim_template"] or "SHA" in payload["allowed_claim_template"]
