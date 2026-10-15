from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = ROOT / ".agents" / "skills"
DNA_SKILL = SKILLS_ROOT / "scp-dna" / "SKILL.md"
DNA_PRINCIPLES = SKILLS_ROOT / "scp-dna" / "references" / "dna-principles.md"
RELEASE_SKILL = SKILLS_ROOT / "scp-release-evidence-gate" / "SKILL.md"
GATE_BINDINGS = SKILLS_ROOT / "release-gate-skill-dna-bindings.json"
RC_WORKFLOW = ROOT / ".github" / "workflows" / "scp-rc-promotion.yml"
STRICT_AUDIT = ROOT / "scripts" / "run_system_audit_strict.py"

REQUIRED_RELEASE_GATES = {
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
REQUIRED_HANDOFF_GATES = {"main_lineage_authority"}


def _read(path: Path) -> str:
    assert path.is_file(), f"required SCP artifact missing: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> dict[str, str] | None:
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


def _load_bindings() -> dict:
    payload = json.loads(_read(GATE_BINDINGS))
    assert payload.get("schema_version") == "scp-release-gate-skill-dna-v1"
    assert isinstance(payload.get("policy"), dict)
    assert isinstance(payload.get("gates"), dict)
    assert isinstance(payload.get("handoff_gates"), dict)
    return payload


def _assert_binding(gate: str, binding: dict, mandatory_dna: set[int]) -> None:
    skills = binding.get("skills")
    dna = binding.get("dna")
    assert isinstance(skills, list) and len(skills) >= 2, (
        f"{gate}: bind SCP DNA plus at least one domain-specific Skill"
    )
    assert skills[0] == "scp-dna", f"{gate}: scp-dna must be the first governing Skill"
    assert len(skills) == len(set(skills)), f"{gate}: duplicate Skill binding"
    for skill_name in skills:
        skill_path = SKILLS_ROOT / skill_name / "SKILL.md"
        text = _read(skill_path)
        data = _frontmatter(text)
        assert data is not None, f"{gate}: Skill {skill_name} has malformed frontmatter"
        assert data.get("name") == skill_name, f"{gate}: invalid Skill {skill_name}"
        assert data.get("description"), f"{gate}: Skill {skill_name} lacks description"

    assert isinstance(dna, list) and dna, f"{gate}: missing DNA invariants"
    assert dna == sorted(set(dna)), f"{gate}: DNA list must be sorted and unique"
    assert all(isinstance(n, int) and 1 <= n <= 29 for n in dna), (
        f"{gate}: DNA references must be in #1..#29"
    )
    assert mandatory_dna.issubset(dna), (
        f"{gate}: every mandatory gate must include DNA #22 PASS≠TRUE and #26 Reality authority"
    )


def test_every_scp_skill_has_valid_closed_manifest() -> None:
    assert SKILLS_ROOT.is_dir(), ".agents/skills must exist"
    skill_dirs = sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir())
    assert skill_dirs, "SCP skill catalog must not be empty"
    for skill_dir in skill_dirs:
        manifest = skill_dir / "SKILL.md"
        text = _read(manifest)
        data = _frontmatter(text)
        assert data is not None, f"{manifest} must have closed YAML frontmatter"
        assert data.get("name") == skill_dir.name
        assert data.get("description"), f"{manifest} must declare a non-empty description"


def test_scp_dna_is_exactly_29_principles_with_release_critical_invariants() -> None:
    skill = _read(DNA_SKILL)
    principles = _read(DNA_PRINCIPLES)
    assert "29 core principles" in skill
    assert "full 26-principle" not in skill.lower()
    assert "Reality has final authority (DNA #26)" in skill
    assert "PASS only means" in skill
    headings = [int(n) for n in re.findall(r"(?m)^##\s+(\d+)\.\s+", principles)]
    assert headings == list(range(1, 30))
    critical = {
        5: ("lineage", "đồng thuận"),
        22: ("PASS", "Goodhart"),
        26: ("Reality", "quyền cuối cùng"),
        28: ("rollback", "Tier-1 Guard"),
        29: ("Planner", "Judge", "Kernel"),
    }
    for number, needles in critical.items():
        block_match = re.search(rf"(?ms)^##\s+{number}\.\s+.*?(?=^##\s+\d+\.|\Z)", principles)
        assert block_match, f"DNA #{number} block missing"
        block = block_match.group(0)
        for needle in needles:
            assert needle in block, f"DNA #{number} lost invariant {needle!r}"


