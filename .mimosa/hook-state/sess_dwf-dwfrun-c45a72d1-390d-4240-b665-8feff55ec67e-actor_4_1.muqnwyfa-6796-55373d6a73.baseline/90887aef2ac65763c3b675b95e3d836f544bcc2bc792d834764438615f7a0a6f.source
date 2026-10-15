import os
import tempfile

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.knowledge.domain_store import DomainKnowledgeStore


def test_subsystem_knowledge_importable():
    """Knowledge domain store: verify storing, domain querying, and record stats."""
    with tempfile.TemporaryDirectory() as td:
        store = DomainKnowledgeStore(data_dir=td)
        try:
            rec = store.store(
                question="What is the speed of light?",
                answer="299,792,458 m/s",
                domain="physics",
                source="standard_model",
                confidence=1.0,
            )
            assert rec is not None
            assert rec.domain == "physics"
            
            records = store.get_by_domain("physics")
            assert len(records) == 1
            assert records[0].answer == "299,792,458 m/s"
            
            stats = store.stats()
            assert stats["total_records"] == 1
        finally:
            store.close()
