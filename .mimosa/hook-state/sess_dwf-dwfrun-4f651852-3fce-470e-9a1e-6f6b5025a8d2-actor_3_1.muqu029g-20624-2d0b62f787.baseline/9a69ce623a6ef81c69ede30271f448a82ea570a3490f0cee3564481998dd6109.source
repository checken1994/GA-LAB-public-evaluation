from __future__ import annotations

from tools.verify_scp_test_skill_contract import (
    DNA_REFERENCE,
    REQUIRED_DNA_INVARIANTS,
    REQUIRED_GATE_IDS,
    REQUIRED_HANDOFF_GATE_IDS,
    dna_principle_numbers,
    load_profile,
    validate_contract,
)


def test_mandatory_test_skill_contract_is_valid():
    evidence = validate_contract()
    assert evidence["status"] == "PASS_WITHIN_SCOPE", evidence["errors"]
    assert evidence["required_gate_count"] == len(REQUIRED_GATE_IDS)
    assert evidence["observed_gate_count"] == len(REQUIRED_GATE_IDS)
    assert evidence["required_handoff_gate_count"] == len(REQUIRED_HANDOFF_GATE_IDS)
    assert evidence["observed_handoff_gate_count"] == len(REQUIRED_HANDOFF_GATE_IDS)
    assert evidence["dna_principle_count"] == 29
    assert set(evidence["mandatory_dna_invariants"]) == REQUIRED_DNA_INVARIANTS


def test_every_required_gate_binds_dna_and_a_specialized_skill():
    profile = load_profile()
    for gate_map, required in (
        (profile["gates"], REQUIRED_GATE_IDS),
        (profile["handoff_gates"], REQUIRED_HANDOFF_GATE_IDS),
    ):
        assert set(gate_map) == required
        for gate_id, binding in gate_map.items():
            skills = binding["skills"]
            dna = binding["dna"]
            assert skills[0] == "scp-dna", gate_id
            assert set(skills) - {"scp-dna"}, gate_id
            assert REQUIRED_DNA_INVARIANTS <= set(dna), gate_id
            assert dna == sorted(set(dna)), gate_id


def test_scp_dna_reference_is_exactly_29_principles_in_order():
    numbers = dna_principle_numbers(DNA_REFERENCE.read_text(encoding="utf-8"))
    assert numbers == list(range(1, 30))


def test_failure_policy_forbids_green_by_weakening_tests():
    policy = load_profile()["failure_policy"]
    assert policy["fix_reality_where_it_fails"] is True
    assert policy["harness_fix_must_preserve_or_increase_strictness"] is True
    forbidden = set(policy["forbidden_shortcuts"])
    assert {
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
    } <= forbidden
