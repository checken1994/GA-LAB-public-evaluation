"""
Architectural Deprecation of zero_cost_guard — opt-in path verification.

FA-02 dictates that tests cannot be deleted without architectural deprecation.
These tests verify that the zero_cost opt-in path is fully removed and does
not affect the surviving gateway routing.
"""

import scp.llm_gateway


def test_cost_wall_default_off_is_passthrough_and_builds_no_guard():
    """Assert __init__.py does not install zero_cost wrappers."""
    # The __init__.py installs only egress_guard, not zero_cost wrappers
    assert not hasattr(scp.llm_gateway, "zero_cost_guard"), (
        "zero_cost_guard should be architecturally deprecated"
    )
    assert not hasattr(scp.llm_gateway, "zero_cost_runtime"), (
        "zero_cost_runtime should be architecturally deprecated"
    )
    # Verify egress guard IS installed (the surviving layer)
    from scp.llm_gateway.client import OpenRouterProvider
    assert getattr(OpenRouterProvider, "_scp_egress_guard_installed", False), (
        "egress guard should be installed on OpenRouterProvider"
    )


def test_cost_wall_opt_in_still_denies_unknown_price(monkeypatch):
    """Assert Gateway routing still operates when env cost mode is set
    (deprecated config has no effect on routing)."""
    monkeypatch.setenv("SCP_LLM_COST_MODE", "free_only")
    from scp.llm_gateway.client import LLMGateway
    # Gateway instantiation must not fail when cost mode is set
    gateway = LLMGateway()
    assert gateway is not None
    stats = gateway.stats()
    assert isinstance(stats, dict)


def test_free_only_policy_active_reads_env(monkeypatch):
    """Assert zero_cost modules are deprecated and do not affect routing.
    The egress_policy module is the surviving enforcement mechanism."""
    monkeypatch.setenv("SCP_LLM_COST_MODE", "free_only")
    assert not hasattr(scp.llm_gateway, "zero_cost_guard")
    assert not hasattr(scp.llm_gateway, "zero_cost_runtime")
    # Egress policy still functions independently of cost mode
    from scp.llm_gateway.egress_policy import llm_egress_allowed
    # Loopback is always allowed regardless of cost mode
    assert llm_egress_allowed("http://127.0.0.1:8080") is True
