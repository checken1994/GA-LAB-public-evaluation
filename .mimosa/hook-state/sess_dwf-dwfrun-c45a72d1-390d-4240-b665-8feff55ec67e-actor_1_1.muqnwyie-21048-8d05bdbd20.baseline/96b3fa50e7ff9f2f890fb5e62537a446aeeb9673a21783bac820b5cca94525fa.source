import os
import tempfile

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.brain.brain import KnowledgeStore


def test_brain_alias_works():
    """Verify KnowledgeStore alias supports real storage and domain retrieval."""
    with tempfile.TemporaryDirectory() as td:
        store_path = os.path.join(td, "brain_knowledge.jsonl")
        ks = KnowledgeStore(path=store_path)
        assert ks.count() == 0
        
        ks.add(
            domain="science",
            claim="Water boils at 100C at 1 atm",
            verified_answer="100C",
            confidence=0.99,
        )
        assert ks.count() == 1
        assert "science" in ks.domains()
        
        results = ks.get_by_domain("science")
        assert len(results) == 1
        assert results[0]["claim"] == "Water boils at 100C at 1 atm"
        
        stats = ks.stats()
        assert stats["total"] == 1