def test_release_evidence_skill_is_fail_closed_and_reality_grounded() -> None:
    release = _read(RELEASE_SKILL)
    for required in ("Static", "Runtime", "Golden task", "Chaos", "Security", "Reproducibility", "BLOCKED", "Reality"):
        assert required in release, f"release evidence skill lost {required!r}"
    assert "Một gate thiếu evidence là `BLOCKED`" in release


def test_every_mandatory_release_gate_has_domain_skill_and_scp_dna_binding() -> None:
    payload = _load_bindings()
    policy = payload["policy"]
    gates = payload["gates"]
    handoff_gates = payload["handoff_gates"]
    assert set(gates) == REQUIRED_RELEASE_GATES
    assert set(handoff_gates) == REQUIRED_HANDOFF_GATES
    assert policy.get("mandatory_skill") == "scp-dna"
    mandatory_dna = set(policy.get("mandatory_dna_invariants", []))
    assert mandatory_dna == {22, 26}
    for gate, binding in {**gates, **handoff_gates}.items():
        _assert_binding(gate, binding, mandatory_dna)


def test_rc_verdict_cannot_claim_pass_for_an_unbound_gate() -> None:
    rc = _read(RC_WORKFLOW)
    payload = _load_bindings()
    for gate in payload["gates"]:
        marker = f"'{gate}': 'PASS'"
        assert rc.count(marker) >= 2, f"{gate}: RC and main handoff must both record PASS"
    for gate in payload["handoff_gates"]:
        assert f"'{gate}': 'PASS'" in rc


def test_main_merge_requires_explicit_human_approval_and_exact_frozen_sha() -> None:
    rc = _read(RC_WORKFLOW)
    for marker in (
        "approve_main_merge:",
        "github.event_name == 'workflow_dispatch'",
        "inputs.approve_main_merge == true",
        'test "$CURRENT" = "$FROZEN_SHA"',
        'test "$PR_HEAD" = "$FROZEN_SHA"',
        '-f sha="$FROZEN_SHA"',
    ):
        assert marker in rc, f"main promotion lost required guard: {marker}"


def test_customer_handoff_requires_immutable_pr_lineage_and_fresh_main_verification() -> None:
    rc = _read(RC_WORKFLOW)
    for marker in (
        "main-lineage-authority:",
        "github.ref == 'refs/heads/main' && github.event_name == 'push'",
        "needs.main-lineage-authority.result == 'success'",
        "needs: [main-lineage-authority, platform-gates, security-and-durability, manifest-provenance]",
        'test "$(git rev-parse HEAD)" = "${{ github.sha }}"',
        "'main_lineage_authority': 'PASS'",
        "'fresh_full_system_verification': True",
        "'verdict': 'CUSTOMER_HANDOFF_PASS'",
    ):
        assert marker in rc, f"customer handoff lost immutable lineage/fresh-verification invariant: {marker}"
    assert "INTEGRATION_SHA=\"$(gh api" not in rc, (
        "post-merge authority must not compare against a mutable integration branch head"
    )
    # A bot-token merge does not trigger push. Its explicit handoff dispatch
    # must be SHA-bound and independently verify immutable merged-PR lineage.
    assert "gh workflow run scp-rc-promotion.yml --repo '${{ github.repository }}' --ref main" in rc
    assert '-f handoff_merge_sha="$MERGE_SHA"' in rc
    assert 'HANDOFF_MERGE_SHA: ${{ inputs.handoff_merge_sha }}' in rc
    assert 'python tools/verify_main_handoff.py' in rc
    assert "inputs.handoff_merge_sha != ''" in rc


def test_mandatory_release_paths_execute_skill_and_dna_contract() -> None:
    rc = _read(RC_WORKFLOW)
    strict = _read(STRICT_AUDIT)
    for test_path in ("tests/T11_release/test_scp_skill_dna_contract.py", "tests/T11_release/test_scp_test_skill_contract.py"):
        assert test_path in rc, f"RC workflow must execute {test_path} explicitly"
    assert "tools/verify_scp_test_skill_contract.py" in rc
    assert "skill_scp_dna_contract" in rc
    assert "tests/T11_release/test_scp_skill_dna_contract.py" in strict
    assert "skill_scp_dna_contract" in strict
    assert "semantic_parity_contract" in strict
    assert "provider_failover_timeout" in strict
    for provider_test in (
        "tests/T05_gateway/test_provider_failover.py",
        "tests/T05_gateway/test_provider_timeout_recovery.py",
        "tests/T05_gateway/test_llm_egress_policy.py",
        "tests/T05_gateway/test_multi_llm_crosscheck.py",
        "tests/T05_gateway/test_multi_llm_crosscheck_concurrency.py",
        "tests/external_audit/test_cascade.py",
    ):
        assert provider_test in strict, f"strict provider gate lost {provider_test}"
