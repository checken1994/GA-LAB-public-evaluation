import hashlib
import os
from pathlib import Path

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

from scp.history.semantic_gate import evaluate_candidate


def test_history_isolated_flow(tmp_path: Path):
    """FA-13: Cover history flow with genuine behavioral execution.

    Verifies SemanticGate fail-closed rejections for missing snapshot/hash/path,
    and valid promotion when cryptographic preconditions are met.
    """
    # 1. Fail-closed: missing source snapshot, hash, and non-existent path
    dec_rejected = evaluate_candidate(
        source_path=tmp_path / "nonexistent.py",
        source_snapshot=None,
        expected_source_sha256=None,
        bug_type="syntax",
        bug_line=1,
        patched_source="a = 1",
        semantic_tests_passed=True,
        independent_external_evidence=True,
    )
    assert not dec_rejected.promotion_allowed
    assert "REJECT_NO_SOURCE_SNAPSHOT" in dec_rejected.reasons
    assert "REJECT_NO_EXPECTED_SOURCE_HASH" in dec_rejected.reasons
    assert "REJECT_SOURCE_PATH_MISSING" in dec_rejected.reasons

    # 2. Fail-closed: missing independent external evidence
    test_file = tmp_path / "candidate.py"
    original_code = "def compute():\n    return 1\n"
    test_file.write_text(original_code, encoding="utf-8")
    original_hash = hashlib.sha256(original_code.encode("utf-8")).hexdigest()

    dec_no_evidence = evaluate_candidate(
        source_path=test_file,
        source_snapshot=original_code,
        expected_source_sha256=original_hash,
        bug_type="logic",
        bug_line=2,
        patched_source="def compute():\n    return 2\n",
        semantic_tests_passed=True,
        independent_external_evidence=False,
    )
    assert not dec_no_evidence.promotion_allowed
    assert any("EVIDENCE" in r for r in dec_no_evidence.reasons)

    # 3. Successful promotion: all integrity checks and evidence satisfied
    dec_promoted = evaluate_candidate(
        source_path=test_file,
        source_snapshot=original_code,
        expected_source_sha256=original_hash,
        bug_type="logic",
        bug_line=2,
        patched_source="def compute():\n    return 2\n",
        semantic_tests_passed=True,
        independent_external_evidence=True,
    )
    assert dec_promoted.promotion_allowed
    assert len(dec_promoted.reasons) == 0
