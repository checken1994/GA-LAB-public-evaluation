from scp.consolidator.consolidator import KnowledgeConsolidator


def test_consolidator_extracts_math_intent():
    kc = KnowledgeConsolidator()
    entity, attr = kc._extract_entity_attribute({"question": "Tính 25 * 4"})
    assert entity == "math_expression"
    assert attr == "deterministic_calculation"

def test_consolidator_extracts_entity_attribute_english():
    kc = KnowledgeConsolidator()
    entity, attr = kc._extract_entity_attribute({"question": "What is the molecular weight of water"})
    assert entity == "water"
    assert attr == "molecular_weight"

def test_consolidator_extracts_entity_attribute_vietnamese():
    kc = KnowledgeConsolidator()
    entity, attr = kc._extract_entity_attribute({"question": "khối lượng phân tử của nước"})
    assert entity == "nước"
    assert attr == "molecular_weight"
