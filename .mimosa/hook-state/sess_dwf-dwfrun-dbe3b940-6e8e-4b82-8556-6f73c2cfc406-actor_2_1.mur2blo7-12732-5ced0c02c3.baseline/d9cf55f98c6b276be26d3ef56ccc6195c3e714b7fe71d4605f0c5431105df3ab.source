import os
from pathlib import Path

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

from scp.core.fast_learning_engine import FastLearningEngine
from scp.learning.continual import ReplayBuffer


class MockInsightCollector:
    """Mock engine to verify ReplayBuffer routing and tier assignment."""
    def __init__(self):
        self.insights = []

    def record_insight(self, domain: str, question: str, answer: str, source: str, trust_tier: int):
        self.insights.append({
            "domain": domain,
            "question": question,
            "answer": answer,
            "source": source,
            "trust_tier": trust_tier,
        })


def test_learning_isolated_flow(tmp_path: Path):
    """FA-13: Cover learning flow with genuine behavioral execution.

    Verifies ReplayBuffer rating-to-trust_tier mapping (>=4 -> tier 1, <4 -> tier 3),
    graceful degradation without engine, and FastLearningEngine state initialization.
    """
    # 1. Behavioral: ReplayBuffer routes feedback and assigns trust tier correctly
    buf = ReplayBuffer.__new__(ReplayBuffer)
    collector = MockInsightCollector()
    buf._engine = collector

    buf.record_feedback(task_id="t-1", prompt="What is 2+2?", completion="4", rating=5)
    buf.record_feedback(task_id="t-2", prompt="What is 3*3?", completion="9", rating=3)

    assert len(collector.insights) == 2
    assert collector.insights[0]["trust_tier"] == 1
    assert collector.insights[0]["source"] == "feedback-5"
    assert collector.insights[1]["trust_tier"] == 3
    assert collector.insights[1]["source"] == "feedback-3"

    # 2. Behavioral: Graceful degradation when engine is unavailable
    buf_no_engine = ReplayBuffer.__new__(ReplayBuffer)
    buf_no_engine._engine = None
    # Should not raise exception
    buf_no_engine.record_feedback(task_id="t-3", prompt="test", completion="out", rating=1)

    # 3. Behavioral: FastLearningEngine adaptive interval and initial stats
    db_file = tmp_path / "test_learning.db"
    engine = FastLearningEngine(scp_db_path=str(db_file), data_dir=str(tmp_path))
    assert engine.get_adaptive_interval() >= 60
    stats = engine.stats()
    assert "cycles_completed" in stats
    assert stats["cycles_completed"] == 0
