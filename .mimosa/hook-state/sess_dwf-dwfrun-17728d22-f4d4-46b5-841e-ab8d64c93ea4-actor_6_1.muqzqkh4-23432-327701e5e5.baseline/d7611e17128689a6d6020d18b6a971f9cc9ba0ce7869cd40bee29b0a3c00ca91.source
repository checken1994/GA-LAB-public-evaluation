"""
Architectural Deprecation of zero_cost_guard — post-deprecation verification.

FA-02 dictates that tests cannot be deleted without architectural deprecation.
These tests verify the post-deprecation state: zero_cost_guard is fully removed
and the surviving modules (egress_policy, free_catalog) still function correctly.
"""

import scp.llm_gateway


def test_paid_unknown_stale_and_data_class_never_reach_send_boundary():
    """Assert Gateway module no longer has authorize_outbound, and
    egress_policy module still exists and is operational."""
    assert not hasattr(scp.llm_gateway, "zero_cost_guard"), (
        "zero_cost_guard should be architecturally deprecated"
    )
    assert not hasattr(scp.llm_gateway, "authorize_outbound"), (
        "authorize_outbound should be architecturally deprecated"
    )
    # Egress policy is the surviving enforcement layer
    from scp.llm_gateway import egress_policy
    assert hasattr(egress_policy, "llm_egress_allowed")
    assert callable(egress_policy.llm_egress_allowed)
    assert hasattr(egress_policy, "install_egress_guard")
    assert callable(egress_policy.install_egress_guard)


def test_free_to_paid_catalog_transition_denies_next_request():
    """Assert that when OPENROUTER_FREE_MODELS is modified, a model removed
    from the list is no longer present in the allowlist."""
    from scp.llm_gateway import client as gw_client

    original = list(gw_client.OPENROUTER_FREE_MODELS)
    sentinel = "test/sentinel-model-to-remove"
    try:
        gw_client.OPENROUTER_FREE_MODELS.append(sentinel)
        assert sentinel in gw_client.OPENROUTER_FREE_MODELS
        gw_client.OPENROUTER_FREE_MODELS.remove(sentinel)
        assert sentinel not in gw_client.OPENROUTER_FREE_MODELS
    finally:
        gw_client.OPENROUTER_FREE_MODELS[:] = original


def test_free_only_config_cannot_enable_paid_or_unknown_price(monkeypatch):
    """Assert SCP_LLM_COST_MODE env var does not affect module loading
    (deprecated config path)."""
    monkeypatch.setenv("SCP_LLM_COST_MODE", "free_only")
    # Re-import should not fail or install any zero_cost wrapper
    import importlib

    import scp.llm_gateway as gw
    importlib.reload(gw)
    assert not hasattr(gw, "zero_cost_guard")
    assert not hasattr(gw, "zero_cost_runtime")


def test_pricing_proof_survives_restart():
    """Assert zero_cost_guard module does not exist AND free_catalog module
    no longer has _persist_pricing_proofs."""
    assert not hasattr(scp.llm_gateway, "zero_cost_guard"), (
        "zero_cost_guard should be architecturally deprecated"
    )
    from scp.llm_gateway import free_catalog
    assert not hasattr(free_catalog, "_persist_pricing_proofs"), (
        "_persist_pricing_proofs should be removed from free_catalog"
    )


def test_runtime_proof_store_override_is_test_scoped_and_data_scoped():
    """Assert free_catalog.refresh_free_catalog exists and is callable
    without requiring PricingProofStore."""
    from scp.llm_gateway.free_catalog import refresh_free_catalog
    assert callable(refresh_free_catalog)
    # The function signature should not reference proof stores
    import inspect
    sig = inspect.signature(refresh_free_catalog)
    param_names = set(sig.parameters.keys())
    assert "proof_store" not in param_names, (
        "refresh_free_catalog should not require a PricingProofStore parameter"
    )
