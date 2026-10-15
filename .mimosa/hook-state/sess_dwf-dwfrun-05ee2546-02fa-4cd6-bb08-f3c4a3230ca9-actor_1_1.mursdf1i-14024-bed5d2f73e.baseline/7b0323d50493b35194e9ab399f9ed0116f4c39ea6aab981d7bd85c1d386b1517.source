from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PROTECTED = ROOT / "spec" / "protected_invariants.yaml"


def test_target_coverage_authority_is_governance_protected():
    payload = yaml.safe_load(PROTECTED.read_text(encoding="utf-8"))
    entries = {row["id"]: row for row in payload.get("protected") or []}
    integrity = entries.get("test.integrity")
    assert integrity is not None, "test.integrity protection must exist"
    assert integrity.get("policy") == "REQUIRE_GOVERNANCE"
    paths = set(integrity.get("path_patterns") or [])
    required = {
        "tests/**",
        "spec/scp_target_test_coverage.yaml",
        "tools/verify_scp_future_target.py",
        "tools/verify_scp_target_test_coverage.py",
    }
    assert required <= paths, f"target coverage authority escaped governance protection: {sorted(required - paths)}"
