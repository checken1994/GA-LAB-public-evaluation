
from scp.knowledge.knowledge_control_db import KnowledgeControlDB


def test_append_only_status_events(tmp_path):
    db = KnowledgeControlDB(tmp_path / "knowledge_control.sqlite")
    
    # 1. Promote to CURATED
    ev1 = db.record_status_event({
        "knowledge_id": "k1",
        "from_status": "RAW",
        "to_status": "CURATED",
        "reason_codes": ["basic_validation_passed"]
    })
    
    # 2. Promote to VERIFIED
    ev2 = db.record_status_event({
        "knowledge_id": "k1",
        "from_status": "CURATED",
        "to_status": "VERIFIED",
        "reason_codes": ["reality_check_passed"]
    })
    
    # Check history
    history = db.get_knowledge_history("k1")
    assert len(history) == 2
    assert history[0]["event_id"] == ev1
    assert history[0]["to_status"] == "CURATED"
    assert history[1]["event_id"] == ev2
    assert history[1]["to_status"] == "VERIFIED"

