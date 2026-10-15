import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.runtime.question_router import detect_language, route_question


def test_subsystem_runtime_importable():
    """Runtime judge & router: verify language detection and domain classification."""
    assert detect_language("Hà Nội là thủ đô của Việt Nam") == "vi"
    assert detect_language("Paris is the capital of France") == "en"
    
    # Test intent and domain classification
    decision = route_question("Paris is the capital of France")
    assert decision.domain == "geography"
    assert decision.lane == "LANE_FACTUAL"
    assert decision.confidence > 0.5
