import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.verify_scp_target_test_coverage import (
    build_effective_coverage,
    load_and_validate,
    validate_coverage_payload,
)

BINDING = ROOT / "spec" / "scp_target_test_coverage.yaml"


def _shipped():
    binding, target, report, errors = load_and_validate(BINDING)
    assert not errors, f"target-test traceability binding is invalid: {errors}"
    return binding, target, report


def test_shipped_target_test_traceability_structure_is_valid():
    assert BINDING.is_file(), "spec/scp_target_test_coverage.yaml must exist"
    _binding, _target, report = _shipped()
    assert report["summary"]["verdict"] == "TRACEABILITY_STRUCTURE_ONLY_NOT_COVERAGE_PROOF"
    assert report["summary"]["coverage_proven"] is False


def test_effective_map_contains_all_138_capabilities_and_67_edges():
    _binding, _target, report = _shipped()
    capabilities = report["capabilities"]
    edges = report["cause_effect_edges"]
    assert len(capabilities) == 138
    assert len(edges) == 67
    assert len({row["target_id"] for row in capabilities}) == 138
    assert len({row["target_id"] for row in edges}) == 67


def test_unclaimed_target_is_explicitly_unproven_not_omitted():
    _binding, _target, report = _shipped()
    rows = {row["target_id"]: row for row in report["capabilities"]}
    row = rows["execution.browser_session_isolation"]
    assert row["status"] == "UNPROVEN"
    assert row["concrete_tests"] == []
    assert row["applicable_gates"] == ["T03", "T08", "T10"]


def test_current_binding_never_turns_test_presence_into_evidence_verified():
    _binding, _target, report = _shipped()
    rows = report["capabilities"] + report["cause_effect_edges"]
    assert not [row for row in rows if row["status"] == "EVIDENCE_VERIFIED"]
    assert report["summary"]["coverage_proven"] is False


def test_validator_rejects_claim_for_unknown_target():
    binding, target, _report = _shipped()
    poisoned = copy.deepcopy(binding)
    poisoned["claims"][0]["target_id"] = "execution.not_in_target"
    errors = validate_coverage_payload(poisoned, target, root=ROOT)
    assert any("unknown target" in error for error in errors), errors


def test_validator_rejects_missing_pytest_node():
    binding, target, _report = _shipped()
    poisoned = copy.deepcopy(binding)
    poisoned["claims"][0]["concrete_tests"] = [
        "tests/T04_kernel/test_kernel_storage.py::test_does_not_exist"
    ]
    errors = validate_coverage_payload(poisoned, target, root=ROOT)
    assert any("pytest node does not exist" in error for error in errors), errors


def test_validator_rejects_test_from_inapplicable_gate():
    binding, target, _report = _shipped()
    poisoned = copy.deepcopy(binding)
    poisoned["claims"][0]["concrete_tests"] = [
        "tests/T00_integrity/test_scp_future_target.py::"
        "test_shipped_future_target_v402_passes_bounded_validator"
    ]
    errors = validate_coverage_payload(poisoned, target, root=ROOT)
    assert any("is not applicable to capability:execution.task_kernel" in error for error in errors), errors


def test_evidence_verified_cannot_be_self_declared_without_provenance():
    binding, target, _report = _shipped()
    poisoned = copy.deepcopy(binding)
    poisoned["claims"][0]["status"] = "EVIDENCE_VERIFIED"
    poisoned["claims"][0]["observed_evidence_level"] = "D"
    poisoned["claims"][0].pop("snapshot_sha", None)
    poisoned["claims"][0].pop("evidence_refs", None)
    errors = validate_coverage_payload(poisoned, target, root=ROOT)
    assert any("requires 40-char snapshot_sha" in error for error in errors), errors
    assert any("requires evidence_refs" in error for error in errors), errors


def test_reverse_mapping_exists_for_every_explicit_concrete_test_claim():
    binding, _target, report = _shipped()
    reverse = report["test_to_targets"]
    for claim in binding["claims"]:
        target_ref = f'{claim["target_kind"]}:{claim["target_id"]}'
        for selector in claim.get("concrete_tests", []):
            assert selector in reverse
            assert target_ref in reverse[selector]


def test_generated_report_is_deterministic_for_same_binding_and_target():
    binding, target, report = _shipped()
    assert build_effective_coverage(binding, target) == report
