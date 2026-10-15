import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scp.contracts.data_class import DataClass
from scp.knowledge.ontology import (
    ALLOWED_STATUS_TRANSITIONS,
    ONTOLOGY_VERSION,
    KnowledgeObject,
    KnowledgeRelation,
    KnowledgeStatus,
    KnowledgeType,
    from_json,
    parse_relation,
    to_json,
    validate_transition,
)

# ==============================================================================
# T02 - KNOWLEDGE ONTOLOGY v1 (26-P0.3)
# ==============================================================================


def _fact() -> KnowledgeObject:
    return KnowledgeObject(
        type="FACT",
        title="provider/model-x prompt price",
        content={"subject": "provider/model-x", "predicate": "prompt_price", "object": 0, "unit": "USD/token"},
    )


def test_all_ontology_types_validate_and_unknown_rejected():
    assert len(KnowledgeType) == 17, "13 formalized + 4 reserved P1 types"
    for type_name in KnowledgeType.__members__:
        obj = KnowledgeObject(type=type_name, title=f"t-{type_name}", content={"k": "v"})
        assert obj.type.value == type_name
    with pytest.raises(ValueError):
        KnowledgeObject(type="EPISTEMOLOGY", title="x", content={"k": "v"})


def test_raw_can_never_jump_to_gold_and_gold_requires_evidence():
    with pytest.raises(ValueError):
        validate_transition(KnowledgeStatus.RAW, KnowledgeStatus.GOLD)
    ladder = ["RAW", "CURATED", "CORROBORATED", "VERIFIED", "GOLD"]
    for current, nxt in zip(ladder, ladder[1:]):
        validate_transition(current, nxt)  # full promotion walk is legal

    gold_without_evidence_raises = pytest.raises(ValueError)
    with gold_without_evidence_raises:
        # GOLD without evidence is rejected AT CONSTRUCTION (the hard edge).
        KnowledgeObject(
            type="FACT", title="gold claim", content={"k": "v"}, status="GOLD",
        )

    gold_ok = KnowledgeObject(
        type="FACT", title="gold claim", content={"k": "v"}, status="GOLD",
        evidence_refs=["ev_0123456789abcdef01234567"],
    )
    assert gold_ok.status is KnowledgeStatus.GOLD


def test_relations_closed_and_invalid_relation_rejected():
    assert {r.value for r in KnowledgeRelation} == {
        "SUPPORTS", "CONTRADICTS", "DERIVED_FROM", "SUPERSEDES", "APPLIES_TO",
        "COUNTEREXAMPLE_OF", "MITIGATES", "CAUSES", "DEPENDS_ON",
    }
    with pytest.raises(ValueError):
        parse_relation("vibes_with")


def test_object_round_trips_json_without_semantics_loss():
    obj = _fact()
    obj.status = "CURATED"
    obj.confidence = 0.8
    obj.independent_lineages = 2
    obj.data_class = DataClass.INTERNAL
    obj.validity = {"observed_at": obj.created_at}

    restored = from_json(to_json(obj))
    assert restored.knowledge_id == obj.knowledge_id
    assert restored.type is obj.type
    assert restored.status is KnowledgeStatus.CURATED
    assert restored.data_class is DataClass.INTERNAL
    assert restored.confidence == 0.8 and restored.independent_lineages == 2
    assert restored.content == obj.content and restored.validity == obj.validity
    assert restored.ontology_version == ONTOLOGY_VERSION


def test_object_rejects_free_text_content_and_bad_confidence():
    with pytest.raises(ValueError):
        KnowledgeObject(type="FACT", title="x", content="just a sentence")
    with pytest.raises(ValueError):
        KnowledgeObject(type="FACT", title="x", content={"k": "v"}, confidence=1.5)
    with pytest.raises(ValueError):
        KnowledgeObject(type="FACT", title="", content={"k": "v"})


def test_status_transition_table_is_closed():
    assert set(ALLOWED_STATUS_TRANSITIONS) == {s.value for s in KnowledgeStatus}
    assert ALLOWED_STATUS_TRANSITIONS["RETIRED"] == set(), "RETIRED is terminal"
