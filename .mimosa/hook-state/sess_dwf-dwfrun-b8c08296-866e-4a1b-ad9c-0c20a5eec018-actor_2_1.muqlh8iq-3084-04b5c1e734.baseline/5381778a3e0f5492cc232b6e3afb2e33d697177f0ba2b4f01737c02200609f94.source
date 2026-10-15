import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from fastapi import FastAPI

from scp.observability.otel import configure_fastapi_otel


def test_subsystem_observability_importable():
    """Observability: verify OpenTelemetry configuration on FastAPI application."""
    app = FastAPI()
    status = configure_fastapi_otel(app)
    assert isinstance(status, dict)
    assert "enabled" in status
    assert status["enabled"] is False  # Default when SCP_OTEL_ENABLED=0
