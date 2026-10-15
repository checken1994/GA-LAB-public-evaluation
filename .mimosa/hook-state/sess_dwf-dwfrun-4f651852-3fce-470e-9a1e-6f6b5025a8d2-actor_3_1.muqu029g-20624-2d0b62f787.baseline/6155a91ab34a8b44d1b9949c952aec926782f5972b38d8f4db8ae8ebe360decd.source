#!/usr/bin/env python3
"""Fail-closed validation that mandatory SCP gates are bound to SCP DNA + skills."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / ".agents" / "skills" / "release-gate-skill-dna-bindings.json"
SKILL_ROOT = ROOT / ".agents" / "skills"
DNA_REFERENCE = SKILL_ROOT / "scp-dna" / "references" / "dna-principles.md"
AGENT_GUIDANCE = ROOT / "AGENTS.md"

REQUIRED_GATE_IDS = {
    "compile_import",
    "unit_integration",
    "semantic_parity",
    "skill_scp_dna_contract",
    "acceptance",
    "fail_closed",
    "bandit_security",
    "mutation",
    "provider_failover_timeout",
    "taskkernel_durability_recovery",
    "reality_tests",
    "bounded_runtime_smoke",
    "dashboard_build_audit",
    "manifest_provenance",
}
REQUIRED_HANDOFF_GATE_IDS = {"main_lineage_authority"}
REQUIRED_DNA_INVARIANTS = {22, 26}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def frontmatter(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return None
    data: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            data[match.group(1)] = match.group(2).strip()
    return data


def dna_principle_numbers(text: str) -> list[int]:
    numbers: list[int] = []
    for line in text.splitlines():
        match = re.match(r"^##\s+(\d+)\.\s+", line)
        if match:
            numbers.append(int(match.group(1)))
    return numbers


def load_profile(path: Path = DEFAULT_PROFILE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_gate_map(
    gate_map: Any,
    *,
    label: str,
    required_ids: set[str],
    errors: list[str],
    referenced_skills: set[str],
) -> tuple[set[str], list[dict[str, Any]]]:
    if not isinstance(gate_map, dict) or not gate_map:
        errors.append(f"{label} must be a non-empty object")
        gate_map = {}

    gate_set = set(gate_map)
    missing = sorted(required_ids - gate_set)
    extra = sorted(gate_set - required_ids)
    if missing:
        errors.append(f"missing mandatory {label}: {', '.join(missing)}")
    if extra:
        errors.append(f"unknown mandatory {label}: {', '.join(extra)}")

    normalized: list[dict[str, Any]] = []
    for gate_id in sorted(gate_map):
        binding = gate_map[gate_id]
        if not isinstance(binding, dict):
            errors.append(f"{gate_id}: binding must be an object")
            continue
        skills = binding.get("skills")
        dna = binding.get("dna")
        if not isinstance(skills, list) or not all(isinstance(item, str) and item for item in skills):
            errors.append(f"{gate_id}: skills must be a non-empty string list")
            continue
        if len(skills) != len(set(skills)):
            errors.append(f"{gate_id}: duplicate skill binding")
        if not skills or skills[0] != "scp-dna":
            errors.append(f"{gate_id}: scp-dna must be the first governing skill")
        if len(set(skills) - {"scp-dna"}) < 1:
            errors.append(f"{gate_id}: at least one specialized SCP skill is mandatory")
        referenced_skills.update(skills)

        if not isinstance(dna, list) or not dna:
            errors.append(f"{gate_id}: dna must be a non-empty integer list")
            dna = []
        elif dna != sorted(set(dna)):
            errors.append(f"{gate_id}: dna references must be sorted and unique")
        if not all(isinstance(number, int) and 1 <= number <= 29 for number in dna):
            errors.append(f"{gate_id}: dna references must be within #1..#29")
        if not REQUIRED_DNA_INVARIANTS.issubset(set(dna)):
            errors.append(f"{gate_id}: DNA #22 and #26 are mandatory")

        normalized.append({"id": gate_id, "required_skills": list(skills), "dna": list(dna)})
    return gate_set, normalized


def validate_contract(path: Path = DEFAULT_PROFILE) -> dict[str, Any]:
    errors: list[str] = []
    if not path.is_file():
        raise FileNotFoundError(f"mandatory SCP Skill/DNA profile missing: {path}")

    profile = load_profile(path)
    if profile.get("schema_version") != "scp-release-gate-skill-dna-v1":
        errors.append("schema_version must be scp-release-gate-skill-dna-v1")

    policy = profile.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be present")
        policy = {}
    if policy.get("mandatory_skill") != "scp-dna":
        errors.append("policy.mandatory_skill must be scp-dna")
    mandatory_dna = policy.get("mandatory_dna_invariants")
    if not isinstance(mandatory_dna, list) or set(mandatory_dna) != REQUIRED_DNA_INVARIANTS:
        errors.append("policy.mandatory_dna_invariants must be exactly [22, 26]")

    referenced_skills: set[str] = set()
    gate_set, normalized_gates = _validate_gate_map(
        profile.get("gates"),
        label="gates",
        required_ids=REQUIRED_GATE_IDS,
        errors=errors,
        referenced_skills=referenced_skills,
    )
    handoff_gate_set, normalized_handoff_gates = _validate_gate_map(
        profile.get("handoff_gates"),
        label="handoff_gates",
        required_ids=REQUIRED_HANDOFF_GATE_IDS,
        errors=errors,
        referenced_skills=referenced_skills,
    )
    if gate_set & handoff_gate_set:
        errors.append("release gate ids and handoff gate ids must be disjoint")

    failure_policy = profile.get("failure_policy")
    if not isinstance(failure_policy, dict):
        errors.append("failure_policy must be present")
        failure_policy = {}
    if failure_policy.get("fix_reality_where_it_fails") is not True:
        errors.append("failure policy must require fixing reality where the test fails")
    if failure_policy.get("harness_fix_must_preserve_or_increase_strictness") is not True:
        errors.append("harness fixes must preserve or increase strictness")
    forbidden = failure_policy.get("forbidden_shortcuts")
    required_forbidden = {
        "delete_test",
        "skip_test",
        "xfail_test",
        "loosen_assertion",
        "lower_threshold",
        "lower_coverage",
        "lower_security_policy",
        "lower_mutation_score",
        "drop_acceptance_gate",
        "ignore_exit_code",
        "fail_open_instead_of_fail_closed",
    }
    if not isinstance(forbidden, list) or not required_forbidden.issubset(set(forbidden)):
        errors.append("failure_policy does not forbid every required test-weakening shortcut")

    skill_evidence: dict[str, dict[str, Any]] = {}
    for skill in sorted(referenced_skills):
        skill_path = SKILL_ROOT / skill / "SKILL.md"
        if not skill_path.is_file():
            errors.append(f"required skill missing: {skill_path.relative_to(ROOT)}")
            continue
        text = skill_path.read_text(encoding="utf-8")
        manifest = frontmatter(text)
        declared = manifest.get("name") if manifest else None
        description = manifest.get("description") if manifest else None
        if manifest is None:
            errors.append(f"skill frontmatter must be closed: {skill_path.relative_to(ROOT)}")
        if declared != skill:
            errors.append(f"skill frontmatter mismatch: expected {skill}, got {declared!r}")
        if not description:
            errors.append(f"skill description missing: {skill_path.relative_to(ROOT)}")
        skill_evidence[skill] = {
            "path": str(skill_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(skill_path),
            "declared_name": declared,
        }

    if not DNA_REFERENCE.is_file():
        errors.append("scp-dna principle reference is missing")
        dna_numbers: list[int] = []
    else:
        dna_text = DNA_REFERENCE.read_text(encoding="utf-8")
        dna_numbers = dna_principle_numbers(dna_text)
        expected = list(range(1, 30))
        if dna_numbers != expected:
            errors.append(
                "scp-dna reference must contain exactly principles 1..29 in order; "
                f"observed={dna_numbers}"
            )

    canonical_profile = str(DEFAULT_PROFILE.relative_to(ROOT)).replace("\\", "/")
    if not AGENT_GUIDANCE.is_file():
        errors.append("AGENTS.md guidance is missing")
    else:
        guidance = AGENT_GUIDANCE.read_text(encoding="utf-8")
        if canonical_profile not in guidance:
            errors.append("AGENTS.md must point to the canonical SCP Skill/DNA binding profile")
        if "scp-dna" not in guidance:
            errors.append("AGENTS.md must require scp-dna")

    try:
        commit = git_head()
    except Exception as exc:  # pragma: no cover - CI/repo contract
        errors.append(f"cannot resolve exact Git HEAD: {exc}")
        commit = "UNKNOWN"

    evidence: dict[str, Any] = {
        "status": "PASS_WITHIN_SCOPE" if not errors else "FAIL",
        "commit": commit,
        "profile": str(path.relative_to(ROOT)).replace("\\", "/"),
        "profile_sha256": sha256_file(path),
        "required_gate_count": len(REQUIRED_GATE_IDS),
        "observed_gate_count": len(gate_set),
        "required_handoff_gate_count": len(REQUIRED_HANDOFF_GATE_IDS),
        "observed_handoff_gate_count": len(handoff_gate_set),
        "dna_principle_count": len(dna_numbers),
        "mandatory_dna_invariants": sorted(REQUIRED_DNA_INVARIANTS),
        "skills": skill_evidence,
        "gate_bindings": normalized_gates,
        "handoff_gate_bindings": normalized_handoff_gates,
        "errors": errors,
    }
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        evidence = validate_contract(args.profile.resolve())
    except Exception as exc:
        evidence = {
            "status": "FAIL",
            "commit": "UNKNOWN",
            "profile": str(args.profile),
            "errors": [f"validator exception: {type(exc).__name__}: {exc}"],
        }

    rendered = json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if evidence.get("status") == "PASS_WITHIN_SCOPE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
