import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.prediction.predictive import QuestionGenerator


def test_subsystem_prediction_importable():
    """Prediction engine: verify question generator transforms financial & crypto feeds."""
    generator = QuestionGenerator()
    data = {
        "crypto": [{"coin": "bitcoin", "price": 60000}],
        "fx": {"rates": {"EUR": 0.92}},
    }
    questions = generator.generate(data)
    assert len(questions) >= 2
    domains = {q["domain"] for q in questions}
    assert "crypto" in domains
    assert "finance" in domains
