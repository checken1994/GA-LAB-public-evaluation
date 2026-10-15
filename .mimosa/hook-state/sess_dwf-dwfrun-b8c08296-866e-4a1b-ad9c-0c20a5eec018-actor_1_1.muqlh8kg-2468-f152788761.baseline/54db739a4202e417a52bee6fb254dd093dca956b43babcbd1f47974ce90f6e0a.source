import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.verify_scp_future_target import (
    compose_future_target,
    reference_alignment_report,
    validate_composed_target,
    validate_future_target,
)

MANIFEST = ROOT / "spec" / "scp_future_target_manifest.yaml"


def _shipped():
    manifest, target, errors = compose_future_target(MANIFEST)
    assert not errors, f"composition failed: {errors}"
    return manifest, target


def test_shipped_future_target_v402_passes_bounded_validator():
    assert MANIFEST.is_file(), "active future-target manifest must exist"
    errors = validate_future_target(MANIFEST)
    assert not errors, f"SCP Future Target v4.0.2 violates declared contract: {errors}"


def test_effective_target_is_base_plus_overlay_with_frozen_counts():
    manifest, target = _shipped()
    systems = list((target.get("core_systems") or {}).values()) + list(
        (target.get("cross_cutting_systems") or {}).values()
    )
    capabilities = [
        cap
        for system in systems
        for cap in (system.get("capabilities") or [])
    ]
    edges = [
        edge
        for system in systems
        for edge in (system.get("cause_effect_edges") or [])
    ]
    assert str(target["spec_revision"]) == "4.0.2"
    assert len(capabilities) == 138
    assert len(edges) == 67
    assert len(target["global_invariants"]) == 34
    # Frozen against the live .agents/skills/ pack (16 SKILL.md entries,
    # including scp-continuous-operations-loop and typesafe-agent-eval).
    assert len(target["skill_traceability"]["skills"]) == 16
    assert manifest["result_contract"]["runtime_verdict"] == "NOT_DERIVED_FROM_TARGET_SPEC"


def test_validator_rejects_orphan_capability():
    manifest, target = _shipped()
    poisoned = copy.deepcopy(target)
    poisoned["core_systems"]["S01_EXECUTION_OS"]["capabilities"].append(
        {"id": "execution.poisoned_orphan", "target_maturity": "M1", "phase": "P0"}
    )
    errors = validate_composed_target(manifest, poisoned, root=ROOT)
    assert any("orphan capabilities" in error for error in errors), errors


def test_validator_rejects_unknown_gate_on_cause_effect_edge():
    manifest, target = _shipped()
    poisoned = copy.deepcopy(target)
    poisoned["core_systems"]["S01_EXECUTION_OS"]["cause_effect_edges"][0]["gates"] = ["T99"]
    errors = validate_composed_target(manifest, poisoned, root=ROOT)
    assert any("unknown gates" in error for error in errors), errors


def test_validator_rejects_skill_traceability_gap():
    manifest, target = _shipped()
    poisoned = copy.deepcopy(target)
    poisoned["skill_traceability"]["skills"].pop("scp-task-kernel-review")
    errors = validate_composed_target(manifest, poisoned, root=ROOT)
    assert any("skill traceability" in error for error in errors), errors


def test_freeze_policy_blocks_validator_recursion_without_new_evidence():
    manifest, target = _shipped()
    poisoned_manifest = copy.deepcopy(manifest)
    poisoned_manifest["freeze_policy"]["must_not_reopen_for"] = [
        item
        for item in poisoned_manifest["freeze_policy"]["must_not_reopen_for"]
        if item != "validator_pass_needs_another_validator_without_new_evidence"
    ]
    errors = validate_composed_target(poisoned_manifest, target, root=ROOT)
    assert any("validator-of-validator recursion" in error for error in errors), errors


def test_reference_alignment_gap_is_reported_not_used_to_delete_target():
    _manifest, target = _shipped()
    report = reference_alignment_report(target, root=ROOT)
    assert set(report) == {"target_missing_from_reference", "reference_not_in_target"}
    # Current reference is intentionally a smaller semantic inventory than v4.0.2.
    assert report["target_missing_from_reference"]
