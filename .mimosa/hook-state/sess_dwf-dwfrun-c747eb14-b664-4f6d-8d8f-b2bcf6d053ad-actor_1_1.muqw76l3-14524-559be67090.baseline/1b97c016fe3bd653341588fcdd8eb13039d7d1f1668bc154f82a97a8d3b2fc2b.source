import os

import pytest

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.web_control import BrowserSession


def test_subsystem_web_control_importable():
    """Web control: verify BrowserSession URL validation blocks non-http and internal IPs."""
    session = BrowserSession()
    assert session.validate_url("https://example.com") == "https://example.com"
    
    # Rejection of non-http/https
    with pytest.raises(ValueError, match="Only public http/https"):
        session.validate_url("ftp://files.example.com")
        
    # Rejection of internal/private IP
    with pytest.raises(ValueError, match="internal/private IP"):
        session.validate_url("http://169.254.169.254/latest/meta-data")
