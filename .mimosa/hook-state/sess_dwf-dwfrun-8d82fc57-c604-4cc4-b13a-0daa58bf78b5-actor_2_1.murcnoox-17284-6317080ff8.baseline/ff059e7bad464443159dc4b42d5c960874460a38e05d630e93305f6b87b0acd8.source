#!/usr/bin/env python3
"""Validate the active SCP Future Target baseline, bounded to declared scope.

Authority:
    spec/scp_future_target_manifest.yaml
      = base matrix + one normative overlay

Exit 0 proves only internal target-spec integrity. It does not prove current
implementation, runtime correctness, release readiness, or "no missing pieces".
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "spec" / "scp_future_target_manifest.yaml"
GATES = {f"T{i:02d}" for i in range(12)}
MATURITIES = {f"M{i}" for i in range(7)}
EVIDENCE = {"A", "B", "C", "D"}

PROTECTED_INVARIANTS = {
    "G09_ZERO_COST_HARD_WALL",
    "G17_HUMAN_AUTHORITY_HIGH_CONSEQUENCE",
    "G19_SAME_SHA_RELEASE_EVIDENCE",
    "G23_EXTERNAL_ROOT_OF_TRUST",
    "G25_NO_CLOSED_WORLD_COMPLETENESS_CLAIM",
    "G26_BOUNDED_VERIFICATION",
    "G27_CATASTROPHIC_FORGETTING_GUARD",
    "G29_INDEPENDENT_META_REVIEW",
    "G30_SANDBOX_SESSION_ISOLATION",
    "G31_SERVICE_CONTRACT_READINESS",
    "G32_SAFETY_PRESERVING_OPTIMIZATION",
    "G33_GATEWAY_RESILIENCE_PRIVACY",
    "G34_SKILL_CONTRACT_TRACEABILITY",
}
V402_CONTRACTS = {
    "task_kernel_contract",
    "sandbox_browser_contract",
    "service_runtime_contract",
    "gateway_resilience_contract",
    "performance_safety_contract",
    "recovery_decision_contract",
    "skill_pack_contract",
}
PROTECTED_FORBIDDEN_EDGES = {
    "RawSecret -> ModelPrompt",
    "RawSecret -> Log",
    "InternalSelfModification -> RootOfTrust",
    "KnownInventoryCoverage -> NoMissingPieceClaim",
}


def _yaml(path: Path) -> dict[str, Any]:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level value must be a mapping")
    return value


def _safe_path(root: Path, rel: Any) -> Path:
    if not isinstance(rel, str) or not rel:
        raise ValueError(f"invalid repository-relative path: {rel!r}")
    path = (root / rel).resolve()
    path.relative_to(root.resolve())
    if not path.is_file():
        raise ValueError(f"file not found: {rel}")
    return path


def _blob_sha(root: Path, rel: str, path: Path) -> str:
    """Git blob SHA of the working-tree content, staged exactly as Git would
    stage it (``git hash-object`` applies the path's clean filters).

    The manifest pin must bind the content actually composed, not a committed
    ancestor of it: hashing ``HEAD`` while composing the working tree would let
    uncommitted overlay/base edits pass validation against a stale pin
    (fail-open). On a clean checkout the filtered hash equals the committed
    blob SHA; a dirty tree hashes differently and fails closed. Archives
    without Git fall back to raw byte hashing.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "hash-object", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        sha = proc.stdout.strip()
        if proc.returncode == 0 and len(sha) == 40:
            return sha
    except (OSError, subprocess.SubprocessError):
        pass
    payload = path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()


def _systems(target: dict[str, Any]):
    for family in ("core_systems", "cross_cutting_systems"):
        mapping = target.get(family) or {}
        if isinstance(mapping, dict):
            for system_id, system in mapping.items():
                if isinstance(system, dict):
                    yield family, system_id, system


def _inventory(target: dict[str, Any]):
    caps: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    systems: dict[str, dict[str, Any]] = {}
    for _family, system_id, system in _systems(target):
        systems[system_id] = system
        caps.extend(row for row in system.get("capabilities") or [] if isinstance(row, dict))
        edges.extend(row for row in system.get("cause_effect_edges") or [] if isinstance(row, dict))
    return systems, caps, edges


def _merge_rows(
    system: dict[str, Any],
    delta: dict[str, Any],
    cap_ids: set[str],
    edge_ids: set[str],
    errors: list[str],
) -> None:
    for row in delta.get("cap") or []:
        if not isinstance(row, list) or len(row) != 3:
            errors.append(f"bad capability overlay row: {row!r}")
            continue
        cap_id, maturity, phase = row
        if cap_id in cap_ids:
            errors.append(f"duplicate capability id across base+overlay: {cap_id}")
            continue
        system.setdefault("capabilities", []).append(
            {"id": cap_id, "target_maturity": maturity, "phase": phase}
        )
        cap_ids.add(cap_id)

    for row in delta.get("edge") or []:
        if not isinstance(row, list) or len(row) != 8:
            errors.append(f"bad cause-effect overlay row: {row!r}")
            continue
        edge_id, covers, cause, authority, effects, must_not, evidence, gates = row
        if edge_id in edge_ids:
            errors.append(f"duplicate cause-effect edge id across base+overlay: {edge_id}")
            continue
        system.setdefault("cause_effect_edges", []).append(
            {
                "id": edge_id,
                "covers_capabilities": covers,
                "cause": cause,
                "authority_path": authority,
                "effects": effects,
                "must_not_effect": must_not,
                "evidence_target": evidence,
                "gates": gates,
            }
        )
        edge_ids.add(edge_id)

    forbidden = system.setdefault("forbidden_paths", [])
    if not isinstance(forbidden, list):
        errors.append("system forbidden_paths must be a list")
    else:
        for value in delta.get("forbid") or []:
            if value not in forbidden:
                forbidden.append(value)


def compose_future_target(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    verify_blob_hashes: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Compose manifest base+overlay exactly once and return errors fail-closed."""
    errors: list[str] = []
    manifest_path = manifest_path.resolve()
    root = manifest_path.parents[1]

    try:
        manifest = _yaml(manifest_path)
        composition = manifest["composition"]
        base_meta = composition["base"]
        overlay_meta = composition["overlay"]
        base_path = _safe_path(root, base_meta["path"])
        overlay_path = _safe_path(root, overlay_meta["path"])
        base = _yaml(base_path)
        overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
        if not isinstance(overlay, dict):
            raise ValueError("overlay top-level value must be a mapping")
    except (KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
        return {}, {}, [f"composition load error: {exc}"]

    if manifest.get("status") != "ACTIVE_BASELINE":
        errors.append("manifest.status must be ACTIVE_BASELINE")
    if str(manifest.get("effective_revision")) != "4.0.2":
        errors.append("manifest.effective_revision must be 4.0.2")
    if composition.get("rule") != "BASE_PLUS_OVERLAY_BY_UNIQUE_ID":
        errors.append("composition.rule must be BASE_PLUS_OVERLAY_BY_UNIQUE_ID")
    if str(base.get("spec_revision")) != str(base_meta.get("revision")):
        errors.append("base revision does not match manifest")
    if overlay.get("format") != overlay_meta.get("format"):
        errors.append("overlay format does not match manifest")
    overlay_result = overlay.get("result") or {}
    if str(overlay_result.get("revision")) != str(manifest.get("effective_revision")):
        errors.append("overlay result revision does not match manifest")
    manifest_result = manifest.get("result_contract") or {}
    for overlay_key, manifest_key in (
        ("core", "core_systems"),
        ("cross", "cross_cutting_systems"),
        ("capabilities", "capabilities"),
        ("edges", "cause_effect_edges"),
        ("invariants", "global_invariants"),
        ("skills", "normative_scp_skills"),
    ):
        if overlay_result.get(overlay_key) != manifest_result.get(manifest_key):
            errors.append(
                f"overlay.result.{overlay_key} must equal "
                f"manifest.result_contract.{manifest_key}"
            )

    expected_overlay_base = [
        base_meta.get("path"),
        base_meta.get("blob_sha"),
        str(base_meta.get("revision")),
    ]
    actual_overlay_base = overlay.get("base")
    if isinstance(actual_overlay_base, list) and len(actual_overlay_base) == 3:
        actual_overlay_base = [
            actual_overlay_base[0],
            actual_overlay_base[1],
            str(actual_overlay_base[2]),
        ]
    if actual_overlay_base != expected_overlay_base:
        errors.append("overlay does not bind the exact manifest base")

    if verify_blob_hashes:
        if _blob_sha(root, base_meta["path"], base_path) != base_meta.get("blob_sha"):
            errors.append("base blob SHA does not match manifest")
        if _blob_sha(root, overlay_meta["path"], overlay_path) != overlay_meta.get("blob_sha"):
            errors.append("overlay blob SHA does not match manifest")

    target = copy.deepcopy(base)
    systems, caps, edges = _inventory(target)
    cap_ids = {row.get("id") for row in caps}
    edge_ids = {row.get("id") for row in edges}
    invariant_ids = {
        row.get("id")
        for row in target.get("global_invariants") or []
        if isinstance(row, dict)
    }

    for row in overlay.get("invariants_add") or []:
        if not isinstance(row, list) or len(row) != 2:
            errors.append(f"bad invariant overlay row: {row!r}")
            continue
        invariant_id, rule = row
        if invariant_id in invariant_ids:
            errors.append(f"duplicate invariant id across base+overlay: {invariant_id}")
            continue
        target.setdefault("global_invariants", []).append({"id": invariant_id, "rule": rule})
        invariant_ids.add(invariant_id)

    for system_id, delta in (overlay.get("systems") or {}).items():
        if system_id not in systems or not isinstance(delta, dict):
            errors.append(f"overlay references unknown/invalid system: {system_id}")
            continue
        _merge_rows(systems[system_id], delta, cap_ids, edge_ids, errors)

    shared = target.setdefault("shared_architecture_contracts", {})
    for name, contract in (overlay.get("contracts") or {}).items():
        if name in shared:
            errors.append(f"overlay contract would overwrite base contract: {name}")
        else:
            shared[name] = copy.deepcopy(contract)

    for gate, additions in (overlay.get("test_obligations_add") or {}).items():
        gate_spec = (target.get("test_architecture") or {}).get(gate)
        if not isinstance(gate_spec, dict):
            errors.append(f"overlay references unknown test gate: {gate}")
            continue
        obligations = gate_spec.setdefault("obligations", [])
        for item in additions:
            if item not in obligations:
                obligations.append(item)

    for phase, additions in (overlay.get("phase_targets_add") or {}).items():
        phase_spec = (target.get("phase_coverage_map") or {}).get(phase)
        if not isinstance(phase_spec, dict):
            errors.append(f"overlay references unknown phase target: {phase}")
            continue
        must_establish = phase_spec.setdefault("must_establish", [])
        for item in additions:
            if item not in must_establish:
                must_establish.append(item)

    questions = target.setdefault("open_questions_required", [])
    question_ids = {row.get("id") for row in questions if isinstance(row, dict)}
    for row in overlay.get("open_questions_add") or []:
        if not isinstance(row, list) or len(row) != 2:
            errors.append(f"bad open-question overlay row: {row!r}")
            continue
        question_id, question = row
        if question_id in question_ids:
            errors.append(f"duplicate open-question id: {question_id}")
            continue
        questions.append({"id": question_id, "question": question})
        question_ids.add(question_id)

    delta = overlay.get("coverage_contract_delta") or {}
    coverage = target.setdefault("coverage_contract", {})
    coverage.setdefault("required", {}).update(delta.get("required") or {})
    for source, destination in (
        ("traceability_add", "traceability_rules"),
        ("fail_if_add", "fail_if"),
    ):
        destination_rows = coverage.setdefault(destination, [])
        for item in delta.get(source) or []:
            if item not in destination_rows:
                destination_rows.append(item)

    target["skill_traceability"] = copy.deepcopy(overlay.get("skill_traceability"))
    target["freeze_policy"] = copy.deepcopy(overlay.get("freeze"))
    target["base_spec_revision"] = base.get("spec_revision")
    target["spec_revision"] = (overlay.get("result") or {}).get("revision")

    result = manifest.get("result_contract") or {}
    structural = target.setdefault("structural_inventory", {})
    structural.update(
        {
            "required_core_systems": result.get("core_systems"),
            "required_cross_cutting_systems": result.get("cross_cutting_systems"),
            "required_capabilities": result.get("capabilities"),
            "required_cause_effect_edges": result.get("cause_effect_edges"),
            "required_test_gates": result.get("test_gates"),
            "required_phases": result.get("phases"),
            "required_global_invariants": result.get("global_invariants"),
        }
    )

    summary = target.setdefault("structural_coverage_summary", {})
    summary.update(
        {
            "core_systems_required": result.get("core_systems"),
            "core_systems_declared": result.get("core_systems"),
            "cross_cutting_required": result.get("cross_cutting_systems"),
            "cross_cutting_declared": result.get("cross_cutting_systems"),
            "capabilities_required": result.get("capabilities"),
            "capabilities_declared": result.get("capabilities"),
            "cause_effect_edges_required": result.get("cause_effect_edges"),
            "cause_effect_edges_declared": result.get("cause_effect_edges"),
            "phases_required": result.get("phases"),
            "phases_declared": result.get("phases"),
            "gates_required": result.get("test_gates"),
            "gates_declared": result.get("test_gates"),
            "global_invariants_required": result.get("global_invariants"),
            "global_invariants_declared": result.get("global_invariants"),
        }
    )
    return manifest, target, errors


def _resolves(reference: str, target: dict[str, Any]) -> bool:
    systems, caps, _edges = _inventory(target)
    direct = set(systems) | {row.get("id") for row in caps}
    direct |= {
        row.get("id")
        for row in target.get("global_invariants") or []
        if isinstance(row, dict)
    }
    if reference in direct or reference in target:
        return True
    value: Any = target
    for part in reference.split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    return True


def validate_composed_target(
    manifest: dict[str, Any],
    target: dict[str, Any],
    *,
    root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    expected = manifest.get("result_contract") or {}
    core = target.get("core_systems") or {}
    cross = target.get("cross_cutting_systems") or {}
    phases = ((target.get("phase_model") or {}).get("phases") or {})
    gates = target.get("test_architecture") or {}
    invariants = target.get("global_invariants") or []

    counts = {
        "core_systems": len(core),
        "cross_cutting_systems": len(cross),
        "phases": len(phases),
        "test_gates": len(gates),
        "global_invariants": len(invariants),
    }
    for key, actual in counts.items():
        if actual != expected.get(key):
            errors.append(f"{key} count mismatch: expected={expected.get(key)} actual={actual}")
    if set(gates) != GATES:
        errors.append(f"test gates must be exactly T00-T11, got {sorted(gates)}")

    coverage = target.get("coverage_contract") or {}
    core_required = set(coverage.get("every_core_system_must_have") or [])
    cross_required = set(coverage.get("every_cross_cutting_system_must_have") or [])
    cap_required = set(coverage.get("every_capability_must_have") or ["id", "target_maturity", "phase"])
    edge_required = set(
        coverage.get("every_cause_effect_edge_must_have")
        or ["id", "covers_capabilities", "cause", "authority_path", "effects", "must_not_effect", "evidence_target", "gates"]
    )

    systems, caps, edges = _inventory(target)
    for family, system_id, system in _systems(target):
        required = core_required if family == "core_systems" else cross_required
        missing = required - set(system)
        if missing:
            errors.append(f"{system_id}: missing system fields {sorted(missing)}")

    cap_ids = [row.get("id") for row in caps]
    edge_ids = [row.get("id") for row in edges]
    for name, ids in (("capability", cap_ids), ("cause-effect edge", edge_ids)):
        duplicates = sorted(key for key, count in Counter(ids).items() if key and count > 1)
        if duplicates:
            errors.append(f"duplicate {name} ids: {duplicates}")

    known_caps = {value for value in cap_ids if isinstance(value, str)}
    covered: set[str] = set()
    for cap in caps:
        cap_id = cap.get("id")
        missing = cap_required - set(cap)
        if missing:
            errors.append(f"{cap_id}: missing capability fields {sorted(missing)}")
        if cap.get("target_maturity") not in MATURITIES:
            errors.append(f"{cap_id}: invalid target_maturity {cap.get('target_maturity')!r}")
        if cap.get("phase") not in phases:
            errors.append(f"{cap_id}: invalid phase {cap.get('phase')!r}")

    for edge in edges:
        edge_id = edge.get("id")
        missing = edge_required - set(edge)
        if missing:
            errors.append(f"{edge_id}: missing edge fields {sorted(missing)}")
        covers = edge.get("covers_capabilities")
        if not isinstance(covers, list) or not covers:
            errors.append(f"{edge_id}: covers_capabilities must be non-empty")
        else:
            unknown = set(covers) - known_caps
            if unknown:
                errors.append(f"{edge_id}: covers unknown capabilities {sorted(unknown)}")
            covered.update(set(covers) & known_caps)
        edge_gates = edge.get("gates")
        if not isinstance(edge_gates, list) or not edge_gates:
            errors.append(f"{edge_id}: gates must be non-empty")
        elif set(edge_gates) - GATES:
            errors.append(f"{edge_id}: unknown gates {sorted(set(edge_gates) - GATES)}")
        if edge.get("evidence_target") not in EVIDENCE:
            errors.append(f"{edge_id}: evidence_target must be A/B/C/D")
        for key in ("authority_path", "effects", "must_not_effect"):
            if not isinstance(edge.get(key), list) or not edge.get(key):
                errors.append(f"{edge_id}: {key} must be non-empty")
        if not isinstance(edge.get("cause"), str) or not edge.get("cause"):
            errors.append(f"{edge_id}: cause must be non-empty")

    orphan = sorted(known_caps - covered)
    if orphan:
        errors.append(f"orphan capabilities without cause-effect coverage: {orphan}")

    if len(caps) != expected.get("capabilities"):
        errors.append(f"capabilities count mismatch: expected={expected.get('capabilities')} actual={len(caps)}")
    if len(edges) != expected.get("cause_effect_edges"):
        errors.append(f"cause_effect_edges count mismatch: expected={expected.get('cause_effect_edges')} actual={len(edges)}")

    invariant_ids = [row.get("id") for row in invariants if isinstance(row, dict)]
    duplicate_invariants = sorted(
        key for key, count in Counter(invariant_ids).items() if key and count > 1
    )
    if duplicate_invariants:
        errors.append(f"duplicate invariant ids: {duplicate_invariants}")
    missing_invariants = PROTECTED_INVARIANTS - set(invariant_ids)
    if missing_invariants:
        errors.append(f"missing protected invariants: {sorted(missing_invariants)}")

    shared = target.get("shared_architecture_contracts") or {}
    missing_contracts = V402_CONTRACTS - set(shared)
    if missing_contracts:
        errors.append(f"missing v4.0.2 contracts: {sorted(missing_contracts)}")

    forbidden = set(((target.get("system_dependency_graph") or {}).get("forbidden_edges") or []))
    if PROTECTED_FORBIDDEN_EDGES - forbidden:
        errors.append(
            f"missing protected forbidden dependencies: {sorted(PROTECTED_FORBIDDEN_EDGES - forbidden)}"
        )

    forbidden_verdicts = set(
        ((target.get("completeness_semantics") or {}).get("forbidden_verdicts") or [])
    )
    for verdict in ("ABSOLUTELY_COMPLETE", "NO_MISSING_PIECES", "CURRENT_RUNTIME_COMPLETE_FROM_SPEC"):
        if verdict not in forbidden_verdicts:
            errors.append(f"completeness semantics must forbid {verdict}")

    summary = target.get("structural_coverage_summary") or {}
    summary_expected = {
        "core_systems_required": expected.get("core_systems"),
        "core_systems_declared": expected.get("core_systems"),
        "cross_cutting_required": expected.get("cross_cutting_systems"),
        "cross_cutting_declared": expected.get("cross_cutting_systems"),
        "capabilities_required": expected.get("capabilities"),
        "capabilities_declared": expected.get("capabilities"),
        "cause_effect_edges_required": expected.get("cause_effect_edges"),
        "cause_effect_edges_declared": expected.get("cause_effect_edges"),
        "phases_required": expected.get("phases"),
        "phases_declared": expected.get("phases"),
        "gates_required": expected.get("test_gates"),
        "gates_declared": expected.get("test_gates"),
        "global_invariants_required": expected.get("global_invariants"),
        "global_invariants_declared": expected.get("global_invariants"),
    }
    for key, value in summary_expected.items():
        if summary.get(key) != value:
            errors.append(f"structural_coverage_summary.{key} must be {value}")

    required = coverage.get("required") or {}
    required_expected = {
        "core_systems": expected.get("core_systems"),
        "cross_cutting_systems": expected.get("cross_cutting_systems"),
        "capabilities": expected.get("capabilities"),
        "cause_effect_edges": expected.get("cause_effect_edges"),
        "test_gates": expected.get("test_gates"),
        "phases": expected.get("phases"),
        "global_invariants": expected.get("global_invariants"),
        "skill_contracts": expected.get("normative_scp_skills"),
    }
    for key, value in required_expected.items():
        if required.get(key) != value:
            errors.append(f"coverage_contract.required.{key} must be {value}")

    trace = target.get("skill_traceability") or {}
    skills = trace.get("skills") or {}
    expected_skill_count = expected.get("normative_scp_skills")
    actual_skills = {
        path.parent.name for path in (root / ".agents" / "skills").glob("*/SKILL.md")
    }
    if trace.get("required") != expected_skill_count or len(skills) != expected_skill_count:
        errors.append("skill traceability count does not match manifest")
    if set(skills) != actual_skills:
        errors.append(
            "skill traceability inventory mismatch: "
            f"missing={sorted(actual_skills - set(skills))} stale={sorted(set(skills) - actual_skills)}"
        )
    for skill, row in skills.items():
        if not isinstance(row, list) or len(row) != 2:
            errors.append(f"{skill}: traceability row must be [maps_to, gates]")
            continue
        references, skill_gates = row
        if not isinstance(references, list) or not references:
            errors.append(f"{skill}: structural mapping must be non-empty")
        else:
            for reference in references:
                if not isinstance(reference, str) or not _resolves(reference, target):
                    errors.append(f"{skill}: unresolved structural reference {reference!r}")
        if not isinstance(skill_gates, list) or not skill_gates:
            errors.append(f"{skill}: gate mapping must be non-empty")
        elif set(skill_gates) - GATES:
            errors.append(f"{skill}: unknown gates {sorted(set(skill_gates) - GATES)}")

    freeze = manifest.get("freeze_policy") or {}
    if str(freeze.get("baseline_revision")) != str(manifest.get("effective_revision")):
        errors.append("freeze baseline revision must equal effective revision")
    if not freeze.get("reopen_only_on"):
        errors.append("freeze policy must define bounded reopen triggers")
    if "validator_pass_needs_another_validator_without_new_evidence" not in set(
        freeze.get("must_not_reopen_for") or []
    ):
        errors.append("freeze policy must forbid validator-of-validator recursion without new evidence")

    return errors


def reference_alignment_report(
    target: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, list[str]]:
    """Reference debt is reported, never used to delete target requirements."""
    target_caps = {row.get("id") for row in _inventory(target)[1] if row.get("id")}
    try:
        reference_caps = set(
            (_yaml(root / "spec" / "complete_scp_reference.yaml").get("capabilities") or {}).keys()
        )
    except (OSError, ValueError):
        reference_caps = set()
    return {
        "target_missing_from_reference": sorted(target_caps - reference_caps),
        "reference_not_in_target": sorted(reference_caps - target_caps),
    }


def validate_future_target(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    verify_blob_hashes: bool = True,
) -> list[str]:
    manifest, target, errors = compose_future_target(
        manifest_path, verify_blob_hashes=verify_blob_hashes
    )
    if target:
        errors.extend(
            validate_composed_target(
                manifest,
                target,
                root=manifest_path.resolve().parents[1],
            )
        )
    return errors


def main() -> int:
    manifest_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MANIFEST
    if not manifest_path.is_file():
        print(f"FAIL: manifest not found: {manifest_path}")
        return 1

    manifest, target, errors = compose_future_target(manifest_path)
    if target:
        errors.extend(
            validate_composed_target(
                manifest,
                target,
                root=manifest_path.resolve().parents[1],
            )
        )
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    alignment = reference_alignment_report(
        target, root=manifest_path.resolve().parents[1]
    )
    if alignment["target_missing_from_reference"] or alignment["reference_not_in_target"]:
        print(
            "INFO: REFERENCE_ALIGNMENT_GAP "
            f"target_missing_from_reference={len(alignment['target_missing_from_reference'])} "
            f"reference_not_in_target={len(alignment['reference_not_in_target'])}"
        )

    result = manifest["result_contract"]
    print(
        "OK: SCP Future Target "
        f"{manifest['effective_revision']} valid within declared scope "
        f"({result['capabilities']} capabilities, {result['cause_effect_edges']} edges, "
        f"{result['global_invariants']} invariants, {result['normative_scp_skills']} Skills)"
    )
    print("SCOPE: target-spec integrity only; runtime/release/absolute completeness not derived")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
