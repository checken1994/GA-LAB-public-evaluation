import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.benchmark.benchmark_suite import BENCHMARK_TASKS
from scp.benchmark.question_generator import generate_random_questions


def test_subsystem_benchmark_importable():
    """Benchmark engine: verify deterministic question generation and benchmark catalog."""
    qs, attacks = generate_random_questions(
        num_math=2, num_geography=2, num_ambiguous=1, num_attacks=1, seed=42
    )
    assert len(qs) == 5
    assert len(attacks) == 1
    assert "question" in qs[0]
    assert "expected_answer" in qs[0]


def test_subsystem_benchmark_task_catalog():
    """Verify configured benchmark tasks."""
    assert "mmlu" in BENCHMARK_TASKS
    assert "gsm8k" in BENCHMARK_TASKS
    assert "codegen" in BENCHMARK_TASKS
