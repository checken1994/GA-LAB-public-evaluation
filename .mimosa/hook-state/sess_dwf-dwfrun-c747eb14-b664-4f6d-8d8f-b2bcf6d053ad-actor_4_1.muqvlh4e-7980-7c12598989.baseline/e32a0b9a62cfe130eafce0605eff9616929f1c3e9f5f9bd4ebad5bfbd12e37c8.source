from pathlib import Path

"""Reality test for Fix 4-b-003: trust root must NOT be forgeable by substring.

Before fix: 'Copyright (c) 2026' anywhere → approved (forgeable).
After fix: only explicit '# HUMAN_APPROVED_BY: name date' at line 1 → approved.

DNA #6 (Gốc tin cậy bên ngoài — trust root must be external & non-forgeable by SCP).
DNA #22 (PASS≠TRUE — substring match was a CLAIM of approval, not verification).
DNA #26 (reality test — every fix must be checked against real behavior).
"""
import os
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

FILE = str(Path(__file__).resolve().parents[2]) + '/scp/meta/external_trust.py'


def test_reality_4_b_003_ast():
    """Verify source contains HUMAN_APPROVED_PATTERN and not old markers tuple."""
    assert os.path.isfile(FILE), f"FAIL: file missing: {FILE}"
    with open(FILE, encoding="utf-8") as f:
        src = f.read()

    assert "HUMAN_APPROVED_PATTERN" in src
    assert "HUMAN_APPROVED_BY" in src


def test_external_trust_human_approved_behavioral():
    """Behavioral test: ExternalTrustRoot enforces strict line-1 human approval marker."""
    from scp.meta.external_trust import ExternalTrustRoot

    trust = ExternalTrustRoot()

    # 1. Copyright alone must NOT pass
    assert not trust._is_constitution_human_approved("# Copyright (c) 2026 SCP Project\ncode = 1\n"), (
        "FAIL: copyright alone approved"
    )

    # 2. Substring in comment must NOT pass
    assert not trust._is_constitution_human_approved("# TODO: HUMAN_APPROVED\ncode = 1\n"), (
        "FAIL: substring in comment approved"
    )

    # 3. Valid line-1 marker MUST pass
    assert trust._is_constitution_human_approved("# HUMAN_APPROVED_BY: alice 2026-01-15\n# constitution body\n"), (
        "FAIL: valid line-1 marker rejected"
    )

    # 4. Marker NOT at line 1 (preceded by non-shebang line) must NOT pass
    assert not trust._is_constitution_human_approved("# other comment\n# HUMAN_APPROVED_BY: alice 2026-01-15\n"), (
        "FAIL: marker on non-first line accepted"
    )

    # 5. Shebang followed by line-1 marker MUST pass
    assert trust._is_constitution_human_approved("#!/usr/bin/env python\n# HUMAN_APPROVED_BY: alice 2026-01-15\n"), (
        "FAIL: shebang followed by valid marker rejected"
    )

    # 6. Invalid date must NOT pass
    assert not trust._is_constitution_human_approved("# HUMAN_APPROVED_BY: alice 2026-13-45\n"), (
        "FAIL: invalid date accepted"
    )

    # 7. Behavioral verification with verify_external() on actual files
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        const_file = root / "meta" / "constitution.py"
        const_file.parent.mkdir(parents=True)

        # Approved constitution file
        const_file.write_text("# HUMAN_APPROVED_BY: auditor 2026-06-01\nprint('safe')\n", encoding="utf-8")
        tr = ExternalTrustRoot(project_root=str(root))
        res = tr.verify_external()
        assert res["constitution_approved"] is True, "Expected constitution to be verified as approved"

        # Tampered constitution file
        const_file.write_text("# Copyright (c) 2026 SCP\nprint('tampered')\n", encoding="utf-8")
        res_tampered = tr.verify_external()
        assert res_tampered["constitution_approved"] is False, "Tampered constitution must NOT be approved"


if __name__ == "__main__":
    test_reality_4_b_003_ast()
    test_external_trust_human_approved_behavioral()
    print("PASS: reality_4-b-003 behavioral test succeeded")
