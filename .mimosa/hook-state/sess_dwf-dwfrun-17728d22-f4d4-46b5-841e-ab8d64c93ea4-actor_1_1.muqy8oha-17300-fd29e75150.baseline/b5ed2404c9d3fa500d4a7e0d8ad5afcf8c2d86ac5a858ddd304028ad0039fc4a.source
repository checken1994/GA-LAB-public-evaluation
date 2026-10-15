import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.api.route_profile import (
    resolve_api_profile,
    route_group_enabled,
)


def test_subsystem_api_importable():
    """API router package: verify route profiling and group resolution."""
    assert resolve_api_profile({"SCP_API_PROFILE": "core"}) == "core"
    assert resolve_api_profile({"SCP_API_PROFILE": "standard"}) == "standard"
    assert resolve_api_profile({"SCP_API_PROFILE": "full"}) == "full"
    
    # Verify core profile does not enable high-surface routes
    assert route_group_enabled("chat", "core") is False
    assert route_group_enabled("chat", "standard") is True
    assert route_group_enabled("versioned_admin", "standard") is False
    assert route_group_enabled("versioned_admin", "full") is True


def test_subsystem_api_route_inventory():
    """Verify route controllers expose registered APIRouters."""
    from scp.api.routes.control_routes import router as control_router
    from scp.api.routes.threat_routes import router as threat_router
    
    assert len(control_router.routes) > 0
    assert len(threat_router.routes) > 0
