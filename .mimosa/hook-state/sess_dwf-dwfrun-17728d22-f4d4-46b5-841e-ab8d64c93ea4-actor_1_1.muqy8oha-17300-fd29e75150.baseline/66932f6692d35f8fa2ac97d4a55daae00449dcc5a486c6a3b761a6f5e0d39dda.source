import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')


from scp.consolidator.consolidator import KnowledgeConsolidator


def test_consolidator_isolated_flow():
    """FA-13: Cover consolidator flow with genuine behavioral execution.

    Verifies entity-attribute extraction for deterministic math expressions,
    structured English and Vietnamese domain patterns, and fact consolidation.
    """
    consolidator = KnowledgeConsolidator()

    # 1. Deterministic math calculation detection
    m_ent, m_attr = consolidator._extract_entity_attribute({"question": "tính 25 * 4"})
    assert m_ent == "math_expression"
    assert m_attr == "deterministic_calculation"

    m_ent2, m_attr2 = consolidator._extract_entity_attribute({"question": "what is 50 / 2"})
    assert m_ent2 == "math_expression"
    assert m_attr2 == "deterministic_calculation"

    # 2. English entity-attribute relation extraction
    ent, attr = consolidator._extract_entity_attribute({"question": "molecular weight of water"})
    assert ent == "water"
    assert attr == "molecular_weight"

    # 3. Fact consolidation pass-through invariant
    facts = [{"fact_id": "f1", "predicate": "capital_of", "object": "France"}]
    consolidated = consolidator.consolidate(facts)
    assert consolidated == facts
