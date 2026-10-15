import pytest

from scp.knowledge.benchmark_authority import (
    BenchmarkAuthority,
    BenchmarkRunRecord,
    BenchmarkStatus,
)
from scp.knowledge.learning_db import LearningDB


@pytest.fixture
def db(tmp_path):
    return LearningDB(tmp_path / "test_learning.sqlite")

def test_benchmark_authority(db):
    auth = BenchmarkAuthority(db)
    rec = BenchmarkRunRecord(
        benchmark_id="gsm8k",
        target_capabilities=["reasoning.math"],
        status=BenchmarkStatus.PASSED,
        score=0.95
    )
    b_id = auth.schedule_benchmark(rec)
    assert b_id.startswith("bmr_")
