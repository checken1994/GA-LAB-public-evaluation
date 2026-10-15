import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.core.capability_token import mint_token, verify_token


def test_subsystem_core_importable():
    """Core business logic: verify capability token issuance and fail-closed verification."""
    token = mint_token(issuer="orchestrator", scope="system.read", capability_level=2)
    assert isinstance(token, str) and len(token) > 20
    
    # Valid token verification
    result = verify_token(token, required_scope="system.read")
    assert result["valid"] is True
    assert result["payload"]["iss"] == "orchestrator"
    assert result["payload"]["scope"] == "system.read"
    assert result["payload"]["cap"] == 2
    
    # Fail-closed check: tampered signature rejected
    tampered = token[:-4] + "ffff"
    tampered_result = verify_token(tampered, required_scope="system.read")
    assert tampered_result["valid"] is False
