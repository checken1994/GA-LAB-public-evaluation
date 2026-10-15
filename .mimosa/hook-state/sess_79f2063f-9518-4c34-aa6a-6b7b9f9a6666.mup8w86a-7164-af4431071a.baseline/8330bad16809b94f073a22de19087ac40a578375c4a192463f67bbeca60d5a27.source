import os

import pytest

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.security.url_safety import ALLOWED_SCHEMES, validate_url


def test_subsystem_security_importable():
    """Security layer: verify zero-trust SSRF validation and URL scheme allowlisting."""
    # Valid external URL
    parsed = validate_url("https://example.com/api", allow_internal=True)
    assert parsed.scheme == "https"
    assert "https" in ALLOWED_SCHEMES
    
    # Scheme rejection
    with pytest.raises(ValueError, match="not in allowlist"):
        validate_url("ftp://example.com/files")
    
    # SSRF & Private IP rejection
    with pytest.raises(ValueError, match="internal/private IP"):
        validate_url("http://169.254.169.254/latest/meta-data")
